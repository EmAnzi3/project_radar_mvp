import argparse
import csv
import json
import re
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import quote_plus


def clean(value):
    return str(value or "").strip()


def normalize_space(value):
    return re.sub(r"\s+", " ", clean(value))


def quoted(value):
    value = normalize_space(value)
    return f'"{value}"' if value else ""


def google_url(query):
    return "https://www.google.com/search?q=" + quote_plus(query)


def bing_url(query):
    return "https://www.bing.com/search?q=" + quote_plus(query)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file, delimiter=";"))


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


def split_multi(value):
    text = clean(value)

    if not text:
        return []

    parts = re.split(r"[|,;\s]+", text)

    result = []

    for part in parts:
        part = clean(part).upper()

        if part and part not in result:
            result.append(part)

    return result


def load_cup_cig_index(path):
    rows = read_csv(path)
    index = defaultdict(list)

    for row in rows:
        cig = clean(row.get("cig")).upper()

        cups = []

        if clean(row.get("cup")):
            cups.append(clean(row.get("cup")).upper())

        if clean(row.get("cups")):
            cups.extend(split_multi(row.get("cups")))

        for cup in cups:
            if not cup or not cig:
                continue

            if cig not in index[cup]:
                index[cup].append(cig)

    return index


def compact_title(title, max_words=8):
    words = normalize_space(title).split()

    if len(words) <= max_words:
        return " ".join(words)

    return " ".join(words[:max_words])


def usable_client(client):
    text = normalize_space(client)
    low = text.lower()

    if not text:
        return ""

    if low in {
        "soggetto privato",
        "-",
        "non disponibile",
        "n.d.",
        "nd",
    }:
        return ""

    if len(text) > 90:
        return ""

    return text


def add_query(rows, existing_queries, base, query_type, query):
    query = normalize_space(query)

    if not query or query in existing_queries:
        return

    existing_queries.add(query)

    rows.append({
        **base,
        "query_index": "",
        "query_type": query_type,
        "query": query,
        "google_url": google_url(query),
        "bing_url": bing_url(query),
    })


def make_cig_queries(target, cig):
    cup = clean(target.get("cup"))
    title = compact_title(target.get("title"))
    client = usable_client(target.get("client"))

    result = []

    def add(query_type, query):
        result.append({
            "query_type": query_type,
            "query": normalize_space(query),
        })

    if cup and cig:
        add(
            "cup_cig_exact",
            f"{quoted(cup)} {quoted(cig)}",
        )

    if cig:
        add("cig_exact", quoted(cig))
        add(
            "cig_aggiudicatario",
            f"{quoted(cig)} aggiudicatario",
        )
        add(
            "cig_affidamento",
            f"{quoted(cig)} affidamento",
        )
        add(
            "cig_impresa",
            f"{quoted(cig)} \"impresa appaltatrice\"",
        )
        add(
            "cig_contratto",
            f"{quoted(cig)} contratto",
        )

        if client:
            add(
                "cig_client",
                f"{quoted(cig)} {quoted(client)}",
            )

        if title:
            add(
                "cig_title",
                f"{quoted(cig)} {quoted(title)}",
            )

    return result


def renumber_queries(rows):
    counters = Counter()

    for row in rows:
        key = row.get("key")
        counters[key] += 1
        row["query_index"] = counters[key]

    return rows


