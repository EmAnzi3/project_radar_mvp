import csv
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.config import BASE_DIR
from app.models import ProjectRecord
from app.taxonomy import (
    classify_nii_category,
    clean_text,
    infer_intervention_type,
    infer_phase_from_opencup,
    is_nii_like_project,
)


RAW_OPENCUP_DIR = BASE_DIR / "data" / "raw" / "opencup"

API_CUP_URL = "https://api.sogei.it/rgs/opencup/o/extServiceApi/v1/opendataes/cup/{cup}"
PORTAL_PROJECT_URL = "https://www.opencup.gov.it/portale/progetto/-/cup/{cup}"

# Fallback tecnico, non banca dati.
# Serve solo a verificare che il collector e il report funzionino anche senza ZIP scaricati.
SEED_CUPS = [
    "F24H20000820001",
]

MIN_PROJECT_VALUE_EUR = 200_000


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def _norm_key(value: str | None) -> str:
    if value is None:
        return ""
    value = value.lower().strip()
    value = value.replace("\ufeff", "")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _first_present(row: dict[str, Any], candidates: list[str]) -> str | None:
    normalized = {_norm_key(k): v for k, v in row.items()}

    for candidate in candidates:
        key = _norm_key(candidate)
        if key in normalized and clean_text(normalized[key]):
            return clean_text(normalized[key])

    # fallback: match contenuto parziale del nome colonna
    for key, value in normalized.items():
        for candidate in candidates:
            ck = _norm_key(candidate)
            if ck and ck in key and clean_text(value):
                return clean_text(value)

    return None




