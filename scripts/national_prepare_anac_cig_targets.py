import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(".")
MATCHES = ROOT / "reports" / "national_anac_cup_cig_matches.csv"
BRANCH_DIR = ROOT / "docs" / "data" / "branches"

OUT_CIG_TARGETS = ROOT / "reports" / "national_anac_cig_targets.csv"
OUT_CUP_SUMMARY = ROOT / "reports" / "national_anac_cup_cig_summary.csv"


META_FIELDS = [
    "title",
    "client",
    "primary_segment",
    "segment",
    "region",
    "province",
    "municipality",
    "value_eur",
    "project_value",
    "branch",
    "source_url",
]


def clean(value):
    return str(value or "").strip()


def norm(value):
    return clean(value).upper()


def load_json_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def metadata_score(meta):
    return sum(1 for field in META_FIELDS if clean(meta.get(field)))


def normalize_record_metadata(record):
    source_url = clean(record.get("source_url") or record.get("url"))

    primary_segment = clean(
        record.get("primary_segment")
        or record.get("segment")
    )

    segment = clean(
        record.get("segment")
        or record.get("primary_segment")
    )

    value = clean(
        record.get("value_eur")
        or record.get("project_value")
        or record.get("value")
    )

    return {
        "title": clean(record.get("title")),
        "client": clean(record.get("client")),
        "primary_segment": primary_segment,
        "segment": segment,
        "region": clean(record.get("region")),
        "province": clean(record.get("province")),
        "municipality": clean(record.get("municipality")),
        "value_eur": value,
        "project_value": value,
        "branch": clean(record.get("branch")),
        "source_url": source_url,
    }


def build_cup_metadata_from_shards():
    cup_meta = {}
    rows_seen = 0

    if not BRANCH_DIR.exists():
        print(f"[WARN] Cartella shard non trovata: {BRANCH_DIR}")
        return cup_meta, rows_seen

    for path in sorted(BRANCH_DIR.glob("*.json")):
        if path.name == "index.json":
            continue

        for record in load_json_rows(path):
            if not isinstance(record, dict):
                continue

            rows_seen += 1
            cup = norm(record.get("cup"))

            if not cup:
                continue

            meta = normalize_record_metadata(record)

            if cup not in cup_meta:
                cup_meta[cup] = meta
                continue

            if metadata_score(meta) > metadata_score(cup_meta[cup]):
                cup_meta[cup] = meta

    return cup_meta, rows_seen


def read_cup_cig_matches():
    if not MATCHES.exists():
        raise SystemExit(f"Manca file match CUP-CIG: {MATCHES}")

    cup_to_cigs = defaultdict(set)
    cig_to_cups = defaultdict(set)
    rows = 0

    with MATCHES.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fields = reader.fieldnames or []

        if "cup" not in fields or "cig" not in fields:
            raise SystemExit(f"Header inatteso in {MATCHES}: {fields}")

        for row in reader:
            rows += 1

            cup = norm(row.get("cup"))
            cig = norm(row.get("cig"))

            if not cup or not cig:
                continue

            cup_to_cigs[cup].add(cig)
            cig_to_cups[cig].add(cup)

    return cup_to_cigs, cig_to_cups, rows


def best_cup_for_cig(cups, cup_meta):
    best = ""
    best_score = -1

    for cup in sorted(cups):
        score = metadata_score(cup_meta.get(cup, {}))

        if score > best_score:
            best = cup
            best_score = score

    return best or sorted(cups)[0]


def write_outputs(cup_to_cigs, cig_to_cups, cup_meta):
    OUT_CIG_TARGETS.parent.mkdir(parents=True, exist_ok=True)

    cig_fields = [
        "cig",
        "cups",
        "cup",
        "title",
        "client",
        "primary_segment",
        "segment",
        "region",
        "province",
        "municipality",
        "value_eur",
        "project_value",
        "branch",
        "source_url",
    ]

    with OUT_CIG_TARGETS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cig_fields, delimiter=";")
        writer.writeheader()

        for cig in sorted(cig_to_cups):
            cups = sorted(cig_to_cups[cig])
            cup = best_cup_for_cig(cups, cup_meta)
            meta = cup_meta.get(cup, {})

            row = {
                "cig": cig,
                "cups": " | ".join(cups),
                "cup": cup,
            }

            for field in META_FIELDS:
                row[field] = clean(meta.get(field))

            writer.writerow(row)

    summary_fields = [
        "cup",
        "cig_count",
        "cigs",
        "title",
        "client",
        "primary_segment",
        "region",
        "province",
        "municipality",
        "value_eur",
        "project_value",
        "branch",
        "source_url",
    ]

    with OUT_CUP_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields, delimiter=";")
        writer.writeheader()

        for cup in sorted(cup_to_cigs):
            cigs = sorted(cup_to_cigs[cup])
            meta = cup_meta.get(cup, {})

            writer.writerow({
                "cup": cup,
                "cig_count": len(cigs),
                "cigs": " | ".join(cigs),
                "title": clean(meta.get("title")),
                "client": clean(meta.get("client")),
                "primary_segment": clean(meta.get("primary_segment") or meta.get("segment")),
                "region": clean(meta.get("region")),
                "province": clean(meta.get("province")),
                "municipality": clean(meta.get("municipality")),
                "value_eur": clean(meta.get("value_eur") or meta.get("project_value")),
                "project_value": clean(meta.get("project_value") or meta.get("value_eur")),
                "branch": clean(meta.get("branch")),
                "source_url": clean(meta.get("source_url")),
            })


def main():
    print("[1/3] Carico metadati CUP dagli shard...")
    cup_meta, shard_rows = build_cup_metadata_from_shards()
    print(f"[OK] Righe shard lette: {shard_rows:,}")
    print(f"[OK] CUP con metadati: {len(cup_meta):,}")

    print("")
    print("[2/3] Carico match CUP-CIG...")
    cup_to_cigs, cig_to_cups, rows = read_cup_cig_matches()
    print(f"[OK] Righe CUP-CIG: {rows:,}")
    print(f"[OK] CUP con almeno un CIG: {len(cup_to_cigs):,}")
    print(f"[OK] CIG unici: {len(cig_to_cups):,}")

    print("")
    print("[3/3] Scrivo target CIG con metadati...")
    write_outputs(cup_to_cigs, cig_to_cups, cup_meta)

    print(f"CIG unici: {len(cig_to_cups)}")
    print(f"CUP con almeno un CIG: {len(cup_to_cigs)}")
    print(f"Output CIG target: {OUT_CIG_TARGETS}")
    print(f"Output summary CUP-CIG: {OUT_CUP_SUMMARY}")


if __name__ == "__main__":
    main()
