import argparse
import csv
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("reports/master_projects_with_opencup_addresses_preview.json")
DEFAULT_OUTPUT = Path("reports/master_projects_with_maps_ultra_strict_preview.json")
DEFAULT_AUDIT = Path("reports/google_maps_links_ultra_strict_audit.csv")

STREET_RE = re.compile(
    r"\b(via|viale|piazza|piazzale|corso|largo|vicolo|strada)\b",
    re.I,
)

NUMBER_RE = re.compile(
    r"(?:,\s*|(?:\bcivico\b|\bciv\.?\b|\bn\.?\b|\bnumero\b)\s*|\s+)"
    r"(\d+[a-z]?(?:/[a-z0-9]+)?)\b",
    re.I,
)

GENERIC_RE = re.compile(
    r"(territorio comunale|intero comune|comune di\s+[a-zà-ù'\s]+\(?[a-z]{2}\)?$|"
    r"varie localit|localit[aà] varie|strade comunali|aree comunali|"
    r"edifici comunali|edifici scolastici|scuole comunali|area urbana|area vasta|"
    r"tratti vari|vie varie|diverse vie|diverse localit|ambito urbano|sub ambito|"
    r"tutto il territorio)",
    re.I,
)

ROAD_NOISE_RE = re.compile(
    r"(\bs\.?\s*s\.?\b|\bs\.?\s*p\.?\b|\bs\.?\s*r\.?\b|\bss\b|\bsp\b|\bsr\b|"
    r"\bss\s*\d+\b|\bsp\s*\d+\b|\bsr\s*\d+\b|\bsrt\s*\d+\b|\ba\s*\d+\b|"
    r"\bautostrada\b|\bsuperstrada\b|\braccordo\b|\bsvincolo\b|"
    r"\bkm\b|\bkm\.|\bchilometr|"
    r"\bprovinciale\b|\bstatale\b|\bregionale\b|\bcomunale\b|"
    r"\blotto\b|\btronco\b|\bvariante\b|\bfondovalle\b|\btangenziale\b|"
    r"\bcollegamento\b|\bitinerario\b|\btratto\b)",
    re.I,
)

INVALID_GEO = {
    "",
    "TUTTI",
    "TUTTE",
    "VARI",
    "VARIE",
    "NAZIONALE",
    "ITALIA",
    "ND",
    "N.D.",
    "-",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm(value: Any) -> str:
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def valid_geo(value: Any) -> bool:
    return norm(value) not in INVALID_GEO


def street_token_count(address: str) -> int:
    return len(STREET_RE.findall(address or ""))


def significant_numbers(address: str) -> list[str]:
    numbers = []

    for m in re.finditer(r"\b\d+[a-z]?(?:/[a-z0-9]+)?\b", address or "", re.I):
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)

        if not digits:
            continue

        n = int(digits)

        # Esclude anni e CAP.
        if 1900 <= n <= 2099:
            continue
        if len(digits) == 5:
            continue

        numbers.append(raw)

    return numbers


def has_locality_tail(address: str) -> bool:
    return bool(re.search(r"\b(loc\.?|localit[aà]|frazione)\b", address or "", re.I))


def has_multiple_addresses(address: str) -> bool:
    text = clean(address)

    if ";" in text:
        return True

    # Più vie/piazze nello stesso campo: di solito è elenco o area diffusa.
    if street_token_count(text) > 1:
        # Eccezione prudente: "Via Strada delle..." può essere un nome strada reale.
        if not re.search(r"\bvia\s+strada\b", text, re.I):
            return True

    # Esempi: 19-21-23, 1-3-5-7.
    if re.search(r"\b\d+\s*-\s*\d+\s*-\s*\d+", text):
        return True

    # Esempio: "42 - C. Poerio, 1/11 - ..."
    if re.search(r"\b\d+\s*-\s*[A-Z]", text, re.I):
        return True

    return False


def clean_address_for_query(address: Any, municipality: Any, province: Any, region: Any) -> str:
    text = clean(address)
    text = re.sub(r"[\u0080-\u009f]", " ", text)
    text = text.replace("–", " - ").replace("—", " - ")
    text = re.sub(r"\s+", " ", text).strip(" ,.;-")

    # Rimuove CAP.
    text = re.sub(r"\b\d{5}\b", "", text).strip(" ,.;-")

    # Rimuove sigla provincia finale tipo (VT).
    text = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", text).strip(" ,.;-")

    # Rimuove Comune/Provincia/Regione se ripetuti in fondo all'indirizzo.
    for geo in [municipality, province, region]:
        geo = clean(geo)
        if not geo:
            continue

        pattern = rf"[, \-]+\b{re.escape(geo)}\b\.?$"
        text = re.sub(pattern, "", text, flags=re.I).strip(" ,.;-")

    # Pulizia doppie virgole/spazi.
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.;-")

    return text


