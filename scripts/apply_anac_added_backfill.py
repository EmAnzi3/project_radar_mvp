import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from apply_monthly_delta import extract_rows, record_key


BADGE = "ANAC aggiunto"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def save_rows(container, row_key, rows):
    if isinstance(container, list):
        return rows

    if isinstance(container, dict) and row_key:
        container[row_key] = rows
        return container

    return container


def normalize_badges(value):
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    text = str(value or "").strip()
    return [text] if text else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path(
            "reports/anac_added_backfill_audit.csv"
        ),
    )
    parser.add_argument(
        "--shards",
        type=Path,
        default=Path("docs/data/branches"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/data/update_manifest.json"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path(
            "reports/anac_added_backfill_applied.json"
        ),
    )
    parser.add_argument(
        "--baseline-commit",
        default="2865b35",
    )
    parser.add_argument(
        "--current-commit",
        default="04e60f3",
    )
    args = parser.parse_args()

    if not args.audit.exists():
        raise SystemExit(
            f"Audit ANAC mancante: {args.audit}"
        )

    audit_rows = []

    with args.audit.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter=";")
        audit_rows = list(reader)

    added_keys = {
        str(row.get("key") or "").strip()
        for row in audit_rows
        if str(row.get("key") or "").strip()
    }

    branch_counts = Counter(
        str(row.get("branch") or "NON ASSEGNATA").strip()
        for row in audit_rows
    )

    if not added_keys:
        raise SystemExit(
            "ERRORE: audit privo di record ANAC aggiunti"
        )

    print(f"Chiavi ANAC da applicare: {len(added_keys):,}")

    matched_keys = set()
    modified_files = 0
    modified_copies = 0

    for path in sorted(args.shards.glob("*.json")):
        if path.name == "index.json":
            continue

        container = load_json(path)
        rows, row_key = extract_rows(container)
        file_changed = False

        for record in rows:
            if not isinstance(record, dict):
                continue

            key = record_key(record)

            if key not in added_keys:
                continue

            matched_keys.add(key)

            badges = normalize_badges(
                record.get("change_badges")
            )

            if BADGE not in badges:
                badges.append(BADGE)
                record["change_badges"] = badges
                file_changed = True

            # Conserva "new" o "updated" quando già presenti.
            # Usa anac_added solo quando non esiste altro stato.
            if not str(
                record.get("change_status") or ""
            ).strip():
                record["change_status"] = "anac_added"
                file_changed = True

            record["anac_added_run"] = (
                datetime.now(timezone.utc)
                .date()
                .isoformat()
            )

            modified_copies += 1

        if file_changed:
            write_json(
                path,
                save_rows(container, row_key, rows),
            )
            modified_files += 1

    missing = added_keys - matched_keys

    if missing:
        raise SystemExit(
            "ERRORE: chiavi ANAC non trovate negli shard: "
            f"{len(missing):,}"
        )

    manifest = load_json(args.manifest)

    existing_rows = (
        manifest.get("by_branch")
        if isinstance(manifest.get("by_branch"), list)
        else []
    )

    by_branch = {}

    for row in existing_rows:
        if not isinstance(row, dict):
            continue

        branch = str(row.get("branch") or "").strip()

        if branch:
            by_branch[branch] = dict(row)

    all_branches = set(by_branch) | set(branch_counts)

    result_rows = []

    for branch in all_branches:
        row = by_branch.get(
            branch,
            {
                "branch": branch,
                "new": 0,
                "updated": 0,
                "anac_added": 0,
                "removed": 0,
            },
        )

        row["anac_added"] = int(
            branch_counts.get(branch, 0)
        )

        row["total_changes"] = sum(
            int(row.get(field) or 0)
            for field in (
                "new",
                "updated",
                "anac_added",
                "removed",
            )
        )

        result_rows.append(row)

    result_rows.sort(
        key=lambda row: (
            int(row.get("total_changes") or 0),
            int(row.get("new") or 0),
            int(row.get("anac_added") or 0),
        ),
        reverse=True,
    )

    manifest["anac_added_records"] = len(added_keys)
    manifest["by_branch"] = result_rows
    manifest["branches_with_news"] = sum(
        1
        for row in result_rows
        if (
            int(row.get("new") or 0)
            or int(row.get("updated") or 0)
            or int(row.get("anac_added") or 0)
        )
    )

    manifest["anac_generated_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )
    manifest["anac_baseline_commit"] = (
        args.baseline_commit
    )
    manifest["anac_current_commit"] = (
        args.current_commit
    )

    # Non vengono modificati:
    # new_records, updated_records, removed_records,
    # previous_unique_records, current_unique_records.
    write_json(args.manifest, manifest)

    summary = {
        "baseline_commit": args.baseline_commit,
        "current_commit": args.current_commit,
        "anac_added_records": len(added_keys),
        "matched_records": len(matched_keys),
        "modified_shard_files": modified_files,
        "modified_record_copies": modified_copies,
        "by_branch": [
            {
                "branch": branch,
                "anac_added": count,
            }
            for branch, count
            in branch_counts.most_common()
        ],
    }

    args.summary.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.summary.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"ANAC aggiunti: {len(added_keys):,}")
    print(f"Chiavi trovate: {len(matched_keys):,}")
    print(f"Copie aggiornate: {modified_copies:,}")
    print(f"Shard modificati: {modified_files:,}")
    print(f"Manifest aggiornato: {args.manifest}")
    print(f"Summary: {args.summary}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
