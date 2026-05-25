import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path(".")
BRANCH_INDEX = ROOT / "docs" / "data" / "branches" / "index.json"
BRANCH_DIR = ROOT / "docs" / "data" / "branches"
OUT = ROOT / "docs" / "data" / "home_stats.json"

AREA_BY_REGION = {
    "VALLE D'AOSTA": "Nord-Ovest",
    "VALLE D AOSTA": "Nord-Ovest",
    "PIEMONTE": "Nord-Ovest",
    "LIGURIA": "Nord-Ovest",
    "LOMBARDIA": "Nord-Ovest",

    "VENETO": "Nord-Est",
    "FRIULI-VENEZIA GIULIA": "Nord-Est",
    "FRIULI VENEZIA GIULIA": "Nord-Est",
    "TRENTINO-ALTO ADIGE": "Nord-Est",
    "TRENTINO ALTO ADIGE": "Nord-Est",

    "EMILIA-ROMAGNA": "Centro",
    "EMILIA ROMAGNA": "Centro",
    "TOSCANA": "Centro",
    "UMBRIA": "Centro",
    "MARCHE": "Centro",
    "SARDEGNA": "Centro",

    "ABRUZZO": "Sud",
    "MOLISE": "Sud",
    "LAZIO": "Sud",
    "PUGLIA": "Sud",
    "CAMPANIA": "Sud",
    "BASILICATA": "Sud",
    "CALABRIA": "Sud",
    "SICILIA": "Sud",
}


def clean(v):
    return str(v or "").strip()


def norm(v):
    return clean(v).upper()


def load_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def has_contractor(record):
    if clean(record.get("contractors")):
        return True
    if clean(record.get("contractor_tax_codes")):
        return True
    if clean(record.get("contractors_summary")):
        return True

    awards = record.get("awards")
    if isinstance(awards, list):
        for award in awards:
            if not isinstance(award, dict):
                continue
            if clean(award.get("contractors")):
                return True
            if clean(award.get("contractor_tax_codes")):
                return True
            if clean(award.get("contractor_name")):
                return True
            if clean(award.get("contractor_tax_code")):
                return True

    return False


def to_number(value):
    text = clean(value)
    text = text.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def area_for_region(region):
    return AREA_BY_REGION.get(norm(region), "Non classificata")


def main():
    if not BRANCH_INDEX.exists():
        raise SystemExit(f"Manca {BRANCH_INDEX}")

    index = json.loads(BRANCH_INDEX.read_text(encoding="utf-8"))

    total_records = int(index.get("unique_records") or 0)
    branches = index.get("branches") or []

    branch_stats = []
    total_with_contractor = 0
    total_value = 0.0

    segment_counter = Counter()
    region_counter = Counter()

    area_stats = defaultdict(lambda: {
        "area": "",
        "count": 0,
        "with_contractor": 0,
        "without_contractor": 0,
        "total_value_eur": 0.0,
    })

    for entry in branches:
        branch_name = clean(entry.get("branch"))
        slug = clean(entry.get("slug"))
        rows = []

        for file_info in entry.get("files", []):
            filename = clean(file_info.get("file"))
            if not filename:
                continue

            path = BRANCH_DIR / filename
            if not path.exists():
                continue

            rows.extend(load_rows(path))

        count = len(rows)
        with_contractor = 0
        branch_value = 0.0

        for r in rows:
            project_value = to_number(r.get("project_value"))
            branch_value += project_value
            total_value += project_value

            if has_contractor(r):
                with_contractor += 1

            segment = clean(r.get("segment")) or "Non classificato"
            region = clean(r.get("region")) or "Non indicata"
            area = area_for_region(region)

            segment_counter[segment] += 1
            region_counter[region] += 1

            area_stats[area]["area"] = area
            area_stats[area]["count"] += 1
            area_stats[area]["total_value_eur"] += project_value
            if has_contractor(r):
                area_stats[area]["with_contractor"] += 1

        without_contractor = max(count - with_contractor, 0)
        coverage = round((with_contractor / count) * 100, 1) if count else 0.0
        avg_value = round(branch_value / count, 2) if count else 0.0

        total_with_contractor += with_contractor

        branch_stats.append({
            "branch": branch_name,
            "slug": slug,
            "count": count,
            "with_contractor": with_contractor,
            "without_contractor": without_contractor,
            "coverage_pct": coverage,
            "total_value_eur": round(branch_value, 2),
            "avg_value_eur": avg_value,
        })

    for a in area_stats.values():
        a["without_contractor"] = max(a["count"] - a["with_contractor"], 0)
        a["coverage_pct"] = round((a["with_contractor"] / a["count"]) * 100, 1) if a["count"] else 0.0
        a["avg_value_eur"] = round(a["total_value_eur"] / a["count"], 2) if a["count"] else 0.0
        a["total_value_eur"] = round(a["total_value_eur"], 2)

    total_without_contractor = max(total_records - total_with_contractor, 0)
    national_coverage = round((total_with_contractor / total_records) * 100, 1) if total_records else 0.0
    avg_project_value = round(total_value / total_records, 2) if total_records else 0.0

    ordered_areas = ["Nord-Ovest", "Nord-Est", "Centro", "Sud"]
    area_payload = [
        area_stats[a]
        for a in ordered_areas
        if area_stats.get(a, {}).get("count", 0) > 0
    ]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_records": total_records,
        "total_branches": len(branches),
        "total_with_contractor": total_with_contractor,
        "total_without_contractor": total_without_contractor,
        "national_coverage_pct": national_coverage,
        "total_value_eur": round(total_value, 2),
        "avg_project_value_eur": avg_project_value,
        "top_branches_by_count": sorted(branch_stats, key=lambda x: x["count"], reverse=True)[:12],
        "top_branches_by_value": sorted(branch_stats, key=lambda x: x["total_value_eur"], reverse=True)[:12],
        "top_branches_by_coverage": sorted(
            [b for b in branch_stats if b["count"] >= 1000],
            key=lambda x: x["coverage_pct"],
            reverse=True,
        )[:12],
        "areas": area_payload,
        "segments": [
            {"name": k, "count": v}
            for k, v in segment_counter.most_common(10)
        ],
        "regions": [
            {"name": k, "count": v}
            for k, v in region_counter.most_common(12)
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: scritto {OUT}")
    print(f"Progetti: {total_records}")
    print(f"Valore totale: {round(total_value, 2)}")
    print(f"Con aggiudicatario: {total_with_contractor}")
    print(f"Copertura: {national_coverage}%")


if __name__ == "__main__":
    main()

