import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CHANGE_FIELDS = (
    "change_status",
    "change_badges",
    "change_run",
    "change_summary",
)


def clean(value: Any) -> str:
    return str(value or "").strip()


def norm(value: Any) -> str:
    return clean(value).upper()


def record_key(record: dict) -> str:
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


def extract_rows(payload: Any) -> tuple[list[dict], str | None]:
    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows, key

    return [], None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def marker_from(record: dict) -> dict:
    marker = {}

    for field in CHANGE_FIELDS:
        if field not in record:
            continue

        value = record.get(field)

        if value in (None, "", []):
            continue

        marker[field] = value

    return marker


def merge_marker(current: dict, incoming: dict) -> dict:
    result = dict(current)

    incoming_badges = incoming.get("change_badges")
    current_badges = result.get("change_badges")

    if isinstance(incoming_badges, list):
        badges = []

        for value in (
            current_badges
            if isinstance(current_badges, list)
            else []
        ) + incoming_badges:
            text = clean(value)
            if text and text not in badges:
                badges.append(text)

        if badges:
            result["change_badges"] = badges

    for field in (
        "change_status",
        "change_run",
        "change_summary",
    ):
        if not result.get(field) and incoming.get(field):
            result[field] = incoming[field]

    return result


def load_markers(shard_dir: Path) -> dict[str, dict]:
    markers: dict[str, dict] = {}

    for path in sorted(shard_dir.glob("*.json")):
        if path.name == "index.json":
            continue

        rows, _ = extract_rows(load_json(path))

        for record in rows:
            if not isinstance(record, dict):
                continue

            marker = marker_from(record)
            if not marker:
                continue

            key = record_key(record)

            if key in markers:
                markers[key] = merge_marker(markers[key], marker)
            else:
                markers[key] = marker

    return markers


def write_master(
    path: Path,
    payload: Any,
    rows: list[dict],
    row_key: str | None,
) -> None:
    if row_key is None:
        output = rows
    else:
        output = dict(payload)
        output[row_key] = rows

    path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shards",
        type=Path,
        default=Path("docs/data/branches"),
    )
    parser.add_argument(
        "--master",
        type=Path,
        default=Path("reports/master_projects.json"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("tmp/change_markers_summary.json"),
    )
    args = parser.parse_args()

    if not args.master.exists():
        raise SystemExit(f"Master mancante: {args.master}")

    markers = load_markers(args.shards)

    payload = load_json(args.master)
    rows, row_key = extract_rows(payload)

    applied = 0
    missing_keys = []

    for record in rows:
        if not isinstance(record, dict):
            continue

        marker = markers.get(record_key(record))

        if not marker:
            continue

        for field, value in marker.items():
            record[field] = value

        applied += 1

    master_keys = {
        record_key(record)
        for record in rows
        if isinstance(record, dict)
    }

    for key in markers:
        if key not in master_keys:
            missing_keys.append(key)

    print(f"Marker sorgente: {len(markers):,}")
    print(f"Marker riapplicati: {applied:,}")
    print(f"Marker mancanti: {len(missing_keys):,}")

    if applied != len(markers):
        raise SystemExit(
            "ERRORE: non tutti i marker OpenCUP sono stati "
            f"riapplicati ({applied}/{len(markers)})"
        )

    write_master(args.master, payload, rows, row_key)

    summary = {
        "source_markers": len(markers),
        "applied_markers": applied,
        "missing_markers": len(missing_keys),
        "master_records": len(rows),
    }

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] Master aggiornato: {args.master}")
    print(f"[OK] Summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