def _clean_optional_value(value: str | None) -> str | None:
    value = clean_text(value)
    if not value:
        return None

    bad_values = {
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

    if value.upper() in bad_values:
        return None

    if set(value) == {"*"}:
        return None

    return value


def _extract_first_valid(row: dict[str, Any], candidates: list[str]) -> str | None:
    value = _first_present(row, candidates)
    return _clean_optional_value(value)


def _to_float(value: str | None) -> float | None:
    if not value:
        return None

    text = str(value).strip()
    text = text.replace("€", "").replace(" ", "")

    # Formati italiani: 1.234.567,89
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def _flatten_json(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}_{key}" if prefix else str(key)
            out.update(_flatten_json(value, new_key))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            new_key = f"{prefix}_{idx}" if prefix else str(idx)
            out.update(_flatten_json(value, new_key))
    else:
        out[prefix] = obj

    return out






def _clean_project_status(value: str | None) -> str | None:
    value = clean_text(value)
    if not value:
        return None

    upper = value.upper()

    # Evita di scambiare il campo geografico "ITALIA" per stato progetto
    if upper in {"ITALIA", "CENTRO", "NORD", "SUD", "ISOLE"}:
        return None

    valid_words = [
        "ATTIVO",
        "CHIUSO",
        "REVOCATO",
        "CANCELLATO",
        "ANNULLATO",
    ]

    if any(w in upper for w in valid_words):
        return upper

    return None


def _looks_like_person_name(value: str | None) -> bool:
    value = clean_text(value)
    if not value:
        return False

    # Esclude codici tipo 27.5, 01.1, 96.0
    if re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", value):
        return False

    # Un nome plausibile ha almeno due parti alfabetiche
    parts = [p for p in re.split(r"\s+", value) if p]
    alpha_parts = [p for p in parts if re.search(r"[A-Za-z?-??-??-?]", p)]

    return len(alpha_parts) >= 2


def _is_non_construction_noise(*values: str | None) -> bool:
    text = " ".join(clean_text(v).lower() for v in values if v)

    noise_words = [
        "premio assicurativo",
        "premi assicurativi",
        "raccolto",
        "animali",
        "sottomisura 17.1",
        "agevolazioni fiscali",
        "agevolazione fiscale",
        "contributive",
        "indennit? compensative",
        "indennita compensative",
        "compensazioni",
        "sostegno al reddito",
        "acquisto servizi reali",
        "attivita' di ricerca",
        "attivit? di ricerca",
        "progetti di ricerca",
        "ricerca sviluppo tecnologico",
        "nuova gamma di elettrodomestici",
        "spese materiale",
    ]

    return any(w in text for w in noise_words)


def _has_procurement_evidence(
    cig: str | None,
    award_date: str | None,
    award_amount: float | None,
    award_source_url: str | None,
) -> bool:
    return bool(cig or award_date or award_amount or award_source_url)


def _record_from_generic_row(row: dict[str, Any], source_url: str | None = None) -> ProjectRecord | None:
    cup = _first_present(row, ["cup", "codice cup", "codice_cup", "codice unico progetto"])

    if cup:
        match = re.search(r"[A-Z0-9]{15}", cup)
        cup = match.group(0) if match else cup

    title = (
        _first_present(row, [
            "descrizione intervento",
            "descrizione_intervento",
            "titolo progetto",
            "titolo_progetto",
            "denominazione progetto",
            "descrizione",
            "struttura infrastruttura oggetto dell intervento",
            "struttura/infrastruttura oggetto dell'intervento",
        ])
        or f"Progetto OpenCUP {cup or ''}".strip()
    )

    description = _first_present(row, [
        "descrizione intervento",
        "descrizione_intervento",
        "struttura infrastruttura oggetto dell intervento",
        "struttura/infrastruttura oggetto dell'intervento",
        "altre informazioni",
    ])

    classification = _first_present(row, ["classificazione", "natura", "classificazione progetto"])
    typology = _first_present(row, ["tipologia", "tipologia intervento", "tipo intervento"])
    area = _first_present(row, ["area intervento", "area d'intervento", "area_di_intervento"])
    sector = _first_present(row, ["settore", "settore intervento"])
    subsector = _first_present(row, ["sottosettore", "sotto settore"])
    opencup_category = _first_present(row, ["categoria", "categoria intervento"])

    status_raw = _first_present(row, [
        "stato progetto",
        "stato del progetto",
        "stato cup",
        "stato intervento",
        "stato",
    ])
    status = _clean_project_status(status_raw)
    year_decision = _first_present(row, ["anno decisione", "anno_decisione"])

    region = _first_present(row, ["regione", "den regione", "den_regione"])
    province = _first_present(row, ["provincia", "den provincia", "den_provincia", "sigla provincia"])
    municipality = _first_present(row, ["comune", "den comune", "den_comune"])
    address = _first_present(row, ["indirizzo", "indirizzo o area di riferimento", "area riferimento"])

    client = _first_present(row, [
        "soggetto titolare",
        "denominazione soggetto titolare",
        "denominazione",
        "soggetto_titolare",
        "beneficiario",
    ])

    cost = _to_float(_first_present(row, [
        "totale costo previsto",
        "costo previsto",
        "costo_previsto",
        "importo",
        "finanziamento",
        "totale finanziamento pubblico previsto",
    ]))

    funding = _first_present(row, [
        "copertura finanziaria",
        "fonte copertura",
        "fonte di copertura",
        "finanziamento",
    ])

    # Campi spesso NON presenti in OpenCUP, ma utili se arrivano da dataset estesi,
    # ANAC, BDNCP, SCP, albo pretorio o altri arricchitori.
    cig = _extract_first_valid(row, [
        "cig",
        "codice cig",
        "smart cig",
        "codice identificativo gara",
    ])

    contractor_name = _extract_first_valid(row, [
        "aggiudicatario",
        "denominazione aggiudicatario",
        "ditta aggiudicataria",
        "impresa aggiudicataria",
        "operatore economico",
        "operatore economico aggiudicatario",
        "contraente",
        "appaltatore",
        "soggetto realizzatore",
        "realizzatore",
        "impresa",
        "ragione sociale impresa",
    ])

    contractor_vat = _extract_first_valid(row, [
        "partita iva aggiudicatario",
        "p iva aggiudicatario",
        "p.iva aggiudicatario",
        "partita iva operatore economico",
        "p iva operatore economico",
        "partita iva impresa",
        "p iva impresa",
        "partita iva",
        "p iva",
        "p.iva",
    ])

    contractor_tax_code = _extract_first_valid(row, [
        "codice fiscale aggiudicatario",
        "cf aggiudicatario",
        "codice fiscale operatore economico",
        "cf operatore economico",
        "codice fiscale impresa",
        "cf impresa",
        "codice fiscale",
    ])

    contractor_address = _extract_first_valid(row, [
        "indirizzo aggiudicatario",
        "sede legale aggiudicatario",
        "indirizzo operatore economico",
        "sede legale operatore economico",
        "indirizzo impresa",
        "sede legale impresa",
    ])

    contractor_city = _extract_first_valid(row, [
        "comune aggiudicatario",
        "citta aggiudicatario",
        "citt? aggiudicatario",
        "comune operatore economico",
        "citta operatore economico",
        "citt? operatore economico",
        "comune impresa",
        "citta impresa",
        "citt? impresa",
    ])

    contractor_province = _extract_first_valid(row, [
        "provincia aggiudicatario",
        "provincia operatore economico",
        "provincia impresa",
        "sigla provincia aggiudicatario",
    ])

    contractor_pec = _extract_first_valid(row, [
        "pec aggiudicatario",
        "pec operatore economico",
        "pec impresa",
        "pec",
    ])

    contractor_email = _extract_first_valid(row, [
        "email aggiudicatario",
        "mail aggiudicatario",
        "email operatore economico",
        "email impresa",
        "mail impresa",
        "email",
    ])

    contractor_phone = _extract_first_valid(row, [
        "telefono aggiudicatario",
        "telefono operatore economico",
        "telefono impresa",
        "telefono",
        "tel",
    ])

    rup = _extract_first_valid(row, [
        "rup",
        "responsabile unico del progetto",
        "responsabile unico del procedimento",
        "responsabile progetto",
        "responsabile procedimento",
    ])

    contact_name = _extract_first_valid(row, [
        "referente",
        "nominativo referente",
        "referente procedura",
        "contatto",
        "responsabile",
    ]) or rup

    contact_role = "RUP / responsabile procedimento" if rup else _extract_first_valid(row, [
        "ruolo referente",
        "qualifica referente",
        "ufficio",
    ])

    contact_email = _extract_first_valid(row, [
        "email referente",
        "mail referente",
        "email rup",
        "mail rup",
        "email responsabile",
        "mail responsabile",
    ])

    contact_phone = _extract_first_valid(row, [
        "telefono referente",
        "tel referente",
        "telefono rup",
        "tel rup",
        "telefono responsabile",
    ])

    award_amount = _to_float(_extract_first_valid(row, [
        "importo aggiudicazione",
        "importo di aggiudicazione",
        "valore aggiudicazione",
        "importo contrattuale",
    ]))

    award_date = _extract_first_valid(row, [
        "data aggiudicazione",
        "data di aggiudicazione",
        "data affidamento",
        "data esito",
    ])

    award_source_url = _extract_first_valid(row, [
        "url aggiudicazione",
        "link aggiudicazione",
        "url esito",
        "link esito",
        "url fonte aggiudicazione",
    ])

    # OpenCUP spesso contiene beneficiari/soggetti collegati, non appaltatori.
    # Quindi appaltatore/RUP si tengono solo se esiste una prova minima di gara o aggiudicazione.
    has_procurement_evidence = _has_procurement_evidence(
        cig=cig,
        award_date=award_date,
        award_amount=award_amount,
        award_source_url=award_source_url,
    )

    if not has_procurement_evidence:
        contractor_name = None
        contractor_vat = None
        contractor_tax_code = None
        contractor_address = None
        contractor_city = None
        contractor_province = None
        contractor_pec = None
        contractor_email = None
        contractor_phone = None

    if not _looks_like_person_name(rup):
        rup = None

    if not _looks_like_person_name(contact_name):
        contact_name = rup

    if not rup and not contact_name:
        contact_role = None
        contact_email = None
        contact_phone = None

    enrichment_status = "da arricchire con ANAC/BDNCP/albo pretorio"
    if has_procurement_evidence and (contractor_name or rup or contact_name or cig):
        enrichment_status = "parzialmente arricchito da fonte gara/appalto"

    combined_text = " ".join([
        title or "",
        description or "",
        classification or "",
        typology or "",
        area or "",
        sector or "",
        subsector or "",
        opencup_category or "",
    ])

    if _is_non_construction_noise(
        title,
        description,
        classification,
        typology,
        area,
        sector,
        subsector,
        opencup_category,
    ):
        return None

    if not is_nii_like_project(combined_text):
        return None

    # Per il radar commerciale principale scartiamo micro-interventi.
    # Si evita rumore da manutenzioni minime, piccoli acquisti e pratiche non prioritarie.
    if cost is not None and cost < MIN_PROJECT_VALUE_EUR:
        return None

    category = classify_nii_category(combined_text)
    intervention_type = infer_intervention_type(combined_text)

    url = source_url
    if not url and cup:
        url = PORTAL_PROJECT_URL.format(cup=cup)

    record = ProjectRecord(
        source="OpenCUP",
        source_url=url,
        external_id=f"OPENCUP-{cup}" if cup else None,
        title=title,
        description=description,
        region=region,
        province=province,
        municipality=municipality,
        address=address,
        sector=sector or area or classification,
        category=category,
        intervention_type=intervention_type,
        phase=infer_phase_from_opencup(status, year_decision),
        status=status,
        client=client,
        client_type="pubblico",
        designer=None,
        works_director=None,
        rup=rup,
        contractor=contractor_name,
        contractor_name=contractor_name,
        contractor_vat=contractor_vat,
        contractor_tax_code=contractor_tax_code,
        contractor_address=contractor_address,
        contractor_city=contractor_city,
        contractor_province=contractor_province,
        contractor_pec=contractor_pec,
        contractor_email=contractor_email,
        contractor_phone=contractor_phone,
        contact_name=contact_name,
        contact_role=contact_role,
        contact_email=contact_email,
        contact_phone=contact_phone,
        estimated_value_eur=cost,
        award_amount_eur=award_amount,
        cup=cup,
        cig=cig,
        funding=funding,
        award_date=award_date,
        award_source_url=award_source_url,
        enrichment_status=enrichment_status,
        ai_notes=f"Classificazione OpenCUP: {classification or ''} | Tipologia: {typology or ''} | Area: {area or ''} | Sottosettore: {subsector or ''} | Anno decisione: {year_decision or ''}",
        last_seen=datetime.now().isoformat(timespec="seconds"),
    )

    return record



def _detect_delimiter(sample: str) -> str:
    candidates = [";", "|", "\t", ","]
    counts = {delimiter: sample.count(delimiter) for delimiter in candidates}
    best = max(counts, key=counts.get)

    if counts[best] <= 0:
        return ";"

    return best


def _iter_csv_rows_from_zip(zip_path: Path):
    import io

    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]

        for csv_name in csv_names:
            print(f"[OpenCUP] Leggo CSV nello zip: {zip_path.name} -> {csv_name}")

            with zf.open(csv_name) as raw:
                wrapper = io.TextIOWrapper(
                    raw,
                    encoding="utf-8-sig",
                    errors="ignore",
                    newline=""
                )

                sample = wrapper.read(8192)
                delimiter = _detect_delimiter(sample)
                wrapper.seek(0)

                print(f"[OpenCUP] Delimitatore rilevato: {repr(delimiter)}")

                reader = csv.DictReader(wrapper, delimiter=delimiter)

                for row in reader:
                    yield row


