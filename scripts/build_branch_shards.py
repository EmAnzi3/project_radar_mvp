import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def safe_slug(value: str) -> str:
    value = str(value or "").strip()

    if not value:
        value = "NON ASSEGNATA"

    lowered = value.lower().strip()

    special = {
        "non assegnata": "NON_ASSEGNATA",
        "non_assegnata": "NON_ASSEGNATA",
        "ambigua": "AMBIGUA",
    }

    if lowered in special:
        return special[lowered]

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")

    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value)
    slug = re.sub(r"_+", "_", slug).strip("_")

    return slug or "NON_ASSEGNATA"


def load_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["projects", "records", "items", "data"]:
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError("Formato JSON non riconosciuto.")


def split_candidates(value):
    if not value:
        return []

    if isinstance(value, list):
        raw = value
    else:
        raw = str(value).split("|")

    return [str(x).strip() for x in raw if str(x).strip()]


def record_branch_list(record):
    values = []

    branch = str(record.get("branch") or "").strip()

    if branch == "AMBIGUA":
        values.append("AMBIGUA")
    elif branch and branch != "NON ASSEGNATA":
        values.append(branch)

    for candidate in split_candidates(record.get("branch_candidates")):
        values.append(candidate)

    if not values:
        values.append("NON ASSEGNATA")

    out = []
    seen = set()

    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)

    return out


def compact_json(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def write_json(path: Path, payload):
    path.write_text(compact_json(payload), encoding="utf-8", newline="\n")


def split_records(records, max_bytes):
    chunks = []
    current = []
    current_size = 0

    for record in records:
        record_size = len(compact_json(record).encode("utf-8")) + 2

        if current and current_size + record_size > max_bytes:
            chunks.append(current)
            current = []
            current_size = 0

        current.append(record)
        current_size += record_size

    if current:
        chunks.append(current)

    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reports/master_projects.json")
    parser.add_argument("--out-dir", default="docs/data/branches")
    parser.add_argument("--max-file-mb", type=float, default=90.0)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    max_bytes = int(args.max_file_mb * 1024 * 1024)

    if not input_path.exists():
        print(f"ERRORE: input non trovato: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    for old_file in out_dir.glob("*.json"):
        old_file.unlink()

    records = load_records(input_path)

    shards = {}

    for record in records:
        if not isinstance(record, dict):
            continue

        for branch in record_branch_list(record):
            shards.setdefault(branch, []).append(record)

    generated_at = datetime.now(timezone.utc).isoformat()

    index = {
        "generated_at_utc": generated_at,
        "source": str(input_path).replace("\\", "/"),
        "unique_records": len(records),
        "total_logical_branches": len(shards),
        "max_file_mb": args.max_file_mb,
        "branches": [],
        "warnings": [],
    }

    for branch_name in sorted(shards.keys()):
        slug = safe_slug(branch_name)
        rows = shards[branch_name]
        chunks = split_records(rows, max_bytes)

        branch_entry = {
            "branch": branch_name,
            "slug": slug,
            "count": len(rows),
            "parts": len(chunks),
            "files": [],
        }

        for i, chunk in enumerate(chunks, start=1):
            if len(chunks) == 1:
                file_name = f"{slug}.json"
            else:
                file_name = f"{slug}_part_{i:03d}.json"

            out_path = out_dir / file_name

            payload = {
                "generated_at_utc": generated_at,
                "branch": branch_name,
                "slug": slug,
                "part": i,
                "parts": len(chunks),
                "count": len(chunk),
                "projects": chunk,
            }

            write_json(out_path, payload)

            size_bytes = out_path.stat().st_size
            size_mb = round(size_bytes / 1024 / 1024, 2)

            file_entry = {
                "file": file_name,
                "count": len(chunk),
                "size_bytes": size_bytes,
                "size_mb": size_mb,
            }

            branch_entry["files"].append(file_entry)

            if size_bytes > 95 * 1024 * 1024:
                index["warnings"].append({
                    "branch": branch_name,
                    "slug": slug,
                    "file": file_name,
                    "size_mb": size_mb,
                    "reason": "File sopra soglia prudenziale 95 MB",
                })

        branch_entry["total_size_bytes"] = sum(f["size_bytes"] for f in branch_entry["files"])
        branch_entry["total_size_mb"] = round(branch_entry["total_size_bytes"] / 1024 / 1024, 2)

        index["branches"].append(branch_entry)

    index["branches"].sort(key=lambda x: (-x["count"], x["branch"]))

    write_json(out_dir / "index.json", index)

    print(f"OK: record unici input: {len(records)}")
    print(f"OK: filiali logiche: {len(shards)}")
    print(f"OK: index scritto: {out_dir / 'index.json'}")

    multi = [b for b in index["branches"] if b["parts"] > 1]
    if multi:
        print("")
        print("Shard multi-file:")
        for b in multi:
            print(f"- {b['branch']}: {b['parts']} parti, {b['total_size_mb']} MB totali")

    if index["warnings"]:
        print("")
        print("ATTENZIONE: file sopra soglia:")
        for w in index["warnings"]:
            print(f"- {w['branch']} / {w['file']}: {w['size_mb']} MB")
        sys.exit(2)


if __name__ == "__main__":
    main()
