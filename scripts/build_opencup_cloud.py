import csv
import json
import os
import re
import sys
import zipfile
import urllib.request
from dataclasses import dataclass, asdict
from html import escape
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent.parent
TMP_DIR = BASE_DIR / "tmp" / "opencup"
DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = BASE_DIR / "reports"

DASHBOARD_LIMIT = int(os.getenv("DASHBOARD_LIMIT", "120"))
MIN_PROJECT_VALUE_EUR = float(os.getenv("MIN_PROJECT_VALUE_EUR", "200000"))
OPENCUP_URL = os.getenv("OPENCUP_URL", "").strip()

PORTAL_PROJECT_URL = "https://www.opencup.gov.it/portale/progetto/-/cup/{cup}"


EXCLUDE_WORDS = [
    "premio assicurativo",
    "premi assicurativi",
    "raccolto",
    "animali",
    "sottomisura 17.1",
    "agevolazioni fiscali",
    "agevolazione fiscale",
    "contributive",
    "indennità compensative",
    "indennita compensative",
    "compensazioni",
    "sostegno al reddito",
    "voucher",
    "corso di formazione",
    "servizio civile",
    "acquisto servizi reali",
    "attivita' di ricerca",
    "attività di ricerca",
    "progetti di ricerca",
    "ricerca sviluppo tecnologico",
    "nuova gamma di elettrodomestici",
    "spese materiale",
]


CATEGORY_KEYWORDS = {
    "Scuole / formazione": [
        "scuola", "scolastico", "asilo", "nido", "infanzia", "primaria",
        "secondaria", "formazione", "polo scolastico", "mensa scolastica"
    ],
    "Sport / impianti sportivi": [
        "palestra", "palazzetto", "campo sportivo", "impianto sportivo",
        "piscina", "spogliatoi", "centro sportivo", "stadio"
    ],
    "Sanità / RSA": [
        "rsa", "casa di riposo", "residenza sanitaria", "centro anziani",
        "ospedale", "poliambulatorio", "distretto sanitario", "sanitario",
        "casa della comunita", "casa della comunità"
    ],
    "Cultura / centri civici": [
        "biblioteca", "teatro", "auditorium", "centro culturale",
        "centro civico", "museo", "sala polivalente", "polo culturale",
        "cinema"
    ],
    "Riqualificazione urbana": [
        "riqualificazione", "rigenerazione urbana", "arredo urbano",
        "parco", "piazza", "verde pubblico", "area dismessa", "recupero area",
        "giardini pubblici"
    ],
    "Edilizia pubblica": [
        "edificio pubblico", "municipio", "sede comunale", "uffici pubblici",
        "fabbricato", "immobile comunale", "edificio polifunzionale",
        "patrimonio comunale"
    ],
    "Infrastrutture / parcheggi": [
        "parcheggio", "strada", "viabilità", "viabilita", "marciapiede",
        "ponte", "rotatoria", "urbanizzazione", "pista ciclabile",
        "pavimentazione stradale", "illuminazione pubblica"
    ],
    "Ambiente / rifiuti / depurazione": [
        "rifiuti", "depuratore", "depurazione", "fognatura", "acquedotto",
        "bonifica", "discarica", "trattamento rifiuti", "acque reflue",
        "risorse idriche"
    ],
    "Industriale / logistica": [
        "magazzino", "logistica", "capannone", "area produttiva",
        "zona industriale", "polo produttivo", "stoccaggio materiali"
    ],
    "Energia": [
        "fotovoltaico", "agrivoltaico", "eolico", "energia", "bess",
        "accumulo", "biometano", "efficientamento energetico"
    ],
    "Residenziale pubblico / ERS": [
        "edilizia residenziale", "alloggi", "ers", "housing",
        "case popolari", "social housing"
    ],
}


