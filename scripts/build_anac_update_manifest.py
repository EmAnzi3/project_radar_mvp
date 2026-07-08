import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def as_int(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def iter_lists(obj):
    if isinstance(obj, list):
        yield obj
        for item in obj:
            yield from iter_lists(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from iter_lists(value)


def find_branch_rows(payload):
    candidates = []

    for rows in iter_lists(payload):
        if not rows or not isinstance(rows, list):
            continue

        dict_rows = [row for row in rows if isinstance(row, dict)]
        if not dict_rows:
            continue

        hits = [
            row for row in dict_rows
            if "branch" in row and "with_contractor" in row
        ]

        if hits:
            candidates.append(hits)

    if not candidates:
        raise SystemExit(
            "ERRORE: impossibile trovare righe per filiale "
            "con campi branch/with_contractor in data_quality.json"
        )

    return max(candidates, key=len)


def branch_contractors(payload):
    out = {}

    for row in find_branch_rows(payload):
        branch = str(row.get("branch") or "").strip()
        if not branch:
            continue

        out[branch] = as_int(row.get("with_contractor"))

    return out


def funnel_value(payload, key):
    return as_int((payload.get("funnel") or {}).get(key))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--old-data-quality",
        default="tmp/data_quality.before.json",
    )
    parser.add_argument(
        "--new-data-quality",
        default="docs/data/data_quality.json",
    )
    parser.add_argument(
        "--old-anac-stats",
        default="tmp/anac_level_stats.before.json",
    )
    parser.add_argument(
        "--new-anac-stats",
        default="docs/data/anac_level_stats.json",
    )
    parser.add_argument(
        "--old-home-stats",
        default="tmp/home_stats.before.json",
    )
    parser.add_argument(
        "--new-home-stats",
        default="docs/data/home_stats.json",
    )
    parser.add_argument(
        "--out",
        default="docs/data/anac_update_manifest.json",
    )
    args = parser.parse_args()

    old_quality = load_json(args.old_data_quality)
    new_quality = load_json(args.new_data_quality)
    old_anac = load_json(args.old_anac_stats)
    new_anac = load_json(args.new_anac_stats)
    old_home = load_json(args.old_home_stats)
    new_home = load_json(args.new_home_stats)

    old_branch = branch_contractors(old_quality)
    new_branch = branch_contractors(new_quality)

    by_branch = []

    for branch in sorted(set(old_branch) | set(new_branch)):
        previous = as_int(old_branch.get(branch))
        current = as_int(new_branch.get(branch))
        delta = max(current - previous, 0)

        by_branch.append({
            "branch": branch,
            "anac_added": delta,
            "previous_with_contractor": previous,
            "current_with_contractor": current,
        })

    branch_sum = sum(row["anac_added"] for row in by_branch)

    previous_with_contractor = as_int(old_quality.get("with_contractor"))
    current_with_contractor = as_int(new_quality.get("with_contractor"))
    unique_delta = max(
        current_with_contractor - previous_with_contractor,
        0,
    )

    previous_home_total = as_int(old_home.get("total_with_contractor"))
    current_home_total = as_int(new_home.get("total_with_contractor"))

    out = {
        "run_id": "anac-only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "anac_added_records": branch_sum,
        "new_company_match_projects": branch_sum,
        "unique_company_match_delta": unique_delta,
        "previous_with_contractor": previous_with_contractor,
        "current_with_contractor": current_with_contractor,
        "previous_home_total_with_contractor": previous_home_total,
        "current_home_total_with_contractor": current_home_total,
        "home_total_with_contractor_delta": max(
            current_home_total - previous_home_total,
            0,
        ),
        "previous_technical_match_projects": funnel_value(
            old_anac,
            "technical_match_projects",
        ),
        "current_technical_match_projects": funnel_value(
            new_anac,
            "technical_match_projects",
        ),
        "new_technical_match_projects": max(
            funnel_value(new_anac, "technical_match_projects")
            - funnel_value(old_anac, "technical_match_projects"),
            0,
        ),
        "previous_enriched_projects": funnel_value(
            old_anac,
            "enriched_projects",
        ),
        "current_enriched_projects": funnel_value(
            new_anac,
            "enriched_projects",
        ),
        "new_enriched_projects": max(
            funnel_value(new_anac, "enriched_projects")
            - funnel_value(old_anac, "enriched_projects"),
            0,
        ),
        "previous_confirmed_projects": funnel_value(
            old_anac,
            "confirmed_projects",
        ),
        "current_confirmed_projects": funnel_value(
            new_anac,
            "confirmed_projects",
        ),
        "new_confirmed_projects": max(
            funnel_value(new_anac, "confirmed_projects")
            - funnel_value(old_anac, "confirmed_projects"),
            0,
        ),
        "by_branch": by_branch,
        "note": (
            "anac_added_records è la somma per filiale dei record che "
            "hanno acquisito nome azienda/contractor nell'ultimo refresh ANAC."
        ),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("ANAC aggiunto UI:", out["anac_added_records"])
    print("Delta contractor unici:", out["unique_company_match_delta"])
    print("Filiali con ANAC:", sum(1 for row in by_branch if row["anac_added"]))


if __name__ == "__main__":
    main()
