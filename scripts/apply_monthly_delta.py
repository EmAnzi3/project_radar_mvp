import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


CHANGE_FIELDS = {
    "change_status",
    "change_badges",
    "change_run",
    "change_summary",
}


SIGNATURE_FIELDS = [
    "title",
    "segment",
    "region",
    "province",
    "municipality",
    "project_value",
    "client",
    "contractors",
    "contractor_tax_codes",
    "contractors_summary",
    "award_date",
    "award_result",
    "award_amount_eur",
    "awards_count",
    "has_anac",
    "branch",
]


def clean(value):
    return str(value or "").strip()


def norm(value):
    return clean(value).upper()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def extract_rows(container):
    if isinstance(container, list):
        return container, None

    if isinstance(container, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            value = container.get(key)
            if isinstance(value, list):
                return value, key

    return [], None


def save_rows(container, row_key, rows):
    if isinstance(container, list):
        return rows

    if isinstance(container, dict) and row_key:
        container[row_key] = rows
        return container

    return container


def record_key(record):
    cup = norm(record.get("cup"))
    if cup:
        return f"CUP::{cup}"

    cig = norm(record.get("cig"))
    if cig:
        return f"CIG::{cig}"

    rid = norm(record.get("id"))
    if rid:
        return f"ID::{rid}"

    blob = "|".join([
        norm(record.get("title")),
        norm(record.get("client")),
        norm(record.get("municipality")),
        norm(record.get("province")),
        clean(record.get("project_value")),
    ])

    return "HASH::" + hashlib.sha1(blob.encode("utf-8")).hexdigest()


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


def compact_awards(record):
    awards = record.get("awards")
    if not isinstance(awards, list):
        return []

    compact = []

    for award in awards:
        if not isinstance(award, dict):
            continue

        compact.append({
            "cig": clean(award.get("cig")),
            "contractors": clean(award.get("contractors") or award.get("contractor_name")),
            "contractor_tax_codes": clean(award.get("contractor_tax_codes") or award.get("contractor_tax_code")),
            "award_date": clean(award.get("award_date")),
            "award_result": clean(award.get("award_result")),
            "award_amount_eur": clean(award.get("award_amount_eur")),
        })

    return sorted(
        compact,
        key=lambda x: (
            x.get("cig", ""),
            x.get("contractors", ""),
            x.get("award_date", ""),
        )
    )


def record_signature(record):
    payload = {
        field: clean(record.get(field))
        for field in SIGNATURE_FIELDS
    }

    payload["has_contractor"] = has_contractor(record)
    payload["awards"] = compact_awards(record)

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def branch_from_path(path):
    return path.stem.replace("_part_001", "")


def build_previous_index(previous_dir):
    previous = {}

    if not previous_dir.exists():
        return previous

    for path in previous_dir.glob("*.json"):
        if path.name == "index.json":
            continue

        try:
            container = load_json(path)
        except Exception:
            continue

        rows, _ = extract_rows(container)

        for record in rows:
            if not isinstance(record, dict):
                continue

            key = record_key(record)

            if key in previous:
                continue

            previous[key] = {
                "signature": record_signature(record),
                "has_contractor": has_contractor(record),
                "branch": clean(record.get("branch")) or branch_from_path(path),
            }

    return previous


def clear_change_fields(record):
    changed = False

    for field in CHANGE_FIELDS:
        if field in record:
            record.pop(field, None)
            changed = True

    return changed


def annotate_current_files(previous, current_dir, manifest_path):
    run_id = datetime.now(timezone.utc).strftime("%Y-%m")
    generated_at = datetime.now(timezone.utc).isoformat()

    current_keys = set()
    by_branch = defaultdict(lambda: {
        "branch": "",
        "new": 0,
        "updated": 0,
        "anac_added": 0,
        "removed": 0,
        "total_changes": 0,
    })

    totals = {
        "new_records": 0,
        "updated_records": 0,
        "anac_added_records": 0,
    }

    files_processed = 0
    files_changed = 0

    for path in current_dir.glob("*.json"):
        if path.name == "index.json":
            continue

        container = load_json(path)
        rows, row_key = extract_rows(container)

        file_changed = False
        files_processed += 1

        for record in rows:
            if not isinstance(record, dict):
                continue

            key = record_key(record)
            current_keys.add(key)

            branch = clean(record.get("branch")) or branch_from_path(path)
            by_branch[branch]["branch"] = branch

            prev = previous.get(key)
            badges = []
            status = ""

            clear_changed = clear_change_fields(record)

            if prev is None:
                status = "new"
                badges.append("Nuovo nel radar")
                totals["new_records"] += 1
                by_branch[branch]["new"] += 1

            else:
                current_has_contractor = has_contractor(record)
                previous_has_contractor = bool(prev.get("has_contractor"))
                signature_changed = record_signature(record) != prev.get("signature")

                if current_has_contractor and not previous_has_contractor:
                    status = "anac_added"
                    badges.append("ANAC aggiunto")
                    totals["anac_added_records"] += 1
                    by_branch[branch]["anac_added"] += 1

                elif signature_changed:
                    status = "updated"
                    badges.append("Aggiornato")
                    totals["updated_records"] += 1
                    by_branch[branch]["updated"] += 1

            if badges:
                record["change_status"] = status
                record["change_badges"] = badges
                record["change_run"] = run_id
                file_changed = True
                by_branch[branch]["total_changes"] += 1
            elif clear_changed:
                file_changed = True

        if file_changed:
            write_json(path, save_rows(container, row_key, rows))
            files_changed += 1

    removed_keys = set(previous.keys()) - current_keys

    for key in removed_keys:
        prev_branch = previous[key].get("branch") or "Non assegnata"
        by_branch[prev_branch]["branch"] = prev_branch
        by_branch[prev_branch]["removed"] += 1
        by_branch[prev_branch]["total_changes"] += 1

    branches_payload = [
        value for value in by_branch.values()
        if value["total_changes"] > 0
    ]

    branches_payload.sort(
        key=lambda x: (
            x["new"] + x["updated"] + x["anac_added"],
            x["new"],
            x["anac_added"],
        ),
        reverse=True,
    )

    manifest = {
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "previous_unique_records": len(previous),
        "current_unique_records": len(current_keys),
        "new_records": totals["new_records"],
        "updated_records": totals["updated_records"],
        "anac_added_records": totals["anac_added_records"],
        "removed_records": len(removed_keys),
        "branches_with_news": sum(
            1 for b in branches_payload
            if b["new"] or b["updated"] or b["anac_added"]
        ),
        "files_processed": files_processed,
        "files_changed": files_changed,
        "by_branch": branches_payload,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest)

    print(f"[OK] Manifest delta scritto: {manifest_path}")
    print(f"Previous records: {len(previous)}")
    print(f"Current records: {len(current_keys)}")
    print(f"Nuovi: {totals['new_records']}")
    print(f"Aggiornati: {totals['updated_records']}")
    print(f"ANAC aggiunto: {totals['anac_added_records']}")
    print(f"Rimossi: {len(removed_keys)}")
    print(f"File modificati: {files_changed}/{files_processed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", default="tmp/previous_branches")
    parser.add_argument("--current", default="docs/data/branches")
    parser.add_argument("--manifest", default="docs/data/update_manifest.json")
    args = parser.parse_args()

    previous_dir = Path(args.previous)
    current_dir = Path(args.current)
    manifest_path = Path(args.manifest)

    if not current_dir.exists():
        raise SystemExit(f"Cartella shard corrente non trovata: {current_dir}")

    previous = build_previous_index(previous_dir)
    annotate_current_files(previous, current_dir, manifest_path)


if __name__ == "__main__":
    main()
