import csv
from pathlib import Path


INPUT = Path("reports/national_operational_shortlist.csv")
OUT = Path("reports/national_anac_cup_targets.csv")


def clean(value):
    return str(value or "").strip()


def main():
    if not INPUT.exists():
        raise SystemExit(f"File non trovato: {INPUT}")

    rows = []

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cup = clean(row.get("cup"))
            if not cup:
                continue

            rows.append({
                "cup": cup,
                "operational_score": clean(row.get("operational_score")),
                "primary_segment": clean(row.get("primary_segment")),
                "title": clean(row.get("title")),
                "category": clean(row.get("category")),
                "region": clean(row.get("region")),
                "province": clean(row.get("province")),
                "municipality": clean(row.get("municipality")),
                "value_eur": clean(row.get("value_eur")),
                "client": clean(row.get("client")),
                "source_url": clean(row.get("source_url")),
            })

    seen = set()
    unique = []

    for row in rows:
        if row["cup"] in seen:
            continue
        seen.add(row["cup"])
        unique.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
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
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)

    print(f"CUP target generati: {len(unique)}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
