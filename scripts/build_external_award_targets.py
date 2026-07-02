import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, "scripts")

from apply_monthly_delta import (
    extract_rows,
    has_contractor,
    load_json,
    record_key,
)


DEFAULT_SEGMENT_KEYWORDS = [
    "fotovoltaico",
    "agrivoltaico",
    "rinnovabile",
    "energia",
    "elettrico",
    "bess",
    "battery",
    "data center",
    "impianto",
    "polo",
    "rifiuti",
    "depurazione",
    "infrastruttura",
    "strada",
    "ferrovia",
    "rete",
]


def clean(value):
    return str(value or "").strip()


def normalize_space(value):
    return re.sub(r"\s+", " ", clean(value))


def to_float(value):
    text = clean(value)
    text = text.replace("€", "")
    text = text.replace("&euro;", "")
    text = text.replace(" ", "")

    if not text:
        return 0.0

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def first_value(record, fields):
    for field in fields:
        value = clean(record.get(field))
        if value:
            return value
    return ""


def value_eur(record):
    return to_float(
        first_value(
            record,
            [
                "value_eur",
                "project_value",
                "value",
                "amount",
                "importo",
            ],
        )
    )


def record_text(record):
    parts = [
        record.get("title"),
        record.get("description"),
        record.get("category"),
        record.get("primary_segment"),
        record.get("segment"),
        record.get("client"),
        record.get("municipality"),
        record.get("province"),
        record.get("region"),
    ]

    return " ".join(clean(part).lower() for part in parts)


def has_relevant_segment(record, keywords):
    text = record_text(record)

    return any(
        keyword.lower() in text
        for keyword in keywords
        if keyword.strip()
    )


def contractor_present(record):
    if has_contractor(record):
        return True

    for field in [
        "contractors",
        "contractors_summary",
        "contractor_name",
        "aggiudicatario",
        "external_contractor_summary",
    ]:
        value = clean(record.get(field))
        if value and value.upper() not in {
            "N.D.",
            "ND",
            "N/A",
            "NON DISPONIBILE",
        }:
            return True

    awards = record.get("awards")

    if isinstance(awards, list):
        for award in awards:
            if not isinstance(award, dict):
                continue

            for field in [
                "contractors",
                "contractor_name",
                "aggiudicatario",
            ]:
                if clean(award.get(field)):
                    return True

    return False


def record_priority(record, keywords):
    score = 0.0

    value = value_eur(record)

    if value > 0:
        score += min(60.0, math.log10(value + 1) * 8)

    level = clean(record.get("anac_level")).lower()

    if level == "technical":
        score += 18
    elif level == "review":
        score += 12
    elif level == "small":
        score += 8
    elif level == "none":
        score += 4

    badges = record.get("change_badges")

    if isinstance(badges, list):
        badge_text = " ".join(clean(x).lower() for x in badges)

        if "nuovo" in badge_text:
            score += 10

        if "aggiornat" in badge_text:
            score += 7

        if "anac" in badge_text:
            score += 5

    if has_relevant_segment(record, keywords):
        score += 12

    if clean(record.get("cup")):
        score += 10

    if first_value(record, ["client", "subject", "owner"]):
        score += 3

    return round(score, 2)


def quoted(value):
    value = normalize_space(value)
    return f'"{value}"' if value else ""


def compact_title(title, max_words=8):
    words = normalize_space(title).split()

    if len(words) <= max_words:
        return " ".join(words)

    return " ".join(words[:max_words])


def generate_queries(record):
    cup = clean(record.get("cup"))
    cig = clean(record.get("cig"))
    title = compact_title(record.get("title"))
    client = normalize_space(
        first_value(record, ["client", "subject", "owner"])
    )

    queries = []

    def add(query_type, query):
        query = normalize_space(query)

        if not query:
            return

        if query not in [item["query"] for item in queries]:
            queries.append(
                {
                    "query_type": query_type,
                    "query": query,
                }
            )

    if cup:
        add("cup_exact", quoted(cup))
        add("cup_cig", f"{quoted(cup)} CIG")
        add("cup_aggiudicatario", f"{quoted(cup)} aggiudicatario")
        add("cup_affidamento", f"{quoted(cup)} affidamento")
        add("cup_impresa", f"{quoted(cup)} \"impresa appaltatrice\"")
        add("cup_contratto", f"{quoted(cup)} contratto")
        add("cup_trasparenza", f"{quoted(cup)} \"Portale Trasparenza\"")

        if client:
            add("cup_client", f"{quoted(cup)} {quoted(client)}")

        if title:
            add("cup_title", f"{quoted(cup)} {quoted(title)}")

    if cig:
        add("cig_exact", quoted(cig))
        add("cig_cup", f"{quoted(cig)} CUP")
        add("cig_aggiudicatario", f"{quoted(cig)} aggiudicatario")
        add("cig_impresa", f"{quoted(cig)} \"impresa appaltatrice\"")

    return queries


