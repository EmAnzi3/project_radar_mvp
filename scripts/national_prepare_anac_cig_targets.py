import csv
from collections import defaultdict
from pathlib import Path


MATCHES = Path("reports/national_anac_cup_cig_matches.csv")
TARGETS = Path("reports/national_anac_cup_targets.csv")

OUT_CIG = Path("reports/national_anac_cig_targets.csv")
OUT_SUMMARY = Path("reports/national_anac_cup_cig_summary.csv")


def clean(value):
    return str(value or "").strip()


def load_targets():
    out = {}

    with TARGETS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cup = clean(row.get("cup"))
            if cup:
                out[cup] = row

    return out


def main():
    if not MATCHES.exists():
        raise SystemExit(f"File non trovato: {MATCHES}")

    if not TARGETS.exists():
        raise SystemExit(f"File non trovato: {TARGETS}")

    targets = load_targets()

    cig_to_cups = defaultdict(set)
    cup_to_cigs = defaultdict(set)

    with MATCHES.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cup = clean(row.get("cup"))
            cig = clean(row.get("cig"))

            if not cup or not cig:
                continue

            cig_to_cups[cig].add(cup)
            cup_to_cigs[cup].add(cig)

    OUT_CIG.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CIG.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cig",
            "cup_count",
            "cups",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()

        for cig, cups in sorted(cig_to_cups.items()):
            writer.writerow({
                "cig": cig,
                "cup_count": len(cups),
                "cups": " | ".join(sorted(cups)),
            })

    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cup",
            "cig_count",
            "cigs",
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

        for cup, cigs in sorted(cup_to_cigs.items(), key=lambda x: len(x[1]), reverse=True):
            meta = targets.get(cup, {})
            writer.writerow({
                "cup": cup,
                "cig_count": len(cigs),
                "cigs": " | ".join(sorted(cigs)),
                "operational_score": clean(meta.get("operational_score")),
                "primary_segment": clean(meta.get("primary_segment")),
                "title": clean(meta.get("title")),
                "category": clean(meta.get("category")),
                "region": clean(meta.get("region")),
                "province": clean(meta.get("province")),
                "municipality": clean(meta.get("municipality")),
                "value_eur": clean(meta.get("value_eur")),
                "client": clean(meta.get("client")),
                "source_url": clean(meta.get("source_url")),
            })

    print(f"CIG unici: {len(cig_to_cups)}")
    print(f"CUP con almeno un CIG: {len(cup_to_cigs)}")
    print(f"Output CIG target: {OUT_CIG}")
    print(f"Output summary CUP-CIG: {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
