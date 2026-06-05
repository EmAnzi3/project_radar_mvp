import argparse
import csv
import json
import re
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("reports/master_projects.json")
DEFAULT_OUTPUT = Path("reports/master_projects_with_maps_smart_preview.json")
DEFAULT_AUDIT = Path("reports/google_maps_links_smart_audit.csv")
DEFAULT_SUMMARY = Path("reports/google_maps_links_smart_summary.json")


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
    r"(territorio comunale|intero comune|"
    r"comune di\s+[a-zà-ù'\s]+\(?[a-z]{2}\)?$|"
    r"varie localit|localit[aà] varie|strade comunali|"
    r"aree comunali|edifici comunali|edifici scolastici|"
    r"scuole comunali|area urbana|area vasta|tratti vari|"
    r"vie varie|diverse vie|diverse localit|ambito urbano|"
    r"sub ambito|tutto il territorio)",
    re.I,
)

ROAD_NOISE_RE = re.compile(
    r"(\bs\.?\s*s\.?\b|\bs\.?\s*p\.?\b|\bs\.?\s*r\.?\b|"
    r"\bss\b|\bsp\b|\bsr\b|\bsrt\b|"
    r"\bautostrada\b|\bsuperstrada\b|\braccordo\b|\bsvincolo\b|"
    r"\bkm\b|\bkm\.|\bchilometr|"
    r"\bprovinciale\b|\bstatale\b|\bregionale\b|\bcomunale\b|"
    r"\blotto\b|\btronco\b|\bvariante\b|\bfondovalle\b|"
    r"\btangenziale\b|\bcollegamento\b|\bitinerario\b|\btratto\b)",
    re.I,
)

MULTI_SITE_RE = re.compile(
    r"(pi[uù]\s+sedi|sedi diverse|diversi edifici|pi[uù]\s+edifici|"
    r"plessi scolastici|edifici scolastici|scuole comunali|"
    r"impianti sportivi comunali|strutture comunali|"
    r"varie sedi|diverse sedi|intero territorio|territorio comunale)",
    re.I,
)

POI_RE = re.compile(
    r"\b("
    r"asilo(?:\s+nido)?|scuola|istituto|liceo|stadio|"
    r"ospedale|policlinico|palazzetto|piscina|teatro|"
    r"biblioteca|museo|caserma|municipio|cimitero|"
    r"mercato|auditorium|universit[aà]|"
    r"centro sportivo|campo sportivo|polo scolastico|"
    r"centro civico|centro culturale"
    r")\b",
    re.I,
)

INVALID_GEO = {
    "",
    "TUTTI",
    "TUTTE",
    "VARI",
    "VARIE",
    "DIVERSI",
    "DIVERSE",
    "NAZIONALE",
    "ITALIA",
    "ND",
    "N.D.",
    "-",
}

STOPWORDS = {
    "ASILO", "NIDO", "SCUOLA", "ISTITUTO", "LICEO", "STADIO",
    "OSPEDALE", "POLICLINICO", "PALAZZETTO", "PISCINA", "TEATRO",
    "BIBLIOTECA", "MUSEO", "CASERMA", "MUNICIPIO", "CIMITERO",
    "MERCATO", "AUDITORIUM", "UNIVERSITA", "CENTRO", "SPORTIVO",
    "CAMPO", "POLO", "SCOLASTICO", "CIVICO", "CULTURALE",
    "COMUNALE", "PROVINCIALE", "REGIONALE", "PUBBLICO", "PUBBLICA",
    "NUOVO", "NUOVA", "REALIZZAZIONE", "RIQUALIFICAZIONE",
    "RISTRUTTURAZIONE", "MANUTENZIONE", "ADEGUAMENTO",
    "AMPLIAMENTO", "COMPLETAMENTO", "RECUPERO", "RESTAURO",
    "MESSA", "SICUREZZA", "LAVORI", "INTERVENTO", "INTERVENTI",
    "PROGETTO", "OPERE", "STRUTTURA", "EDIFICIO", "PLESSO",
    "COMPRENSIVO", "PRIMARIA", "SECONDARIA", "INFANZIA",
    "PRIMO", "SECONDO", "GRADO", "VIA", "VIALE", "PIAZZA",
    "PIAZZALE", "CORSO", "LARGO", "VICOLO", "STRADA",
    "DEL", "DELLA", "DELLE", "DEI", "DEGLI", "DI", "DA",
    "PER", "CON", "NEL", "NELLA", "SUL", "SULLA", "AL", "ALLA",
}


def clean(value: Any) -> str:
    return str(value or "").strip()


