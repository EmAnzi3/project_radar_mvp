import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".")
ANAC_CUP_ZIP = ROOT / "data" / "raw" / "anac" / "cup.zip"

TARGETS_CSV = ROOT / "reports" / "national_anac_cup_targets.csv"
BRANCH_DIR = ROOT / "docs" / "data" / "branches"

OUT = ROOT / "reports" / "national_anac_cup_cig_matches.csv"
OUT_SUMMARY = ROOT / "reports" / "national_anac_cup_cig_summary.csv"
OUT_JSON = ROOT / "reports" / "national_anac_cup_cig_summary.json"


def clean(value):
    return str(value or "").strip()


def norm(value):
    return clean(value).upper()


def detect_delimiter(sample):
    if sample.count(";") >= sample.count(","):
        return ";"
    return ","


def normalized_field_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_cup_field(fields):
    normalized = {normalized_field_name(f): f for f in fields}

    for key in ["cup", "codicecup", "codicecupopera", "idcup"]:
        if key in normalized:
            return normalized[key]

    for field in fields:
        if "cup" in normalized_field_name(field):
            return field

    return None


def load_json_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def collect_targets_from_csv():
    if not TARGETS_CSV.exists():
        return set(), 0

    sample = TARGETS_CSV.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    delimiter = detect_delimiter(sample)

    cups = set()
    rows = 0

    with TARGETS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fields = reader.fieldnames or []
        cup_field = find_cup_field(fields)

        if not cup_field:
            raise SystemExit(f"Colonna CUP non trovata in {TARGETS_CSV}. Header: {fields}")

        for row in reader:
            rows += 1
            cup = norm(row.get(cup_field))

            if cup:
                cups.add(cup)

    return cups, rows


def collect_targets_from_shards():
    cups = set()
    rows = 0

    for path in sorted(BRANCH_DIR.glob("*.json")):
        if path.name == "index.json":
            continue

        for row in load_json_rows(path):
            if not isinstance(row, dict):
                continue

            rows += 1
            cup = norm(row.get("cup"))

            if cup:
                cups.add(cup)

    return cups, rows


def collect_target_cups():
    csv_cups, csv_rows = collect_targets_from_csv()

    if csv_cups:
        print(f"[OK] Target CUP da {TARGETS_CSV}: {len(csv_cups):,} CUP unici su {csv_rows:,} righe")
    else:
        print(f"[WARN] Target CSV mancante/vuoto: {TARGETS_CSV}")

    shard_cups = set()
    shard_rows = 0

    if BRANCH_DIR.exists():
        shard_cups, shard_rows = collect_targets_from_shards()
        print(f"[OK] Target CUP da shard: {len(shard_cups):,} CUP unici su {shard_rows:,} righe")
    else:
        print(f"[WARN] Cartella shard non trovata: {BRANCH_DIR}")

    target_cups = set(csv_cups) | set(shard_cups)

    print(f"[OK] Target CUP complessivi usati per match: {len(target_cups):,}")

    if csv_cups and shard_cups and len(csv_cups) < len(shard_cups) * 0.10:
        print(
            "[WARN] Il target CSV è molto più piccolo degli shard: "
            "probabile target ridotto/stale. Uso union CSV+shard."
        )

    return target_cups


def find_data_member(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        candidates = [
            info for info in zf.infolist()
            if info.filename.lower().endswith((".csv", ".txt"))
        ]

        if not candidates:
            raise SystemExit(f"Nessun CSV/TXT trovato in {zip_path}")

        candidates.sort(key=lambda x: x.file_size, reverse=True)
        return candidates[0].filename


def scan_anac_cup_zip(target_cups):
    if not ANAC_CUP_ZIP.exists():
        raise SystemExit(f"Manca file ANAC: {ANAC_CUP_ZIP}")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    member_name = find_data_member(ANAC_CUP_ZIP)

    raw_rows = 0
    match_rows = 0
    matched_cups = set()
    matched_cigs = set()
    cup_to_cig_count = defaultdict(int)

    with zipfile.ZipFile(ANAC_CUP_ZIP, "r") as zf:
        with zf.open(member_name, "r") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
            reader = csv.DictReader(text, delimiter=";")

            fields = reader.fieldnames or []

            if "CUP" not in fields or "CIG" not in fields:
                raise SystemExit(f"Colonne CUP/CIG non trovate. Header: {fields}")

            with OUT.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["cup", "cig"],
                    delimiter=";"
                )
                writer.writeheader()

                for row in reader:
                    raw_rows += 1

                    cup = norm(row.get("CUP"))
                    if not cup or cup not in target_cups:
                        continue

                    cig = norm(row.get("CIG"))
                    if not cig:
                        continue

                    writer.writerow({
                        "cup": cup,
                        "cig": cig,
                    })

                    match_rows += 1
                    matched_cups.add(cup)
                    matched_cigs.add(cig)
                    cup_to_cig_count[cup] += 1

                    if raw_rows % 1_000_000 == 0:
                        print(
                            f"[SCAN] raw={raw_rows:,} | "
                            f"match_rows={match_rows:,} | "
                            f"matched_cups={len(matched_cups):,}"
                        )

    unmatched_cups = target_cups - matched_cups

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "anac_zip": str(ANAC_CUP_ZIP),
        "anac_member": member_name,
        "target_cups": len(target_cups),
        "anac_rows_scanned": raw_rows,
        "match_rows": match_rows,
        "matched_target_cups": len(matched_cups),
        "unmatched_target_cups": len(unmatched_cups),
        "matched_unique_cigs": len(matched_cigs),
        "coverage_target_cups_pct": round((len(matched_cups) / len(target_cups)) * 100, 2) if target_cups else 0,
        "avg_cig_per_matched_cup": round(match_rows / len(matched_cups), 2) if matched_cups else 0,
    }

    return summary


def write_summary_csv(summary):
    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["metric", "value"],
            delimiter=";"
        )
        writer.writeheader()

        for key, value in summary.items():
            writer.writerow({
                "metric": key,
                "value": value,
            })


def main():
    print("[1/2] Carico CUP target...")
    target_cups = collect_target_cups()

    if not target_cups:
        raise SystemExit("Nessun CUP target trovato.")

    print("")
    print("[2/2] Match CUP-CIG su cup.zip ANAC...")
    summary = scan_anac_cup_zip(target_cups)

    write_summary_csv(summary)
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("")
    print("=== NATIONAL ANAC CUP-CIG MATCH ===")
    print(f"CUP target: {summary['target_cups']:,}")
    print(f"Righe ANAC scansionate: {summary['anac_rows_scanned']:,}")
    print(f"Righe match CUP-CIG: {summary['match_rows']:,}")
    print(f"CUP target con almeno un CIG: {summary['matched_target_cups']:,}")
    print(f"CUP target senza CIG: {summary['unmatched_target_cups']:,}")
    print(f"CIG unici matchati: {summary['matched_unique_cigs']:,}")
    print(f"Copertura CUP target: {summary['coverage_target_cups_pct']}%")
    print(f"CIG medi per CUP matchato: {summary['avg_cig_per_matched_cup']}")

    print("")
    print(f"[OK] Output: {OUT}")
    print(f"[OK] Summary CSV: {OUT_SUMMARY}")
    print(f"[OK] Summary JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
