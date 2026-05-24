import csv
import json
from pathlib import Path

OUT = Path("reports/national_anac_cup_targets.csv")

INPUT_JSON = Path("docs/national_operational_data.json")
INPUT_BRANCH_INDEX = Path("docs/data/branches/index.json")
INPUT_BRANCH_DIR = Path("docs/data/branches")
INPUT_CSV_FALLBACK = Path("reports/national_operational_shortlist.csv")


def clean(value):
    return str(value or "").replace("\ufeff", "").strip()


def to_float(value):
    text = clean(value)
    text = text.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def load_json_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["records", "projects", "data", "rows"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def iter_branch_shards():
    if not INPUT_BRANCH_INDEX.exists():
        return

    index = json.loads(INPUT_BRANCH_INDEX.read_text(encoding="utf-8"))

    for branch in index.get("branches", []):
        for file_info in branch.get("files", []):
            filename = clean(file_info.get("file"))
            if not filename:
                continue

            path = INPUT_BRANCH_DIR / filename
            if not path.exists():
                continue

            for row in load_json_rows(path):
                yield row


def iter_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            yield row


def iter_source_rows():
    if INPUT_JSON.exists():
        print(f"Input ANAC target: {INPUT_JSON}")
        yield from load_json_rows(INPUT_JSON)
        return

    if INPUT_BRANCH_INDEX.exists():
        print(f"Input ANAC target: {INPUT_BRANCH_INDEX} + shard filiali")
        yield from iter_branch_shards()
        return

    if INPUT_CSV_FALLBACK.exists():
        print(f"Input ANAC target fallback: {INPUT_CSV_FALLBACK}")
        yield from iter_csv_rows(INPUT_CSV_FALLBACK)
        return

    raise SystemExit(
        "Nessun input trovato per target ANAC: "
        f"{INPUT_JSON}, {INPUT_BRANCH_INDEX}, {INPUT_CSV_FALLBACK}"
    )


def normalized_target(row):
    return {
        "cup": clean(row.get("cup")).upper(),
        "operational_score": clean(
            row.get("operational_score")
            or row.get("commercial_score")
            or row.get("score")
        ),
        "primary_segment": clean(
            row.get("primary_segment")
            or row.get("segment")
        ),
        "title": clean(row.get("title")),
        "category": clean(row.get("category")),
        "region": clean(row.get("region")),
        "province": clean(row.get("province")),
        "municipality": clean(row.get("municipality")),
        "value_eur": clean(
            row.get("value_eur")
            or row.get("project_value")
        ),
        "client": clean(row.get("client")),
        "source_url": clean(
            row.get("source_url")
            or row.get("url")
        ),
    }


def rank_target(row):
    return (
        to_float(row.get("operational_score")),
        to_float(row.get("value_eur")),
        1 if clean(row.get("title")) else 0,
    )


def main():
    by_cup = {}
    scanned = 0
    skipped_no_cup = 0

    for raw in iter_source_rows():
        scanned += 1
        row = normalized_target(raw)

        cup = row["cup"]
        if not cup:
            skipped_no_cup += 1
            continue

        current = by_cup.get(cup)
        if current is None or rank_target(row) > rank_target(current):
            by_cup[cup] = row

    rows = sorted(
        by_cup.values(),
        key=lambda r: (
            -to_float(r.get("operational_score")),
            -to_float(r.get("value_eur")),
            r.get("cup"),
        ),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "cup",
        "operational_score",
        "primary_segment",
        "title",
        "category",
        "region",
        "province",
        "municipality",
        "value_eur",
        "client",
        "source_url",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Righe lette: {scanned}")
    print(f"Righe senza CUP saltate: {skipped_no_cup}")
    print(f"CUP target generati: {len(rows)}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()