def google_url(query):
    return "https://www.google.com/search?q=" + quote_plus(query)


def bing_url(query):
    return "https://www.bing.com/search?q=" + quote_plus(query)


def load_unique_records(branch_dir):
    records = {}

    for path in sorted(branch_dir.glob("*.json")):
        if path.name == "index.json":
            continue

        payload = load_json(path)
        rows, _ = extract_rows(payload)

        for row in rows:
            if not isinstance(row, dict):
                continue

            key = record_key(row)
            score = (
                1 if contractor_present(row) else 0,
                value_eur(row),
                len(generate_queries(row)),
            )

            current = records.get(key)

            if current is None or score > current["quality_score"]:
                records[key] = {
                    "record": row,
                    "quality_score": score,
                }

    return {
        key: item["record"]
        for key, item in records.items()
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_preview_html(path, targets, queries, html_top):
    by_key = {}

    for row in queries:
        by_key.setdefault(row["key"], []).append(row)

    selected = targets[:html_top]

    parts = [
        "<!doctype html>",
        "<html lang='it'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>External Award Queries Preview</title>",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}",
        ".target{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:0 0 16px}",
        ".meta{color:#64748b;font-size:13px;margin:4px 0 10px}",
        "a{color:#0369a1;text-decoration:none}",
        "a:hover{text-decoration:underline}",
        ".query{margin:5px 0}",
        ".badge{display:inline-block;background:#e2e8f0;border-radius:999px;padding:2px 8px;font-size:12px;margin-right:4px}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>External Award Queries Preview</h1>",
        f"<p>Primi {len(selected)} target. File operativo: <code>reports/external_award_queries.csv</code></p>",
    ]

    for index, target in enumerate(selected, start=1):
        key = target["key"]
        qrows = by_key.get(key, [])

        parts.append("<section class='target'>")
        parts.append(
            f"<h2>{index}. {target['title'] or '(senza titolo)'}</h2>"
        )
        parts.append(
            "<div class='meta'>"
            f"CUP: <strong>{target['cup']}</strong> · "
            f"Valore: {target['value_eur']} · "
            f"Filiale: {target['branch']} · "
            f"ANAC: {target['anac_level']} · "
            f"Score: {target['priority_score']}"
            "</div>"
        )
        parts.append(
            "<div class='meta'>"
            f"{target['client']} · "
            f"{target['municipality']} {target['province']} {target['region']}"
            "</div>"
        )

        for q in qrows:
            parts.append(
                "<div class='query'>"
                f"<span class='badge'>{q['query_type']}</span> "
                f"<a href='{q['google_url']}' target='_blank'>Google</a> · "
                f"<a href='{q['bing_url']}' target='_blank'>Bing</a> "
                f"<code>{q['query']}</code>"
                "</div>"
            )

        parts.append("</section>")

    parts.extend(["</body>", "</html>"])

    path.write_text(
        "\n".join(parts),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--branches",
        type=Path,
        default=Path("docs/data/branches"),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--html-top",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--targets-out",
        type=Path,
        default=Path("reports/external_award_targets.csv"),
    )
    parser.add_argument(
        "--queries-out",
        type=Path,
        default=Path("reports/external_award_queries.csv"),
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=Path("reports/external_award_queries_preview.html"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("reports/external_award_targets_summary.json"),
    )
    parser.add_argument(
        "--segment-keyword",
        action="append",
        default=[],
    )

    args = parser.parse_args()

    keywords = DEFAULT_SEGMENT_KEYWORDS + args.segment_keyword

    if not args.branches.exists():
        raise SystemExit(
            f"Cartella shard non trovata: {args.branches}"
        )

    print("Caricamento record unici...")
    records = load_unique_records(args.branches)

    print("Record unici:", f"{len(records):,}")

    candidates = []
    skipped = Counter()

    for key, record in records.items():
        cup = clean(record.get("cup"))

        if not cup:
            skipped["without_cup"] += 1
            continue

        if contractor_present(record):
            skipped["already_has_contractor"] += 1
            continue

        queries = generate_queries(record)

        if not queries:
            skipped["without_queries"] += 1
            continue

        score = record_priority(record, keywords)

        candidates.append(
            {
                "key": key,
                "cup": cup,
                "cig": clean(record.get("cig")),
                "title": normalize_space(record.get("title")),
                "client": normalize_space(
                    first_value(record, ["client", "subject", "owner"])
                ),
                "region": clean(record.get("region")),
                "province": clean(record.get("province")),
                "municipality": clean(record.get("municipality")),
                "branch": clean(record.get("branch") or "NON ASSEGNATA"),
                "value_eur": value_eur(record),
                "category": clean(record.get("category")),
                "primary_segment": clean(record.get("primary_segment")),
                "anac_level": clean(record.get("anac_level") or "none"),
                "anac_match_cig_count": clean(
                    record.get("anac_match_cig_count")
                ),
                "change_status": clean(record.get("change_status")),
                "change_badges": " | ".join(
                    record.get("change_badges")
                    if isinstance(record.get("change_badges"), list)
                    else []
                ),
                "priority_score": score,
                "queries_count": len(queries),
                "source_url": clean(record.get("source_url")),
            }
        )

    candidates.sort(
        key=lambda row: (
            float(row["priority_score"]),
            float(row["value_eur"]),
        ),
        reverse=True,
    )

    targets = candidates[: args.top]

    query_rows = []

    for rank, target in enumerate(targets, start=1):
        record = records[target["key"]]

        for query_index, query_data in enumerate(
            generate_queries(record),
            start=1,
        ):
            query = query_data["query"]

            query_rows.append(
                {
                    "target_rank": rank,
                    "key": target["key"],
                    "cup": target["cup"],
                    "cig": target["cig"],
                    "branch": target["branch"],
                    "region": target["region"],
                    "province": target["province"],
                    "municipality": target["municipality"],
                    "value_eur": target["value_eur"],
                    "anac_level": target["anac_level"],
                    "priority_score": target["priority_score"],
                    "query_index": query_index,
                    "query_type": query_data["query_type"],
                    "query": query,
                    "google_url": google_url(query),
                    "bing_url": bing_url(query),
                }
            )

    write_csv(
        args.targets_out,
        targets,
        [
            "key",
            "cup",
            "cig",
            "title",
            "client",
            "region",
            "province",
            "municipality",
            "branch",
            "value_eur",
            "category",
            "primary_segment",
            "anac_level",
            "anac_match_cig_count",
            "change_status",
            "change_badges",
            "priority_score",
            "queries_count",
            "source_url",
        ],
    )

    write_csv(
        args.queries_out,
        query_rows,
        [
            "target_rank",
            "key",
            "cup",
            "cig",
            "branch",
            "region",
            "province",
            "municipality",
            "value_eur",
            "anac_level",
            "priority_score",
            "query_index",
            "query_type",
            "query",
            "google_url",
            "bing_url",
        ],
    )

    write_preview_html(
        args.html_out,
        targets,
        query_rows,
        args.html_top,
    )

    summary = {
        "unique_records": len(records),
        "candidate_records": len(candidates),
        "selected_targets": len(targets),
        "generated_queries": len(query_rows),
        "skipped": dict(skipped),
        "by_anac_level": dict(
            Counter(row["anac_level"] for row in targets)
        ),
        "by_branch_top20": dict(
            Counter(row["branch"] for row in targets).most_common(20)
        ),
        "outputs": {
            "targets": str(args.targets_out),
            "queries": str(args.queries_out),
            "preview_html": str(args.html_out),
        },
    }

    args.summary_out.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Candidati senza aggiudicatario:", f"{len(candidates):,}")
    print("Target selezionati:", f"{len(targets):,}")
    print("Query generate:", f"{len(query_rows):,}")
    print("Saltati:", dict(skipped))
    print()
    print("Output:")
    print("-", args.targets_out)
    print("-", args.queries_out)
    print("-", args.html_out)
    print("-", args.summary_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