@dataclass
class ProjectRecord:
    source: str
    source_url: str
    external_id: str
    title: str
    description: str
    region: Optional[str]
    province: Optional[str]
    municipality: Optional[str]
    address: Optional[str]
    sector: Optional[str]
    category: str
    intervention_type: Optional[str]
    phase: Optional[str]
    status: Optional[str]
    client: Optional[str]
    client_type: Optional[str]
    estimated_value_eur: Optional[float]
    award_amount_eur: Optional[float]
    cup: Optional[str]
    cig: Optional[str]
    funding: Optional[str]
    contractor_name: Optional[str]
    contractor_vat: Optional[str]
    contractor_tax_code: Optional[str]
    contractor_address: Optional[str]
    contractor_city: Optional[str]
    contractor_province: Optional[str]
    contractor_pec: Optional[str]
    contractor_email: Optional[str]
    contractor_phone: Optional[str]
    contact_name: Optional[str]
    contact_role: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    commercial_score: int
    ai_notes: Optional[str]
    enrichment_status: Optional[str]


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_optional(value: Optional[str]) -> Optional[str]:
    value = clean_text(value)
    if not value:
        return None

    bad = {
        "DATO NON PRESENTE",
        "NON PRESENTE",
        "N.D.",
        "ND",
        "NO",
        "N",
        "***************",
        "********",
        "-",
    }

    if value.upper() in bad:
        return None

    if set(value) == {"*"}:
        return None

    return value


def row_get(row: list[str], idx: int) -> Optional[str]:
    if idx >= len(row):
        return None
    return clean_optional(row[idx])


