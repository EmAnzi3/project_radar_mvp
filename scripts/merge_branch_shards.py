import argparse
import json
from pathlib import Path

from apply_monthly_delta import record_key


def extract_rows(payload):
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            if isinstance(payload.get(key), list):
                return payload[key]

    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("docs/data/branches"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/master_projects_from_shards.json"),
    )
    args = parser.parse_args()

    index_path = args.input_dir / "index.json"

    if not index_path.exists():
        raise SystemExit(f"Indice shard mancante: {index_path}")

    index = json.loads(index_path.read_text(encoding="utf-8"))

    files_seen = set()
    records_by_key = {}

    physical_rows = 0
    duplicate_rows = 0

    for branch in index.get("branches", []):
        for file_info in branch.get("files", []):
            filename = str(file_info.get("file") or "").strip()

            if not filename or filename in files_seen:
                continue

            files_seen.add(filename)
            path = args.input_dir / filename

            if not path.exists():
                raise SystemExit(f"Shard mancante: {path}")

            payload = json.loads(path.read_text(encoding="utf-8"))
            part_rows = extract_rows(payload)

            print(f"[LOAD] {filename}: {len(part_rows):,}")

            for record in part_rows:
                if not isinstance(record, dict):
                    continue

                physical_rows += 1
                key = record_key(record)

                if key in records_by_key:
                    duplicate_rows += 1
                    continue

                records_by_key[key] = record

    rows = list(records_by_key.values())
    expected = int(index.get("unique_records") or 0)

    print()
    print(f"[SUMMARY] File letti: {len(files_seen)}")
    print(f"[SUMMARY] Righe fisiche: {physical_rows:,}")
    print(f"[SUMMARY] Duplicazioni tra filiali: {duplicate_rows:,}")
    print(f"[SUMMARY] Record unici ricomposti: {len(rows):,}")
    print(f"[SUMMARY] Record unici attesi: {expected:,}")

    if expected and len(rows) != expected:
        raise SystemExit(
            "Conteggio univoco incoerente: "
            f"ricomposti={len(rows)} attesi={expected}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"[OK] Master temporaneo: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