def is_precise_address(address: str) -> tuple[bool, str]:
    addr = clean(address)

    if not addr or set(addr) == {"*"}:
        return False, "empty_or_placeholder"

    if GENERIC_RE.search(addr):
        return False, "generic"

    if has_multiple_addresses(addr):
        return False, "multiple_addresses"

    if len(addr) > 85:
        return False, "address_too_long"

    if has_locality_tail(addr):
        return False, "locality_tail"

    if ROAD_NOISE_RE.search(addr):
        return False, "road_or_linear_infrastructure"

    if not STREET_RE.search(addr):
        return False, "no_street_token"

    nums = significant_numbers(addr)

    if len(nums) == 0:
        return False, "street_without_number"

    if len(nums) > 1:
        return False, "multiple_numbers"

    number_match = NUMBER_RE.search(addr)
    if not number_match:
        return False, "street_without_number"

    raw_number = number_match.group(1)
    digits = re.sub(r"\D", "", raw_number)

    if not digits:
        return False, "street_without_number"

    n = int(digits)

    if 1900 <= n <= 2099:
        return False, "number_looks_like_year"

    if len(digits) == 5:
        return False, "number_looks_like_cap"

    return True, "ok_address_with_number"


def append_unique(parts: list[str], value: Any) -> None:
    value = clean(value)
    if not value:
        return

    if not valid_geo(value):
        return

    value_norm = norm(value)

    for existing in parts:
        if norm(existing) == value_norm:
            return

    parts.append(value)


def build_query(record: dict[str, Any]) -> str:
    address = clean_address_for_query(
        record.get("address"),
        record.get("municipality"),
        record.get("province"),
        record.get("region"),
    )

    parts = [address]

    append_unique(parts, record.get("municipality"))
    append_unique(parts, record.get("province"))
    append_unique(parts, record.get("region"))
    parts.append("Italia")

    return ", ".join(p for p in parts if clean(p))


def maps_url(query: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(query)


def write_audit(path: Path, rows: list[dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "reason",
        "maps_precision",
        "cup",
        "title",
        "branch",
        "region",
        "province",
        "municipality",
        "address",
        "maps_query",
        "maps_url",
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

    out_records = []
    audit_rows = []

    for record in records:
        r = dict(record)

        for key in ["maps_url", "maps_query", "maps_precision", "maps_source"]:
            r.pop(key, None)

        address = clean(r.get("address"))
        municipality = clean(r.get("municipality"))

        ok, reason = is_precise_address(address)

        query = ""
        url = ""

        if ok and valid_geo(municipality):
            query = build_query(r)

            if query:
                url = maps_url(query)

                r["maps_url"] = url
                r["maps_query"] = query
                r["maps_precision"] = "address_with_number"
                r["maps_source"] = "opencup_address"

                reason = "ok_address_with_number"
            else:
                reason = "empty_query"

        elif ok and not valid_geo(municipality):
            reason = "missing_municipality"

        out_records.append(r)

        audit_rows.append({
            "reason": reason,
            "maps_precision": clean(r.get("maps_precision")),
            "cup": clean(r.get("cup")),
            "title": clean(r.get("title"))[:250],
            "branch": clean(r.get("branch")),
            "region": clean(r.get("region")),
            "province": clean(r.get("province")),
            "municipality": clean(r.get("municipality")),
            "address": address[:250],
            "maps_query": query,
            "maps_url": url,
            "source_url": clean(r.get("source_url")),
        })

    output_path = args.input if args.apply else args.output

    write_records(output_path, original_payload, out_records, list_key)
    write_audit(args.audit, audit_rows)

    counts = Counter(row["reason"] for row in audit_rows)

    print(f"[OK] Record letti: {len(records):,}")
    print(f"[OK] Output scritto: {output_path}")
    print(f"[OK] Audit scritto: {args.audit}")
    print("[SUMMARY]")
    for key, count in counts.most_common():
        print(f"- {key}: {count:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

