import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def clean(v):
    return str(v or "").strip()


def norm(v):
    return clean(v).upper()


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

    return "HASH::" + hashlib.sha1(
        blob.encode("utf-8")
    ).hexdigest()


def extract_rows(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows

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


def load_bytes(raw):
    return json.loads(raw.decode("utf-8-sig"))


def iter_fs_records(shard_dir):
    for path in sorted(Path(shard_dir).glob("*.json")):
        if path.name == "index.json":
            continue

        payload = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        for row in extract_rows(payload):
            if isinstance(row, dict):
                yield row


def iter_git_records(ref, prefix="docs/data/branches"):
    result = subprocess.run(
        [
            "git", "ls-tree", "-r", "--name-only",
            ref, prefix
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    paths = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".json")
        and not line.strip().endswith("/index.json")
    ]

    for path in sorted(paths):
        raw = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            check=True,
            capture_output=True,
        ).stdout

        payload = load_bytes(raw)

        for row in extract_rows(payload):
            if isinstance(row, dict):
                yield row


def create_snapshot(records):
    seen = set()
    with_contractor = set()
    total = 0

    for row in records:
        key = record_key(row)

        if key in seen:
            continue

        seen.add(key)
        total += 1

        if has_contractor(row):
            with_contractor.add(key)

    return {
        "total_records": total,
        "with_contractor_count": len(with_contractor),
        "with_contractor_keys": sorted(with_contractor),
    }


def snapshot_command(args):
    if args.git_ref:
        records = iter_git_records(args.git_ref)
        source = f"git:{args.git_ref}"
    else:
        records = iter_fs_records(args.shards)
        source = str(args.shards)

    payload = create_snapshot(records)
    payload["source"] = source
    payload["generated_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Snapshot:", source)
    print("Record:", payload["total_records"])
    print(
        "Con contractor:",
        payload["with_contractor_count"]
    )


def build_command(args):
    snapshot = json.loads(
        Path(args.snapshot).read_text(
            encoding="utf-8-sig"
        )
    )

    before = set(
        snapshot.get("with_contractor_keys") or []
    )

    seen = set()
    added = []

    for row in iter_fs_records(args.shards):
        key = record_key(row)

        if key in seen:
            continue
        seen.add(key)

        if not has_contractor(row):
            continue

        if key in before:
            continue

        added.append({
            "key": key,
            "branch": clean(row.get("branch")),
            "cup": clean(row.get("cup")),
            "cig": clean(row.get("cig")),
            "title": clean(row.get("title")),
            "contractors": clean(
                row.get("contractors")
                or row.get("contractors_summary")
            ),
            "contractor_tax_codes": clean(
                row.get("contractor_tax_codes")
            ),
        })

    added.sort(
        key=lambda r: (r["branch"], r["key"])
    )

    by_branch = Counter(
        row["branch"] for row in added
    )

    payload = {
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "count": len(added),
        "by_branch": [
            {
                "branch": branch,
                "anac_added": count,
            }
            for branch, count
            in sorted(by_branch.items())
        ],
        "records": added,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.sync_manifest:
        manifest_path = Path(args.sync_manifest)
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8-sig"
            )
        )

        manifest["anac_added_records"] = len(added)
        manifest["new_company_match_projects"] = len(added)

        exact = dict(by_branch)

        existing = {
            str(row.get("branch") or ""): row
            for row in manifest.get("by_branch", [])
            if isinstance(row, dict)
        }

        all_branches = sorted(
            set(existing) | set(exact)
        )

        rows = []

        for branch in all_branches:
            row = dict(existing.get(branch) or {})
            row["branch"] = branch
            row["anac_added"] = int(
                exact.get(branch, 0)
            )
            rows.append(row)

        manifest["by_branch"] = rows
        manifest["note"] = (
            "Conteggio esatto dei record passati da "
            "senza contractor a con contractor "
            "nell'ultimo refresh ANAC."
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print()
    print("ANAC aggiunti ESATTI:", len(added))
    print("Filiali interessate:", len(by_branch))
    print()

    for branch, count in sorted(
        by_branch.items(),
        key=lambda x: (-x[1], x[0])
    ):
        print(f"{branch}: {count}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    snap = sub.add_parser("snapshot")
    snap.add_argument(
        "--shards",
        default="docs/data/branches",
    )
    snap.add_argument("--git-ref")
    snap.add_argument(
        "--out",
        default="tmp/anac_contractors_before.json",
    )

    build = sub.add_parser("build")
    build.add_argument(
        "--snapshot",
        default="tmp/anac_contractors_before.json",
    )
    build.add_argument(
        "--shards",
        default="docs/data/branches",
    )
    build.add_argument(
        "--out",
        default="docs/data/anac_added_records.json",
    )
    build.add_argument("--sync-manifest")

    args = parser.parse_args()

    if args.command == "snapshot":
        snapshot_command(args)
    else:
        build_command(args)


if __name__ == "__main__":
    main()
