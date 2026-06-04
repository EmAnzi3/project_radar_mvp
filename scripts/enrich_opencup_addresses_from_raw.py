import argparse
import csv
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("reports/master_projects.json")
DEFAULT_OUTPUT = Path("reports/master_projects_with_opencup_addresses_preview.json")
DEFAULT_AUDIT = Path("reports/opencup_address_enrichment_audit.csv")
RAW_DIR = Path("data/raw/opencup")

INVALID_VALUES = {
    "",
    "-",
    "ND",
    "N.D.",
    "NON PRESENTE",
    "DATO NON PRESENTE",
    "**********",
    "***************",
}

STREET_RE = re.compile(r"\b(via|viale|piazza|piazzale|corso|largo|vicolo|strada)\b", re.I)
HOUSE_NUMBER_RE = re.compile(
    r"(?:,\s*|(?:\bcivico\b|\bciv\.?\b|\bn\.?\b|\bnumero\b)\s*|\s+)"
    r"(\d+[a-z]?(?:/[a-z0-9]+)?)\b",
    re.I,
)

GENERIC_RE = re.compile(
    r"(territorio comunale|intero comune|comune di\s+[a-zà-ù'\s]+\(?[a-z]{2}\)?$|"
    r"varie localit|localit[aà] varie|strade comunali|aree comunali|"
    r"edifici comunali|edifici scolastici|scuole comunali|area urbana|area vasta|"
    r"tratti vari|vie varie|diverse vie|diverse localit|ambito urbano|tutto il territorio)",
    re.I,
)

ROAD_NOISE_RE = re.compile(
    r"\b(provinciale|statale|regionale|comunale|ss|s\.s\.|sp|s\.p\.|sr|s\.r\.|"
    r"lotto|tronco|variante|fondovalle|tangenziale|collegamento|tratto)\b",
    re.I,
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_key(value: Any) -> str:
    text = clean(value).lower().replace("\ufeff", "")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def first_present(row: dict[str, Any], candidates: list[str]) -> str:
    normalized = {norm_key(k): v for k, v in row.items()}

    for candidate in candidates:
        key = norm_key(candidate)
        value = clean(normalized.get(key))
        if value:
            return value

    return ""


def detect_delimiter(sample: str) -> str:
    candidates = [";", "|", "\t", ","]
    return max(candidates, key=lambda d: sample.count(d))


def load_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data, data, None

    if isinstance(data, dict):
        for key in ["projects", "records", "items", "data", "rows"]:
            if isinstance(data.get(key), list):
                return data, data[key], key

    raise RuntimeError(f"Formato JSON non riconosciuto: {path}")


def write_records(path: Path, original_payload: Any, records: list[dict[str, Any]], list_key: str | None):
    path.parent.mkdir(parents=True, exist_ok=True)

    if list_key is None:
        payload = records
    else:
        payload = dict(original_payload)
        payload[list_key] = records

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_address(value: str) -> str:
    text = clean(value)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    if set(text) == {"*"}:
        return ""

    if text.upper() in INVALID_VALUES:
        return ""

    return text


def address_quality(address: str) -> str:
    addr = clean_address(address)

    if not addr:
        return "empty_or_placeholder"

    if GENERIC_RE.search(addr):
        return "generic"

    if not STREET_RE.search(addr):
        return "no_street_token"

    if ROAD_NOISE_RE.search(addr):
        return "road_or_linear_infrastructure"

    if HOUSE_NUMBER_RE.search(addr):
        return "street_with_number"

    return "street_without_number"


def iter_raw_rows():
    files = sorted(RAW_DIR.glob("*.csv")) + sorted(RAW_DIR.glob("*.zip"))

    for path in files:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                sample = f.read(8192)
                delimiter = detect_delimiter(sample)
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    yield path.name, row

        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                for name in zf.namelist():
                    if not name.lower().endswith(".csv"):
                        continue

                    with zf.open(name) as raw:
                        f = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="ignore", newline="")
                        sample = f.read(8192)
                        delimiter = detect_delimiter(sample)
                        f.seek(0)
                        reader = csv.DictReader(f, delimiter=delimiter)

                        for row in reader:
                            yield f"{path.name}->{name}", row


def build_raw_address_index(target_cups: set[str]) -> dict[str, dict[str, str]]:
    index = {}

    for label, row in iter_raw_rows():
        cup = first_present(row, ["CUP", "CODICE_CUP", "codice cup", "codice_cup"]).upper()
        if not cup or cup not in target_cups:
            continue

        if cup in index:
            continue

        address = clean_address(first_present(row, [
            "INDIRIZZO_INTERVENTO",
            "indirizzo intervento",
            "indirizzo_intervento",
            "indirizzo o area di riferimento",
            "area riferimento",
        ]))

        if not address:
            continue

        index[cup] = {
            "address": address,
            "address_source_field": "INDIRIZZO_INTERVENTO",
            "address_source_file": label,
            "raw_region": first_present(row, ["REGIONE", "DEN_REGIONE", "den_regione"]),
            "raw_province": first_present(row, ["PROVINCIA", "DEN_PROVINCIA", "SIGLA_PROVINCIA", "den_provincia"]),
            "raw_municipality": first_present(row, ["COMUNE", "DEN_COMUNE", "den_comune"]),
            "address_quality": address_quality(address),
        }

    return index


def write_audit(path: Path, rows: list[dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "status",
        "address_quality",
        "cup",
        "title",
        "branch",
        "region",
        "province",
        "municipality",
        "address",
        "address_source_file",
        "source_url",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    original_payload, records, list_key = load_records(args.input)

    target_cups = {
        clean(r.get("cup")).upper()
        for r in records
        if clean(r.get("cup"))
    }

    print(f"[LOAD] Record master: {len(records):,}")
    print(f"[LOAD] CUP target: {len(target_cups):,}")
    print("[RAW] Scansione raw OpenCUP...")

    raw_index = build_raw_address_index(target_cups)
    print(f"[RAW] CUP con INDIRIZZO_INTERVENTO trovato: {len(raw_index):,}")

    out_records = []
    audit_rows = []

    for r in records:
        item = dict(r)
        cup = clean(item.get("cup")).upper()
        raw = raw_index.get(cup)

        if raw:
            if not clean(item.get("address")):
                item["address"] = raw["address"]

            item["address_source_field"] = raw["address_source_field"]
            item["address_source_file"] = raw["address_source_file"]
            item["address_quality"] = raw["address_quality"]

            status = "enriched"
        else:
            status = "not_found"

        out_records.append(item)

        audit_rows.append({
            "status": status,
            "address_quality": clean(item.get("address_quality")),
            "cup": cup,
            "title": clean(item.get("title"))[:250],
            "branch": clean(item.get("branch")),
            "region": clean(item.get("region")),
            "province": clean(item.get("province")),
            "municipality": clean(item.get("municipality")),
            "address": clean(item.get("address"))[:250],
            "address_source_file": clean(item.get("address_source_file")),
            "source_url": clean(item.get("source_url")),
        })

    output_path = args.input if args.apply else args.output

    write_records(output_path, original_payload, out_records, list_key)
    write_audit(args.audit, audit_rows)

    counts = Counter(row["status"] for row in audit_rows)
    quality = Counter(row["address_quality"] or "none" for row in audit_rows)

    print(f"[OK] Output scritto: {output_path}")
    print(f"[OK] Audit scritto: {args.audit}")
    print("[SUMMARY status]")
    for key, count in counts.most_common():
        print(f"- {key}: {count:,}")

    print("[SUMMARY quality]")
    for key, count in quality.most_common():
        print(f"- {key}: {count:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