def _iter_csv_rows_from_plain_file(csv_path: Path):
    print(f"[OpenCUP] Leggo CSV: {csv_path.name}")

    with csv_path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        sample = f.read(8192)
        delimiter = _detect_delimiter(sample)
        f.seek(0)

        print(f"[OpenCUP] Delimitatore rilevato: {repr(delimiter)}")

        reader = csv.DictReader(f, delimiter=delimiter)

        for row in reader:
            yield row



def collect_from_local_opencup_files(
    max_records: int | None = None,
    max_scan_rows: int | None = None,
) -> list[ProjectRecord]:
    RAW_OPENCUP_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(RAW_OPENCUP_DIR.glob("*.zip")) + sorted(RAW_OPENCUP_DIR.glob("*.csv"))

    if not files:
        print("[OpenCUP] Nessun file ZIP/CSV trovato in data/raw/opencup.")
        return []

    records: list[ProjectRecord] = []
    seen: set[str] = set()
    scanned_rows = 0

    for file_path in files:
        if file_path.suffix.lower() == ".zip":
            rows_iter = _iter_csv_rows_from_zip(file_path)
        else:
            rows_iter = _iter_csv_rows_from_plain_file(file_path)

        for row in rows_iter:
            scanned_rows += 1

            if scanned_rows % 25_000 == 0:
                print(
                    f"[OpenCUP] Righe lette: {scanned_rows:,} | "
                    f"record candidati: {len(records):,}"
                )

            try:
                record = _record_from_generic_row(row)
            except Exception as exc:
                print(f"[OpenCUP] Riga saltata per errore parsing: {exc}")
                continue

            if not record:
                if max_scan_rows is not None and scanned_rows >= max_scan_rows:
                    print(f"[OpenCUP] Limite scansione raggiunto: {max_scan_rows:,} righe.")
                    break
                continue

            key = record.cup or record.external_id or record.title
            if key in seen:
                if max_scan_rows is not None and scanned_rows >= max_scan_rows:
                    print(f"[OpenCUP] Limite scansione raggiunto: {max_scan_rows:,} righe.")
                    break
                continue

            seen.add(key)
            records.append(record)

            if max_scan_rows is not None and scanned_rows >= max_scan_rows:
                print(f"[OpenCUP] Limite scansione raggiunto: {max_scan_rows:,} righe.")
                break

        if max_scan_rows is not None and scanned_rows >= max_scan_rows:
            break

    print(f"[OpenCUP] Scansione completata. Righe lette: {scanned_rows:,}. Candidati: {len(records):,}")

    records.sort(
        key=lambda r: (
            r.estimated_value_eur or 0,
            r.last_seen or "",
        ),
        reverse=True,
    )

    if max_records is not None and len(records) > max_records:
        print(f"[OpenCUP] Record candidati: {len(records):,}. Tengo i primi {max_records} per valore.")
        records = records[:max_records]

    return records


