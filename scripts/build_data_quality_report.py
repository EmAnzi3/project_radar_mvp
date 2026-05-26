import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path(".")
BRANCH_DIR = ROOT / "docs" / "data" / "branches"
OUT_JSON = ROOT / "docs" / "data" / "data_quality.json"


WARN_SHARD_MB = 45
CRITICAL_SHARD_MB = 90


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


def has_link(record):
    return bool(clean(record.get("source_url") or record.get("url")))


def has_project_value(record):
    text = clean(record.get("project_value"))
    if not text:
        return False

    try:
        return float(text.replace(".", "").replace(",", ".")) > 0
    except Exception:
        return False


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


def sample_record(record):
    return {
        "branch": clean(record.get("branch")),
        "title": clean(record.get("title"))[:180],
        "cup": clean(record.get("cup")),
        "region": clean(record.get("region")),
        "province": clean(record.get("province")),
        "municipality": clean(record.get("municipality")),
        "value": clean(record.get("project_value")),
        "source": clean(record.get("source") or record.get("sources")),
        "source_url": clean(record.get("source_url") or record.get("url")),
    }


def pct(part, total):
    return round((part / total) * 100, 2) if total else 0.0


def main():
    if not BRANCH_DIR.exists():
        raise SystemExit(f"Manca cartella shard: {BRANCH_DIR}")

    totals = Counter()
    by_branch = defaultdict(Counter)
    samples = defaultdict(list)
    cup_counter = Counter()
    shard_files = []

    all_rows = 0

    for path in sorted(BRANCH_DIR.glob("*.json")):
        if path.name == "index.json":
            continue

        rows = load_rows(path)
        branch_from_file = path.stem
        mb = path.stat().st_size / 1024 / 1024

        shard_status = "ok"
        if mb >= CRITICAL_SHARD_MB:
            shard_status = "critical"
        elif mb >= WARN_SHARD_MB:
            shard_status = "warning"

        shard_files.append({
            "file": path.name,
            "branch": branch_from_file,
            "records": len(rows),
            "mb": round(mb, 2),
            "status": shard_status,
        })

        for r in rows:
            if not isinstance(r, dict):
                continue

            all_rows += 1

            branch = clean(r.get("branch")) or branch_from_file
            branch_norm = norm(branch)

            totals["records"] += 1
            by_branch[branch]["records"] += 1

            cup = clean(r.get("cup")).upper()
            if cup:
                cup_counter[cup] += 1
            else:
                totals["missing_cup"] += 1
                by_branch[branch]["missing_cup"] += 1
                if len(samples["missing_cup"]) < 10:
                    samples["missing_cup"].append(sample_record(r))

            if branch_norm in {"NON ASSEGNATA", "NON_ASSEGNATA"}:
                totals["non_assegnata"] += 1
                by_branch[branch]["non_assegnata"] += 1
                if len(samples["non_assegnata"]) < 10:
                    samples["non_assegnata"].append(sample_record(r))

            if branch_norm == "AMBIGUA":
                totals["ambigua"] += 1
                by_branch[branch]["ambigua"] += 1
                if len(samples["ambigua"]) < 10:
                    samples["ambigua"].append(sample_record(r))

            if not clean(r.get("region")):
                totals["missing_region"] += 1
                by_branch[branch]["missing_region"] += 1
                if len(samples["missing_region"]) < 10:
                    samples["missing_region"].append(sample_record(r))

            if not clean(r.get("province")):
                totals["missing_province"] += 1
                by_branch[branch]["missing_province"] += 1
                if len(samples["missing_province"]) < 10:
                    samples["missing_province"].append(sample_record(r))

            if not clean(r.get("municipality")):
                totals["missing_municipality"] += 1
                by_branch[branch]["missing_municipality"] += 1
                if len(samples["missing_municipality"]) < 10:
                    samples["missing_municipality"].append(sample_record(r))

            if not has_project_value(r):
                totals["missing_project_value"] += 1
                by_branch[branch]["missing_project_value"] += 1
                if len(samples["missing_project_value"]) < 10:
                    samples["missing_project_value"].append(sample_record(r))

            if not has_link(r):
                totals["missing_source_url"] += 1
                by_branch[branch]["missing_source_url"] += 1
                if len(samples["missing_source_url"]) < 10:
                    samples["missing_source_url"].append(sample_record(r))

            if has_contractor(r):
                totals["with_contractor"] += 1
                by_branch[branch]["with_contractor"] += 1

    duplicate_cups = {cup: count for cup, count in cup_counter.items() if count > 1}

    branch_payload = []
    for branch, c in by_branch.items():
        records = c["records"]
        branch_payload.append({
            "branch": branch,
            "records": records,
            "non_assegnata": c["non_assegnata"],
            "ambigua": c["ambigua"],
            "missing_region": c["missing_region"],
            "missing_province": c["missing_province"],
            "missing_municipality": c["missing_municipality"],
            "missing_project_value": c["missing_project_value"],
            "missing_source_url": c["missing_source_url"],
            "missing_cup": c["missing_cup"],
            "with_contractor": c["with_contractor"],
            "contractor_coverage_pct": pct(c["with_contractor"], records),
        })

    branch_payload.sort(
        key=lambda x: (
            x["non_assegnata"] + x["ambigua"] + x["missing_province"] + x["missing_municipality"] + x["missing_source_url"],
            x["records"],
        ),
        reverse=True,
    )

    shard_files.sort(key=lambda x: x["mb"], reverse=True)

    issues = [
        {
            "key": "non_assegnata",
            "label": "Record non assegnati",
            "count": totals["non_assegnata"],
            "pct": pct(totals["non_assegnata"], totals["records"]),
            "severity": "warning" if totals["non_assegnata"] else "ok",
        },
        {
            "key": "ambigua",
            "label": "Record ambigui",
            "count": totals["ambigua"],
            "pct": pct(totals["ambigua"], totals["records"]),
            "severity": "warning" if totals["ambigua"] else "ok",
        },
        {
            "key": "missing_municipality",
            "label": "Comune mancante",
            "count": totals["missing_municipality"],
            "pct": pct(totals["missing_municipality"], totals["records"]),
            "severity": "warning" if totals["missing_municipality"] else "ok",
        },
        {
            "key": "missing_province",
            "label": "Provincia mancante",
            "count": totals["missing_province"],
            "pct": pct(totals["missing_province"], totals["records"]),
            "severity": "warning" if totals["missing_province"] else "ok",
        },
        {
            "key": "missing_project_value",
            "label": "Valore progetto mancante",
            "count": totals["missing_project_value"],
            "pct": pct(totals["missing_project_value"], totals["records"]),
            "severity": "info" if totals["missing_project_value"] else "ok",
        },
        {
            "key": "missing_source_url",
            "label": "Fonte/link mancante",
            "count": totals["missing_source_url"],
            "pct": pct(totals["missing_source_url"], totals["records"]),
            "severity": "warning" if totals["missing_source_url"] else "ok",
        },
        {
            "key": "missing_cup",
            "label": "CUP mancante",
            "count": totals["missing_cup"],
            "pct": pct(totals["missing_cup"], totals["records"]),
            "severity": "warning" if totals["missing_cup"] else "ok",
        },
    ]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_records": totals["records"],
        "with_contractor": totals["with_contractor"],
        "contractor_coverage_pct": pct(totals["with_contractor"], totals["records"]),
        "duplicate_cups_count": len(duplicate_cups),
        "duplicate_cups_top": [
            {"cup": cup, "count": count}
            for cup, count in Counter(duplicate_cups).most_common(25)
        ],
        "issues": issues,
        "samples": samples,
        "branches": branch_payload,
        "shards": shard_files,
        "shard_thresholds": {
            "warning_mb": WARN_SHARD_MB,
            "critical_mb": CRITICAL_SHARD_MB,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] Data quality scritto: {OUT_JSON}")
    print(f"Record: {totals['records']}")
    print(f"Non assegnati: {totals['non_assegnata']}")
    print(f"Ambigui: {totals['ambigua']}")
    print(f"Comune mancante: {totals['missing_municipality']}")
    print(f"Fonte mancante: {totals['missing_source_url']}")
    print(f"Shard warning: {sum(1 for s in shard_files if s['status'] == 'warning')}")
    print(f"Shard critical: {sum(1 for s in shard_files if s['status'] == 'critical')}")


if __name__ == "__main__":
    main()