def ascii_norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", errors="ignore").decode("ascii")
    text = re.sub(r"[^A-Z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def valid_geo(value: Any) -> bool:
    return ascii_norm(value) not in INVALID_GEO


def load_records(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        return payload, payload, None

    if isinstance(payload, dict):
        for key in ("projects", "records", "items", "data", "rows"):
            if isinstance(payload.get(key), list):
                return payload, payload[key], key

    raise RuntimeError(f"Formato JSON non riconosciuto: {path}")


def write_records(path: Path, payload: Any, records: list[dict], key: str | None):
    path.parent.mkdir(parents=True, exist_ok=True)

    if key is None:
        output = records
    else:
        output = dict(payload)
        output[key] = records

    path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def street_token_count(address: str) -> int:
    return len(STREET_RE.findall(address or ""))


def has_multiple_addresses(address: str) -> bool:
    text = clean(address)

    if ";" in text or "|" in text:
        return True

    if street_token_count(text) > 1:
        if not re.search(r"\bvia\s+strada\b", text, re.I):
            return True

    if re.search(r"\b\d+\s*-\s*\d+\s*-\s*\d+", text):
        return True

    return False


def significant_numbers(address: str) -> list[str]:
    result = []

    for match in re.finditer(
        r"\b\d+[a-z]?(?:/[a-z0-9]+)?\b",
        address or "",
        re.I,
    ):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)

        if not digits:
            continue

        number = int(digits)

        if 1900 <= number <= 2099:
            continue

        if len(digits) == 5:
            continue

        result.append(raw)

    return result


def clean_address_for_query(
    address: Any,
    municipality: Any,
    province: Any,
    region: Any,
) -> str:
    text = clean(address)
    text = re.sub(r"[\u0080-\u009f]", " ", text)
    text = text.replace("–", " - ").replace("—", " - ")
    text = re.sub(r"\s+", " ", text).strip(" ,.;-")

    text = re.sub(r"\b\d{5}\b", "", text).strip(" ,.;-")
    text = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", text).strip(" ,.;-")

    for geo in (municipality, province, region):
        geo = clean(geo)
        if not geo:
            continue

        text = re.sub(
            rf"[, \-]+\b{re.escape(geo)}\b\.?$",
            "",
            text,
            flags=re.I,
        ).strip(" ,.;-")

    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,+", ",", text)
    return re.sub(r"\s+", " ", text).strip(" ,.;-")


def append_unique(parts: list[str], value: Any):
    value = clean(value)

    if not value or not valid_geo(value):
        return

    normalized = ascii_norm(value)

    if any(ascii_norm(existing) == normalized for existing in parts):
        return

    parts.append(value)


def build_query(primary: str, record: dict) -> str:
    parts = [clean(primary)]

    append_unique(parts, record.get("municipality"))
    append_unique(parts, record.get("province"))
    append_unique(parts, record.get("region"))

    parts.append("Italia")
    return ", ".join(part for part in parts if clean(part))


def maps_url(query: str) -> str:
    return (
        "https://www.google.com/maps/search/?api=1&query="
        + urllib.parse.quote_plus(query)
    )


def exact_address_query(record: dict) -> str:
    address = clean(record.get("address"))
    municipality = clean(record.get("municipality"))

    if not address or not valid_geo(municipality):
        return ""

    if GENERIC_RE.search(address):
        return ""

    if has_multiple_addresses(address):
        return ""

    if ROAD_NOISE_RE.search(address):
        return ""

    if not STREET_RE.search(address):
        return ""

    numbers = significant_numbers(address)

    if len(numbers) != 1:
        return ""

    if not NUMBER_RE.search(address):
        return ""

    cleaned = clean_address_for_query(
        address,
        record.get("municipality"),
        record.get("province"),
        record.get("region"),
    )

    return build_query(cleaned, record)


def street_without_number_query(record: dict) -> str:
    address = clean(record.get("address"))
    municipality = clean(record.get("municipality"))

    if not address or not valid_geo(municipality):
        return ""

    if len(address) > 130:
        return ""

    if GENERIC_RE.search(address):
        return ""

    if has_multiple_addresses(address):
        return ""

    if ROAD_NOISE_RE.search(address):
        return ""

    if street_token_count(address) != 1:
        return ""

    if significant_numbers(address):
        return ""

    cleaned = clean_address_for_query(
        address,
        record.get("municipality"),
        record.get("province"),
        record.get("region"),
    )

    return build_query(cleaned, record)


def extract_named_poi(record: dict) -> str:
    title = clean(record.get("title"))
    address = clean(record.get("address"))

    source = title if POI_RE.search(title) else address

    if not source:
        return ""

    if MULTI_SITE_RE.search(source):
        return ""

    if has_multiple_addresses(source):
        return ""

    match = POI_RE.search(source)

    if not match:
        return ""

    candidate = source[match.start():]
    candidate = re.split(r"[;|\n]", candidate, maxsplit=1)[0]
    candidate = re.split(
        r"\b(?:LAVORI|INTERVENTI|OPERE|PROGETTO)\s+(?:DI|PER)\b",
        candidate,
        maxsplit=1,
        flags=re.I,
    )[0]

    candidate = re.sub(r"\s+", " ", candidate).strip(" ,.;-")

    # Se il titolo contiene anche la strada, conserva come POI soltanto
    # la parte identificativa precedente: es. "Asilo R. Milazzo Via..."
    street_match = STREET_RE.search(candidate)

    if street_match and street_match.start() > 0:
        before_street = candidate[:street_match.start()].strip(" ,.;-")

        if POI_RE.search(before_street):
            candidate = before_street

    # Evita ripetizioni come "Istituto Barsanti Massa, Massa..."
    for field in ("municipality", "province", "region"):
        geo = clean(record.get(field))

        if not geo:
            continue

        candidate = re.sub(
            rf"(?:[, \-]+){re.escape(geo)}\.?$",
            "",
            candidate,
            flags=re.I,
        ).strip(" ,.;-")

    if len(candidate) > 160:
        candidate = candidate[:160].rsplit(" ", 1)[0].strip()

    geo_tokens = set()

    for field in ("municipality", "province", "region"):
        geo_tokens.update(ascii_norm(record.get(field)).split())

    tokens = ascii_norm(candidate).split()

    distinctive = [
        token
        for token in tokens
        if token not in STOPWORDS
        and token not in geo_tokens
        and len(token) >= 4
        and not token.isdigit()
    ]

    if not distinctive:
        return ""

    return candidate


def named_poi_with_street_query(record: dict) -> str:
    if not valid_geo(record.get("municipality")):
        return ""

    poi = extract_named_poi(record)
    address = clean(record.get("address"))

    if not poi or not address:
        return ""

    if len(address) > 130:
        return ""

    if GENERIC_RE.search(address):
        return ""

    if has_multiple_addresses(address):
        return ""

    if ROAD_NOISE_RE.search(address):
        return ""

    if street_token_count(address) != 1:
        return ""

    if significant_numbers(address):
        return ""

    cleaned_address = clean_address_for_query(
        address,
        record.get("municipality"),
        record.get("province"),
        record.get("region"),
    )

    if not cleaned_address:
        return ""

    return build_query(f"{poi}, {cleaned_address}", record)


def named_poi_query(record: dict) -> str:
    if not valid_geo(record.get("municipality")):
        return ""

    poi = extract_named_poi(record)

    if not poi:
        return ""

    return build_query(poi, record)


def enrich_record(record: dict) -> tuple[dict, str]:
    result = dict(record)

    previous = {
        key: result.get(key)
        for key in (
            "maps_url",
            "maps_query",
            "maps_precision",
            "maps_source",
            "maps_confidence",
        )
    }

    for key in previous:
        result.pop(key, None)

    query = exact_address_query(result)

    if query:
        precision = "address_with_number"
        confidence = "high"
        source = "opencup_address"
    else:
        query = named_poi_with_street_query(result)

        if query:
            precision = "named_poi_with_street"
            confidence = "high"
            source = "project_title+opencup_address"
        else:
            query = street_without_number_query(result)

            if query:
                precision = "street_without_number"
                confidence = "medium"
                source = "opencup_address"
            else:
                query = named_poi_query(result)

                if query:
                    precision = "named_poi"
                    confidence = "medium_high"
                    source = "project_title"
                else:
                    precision = ""
                    confidence = ""
                    source = ""

    if query:
        result["maps_url"] = maps_url(query)
        result["maps_query"] = query
        result["maps_precision"] = precision
        result["maps_source"] = source
        result["maps_confidence"] = confidence
        return result, precision

    if clean(previous.get("maps_url")):
        for key, value in previous.items():
            if value not in (None, ""):
                result[key] = value

        return result, clean(previous.get("maps_precision")) or "legacy_preserved"

    return result, "no_match"


def write_audit(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "maps_precision",
        "maps_confidence",
        "cup",
        "title",
        "branch",
        "region",
        "province",
        "municipality",
        "address",
        "maps_query",
        "maps_url",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    payload, records, key = load_records(args.input)

    output_records = []
    audit_rows = []
    counts = Counter()
    examples = defaultdict(list)

    for record in records:
        enriched, precision = enrich_record(record)
        output_records.append(enriched)
        counts[precision] += 1

        if clean(enriched.get("maps_url")):
            audit_row = {
                "maps_precision": clean(enriched.get("maps_precision")),
                "maps_confidence": clean(enriched.get("maps_confidence")),
                "cup": clean(enriched.get("cup")),
                "title": clean(enriched.get("title"))[:250],
                "branch": clean(enriched.get("branch")),
                "region": clean(enriched.get("region")),
                "province": clean(enriched.get("province")),
                "municipality": clean(enriched.get("municipality")),
                "address": clean(enriched.get("address"))[:250],
                "maps_query": clean(enriched.get("maps_query")),
                "maps_url": clean(enriched.get("maps_url")),
            }

            audit_rows.append(audit_row)

            if len(examples[precision]) < 25:
                examples[precision].append(audit_row)

    output_path = args.input if args.apply else args.output
    write_records(output_path, payload, output_records, key)
    write_audit(args.audit, audit_rows)

    summary = {
        "input_records": len(records),
        "records_with_maps": len(audit_rows),
        "counts": dict(counts),
        "examples": dict(examples),
    }

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] Record letti: {len(records):,}")
    print(f"[OK] Record con Maps: {len(audit_rows):,}")
    print(f"[OK] Output: {output_path}")
    print(f"[OK] Audit: {args.audit}")
    print(f"[OK] Summary: {args.summary}")
    print("[SUMMARY]")

    for name, count in counts.most_common():
        print(f"- {name}: {count:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