def _collect_cup_via_api(cup: str) -> ProjectRecord | None:
    url = API_CUP_URL.format(cup=cup)

    try:
        response = requests.get(url, headers=HEADERS, timeout=45)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"[OpenCUP] API non riuscita per {cup}: {exc}")
        return _collect_cup_via_portal(cup)

    flat = _flatten_json(data)
    row = {k: v for k, v in flat.items()}

    record = _record_from_generic_row(row, source_url=PORTAL_PROJECT_URL.format(cup=cup))

    if record:
        record.source_url = PORTAL_PROJECT_URL.format(cup=cup)
        record.cup = record.cup or cup
        record.external_id = f"OPENCUP-{cup}"

    return record


def _extract_after_label(text: str, label: str, next_labels: list[str]) -> str | None:
    escaped_label = re.escape(label)
    next_pattern = "|".join(re.escape(x) for x in next_labels)
    pattern = rf"{escaped_label}\s+(.+?)(?:\s+(?:{next_pattern})\s+|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return clean_text(match.group(1))


def _collect_cup_via_portal(cup: str) -> ProjectRecord | None:
    url = PORTAL_PROJECT_URL.format(cup=cup)

    try:
        response = requests.get(url, headers=HEADERS, timeout=45)
        response.raise_for_status()
    except Exception as exc:
        print(f"[OpenCUP] Portale non riuscito per {cup}: {exc}")
        return None

    soup = BeautifulSoup(response.text, "lxml")
    text = clean_text(soup.get_text(" ", strip=True))

    labels = [
        "CUP:", "Totale costo previsto", "Totale Finanziamento pubblico previsto",
        "Anno decisione", "Stato", "Soggetto titolare", "Descrizione intervento",
        "Struttura/Infrastruttura oggetto dell'intervento",
        "Indirizzo o area di riferimento", "Regione", "Provincia", "Comune",
        "Classificazione", "Tipologia", "Area d'intervento", "Settore",
        "Sottosettore", "Categoria", "Data di generazione"
    ]

    title = None
    cup_pos = text.find("CUP:")
    if cup_pos > 0:
        before = text[:cup_pos]
        # prende l'ultimo blocco sensato prima di CUP
        parts = [p.strip() for p in re.split(r"Dettaglio Progetto|version portlet|version theme", before) if p.strip()]
        if parts:
            title = parts[-1][-500:]

    description = _extract_after_label(text, "Descrizione intervento", labels)
    client = _extract_after_label(text, "Soggetto titolare", labels)
    region = _extract_after_label(text, "Regione", labels)
    province = _extract_after_label(text, "Provincia", labels)
    municipality = _extract_after_label(text, "Comune", labels)
    address = _extract_after_label(text, "Indirizzo o area di riferimento", labels)
    status = _extract_after_label(text, "Stato", labels)
    classification = _extract_after_label(text, "Classificazione", labels)
    typology = _extract_after_label(text, "Tipologia", labels)
    area = _extract_after_label(text, "Area d'intervento", labels)
    sector = _extract_after_label(text, "Settore", labels)
    category_raw = _extract_after_label(text, "Categoria", labels)
    year_decision = _extract_after_label(text, "Anno decisione", labels)
    cost = _to_float(_extract_after_label(text, "Totale costo previsto", labels))

    row = {
        "cup": cup,
        "descrizione intervento": description or title,
        "soggetto titolare": client,
        "regione": region,
        "provincia": province,
        "comune": municipality,
        "indirizzo o area di riferimento": address,
        "stato": status,
        "classificazione": classification,
        "tipologia": typology,
        "area intervento": area,
        "settore": sector,
        "categoria": category_raw,
        "anno decisione": year_decision,
        "totale costo previsto": cost,
    }

    return _record_from_generic_row(row, source_url=url)


def collect_from_seed_cups(max_records: int = 20) -> list[ProjectRecord]:
    records: list[ProjectRecord] = []

    for cup in SEED_CUPS[:max_records]:
        print(f"[OpenCUP] Leggo CUP seed: {cup}")
        record = _collect_cup_via_api(cup)
        if record:
            records.append(record)

    return records


def collect_opencup(max_records: int | None = None) -> list[ProjectRecord]:
    records = collect_from_local_opencup_files(max_records=max_records)

    if records:
        print(f"[OpenCUP] Record da file locale: {len(records):,}")
        return records

    print("[OpenCUP] Uso fallback seed CUP.")
    fallback_limit = len(SEED_CUPS) if max_records is None else min(max_records, len(SEED_CUPS))
    return collect_from_seed_cups(max_records=fallback_limit)