def write_preview_html(path, targets, query_rows, html_top):
    by_key = defaultdict(list)

    for row in query_rows:
        by_key[row["key"]].append(row)

    parts = [
        "<!doctype html>",
        "<html lang='it'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>External Award Queries + CIG</title>",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}",
        ".target{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:0 0 16px}",
        ".meta{color:#64748b;font-size:13px;margin:4px 0 10px}",
        "a{color:#0369a1;text-decoration:none}",
        "a:hover{text-decoration:underline}",
        ".query{margin:5px 0}",
        ".badge{display:inline-block;background:#e2e8f0;border-radius:999px;padding:2px 8px;font-size:12px;margin-right:4px}",
        ".cig{background:#fde68a}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>External Award Queries + CIG</h1>",
        f"<p>Primi {html_top} target con query CUP e CIG. File operativo: <code>reports/external_award_queries_plus_cig.csv</code></p>",
    ]

    for rank, target in enumerate(targets[:html_top], start=1):
        key = target["key"]
        queries = by_key.get(key, [])

        parts.append("<section class='target'>")
        parts.append(
            f"<h2>{rank}. {target.get('title') or '(senza titolo)'}</h2>"
        )
        parts.append(
            "<div class='meta'>"
            f"CUP: <strong>{target.get('cup')}</strong> · "
            f"CIG tecnici: <strong>{target.get('matched_cigs', '')}</strong> · "
            f"Valore: {target.get('value_eur')} · "
            f"Filiale: {target.get('branch')} · "
            f"ANAC: {target.get('anac_level')} · "
            f"Score: {target.get('priority_score')}"
            "</div>"
        )
        parts.append(
            "<div class='meta'>"
            f"{target.get('client', '')} · "
            f"{target.get('municipality', '')} "
            f"{target.get('province', '')} "
            f"{target.get('region', '')}"
            "</div>"
        )

        for query in queries:
            cls = "badge cig" if "cig" in query["query_type"] else "badge"

            parts.append(
                "<div class='query'>"
                f"<span class='{cls}'>{query['query_type']}</span> "
                f"<a href='{query['google_url']}' target='_blank'>Google</a> · "
                f"<a href='{query['bing_url']}' target='_blank'>Bing</a> "
                f"<code>{query['query']}</code>"
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
        "--targets",
        type=Path,
        default=Path("reports/external_award_targets.csv"),
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("reports/external_award_queries.csv"),
    )
    parser.add_argument(
        "--cup-cig",
        type=Path,
        default=Path("reports/national_anac_cup_cig_matches.csv"),
    )
    parser.add_argument(
        "--queries-out",
        type=Path,
        default=Path("reports/external_award_queries_plus_cig.csv"),
    )
    parser.add_argument(
        "--targets-out",
        type=Path,
        default=Path("reports/external_award_targets_plus_cig.csv"),
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=Path("reports/external_award_queries_plus_cig_preview.html"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("reports/external_award_queries_plus_cig_summary.json"),
    )
    parser.add_argument(
        "--max-cigs-per-cup",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--html-top",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    if not args.targets.exists():
        raise SystemExit(f"Target mancanti: {args.targets}")

    if not args.queries.exists():
        raise SystemExit(f"Query mancanti: {args.queries}")

    if not args.cup_cig.exists():
        raise SystemExit(f"Match CUP-CIG mancanti: {args.cup_cig}")

    targets = read_csv(args.targets)
    original_queries = read_csv(args.queries)
    cup_cig_index = load_cup_cig_index(args.cup_cig)

    rows = list(original_queries)
    existing_queries = {
        normalize_space(row.get("query"))
        for row in rows
        if normalize_space(row.get("query"))
    }

    targets_out = []
    added_rows = 0
    targets_with_cigs = 0
    cigs_used = 0

    for target in targets:
        cup = clean(target.get("cup")).upper()
        cigs = cup_cig_index.get(cup, [])
        selected_cigs = cigs[: args.max_cigs_per_cup]

        target = dict(target)
        target["matched_cigs"] = " | ".join(selected_cigs)
        target["matched_cigs_count"] = len(cigs)
        target["matched_cigs_used"] = len(selected_cigs)

        targets_out.append(target)

        if selected_cigs:
            targets_with_cigs += 1
            cigs_used += len(selected_cigs)

        for cig in selected_cigs:
            base = {
                "target_rank": target.get("target_rank", ""),
                "key": target.get("key", ""),
                "cup": target.get("cup", ""),
                "cig": cig,
                "branch": target.get("branch", ""),
                "region": target.get("region", ""),
                "province": target.get("province", ""),
                "municipality": target.get("municipality", ""),
                "value_eur": target.get("value_eur", ""),
                "anac_level": target.get("anac_level", ""),
                "priority_score": target.get("priority_score", ""),
            }

            before = len(rows)

            for query in make_cig_queries(target, cig):
                add_query(
                    rows,
                    existing_queries,
                    base,
                    query["query_type"],
                    query["query"],
                )

            added_rows += len(rows) - before

    rows = renumber_queries(rows)

    query_fields = [
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
    ]

    target_fields = list(targets_out[0].keys()) if targets_out else []

    write_csv(args.queries_out, rows, query_fields)
    write_csv(args.targets_out, targets_out, target_fields)

    write_preview_html(
        args.html_out,
        targets_out,
        rows,
        args.html_top,
    )

    summary = {
        "targets": len(targets),
        "original_queries": len(original_queries),
        "targets_with_cigs": targets_with_cigs,
        "cigs_used": cigs_used,
        "added_cig_queries": added_rows,
        "total_queries": len(rows),
        "max_cigs_per_cup": args.max_cigs_per_cup,
        "outputs": {
            "queries_plus_cig": str(args.queries_out),
            "targets_plus_cig": str(args.targets_out),
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

    print("Target:", f"{len(targets):,}")
    print("Query originali:", f"{len(original_queries):,}")
    print("Target con CIG:", f"{targets_with_cigs:,}")
    print("CIG usati:", f"{cigs_used:,}")
    print("Query CIG aggiunte:", f"{added_rows:,}")
    print("Query totali:", f"{len(rows):,}")
    print()
    print("Output:")
    print("-", args.queries_out)
    print("-", args.targets_out)
    print("-", args.html_out)
    print("-", args.summary_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