def to_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None

    text = str(value).strip()
    text = text.replace("€", "").replace(" ", "")

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def split_composite_project(value: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    value = clean_text(value)
    if not value:
        return None, None, None

    parts = [clean_text(p) for p in value.split("*")]
    title = parts[0] if len(parts) > 0 else value
    location = parts[1] if len(parts) > 1 else None
    description = parts[2] if len(parts) > 2 else value
    return title, location, description


def clean_status(value: Optional[str]) -> Optional[str]:
    value = clean_text(value)
    if not value:
        return None

    upper = value.upper()

    if upper in {"ITALIA", "CENTRO", "NORD", "SUD", "ISOLE"}:
        return None

    for word in ["ATTIVO", "CHIUSO", "REVOCATO", "CANCELLATO", "ANNULLATO"]:
        if word in upper:
            return upper

    return None


def classify_category(text: str) -> str:
    lower = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return category

    return "Altro"


def infer_intervention_type(text: str) -> Optional[str]:
    lower = text.lower()

    if "nuova realizzazione" in lower or "nuova costruzione" in lower or "realizzazione" in lower or "costruzione" in lower:
        return "nuova costruzione"
    if "ristrutturazione" in lower:
        return "ristrutturazione"
    if "riqualificazione" in lower:
        return "riqualificazione"
    if "manutenzione straordinaria" in lower:
        return "manutenzione straordinaria"
    if "messa in sicurezza" in lower:
        return "messa in sicurezza"
    if "efficientamento" in lower:
        return "efficientamento energetico"

    return None


def infer_phase(status: Optional[str]) -> str:
    if not status:
        return "programmazione"

    upper = status.upper()

    if "ATTIVO" in upper:
        return "programmazione / progetto attivo"
    if "CHIUSO" in upper:
        return "chiuso"
    if "REVOCATO" in upper or "CANCELLATO" in upper:
        return "revocato / cancellato"

    return "programmazione"


def is_noise(*values: Optional[str]) -> bool:
    lower = " ".join(clean_text(v).lower() for v in values if v)
    return any(w in lower for w in EXCLUDE_WORDS)


def is_public_works_candidate(text: str) -> bool:
    lower = text.lower()

    words = [
        "lavori pubblici",
        "realizzazione di lavori pubblici",
        "opere ed impiantistica",
        "nuova realizzazione",
        "manutenzione straordinaria",
        "ristrutturazione",
        "riqualificazione",
        "messa in sicurezza",
        "adeguamento sismico",
        "efficientamento energetico",
        "infrastrutture sociali",
        "infrastrutture ambientali",
        "infrastrutture di trasporto",
        "immobili",
        "ambiente ed energia",
        "trasporti",
    ]

    return any(w in lower for w in words)


def calculate_score(record: ProjectRecord) -> int:
    score = 0

    high_categories = {
        "Scuole / formazione",
        "Sport / impianti sportivi",
        "Sanità / RSA",
        "Cultura / centri civici",
        "Riqualificazione urbana",
        "Edilizia pubblica",
        "Infrastrutture / parcheggi",
        "Ambiente / rifiuti / depurazione",
        "Industriale / logistica",
        "Residenziale pubblico / ERS",
    }

    if record.category in high_categories:
        score += 25

    value = record.estimated_value_eur or 0

    if value >= 10_000_000:
        score += 35
    elif value >= 5_000_000:
        score += 30
    elif value >= 1_000_000:
        score += 22
    elif value >= 300_000:
        score += 12
    elif value >= 200_000:
        score += 6
    else:
        score -= 20

    if record.phase:
        score += 15

    if record.intervention_type:
        score += 10

    if record.client:
        score += 8

    if record.region:
        score += 3
    if record.province:
        score += 3
    if record.municipality:
        score += 4

    return max(0, min(score, 100))


def parse_row(row: list[str]) -> Optional[ProjectRecord]:
    cup = row_get(row, 0)
    if not cup:
        return None

    match = re.search(r"[A-Z0-9]{15}", cup)
    cup = match.group(0) if match else cup

    composite = row_get(row, 1)
    composite_title, composite_location, composite_description = split_composite_project(composite)

    year_decision = row_get(row, 2)
    status = clean_status(row_get(row, 3))

    cost = to_float(row_get(row, 4))
    if cost is not None and cost < MIN_PROJECT_VALUE_EUR:
        return None

    region = row_get(row, 11)
    province = row_get(row, 14) or row_get(row, 13)
    municipality = row_get(row, 16)

    street_name = row_get(row, 19)
    street_type = row_get(row, 20)
    street_number = row_get(row, 21)
    address = " ".join(x for x in [street_type, street_name, street_number] if x) or composite_location

    client = row_get(row, 17)

    classification = row_get(row, 33)
    nature = row_get(row, 35)
    typology = row_get(row, 37)
    area = row_get(row, 39)
    sector = row_get(row, 41)
    subsector = row_get(row, 43)
    opencup_category = row_get(row, 45)

    description = row_get(row, 48) or composite_description or composite or ""
    title = row_get(row, 52) or composite_title or description or f"Progetto OpenCUP {cup}"
    location_hint = row_get(row, 53)

    combined = " ".join(
        x for x in [
            title,
            description,
            location_hint,
            classification,
            nature,
            typology,
            area,
            sector,
            subsector,
            opencup_category,
        ]
        if x
    )

    if is_noise(title, description, classification, nature, typology, area, sector, subsector, opencup_category):
        return None

    if not is_public_works_candidate(combined):
        return None

    category = classify_category(combined)
    intervention_type = infer_intervention_type(combined)

    funding = None
    for idx in range(55, min(len(row), 80)):
        value = row_get(row, idx)
        if value and value.upper() in {
            "STATALE",
            "REGIONALE",
            "COMUNALE",
            "PROVINCIALE",
            "COMUNITARIA",
            "PRIVATA",
            "ALTRA PUBBLICA",
        }:
            funding = value
            break

    record = ProjectRecord(
        source="OpenCUP",
        source_url=PORTAL_PROJECT_URL.format(cup=cup),
        external_id=f"OPENCUP-{cup}",
        title=title,
        description=description,
        region=region,
        province=province,
        municipality=municipality,
        address=address,
        sector=sector or area or nature or classification,
        category=category,
        intervention_type=intervention_type,
        phase=infer_phase(status),
        status=status,
        client=client,
        client_type="pubblico",
        estimated_value_eur=cost,
        award_amount_eur=None,
        cup=cup,
        cig=None,
        funding=funding,
        contractor_name=None,
        contractor_vat=None,
        contractor_tax_code=None,
        contractor_address=None,
        contractor_city=None,
        contractor_province=None,
        contractor_pec=None,
        contractor_email=None,
        contractor_phone=None,
        contact_name=None,
        contact_role=None,
        contact_email=None,
        contact_phone=None,
        commercial_score=0,
        ai_notes=(
            f"Classificazione OpenCUP: {classification or ''} | "
            f"Natura: {nature or ''} | "
            f"Tipologia: {typology or ''} | "
            f"Area: {area or ''} | "
            f"Settore: {sector or ''} | "
            f"Sottosettore: {subsector or ''} | "
            f"Anno decisione: {year_decision or ''}"
        ),
        enrichment_status="da arricchire con ANAC/BDNCP/albo pretorio",
    )

    record.commercial_score = calculate_score(record)
    return record


def download_zip() -> Path:
    if not OPENCUP_URL:
        raise RuntimeError("OPENCUP_URL non impostato. Passalo dal workflow GitHub Actions.")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TMP_DIR / "opencup.zip"

    print(f"[Download] Scarico OpenCUP da: {OPENCUP_URL}")
    urllib.request.urlretrieve(OPENCUP_URL, zip_path)

    print(f"[Download] Salvato: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


def process_zip(zip_path: Path) -> list[ProjectRecord]:
    records: list[ProjectRecord] = []
    seen: set[str] = set()
    scanned = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        print(f"[OpenCUP] CSV trovati nello ZIP: {len(csv_names)}")

        for csv_name in csv_names:
            print(f"[OpenCUP] Elaboro: {csv_name}")

            with zf.open(csv_name) as raw:
                text = (line.decode("utf-8-sig", errors="ignore") for line in raw)
                reader = csv.reader(text, delimiter=";")

                next(reader, None)

                for row in reader:
                    scanned += 1

                    if scanned % 100_000 == 0:
                        print(f"[OpenCUP] Righe lette: {scanned:,} | candidati: {len(records):,}")

                    rec = parse_row(row)
                    if not rec:
                        continue

                    key = rec.cup or rec.external_id
                    if key in seen:
                        continue

                    seen.add(key)
                    records.append(rec)

    print(f"[OpenCUP] Scansione completata. Righe lette: {scanned:,}. Candidati: {len(records):,}")

    records.sort(
        key=lambda r: (
            r.commercial_score,
            r.estimated_value_eur or 0,
        ),
        reverse=True,
    )

    return records


def money(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{float(value):,.0f} &euro;".replace(",", ".")


def txt(value) -> str:
    return escape(str(value or ""))




def value_band(value: Optional[float]) -> str:
    value = value or 0

    if value >= 1_000_000_000:
        return ">= 1B"
    if value >= 500_000_000:
        return "500M - 1B"
    if value >= 100_000_000:
        return "100M - 500M"
    if value >= 50_000_000:
        return "50M - 100M"
    if value >= 20_000_000:
        return "20M - 50M"
    if value >= 5_000_000:
        return "5M - 20M"
    if value >= 1_000_000:
        return "1M - 5M"
    if value >= 500_000:
        return "500k - 1M"
    if value >= 200_000:
        return "200k - 500k"
    return "< 200k"


def is_local_public_client(client: Optional[str]) -> bool:
    c = clean_text(client).upper()

    local_markers = [
        "COMUNE",
        "PROVINCIA",
        "CITTA' METROPOLITANA",
        "CITT? METROPOLITANA",
        "REGIONE",
        "AZIENDA USL",
        "ASL",
        "AZIENDA OSPEDALIERA",
        "UNIONE DEI COMUNI",
    ]

    return any(m in c for m in local_markers)


def is_macro_national_project(record: ProjectRecord) -> bool:
    text = " ".join(
        clean_text(x).lower()
        for x in [
            record.title,
            record.description,
            record.sector,
            record.client,
        ]
        if x
    )

    macro_terms = [
        "autostrada",
        "autostradale",
        "ferrovia",
        "ferroviario",
        "alta velocit?",
        "alta velocita",
        "concessione",
        "raccordo autostradale",
        "collegamento autostradale",
        "corridoio",
        "rete elettrica nazionale",
        "hvdc",
        "terna",
    ]

    return (record.estimated_value_eur or 0) >= 100_000_000 and any(t in text for t in macro_terms)


def write_counter_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_records_csv(path: Path, records: list[ProjectRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "score",
        "cup",
        "title",
        "category",
        "region",
        "province",
        "municipality",
        "value_eur",
        "client",
        "phase",
        "status",
        "source_url",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()

        for r in records:
            writer.writerow({
                "score": r.commercial_score,
                "cup": r.cup,
                "title": r.title,
                "category": r.category,
                "region": r.region,
                "province": r.province,
                "municipality": r.municipality,
                "value_eur": r.estimated_value_eur,
                "client": r.client,
                "phase": r.phase,
                "status": r.status,
                "source_url": r.source_url,
            })


def write_diagnostics(records: list[ProjectRecord]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    by_category = {}
    by_value_band = {}
    by_region = {}

    for r in records:
        value = r.estimated_value_eur or 0

        cat = r.category or "ND"
        band = value_band(value)
        region = r.region or "ND"

        by_category.setdefault(cat, {"category": cat, "count": 0, "total_value_eur": 0, "avg_score": 0})
        by_category[cat]["count"] += 1
        by_category[cat]["total_value_eur"] += value
        by_category[cat]["avg_score"] += r.commercial_score or 0

        by_value_band.setdefault(band, {"value_band": band, "count": 0, "total_value_eur": 0, "avg_score": 0})
        by_value_band[band]["count"] += 1
        by_value_band[band]["total_value_eur"] += value
        by_value_band[band]["avg_score"] += r.commercial_score or 0

        by_region.setdefault(region, {"region": region, "count": 0, "total_value_eur": 0, "avg_score": 0})
        by_region[region]["count"] += 1
        by_region[region]["total_value_eur"] += value
        by_region[region]["avg_score"] += r.commercial_score or 0

    for container in [by_category, by_value_band, by_region]:
        for row in container.values():
            count = row["count"] or 1
            row["avg_score"] = round(row["avg_score"] / count, 2)
            row["total_value_eur"] = round(row["total_value_eur"], 2)

    category_rows = sorted(
        by_category.values(),
        key=lambda x: (x["count"], x["total_value_eur"]),
        reverse=True,
    )

    value_band_order = {
        ">= 1B": 1,
        "500M - 1B": 2,
        "100M - 500M": 3,
        "50M - 100M": 4,
        "20M - 50M": 5,
        "5M - 20M": 6,
        "1M - 5M": 7,
        "500k - 1M": 8,
        "200k - 500k": 9,
        "< 200k": 10,
    }

    value_rows = sorted(
        by_value_band.values(),
        key=lambda x: value_band_order.get(x["value_band"], 99),
    )

    region_rows = sorted(
        by_region.values(),
        key=lambda x: (x["count"], x["total_value_eur"]),
        reverse=True,
    )

    write_counter_csv(
        REPORTS_DIR / "diagnostics_by_category.csv",
        category_rows,
        ["category", "count", "total_value_eur", "avg_score"],
    )

    write_counter_csv(
        REPORTS_DIR / "diagnostics_by_value_band.csv",
        value_rows,
        ["value_band", "count", "total_value_eur", "avg_score"],
    )

    write_counter_csv(
        REPORTS_DIR / "diagnostics_by_region.csv",
        region_rows,
        ["region", "count", "total_value_eur", "avg_score"],
    )

    # Top 20 per categoria
    top_by_category = []
    categories = sorted(set(r.category or "ND" for r in records))

    for category in categories:
        subset = [r for r in records if (r.category or "ND") == category]
        subset.sort(
            key=lambda r: (
                r.commercial_score or 0,
                r.estimated_value_eur or 0,
            ),
            reverse=True,
        )
        top_by_category.extend(subset[:20])

    write_records_csv(REPORTS_DIR / "top_by_category.csv", top_by_category)

    # Mid-market: fascia commercialmente pi? lavorabile
    mid_market = [
        r for r in records
        if 1_000_000 <= (r.estimated_value_eur or 0) <= 50_000_000
    ]
    mid_market.sort(
        key=lambda r: (
            r.commercial_score or 0,
            r.estimated_value_eur or 0,
        ),
        reverse=True,
    )

    write_records_csv(REPORTS_DIR / "top_mid_market.csv", mid_market[:1000])

    # Enti locali / territoriali
    local_public = [
        r for r in records
        if is_local_public_client(r.client)
    ]
    local_public.sort(
        key=lambda r: (
            r.commercial_score or 0,
            r.estimated_value_eur or 0,
        ),
        reverse=True,
    )

    write_records_csv(REPORTS_DIR / "top_local_public.csv", local_public[:1000])

    # Macro-opere nazionali: non escluse, ma separate per analisi
    macro = [
        r for r in records
        if is_macro_national_project(r)
    ]
    macro.sort(
        key=lambda r: (
            r.estimated_value_eur or 0,
            r.commercial_score or 0,
        ),
        reverse=True,
    )

    write_records_csv(REPORTS_DIR / "top_macro_projects.csv", macro[:1000])

    print("[Diagnostics] reports/diagnostics_by_category.csv")
    print("[Diagnostics] reports/diagnostics_by_value_band.csv")
    print("[Diagnostics] reports/diagnostics_by_region.csv")
    print("[Diagnostics] reports/top_by_category.csv")
    print("[Diagnostics] reports/top_mid_market.csv")
    print("[Diagnostics] reports/top_local_public.csv")
    print("[Diagnostics] reports/top_macro_projects.csv")


def write_outputs(records: list[ProjectRecord]) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    dashboard_records = records[:DASHBOARD_LIMIT]

    data = {
        "source": "OpenCUP",
        "mode": "github_actions_full_scan",
        "total_candidates": len(records),
        "dashboard_count": len(dashboard_records),
        "min_project_value_eur": MIN_PROJECT_VALUE_EUR,
        "records": [asdict(r) for r in dashboard_records],
    }

    (DOCS_DIR / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (REPORTS_DIR / "top_projects.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "score", "cup", "title", "category", "region", "province", "municipality",
            "value_eur", "client", "source_url"
        ])

        for r in records[:1000]:
            writer.writerow([
                r.commercial_score,
                r.cup,
                r.title,
                r.category,
                r.region,
                r.province,
                r.municipality,
                r.estimated_value_eur,
                r.client,
                r.source_url,
            ])

    rows = []
    for r in dashboard_records:
        rows.append(f"""
        <tr>
          <td class="score">{r.commercial_score}</td>
          <td>
            <strong>{txt(r.title)}</strong>
            <div class="desc">{txt(r.description)}</div>
            <div class="small">{txt(r.enrichment_status)}</div>
          </td>
          <td>{txt(r.category)}</td>
          <td>{txt(r.region)}</td>
          <td>{txt(r.province)}</td>
          <td>{txt(r.municipality)}</td>
          <td>{txt(r.phase)}</td>
          <td>{txt(r.status)}</td>
          <td>{money(r.estimated_value_eur)}</td>
          <td>{txt(r.client)}</td>
          <td>{txt(r.cup)}</td>
          <td><a href="{txt(r.source_url)}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      background: #f6f7f9;
      color: #1f2933;
    }}
    h1 {{
      margin-bottom: 4px;
    }}
    .subtitle {{
      color: #617083;
      margin-bottom: 16px;
    }}
    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 18px;
      color: #4b5563;
      font-size: 14px;
    }}
    .pill {{
      background: white;
      border: 1px solid #e5e7eb;
      padding: 8px 10px;
      border-radius: 999px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .table-wrap {{
      overflow-x: auto;
      background: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border-radius: 12px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 1450px;
      background: white;
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      font-size: 14px;
      vertical-align: top;
    }}
    th {{
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    tr:hover {{
      background: #f3f4f6;
    }}
    .score {{
      font-weight: bold;
      font-size: 18px;
    }}
    .desc {{
      color: #4b5563;
      font-size: 12px;
      margin-top: 5px;
      max-width: 520px;
      max-height: 62px;
      overflow: hidden;
    }}
    .small {{
      color: #6b7280;
      font-size: 11px;
      margin-top: 6px;
      font-style: italic;
    }}
    a {{
      color: #0f766e;
      font-weight: bold;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <h1>Project Radar MVP</h1>
  <div class="subtitle">Radar generalista progetti/opere - OpenCUP</div>

  <div class="meta">
    <div class="pill">Modalità: GitHub Actions full scan</div>
    <div class="pill">Candidati totali: {len(records)}</div>
    <div class="pill">Record mostrati: {len(dashboard_records)}</div>
    <div class="pill">Soglia minima: {money(MIN_PROJECT_VALUE_EUR)}</div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Score</th>
          <th>Progetto</th>
          <th>Categoria</th>
          <th>Regione</th>
          <th>Prov.</th>
          <th>Comune</th>
          <th>Fase</th>
          <th>Stato</th>
          <th>Valore</th>
          <th>Committente</th>
          <th>CUP</th>
          <th>Fonte</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    print(f"[Output] docs/data.json")
    print(f"[Output] docs/index.html")
    write_diagnostics(records)

    print(f"[Output] reports/top_projects.csv")


def main() -> None:
    zip_path = download_zip()
    records = process_zip(zip_path)
    write_outputs(records)


if __name__ == "__main__":
    main()
