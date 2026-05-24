from pathlib import Path
import csv
import json
import re

ROOT = Path(".")
OUT = ROOT / "reports" / "master_projects.json"
BRANCH_MAP = ROOT / "config" / "municipality_to_branch.csv"

SOURCES = [
    ROOT / "docs" / "data" / "national_anac_relevant_awards.json",
    ROOT / "docs" / "national_operational_data.json",
]

def clean(v):
    if v is None:
        return ""
    return str(v).strip()

def load_json(path):
    if not path.exists():
        print(f"[SKIP] manca: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("records", [])
    print(f"[OK] {path}: {len(data)} record")
    return data

def key_for(r):
    cup = clean(r.get("cup")).upper()
    cig = clean(r.get("cig")).upper()
    title = clean(r.get("title")).upper()
    municipality = clean(r.get("municipality")).upper()
    if cup and cig:
        return f"CUP_CIG::{cup}::{cig}"
    if cup:
        return f"CUP::{cup}"
    return f"TITLE::{title}::{municipality}"



def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()



REGION_BRANCH_FALLBACKS = {
    "ABRUZZO": "Roma Nomentana",
    "MARCHE": "Rimini",
    "SICILIA": "Catania",
    "CALABRIA": "Cosenza",
    "FRIULI VENEZIA GIULIA": "Udine",
    "PUGLIA": "Bari",
    "UMBRIA": "Perugia",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",

}

PROVINCE_BRANCH_FALLBACKS = {
    "PISTOIA": "Firenze",
    "PT": "Firenze",
    "PRATO": "Firenze",
    "PO": "Firenze",
    "FIRENZE": "Firenze",
    "FI": "Firenze",
    "SIENA": "Firenze",
    "SI": "Firenze",
    "AREZZO": "Firenze",
    "AR": "Firenze",

    "BOLOGNA": "Bologna",
    "BO": "Bologna",

    "BOLZANO": "Bolzano",
    "BOLZANO BOZEN": "Bolzano",
    "BOZEN": "Bolzano",
    "BZ": "Bolzano",

    "TRENTO": "Trento",
    "TN": "Trento",
    "ALESSANDRIA": "Milano Sud",
    "AL": "Milano Sud",
    "AOSTA": "Torino",
    "AO": "Torino",
    "ASTI": "Torino",
    "AT": "Torino",
    "AVELLINO": "Napoli",
    "AV": "Napoli",
    "BARI": "Bari",
    "BA": "Bari",
    "BARLETTA ANDRIA TRANI": "Bari",
    "BARLETTA-ANDRIA-TRANI": "Bari",
    "BT": "Bari",
    "BELLUNO": "Treviso",
    "BL": "Treviso",
    "BENEVENTO": "Napoli",
    "BN": "Napoli",
    "BERGAMO": "Bergamo",
    "BG": "Bergamo",
    "BIELLA": "Torino",
    "BI": "Torino",
    "POTENZA": "SALERNO",
    "PZ": "SALERNO",
    "MATERA": "Bari",
    "MT": "Bari",
    "CAMPOBASSO": "Bari",
    "CB": "Bari",
    "ISERNIA": "Frosinone",
    "IS": "Frosinone",
    "VERCELLI": "Torino",
    "VC": "Torino",
    "VERBANO CUSIO OSSOLA": "Milano Ovest",
    "VERBANO-CUSIO-OSSOLA": "Milano Ovest",
    "VB": "Milano Ovest",
    "NOVARA": "Milano Ovest",
    "NO": "Milano Ovest",
    "COMO": "Milano Nord",
    "CO": "Milano Nord",
    "VARESE": "Milano Ovest",
    "VA": "Milano Ovest",
    "PAVIA": "Milano Sud",
    "PV": "Milano Sud",
    "LODI": "Milano Est",
    "LO": "Milano Est",
    "MANTOVA": "Verona",
    "MN": "Verona",
    "CREMONA": "Brescia",
    "CR": "Brescia",
    "REGGIO NELL EMILIA": "Parma",
    "REGGIO NELL'EMILIA": "Parma",
    "REGGIO EMILIA": "Parma",
    "RE": "Parma",
    "FORLI CESENA": "Rimini",
    "FORLI-CESENA": "Rimini",
    "FC": "Rimini",
    "FERRARA": "Bologna",
    "FE": "Bologna",
    "PIACENZA": "Parma",
    "PC": "Parma",
    "RAVENNA": "Rimini",
    "RA": "Rimini",
    "MODENA": "Sassuolo",
    "MO": "Sassuolo",
    "VICENZA": "Padova",
    "VI": "Padova",
    "ROVIGO": "Padova",
    "RO": "Padova",
    "SAVONA": "Albenga",
    "SV": "Albenga",
    "IMPERIA": "Albenga",
    "IM": "Albenga",
    "LA SPEZIA": "Lucca",
    "SP": "Lucca",
    "GROSSETO": "Livorno",
    "GR": "Livorno",
    "RIETI": "Roma Nomentana",
    "RI": "Roma Nomentana",
    "LATINA": "Frosinone",
    "LT": "Frosinone",
    "BRINDISI": "Bari",
    "BR": "Bari",
    "FOGGIA": "Bari",
    "FG": "Bari",
    "LECCE": "Bari",
    "LE": "Bari",
    "TARANTO": "Bari",
    "TA": "Bari",
    "PERUGIA": "Perugia",
    "PG": "Perugia",
    "TERNI": "Perugia",
    "TR": "Perugia",
    "NUORO": "Sassari",
    "NU": "Sassari",
    "ORISTANO": "Cagliari",
    "OR": "Cagliari",
    "MONZA E DELLA BRIANZA": "Milano Nord",
    "MONZA BRIANZA": "Milano Nord",
    "MB": "Milano Nord",
    "PISA": "Livorno",
    "PI": "Livorno",
    "CASERTA": "Napoli",
    "CE": "Napoli",
    "VITERBO": "Roma Nomentana",
    "VT": "Roma Nomentana",
    "MASSA CARRARA": "Lucca",
    "MASSA-CARRARA": "Lucca",
    "MS": "Lucca",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",
    "CARBONIA IGLESIAS": "Cagliari",
    "CARBONIA-IGLESIAS": "Cagliari",
    "CI": "Cagliari",
    "CITTA METROPOLITANA DI CAGLIARI": "Cagliari",
    "CITTA' METROPOLITANA DI CAGLIARI": "Cagliari",
    "CA": "Cagliari",
    "CITTA METROPOLITANA DI SASSARI": "Sassari",
    "CITTA' METROPOLITANA DI SASSARI": "Sassari",
    "SS": "Sassari",
    "GALLURA NORD EST SARDEGNA": "Sassari",
    "GALLURA NORD-EST SARDEGNA": "Sassari",
    "MEDIO CAMPIDANO": "Cagliari",
    "VS": "Cagliari",
    "OGLIASTRA": "Cagliari",
    "OG": "Cagliari",
    "OLBIA TEMPIO": "Sassari",
    "OLBIA-TEMPIO": "Sassari",
    "OT": "Sassari",
    "SUD SARDEGNA": "Cagliari",
    "SU": "Cagliari",

}


def territorial_branch_fallback(record):
    region = norm(record.get("region"))
    province_values = province_variants(record.get("province"))

    for province in province_values:
        branch = PROVINCE_BRANCH_FALLBACKS.get(province)
        if branch:
            return {
                "branch": branch,
                "branch_candidates": "",
                "branch_confidence": "territoriale_provincia",
                "method": "fallback_provincia_territoriale",
            }

    branch = REGION_BRANCH_FALLBACKS.get(region)
    if branch:
        return {
            "branch": branch,
            "branch_candidates": "",
            "branch_confidence": "territoriale_regione",
            "method": "fallback_regione_territoriale",
        }

    return None

def load_branch_map():
    exact = {}

    if not BRANCH_MAP.exists():
        print(f"[WARN] Mappa filiali non trovata: {BRANCH_MAP}")
        return exact

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            municipality_norm = clean(row.get("municipality_norm"))
            province_norm = clean(row.get("province_norm"))

            if not municipality_norm or not province_norm:
                continue

            exact[(municipality_norm, province_norm)] = {
                "branch": clean(row.get("branch")),
                "branch_candidates": clean(row.get("branch_candidates")),
                "branch_confidence": clean(row.get("confidence")),
            }

    print(f"[OK] Mappa comuni → filiali: {len(exact)} chiavi esatte")
    return exact


def apply_branch_assignment(record, branch_map):
    existing_branch = clean(record.get("branch"))

    # Se ha già una filiale vera o AMBIGUA, non sovrascriviamo.
    if existing_branch and existing_branch not in {"NON ASSEGNATA", "NON_ASSEGNATA"}:
        return record

    key = (
        norm(record.get("municipality")),
        norm(record.get("province")),
    )

    match = branch_map.get(key)

    if match:
        record["branch"] = match["branch"] or "NON ASSEGNATA"
        record["branch_candidates"] = match["branch_candidates"]
        record["branch_confidence"] = match["branch_confidence"]
    else:
        record["branch"] = "NON ASSEGNATA"
        record["branch_candidates"] = ""
        record["branch_confidence"] = "nessuna"

    return record

def normalize(r, source_name):
    return {
        "id": "",
        "source": source_name,
        "sources": [source_name],
        "branch": clean(r.get("branch") or r.get("assigned_branch") or r.get("filiale")),
        "branch_candidates": clean(r.get("branch_candidates")),
        "branch_confidence": clean(r.get("branch_confidence")),
        "segment": clean(r.get("segment") or r.get("primary_segment")),
        "cup": clean(r.get("cup")),
        "cig": clean(r.get("cig")),
        "title": clean(r.get("title")),
        "category": clean(r.get("category")),
        "region": clean(r.get("region")),
        "province": clean(r.get("province")),
        "municipality": clean(r.get("municipality")),
        "address": clean(
            r.get("INDIRIZZO_INTERVENTO")
            or r.get("indirizzo_intervento")
            or r.get("indirizzo")
            or r.get("address")
        ),
        "project_value": r.get("project_value") or r.get("value_eur") or r.get("value") or 0,
        "client": clean(r.get("client")),
        "contractors": clean(r.get("contractors") or r.get("contractor_name")),
        "contractor_tax_codes": clean(r.get("contractor_tax_codes") or r.get("contractor_tax_code")),
        "award_date": clean(r.get("award_date")),
        "award_result": clean(r.get("award_result")),
        "source_url": clean(r.get("source_url") or r.get("url")),
        "has_anac": bool(clean(r.get("cig")) or clean(r.get("contractors")) or clean(r.get("award_date"))),
    }

def merge_record(base, incoming):
    for k, v in incoming.items():
        if k == "sources":
            base["sources"] = sorted(set(base.get("sources", []) + incoming.get("sources", [])))
            continue

        if k == "has_anac":
            base[k] = bool(base.get(k)) or bool(v)
            continue

        if not base.get(k) and v:
            base[k] = v

    # Se il record ANAC ha dati più forti, privilegiali
    if incoming.get("has_anac"):
        for k in ["cig", "contractors", "contractor_tax_codes", "award_date", "award_result"]:
            if incoming.get(k):
                base[k] = incoming[k]
        base["has_anac"] = True

    return base


def cup_year(cup):
    c = clean(cup)
    if len(c) < 6:
        return None
    yy = c[4:6]
    if not yy.isdigit():
        return None
    n = int(yy)
    return 2000 + n if n <= 40 else 1900 + n

def apply_quality_layer(r):
    flags = []
    score = 50

    value = float(r.get("project_value") or 0)
    title = clean(r.get("title")).upper()
    municipality = clean(r.get("municipality"))
    has_anac = bool(r.get("has_anac"))
    awards_count = int(r.get("awards_count") or 0)
    year = cup_year(r.get("cup"))

    if has_anac:
        score += 25
    else:
        flags.append("NO_ANAC_MATCH")
        score -= 8

    if awards_count > 1:
        score += min(12, awards_count * 2)

    if year:
        r["cup_year"] = year
        if year < 2015:
            flags.append("OLD_CUP")
            score -= 12
        elif year >= 2023:
            score += 8
    else:
        flags.append("CUP_YEAR_UNKNOWN")
        score -= 5

    generic_terms = [
        "TERRITORIO COMUNALE",
        "EDIFICI DEMANIALI",
        "EDIFICI SCOLASTICI",
        "SERVIZIO DI MANUTENZIONE",
        "MANUTENZIONE ORDINARIA",
        "VERDE",
        "RIFACIMENTO SERVIZI IGIENICI",
        "PIAZZALE",
        "ARREDAMENTO URBANO",
    ]

    if any(t in title for t in generic_terms):
        flags.append("GENERIC_OR_MAINTENANCE_TITLE")
        score -= 15

    if value >= 150_000_000 and not has_anac:
        flags.append("HIGH_VALUE_WITHOUT_ANAC")
        score -= 12

    if value >= 100_000_000 and year and year < 2015:
        flags.append("OLD_HIGH_VALUE")
        score -= 15

    if value >= 100_000_000 and any(t in title for t in [
        "SERVIZI IGIENICI",
        "VERDE",
        "MUNICIPIO",
        "PIAZZALE",
        "SCUOLA MEDIA",
        "URBANIZZAZIONE PRIMARIA",
    ]):
        flags.append("VALUE_SUSPICIOUS")
        score -= 25

    if r.get("branch") in ("", None):
        flags.append("BRANCH_MISSING")
        score -= 8

    if r.get("branch") == "AMBIGUA":
        flags.append("BRANCH_AMBIGUOUS")
        score -= 4

    if r.get("branch") == "NON ASSEGNATA":
        flags.append("BRANCH_NOT_ASSIGNED")
        score -= 10

    if value >= 50_000_000:
        score += 8
    elif value >= 10_000_000:
        score += 4

    score = max(0, min(100, int(score)))

    if score >= 75:
        reliability = "ALTA"
    elif score >= 50:
        reliability = "MEDIA"
    else:
        reliability = "BASSA"

    r["quality_flags"] = flags
    r["commercial_score"] = score
    r["data_reliability"] = reliability

    return r


def group_projects(rows):
    groups = {}

    for r in rows:
        cup = clean(r.get("cup")).upper()
        key = cup if cup else clean(r.get("id"))

        if key not in groups:
            groups[key] = []

        groups[key].append(r)

    out = []

    for key, items in groups.items():
        base = max(items, key=lambda x: float(x.get("project_value") or 0)).copy()

        awards = []
        contractors_seen = []

        for r in items:
            if r.get("has_anac"):
                award = {
                    "cig": r.get("cig", ""),
                    "contractors": r.get("contractors", ""),
                    "contractor_tax_codes": r.get("contractor_tax_codes", ""),
                    "award_amount_eur": r.get("award_amount_eur", ""),
                    "award_share_pct": r.get("award_share_pct", ""),
                    "award_weight": r.get("award_weight", ""),
                    "ratio_note": r.get("ratio_note", ""),
                    "award_date": r.get("award_date", ""),
                    "award_result": r.get("award_result", ""),
                    "award_criteria": r.get("award_criteria", ""),
                    "included_services": r.get("included_services", ""),
                    "id_aggiudicazione": r.get("id_aggiudicazione", "")
                }
                awards.append(award)

                for c in clean(r.get("contractors")).split("|"):
                    c = c.strip()
                    if c and c not in contractors_seen:
                        contractors_seen.append(c)

        base["awards"] = awards
        base["awards_count"] = len(awards)
        base["has_anac"] = bool(awards)
        base["contractors_summary"] = (
            contractors_seen[0] + (f" + altri {len(contractors_seen)-1} OE" if len(contractors_seen) > 1 else "")
            if contractors_seen else ""
        )

        # se il progetto ? OpenCUP puro, pulisce campi ANAC singoli
        if not awards:
            for k in [
                "cig", "contractors", "contractor_tax_codes",
                "award_date", "award_result", "award_amount_eur",
                "award_share_pct", "award_weight", "ratio_note"
            ]:
                base[k] = ""

        out.append(base)

    return out



# --- Branch assignment override v2: project location only, no CAP soggetto titolare ---

PROVINCE_ALIASES = {
    "MONZA E DELLA BRIANZA": "MB",
    "MONZA BRIANZA": "MB",
    "FORLI CESENA": "FC",
    "FORLI-CESENA": "FC",
    "FORLI": "FC",
    "REGGIO NELL EMILIA": "RE",
    "REGGIO EMILIA": "RE",
    "BOLZANO": "BZ",
    "BOLZANO BOZEN": "BZ",
    "BOZEN": "BZ",
    "AOSTA": "AO",
    "VALLE D AOSTA": "AO",
    "SUD SARDEGNA": "SU",
    "CITTA METROPOLITANA DI CAGLIARI": "CA",
    "CITTA METROPOLITANA DI FIRENZE": "FI",
    "CITTA METROPOLITANA DI ROMA CAPITALE": "RM",
    "CITTA METROPOLITANA DI MILANO": "MI",
    "CITTA METROPOLITANA DI NAPOLI": "NA",
    "CITTA METROPOLITANA DI TORINO": "TO",
    "CITTA METROPOLITANA DI BOLOGNA": "BO",
    "CITTA METROPOLITANA DI GENOVA": "GE",
    "CITTA METROPOLITANA DI VENEZIA": "VE",
    "CITTA METROPOLITANA DI BARI": "BA",
    "CITTA METROPOLITANA DI REGGIO CALABRIA": "RC",
    "MASSA CARRARA": "MS",
    "LA SPEZIA": "SP",
    "PESARO E URBINO": "PU",
    "BARLETTA ANDRIA TRANI": "BT",
    "VERBANO CUSIO OSSOLA": "VB",
    "VIBO VALENTIA": "VV",
    "ASCOLI PICENO": "AP",
    "REGGIO CALABRIA": "RC",
    "CALTANISSETTA": "CL",
    "CARBONIA IGLESIAS": "CI",
    "CARBONIA-IGLESIAS": "CI",
    "CITTA' METROPOLITANA DI CAGLIARI": "CA",
    "CITTA METROPOLITANA DI SASSARI": "SS",
    "CITTA' METROPOLITANA DI SASSARI": "SS",
    "GALLURA NORD EST SARDEGNA": "OT",
    "GALLURA NORD-EST SARDEGNA": "OT",
    "MEDIO CAMPIDANO": "VS",
    "OGLIASTRA": "OG",
    "OLBIA TEMPIO": "OT",
    "OLBIA-TEMPIO": "OT",
    "VALLE D'AOSTA": "AO",

}


def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def province_variants(value):
    raw = norm(value)
    variants = set()

    if raw:
        variants.add(raw)

    alias = PROVINCE_ALIASES.get(raw)
    if alias:
        variants.add(alias)

    return {v for v in variants if v}



REGION_BRANCH_FALLBACKS = {
    "ABRUZZO": "Roma Nomentana",
    "MARCHE": "Rimini",
    "SICILIA": "Catania",
    "CALABRIA": "Cosenza",
    "FRIULI VENEZIA GIULIA": "Udine",
    "PUGLIA": "Bari",
    "UMBRIA": "Perugia",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",

}

PROVINCE_BRANCH_FALLBACKS = {
    "PISTOIA": "Firenze",
    "PT": "Firenze",
    "PRATO": "Firenze",
    "PO": "Firenze",
    "FIRENZE": "Firenze",
    "FI": "Firenze",
    "SIENA": "Firenze",
    "SI": "Firenze",
    "AREZZO": "Firenze",
    "AR": "Firenze",

    "BOLOGNA": "Bologna",
    "BO": "Bologna",

    "BOLZANO": "Bolzano",
    "BOLZANO BOZEN": "Bolzano",
    "BOZEN": "Bolzano",
    "BZ": "Bolzano",

    "TRENTO": "Trento",
    "TN": "Trento",
    "ALESSANDRIA": "Milano Sud",
    "AL": "Milano Sud",
    "AOSTA": "Torino",
    "AO": "Torino",
    "ASTI": "Torino",
    "AT": "Torino",
    "BIELLA": "Torino",
    "BI": "Torino",
    "VERCELLI": "Torino",
    "VC": "Torino",
    "VERBANO CUSIO OSSOLA": "Milano Ovest",
    "VERBANO-CUSIO-OSSOLA": "Milano Ovest",
    "VB": "Milano Ovest",
    "NOVARA": "Milano Ovest",
    "NO": "Milano Ovest",
    "COMO": "Milano Nord",
    "CO": "Milano Nord",
    "VARESE": "Milano Ovest",
    "VA": "Milano Ovest",
    "PAVIA": "Milano Sud",
    "PV": "Milano Sud",
    "LODI": "Milano Est",
    "LO": "Milano Est",
    "MANTOVA": "Verona",
    "MN": "Verona",
    "CREMONA": "Brescia",
    "CR": "Brescia",
    "REGGIO NELL EMILIA": "Parma",
    "REGGIO NELL'EMILIA": "Parma",
    "REGGIO EMILIA": "Parma",
    "RE": "Parma",
    "FORLI CESENA": "Rimini",
    "FORLI-CESENA": "Rimini",
    "FC": "Rimini",
    "FERRARA": "Bologna",
    "FE": "Bologna",
    "PIACENZA": "Parma",
    "PC": "Parma",
    "RAVENNA": "Rimini",
    "RA": "Rimini",
    "MODENA": "Sassuolo",
    "MO": "Sassuolo",
    "VICENZA": "Padova",
    "VI": "Padova",
    "ROVIGO": "Padova",
    "RO": "Padova",
    "BELLUNO": "Treviso",
    "BL": "Treviso",
    "SAVONA": "Albenga",
    "SV": "Albenga",
    "IMPERIA": "Albenga",
    "IM": "Albenga",
    "LA SPEZIA": "Lucca",
    "SP": "Lucca",
    "GROSSETO": "Livorno",
    "GR": "Livorno",
    "RIETI": "Roma Nomentana",
    "RI": "Roma Nomentana",
    "LATINA": "Frosinone",
    "LT": "Frosinone",
    "AVELLINO": "Napoli",
    "AV": "Napoli",
    "BENEVENTO": "Napoli",
    "BN": "Napoli",
    "POTENZA": "SALERNO",
    "PZ": "SALERNO",
    "BARI": "Bari",
    "BA": "Bari",
    "BARLETTA ANDRIA TRANI": "Bari",
    "BARLETTA-ANDRIA-TRANI": "Bari",
    "BT": "Bari",
    "BRINDISI": "Bari",
    "BR": "Bari",
    "FOGGIA": "Bari",
    "FG": "Bari",
    "LECCE": "Bari",
    "LE": "Bari",
    "TARANTO": "Bari",
    "TA": "Bari",
    "MATERA": "Bari",
    "MT": "Bari",
    "CAMPOBASSO": "Bari",
    "CB": "Bari",
    "ISERNIA": "Frosinone",
    "IS": "Frosinone",
    "PERUGIA": "Perugia",
    "PG": "Perugia",
    "TERNI": "Perugia",
    "TR": "Perugia",
    "NUORO": "Sassari",
    "NU": "Sassari",
    "ORISTANO": "Cagliari",
    "OR": "Cagliari",
    "MONZA E DELLA BRIANZA": "Milano Nord",
    "MONZA BRIANZA": "Milano Nord",
    "MB": "Milano Nord",
    "PISA": "Livorno",
    "PI": "Livorno",
    "CASERTA": "Napoli",
    "CE": "Napoli",
    "VITERBO": "Roma Nomentana",
    "VT": "Roma Nomentana",
    "MASSA CARRARA": "Lucca",
    "MASSA-CARRARA": "Lucca",
    "MS": "Lucca",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",
    "CARBONIA IGLESIAS": "Cagliari",
    "CARBONIA-IGLESIAS": "Cagliari",
    "CI": "Cagliari",
    "CITTA METROPOLITANA DI CAGLIARI": "Cagliari",
    "CITTA' METROPOLITANA DI CAGLIARI": "Cagliari",
    "CA": "Cagliari",
    "CITTA METROPOLITANA DI SASSARI": "Sassari",
    "CITTA' METROPOLITANA DI SASSARI": "Sassari",
    "SS": "Sassari",
    "GALLURA NORD EST SARDEGNA": "Sassari",
    "GALLURA NORD-EST SARDEGNA": "Sassari",
    "MEDIO CAMPIDANO": "Cagliari",
    "VS": "Cagliari",
    "OGLIASTRA": "Cagliari",
    "OG": "Cagliari",
    "OLBIA TEMPIO": "Sassari",
    "OLBIA-TEMPIO": "Sassari",
    "OT": "Sassari",
    "SUD SARDEGNA": "Cagliari",
    "SU": "Cagliari",

}


def territorial_branch_fallback(record):
    region = norm(record.get("region"))
    province_values = province_variants(record.get("province"))

    for province in province_values:
        branch = PROVINCE_BRANCH_FALLBACKS.get(province)
        if branch:
            return {
                "branch": branch,
                "branch_candidates": "",
                "branch_confidence": "territoriale_provincia",
                "method": "fallback_provincia_territoriale",
            }

    branch = REGION_BRANCH_FALLBACKS.get(region)
    if branch:
        return {
            "branch": branch,
            "branch_candidates": "",
            "branch_confidence": "territoriale_regione",
            "method": "fallback_regione_territoriale",
        }

    return None

def load_branch_map():
    exact = {}
    municipality_only = {}
    municipality_signature = {}
    municipality_ambiguous = set()

    if not BRANCH_MAP.exists():
        print(f"[WARN] Mappa filiali non trovata: {BRANCH_MAP}")
        return {"exact": exact, "municipality_only": municipality_only}

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            municipality_norm = clean(row.get("municipality_norm"))
            province_norm = clean(row.get("province_norm"))

            if not municipality_norm or not province_norm:
                continue

            item = {
                "branch": clean(row.get("branch")),
                "branch_candidates": clean(row.get("branch_candidates")),
                "branch_confidence": clean(row.get("confidence")),
            }

            province_keys = set()
            province_keys.add(province_norm)
            province_keys.update(province_variants(province_norm))
            province_keys.update(province_variants(row.get("province")))
            province_keys.update(province_variants(row.get("sigla_provincia")))
            province_keys.update(province_variants(row.get("province_code")))

            for province_key in province_keys:
                if province_key:
                    exact[(municipality_norm, province_key)] = item

            signature = (item["branch"], item["branch_candidates"])
            previous_signature = municipality_signature.get(municipality_norm)

            if previous_signature and previous_signature != signature:
                municipality_ambiguous.add(municipality_norm)
            else:
                municipality_only[municipality_norm] = item
                municipality_signature[municipality_norm] = signature

    for municipality_norm in municipality_ambiguous:
        municipality_only.pop(municipality_norm, None)

    print(f"[OK] Mappa comuni → filiali: {len(exact)} chiavi esatte, {len(municipality_only)} fallback comune")
    return {"exact": exact, "municipality_only": municipality_only}


def apply_branch_assignment(record, branch_map):
    existing_branch = clean(record.get("branch"))

    # Non usare CAP_SOGGETTO_TITOLARE: non localizza il progetto.
    # Se ha già una filiale vera o AMBIGUA, non sovrascriviamo.
    if existing_branch and existing_branch not in {"NON ASSEGNATA", "NON_ASSEGNATA"}:
        return record

    municipality = norm(record.get("municipality"))
    province_raw = record.get("province")

    invalid_geo = {"", "TUTTI", "TUTTE", "VARI", "VARIE", "NAZIONALE", "ITALIA"}

    match = None
    method = "none"

    if municipality not in invalid_geo:
        for province in province_variants(province_raw):
            if province in invalid_geo:
                continue

            match = branch_map["exact"].get((municipality, province))
            if match:
                method = "exact_or_alias_province"
                break

    # Fallback prudente: solo se il comune è univoco nella mappa.
    if not match and municipality not in invalid_geo:
        match = branch_map["municipality_only"].get(municipality)
        if match:
            method = "fallback_comune_univoco"

    # Fallback commerciale esplicito su provincia/regione.
    territorial_match = None
    if not match:
        territorial_match = territorial_branch_fallback(record)

    if match:
        record["branch"] = match["branch"] or "NON ASSEGNATA"
        record["branch_candidates"] = match["branch_candidates"]
        record["branch_confidence"] = match["branch_confidence"] or method
        record["branch_assignment_method"] = method
    elif territorial_match:
        record["branch"] = territorial_match["branch"]
        record["branch_candidates"] = territorial_match["branch_candidates"]
        record["branch_confidence"] = territorial_match["branch_confidence"]
        record["branch_assignment_method"] = territorial_match["method"]
    else:
        record["branch"] = "NON ASSEGNATA"
        record["branch_candidates"] = ""
        record["branch_confidence"] = "nessuna"
        record["branch_assignment_method"] = "none"

    return record



MUNICIPALITY_BRANCH_FALLBACKS = {
    "VERMEZZO CON ZELO": "Milano Sud",
}

# --- Branch assignment override v3: project location only, automatic same-name province fallback ---

PROVINCE_ALIASES = {
    "MONZA E DELLA BRIANZA": "MB",
    "MONZA BRIANZA": "MB",
    "FORLI CESENA": "FC",
    "FORLI-CESENA": "FC",
    "FORLI": "FC",
    "REGGIO NELL EMILIA": "RE",
    "REGGIO EMILIA": "RE",
    "BOLZANO": "BZ",
    "BOLZANO BOZEN": "BZ",
    "BOZEN": "BZ",
    "AOSTA": "AO",
    "VALLE D AOSTA": "AO",
    "SUD SARDEGNA": "SU",
    "CITTA METROPOLITANA DI CAGLIARI": "CA",
    "CITTA METROPOLITANA DI FIRENZE": "FI",
    "CITTA METROPOLITANA DI ROMA CAPITALE": "RM",
    "CITTA METROPOLITANA DI MILANO": "MI",
    "CITTA METROPOLITANA DI NAPOLI": "NA",
    "CITTA METROPOLITANA DI TORINO": "TO",
    "CITTA METROPOLITANA DI BOLOGNA": "BO",
    "CITTA METROPOLITANA DI GENOVA": "GE",
    "CITTA METROPOLITANA DI VENEZIA": "VE",
    "CITTA METROPOLITANA DI BARI": "BA",
    "CITTA METROPOLITANA DI REGGIO CALABRIA": "RC",
    "MASSA CARRARA": "MS",
    "LA SPEZIA": "SP",
    "PESARO E URBINO": "PU",
    "BARLETTA ANDRIA TRANI": "BT",
    "BARLETTA-ANDRIA-TRANI": "BT",
    "VERBANO CUSIO OSSOLA": "VB",
    "VIBO VALENTIA": "VV",
    "ASCOLI PICENO": "AP",
    "REGGIO CALABRIA": "RC",
    "CALTANISSETTA": "CL",
    "CARBONIA IGLESIAS": "CI",
    "CARBONIA-IGLESIAS": "CI",
    "CITTA' METROPOLITANA DI CAGLIARI": "CA",
    "CITTA METROPOLITANA DI SASSARI": "SS",
    "CITTA' METROPOLITANA DI SASSARI": "SS",
    "GALLURA NORD EST SARDEGNA": "OT",
    "GALLURA NORD-EST SARDEGNA": "OT",
    "MEDIO CAMPIDANO": "VS",
    "OGLIASTRA": "OG",
    "OLBIA TEMPIO": "OT",
    "OLBIA-TEMPIO": "OT",
    "VALLE D'AOSTA": "AO",

}

REGION_BRANCH_FALLBACKS = {
    "ABRUZZO": "Roma Nomentana",
    "MARCHE": "Rimini",
    "SICILIA": "Catania",
    "CALABRIA": "Cosenza",
    "FRIULI VENEZIA GIULIA": "Udine",
    "PUGLIA": "Bari",
    "UMBRIA": "Perugia",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",

}

PROVINCE_BRANCH_FALLBACKS = {
    "ALESSANDRIA": "Milano Sud",
    "AL": "Milano Sud",

    "AOSTA": "Torino",
    "AO": "Torino",

    "ASTI": "Torino",
    "AT": "Torino",

    "AVELLINO": "Napoli",
    "AV": "Napoli",

    "BARLETTA ANDRIA TRANI": "Bari",
    "BARLETTA-ANDRIA-TRANI": "Bari",
    "BT": "Bari",

    "BELLUNO": "Treviso",
    "BL": "Treviso",

    "BENEVENTO": "Napoli",
    "BN": "Napoli",

    "BIELLA": "Torino",
    "BI": "Torino",

    "PISTOIA": "Firenze",
    "PT": "Firenze",
    "PRATO": "Firenze",
    "PO": "Firenze",
    "FIRENZE": "Firenze",
    "FI": "Firenze",
    "SIENA": "Firenze",
    "SI": "Firenze",
    "AREZZO": "Firenze",
    "AR": "Firenze",

    "POTENZA": "SALERNO",
    "PZ": "SALERNO",

    "MATERA": "Bari",
    "MT": "Bari",

    "CAMPOBASSO": "Bari",
    "CB": "Bari",

    "ISERNIA": "Frosinone",
    "IS": "Frosinone",
    "VERCELLI": "Torino",
    "VC": "Torino",
    "VERBANO CUSIO OSSOLA": "Milano Ovest",
    "VERBANO-CUSIO-OSSOLA": "Milano Ovest",
    "VB": "Milano Ovest",
    "NOVARA": "Milano Ovest",
    "NO": "Milano Ovest",
    "COMO": "Milano Nord",
    "CO": "Milano Nord",
    "VARESE": "Milano Ovest",
    "VA": "Milano Ovest",
    "PAVIA": "Milano Sud",
    "PV": "Milano Sud",
    "LODI": "Milano Est",
    "LO": "Milano Est",
    "MANTOVA": "Verona",
    "MN": "Verona",
    "CREMONA": "Brescia",
    "CR": "Brescia",
    "REGGIO NELL EMILIA": "Parma",
    "REGGIO NELL'EMILIA": "Parma",
    "REGGIO EMILIA": "Parma",
    "RE": "Parma",
    "FORLI CESENA": "Rimini",
    "FORLI-CESENA": "Rimini",
    "FC": "Rimini",
    "FERRARA": "Bologna",
    "FE": "Bologna",
    "PIACENZA": "Parma",
    "PC": "Parma",
    "RAVENNA": "Rimini",
    "RA": "Rimini",
    "MODENA": "Sassuolo",
    "MO": "Sassuolo",
    "VICENZA": "Padova",
    "VI": "Padova",
    "ROVIGO": "Padova",
    "RO": "Padova",
    "SAVONA": "Albenga",
    "SV": "Albenga",
    "IMPERIA": "Albenga",
    "IM": "Albenga",
    "LA SPEZIA": "Lucca",
    "SP": "Lucca",
    "GROSSETO": "Livorno",
    "GR": "Livorno",
    "RIETI": "Roma Nomentana",
    "RI": "Roma Nomentana",
    "LATINA": "Frosinone",
    "LT": "Frosinone",
    "BARI": "Bari",
    "BA": "Bari",
    "BRINDISI": "Bari",
    "BR": "Bari",
    "FOGGIA": "Bari",
    "FG": "Bari",
    "LECCE": "Bari",
    "LE": "Bari",
    "TARANTO": "Bari",
    "TA": "Bari",
    "PERUGIA": "Perugia",
    "PG": "Perugia",
    "TERNI": "Perugia",
    "TR": "Perugia",
    "NUORO": "Sassari",
    "NU": "Sassari",
    "ORISTANO": "Cagliari",
    "OR": "Cagliari",
    "MONZA E DELLA BRIANZA": "Milano Nord",
    "MONZA BRIANZA": "Milano Nord",
    "MB": "Milano Nord",
    "PISA": "Livorno",
    "PI": "Livorno",
    "CASERTA": "Napoli",
    "CE": "Napoli",
    "VITERBO": "Roma Nomentana",
    "VT": "Roma Nomentana",
    "MASSA CARRARA": "Lucca",
    "MASSA-CARRARA": "Lucca",
    "MS": "Lucca",
    "VALLE D AOSTA": "Torino",
    "VALLE D'AOSTA": "Torino",
    "CARBONIA IGLESIAS": "Cagliari",
    "CARBONIA-IGLESIAS": "Cagliari",
    "CI": "Cagliari",
    "CITTA METROPOLITANA DI CAGLIARI": "Cagliari",
    "CITTA' METROPOLITANA DI CAGLIARI": "Cagliari",
    "CA": "Cagliari",
    "CITTA METROPOLITANA DI SASSARI": "Sassari",
    "CITTA' METROPOLITANA DI SASSARI": "Sassari",
    "SS": "Sassari",
    "GALLURA NORD EST SARDEGNA": "Sassari",
    "GALLURA NORD-EST SARDEGNA": "Sassari",
    "MEDIO CAMPIDANO": "Cagliari",
    "VS": "Cagliari",
    "OGLIASTRA": "Cagliari",
    "OG": "Cagliari",
    "OLBIA TEMPIO": "Sassari",
    "OLBIA-TEMPIO": "Sassari",
    "OT": "Sassari",
    "SUD SARDEGNA": "Cagliari",
    "SU": "Cagliari",

}


def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def province_variants(value):
    raw = norm(value)
    variants = set()

    if raw:
        variants.add(raw)

    alias = PROVINCE_ALIASES.get(raw)
    if alias:
        variants.add(alias)

    return {v for v in variants if v}


def load_branch_map():
    exact = {}
    municipality_only = {}
    municipality_signature = {}
    municipality_ambiguous = set()

    branch_by_norm = {}
    branch_norm_ambiguous = set()

    if not BRANCH_MAP.exists():
        print(f"[WARN] Mappa filiali non trovata: {BRANCH_MAP}")
        return {
            "exact": exact,
            "municipality_only": municipality_only,
            "branch_by_norm": branch_by_norm,
        }

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            municipality_norm = clean(row.get("municipality_norm"))
            province_norm = clean(row.get("province_norm"))

            if not municipality_norm or not province_norm:
                continue

            item = {
                "branch": clean(row.get("branch")),
                "branch_candidates": clean(row.get("branch_candidates")),
                "branch_confidence": clean(row.get("confidence")),
            }

            branch = item["branch"]
            branch_norm = norm(branch)

            if branch and branch not in {"AMBIGUA", "NON ASSEGNATA"} and branch_norm not in {"MILANO", "ROMA"}:
                previous_branch = branch_by_norm.get(branch_norm)
                if previous_branch and previous_branch != branch:
                    branch_norm_ambiguous.add(branch_norm)
                else:
                    branch_by_norm[branch_norm] = branch

            province_keys = set()
            province_keys.add(province_norm)
            province_keys.update(province_variants(province_norm))
            province_keys.update(province_variants(row.get("province")))
            province_keys.update(province_variants(row.get("sigla_provincia")))
            province_keys.update(province_variants(row.get("province_code")))

            for province_key in province_keys:
                if province_key:
                    exact[(municipality_norm, province_key)] = item

            signature = (item["branch"], item["branch_candidates"])
            previous_signature = municipality_signature.get(municipality_norm)

            if previous_signature and previous_signature != signature:
                municipality_ambiguous.add(municipality_norm)
            else:
                municipality_only[municipality_norm] = item
                municipality_signature[municipality_norm] = signature

    for municipality_norm in municipality_ambiguous:
        municipality_only.pop(municipality_norm, None)

    for branch_norm in branch_norm_ambiguous:
        branch_by_norm.pop(branch_norm, None)

    # Esclusione prudente: Roma e Milano hanno più filiali.
    branch_by_norm.pop("ROMA", None)
    branch_by_norm.pop("MILANO", None)

    print(
        f"[OK] Mappa comuni → filiali: {len(exact)} chiavi esatte, "
        f"{len(municipality_only)} fallback comune, "
        f"{len(branch_by_norm)} fallback provincia=filiale"
    )

    return {
        "exact": exact,
        "municipality_only": municipality_only,
        "branch_by_norm": branch_by_norm,
    }


def same_name_province_branch_fallback(record, branch_map):
    province_values = province_variants(record.get("province"))

    # Roma e Milano escluse: più filiali.
    blocked = {"ROMA", "RM", "MILANO", "MI"}

    for province in province_values:
        if province in blocked:
            continue

        branch = branch_map.get("branch_by_norm", {}).get(province)
        if branch:
            return {
                "branch": branch,
                "branch_candidates": "",
                "branch_confidence": "territoriale_provincia_omonima",
                "method": "fallback_provincia_omonima_filiale",
            }

    return None


def territorial_branch_fallback(record):
    region = norm(record.get("region"))
    province_values = province_variants(record.get("province"))

    for province in province_values:
        branch = PROVINCE_BRANCH_FALLBACKS.get(province)
        if branch:
            return {
                "branch": branch,
                "branch_candidates": "",
                "branch_confidence": "territoriale_provincia",
                "method": "fallback_provincia_territoriale",
            }

    branch = REGION_BRANCH_FALLBACKS.get(region)
    if branch:
        return {
            "branch": branch,
            "branch_candidates": "",
            "branch_confidence": "territoriale_regione",
            "method": "fallback_regione_territoriale",
        }

    return None


def apply_branch_assignment(record, branch_map):
    existing_branch = clean(record.get("branch"))

    # Non usare CAP_SOGGETTO_TITOLARE: non localizza il progetto.
    # Se ha già una filiale vera o AMBIGUA, non sovrascriviamo.
    if existing_branch and existing_branch not in {"NON ASSEGNATA", "NON_ASSEGNATA"}:
        return record

    municipality = norm(record.get("municipality"))
    province_raw = record.get("province")

    invalid_geo = {"", "TUTTI", "TUTTE", "VARI", "VARIE", "NAZIONALE", "ITALIA"}

    match = None
    method = "none"

    if municipality not in invalid_geo:
        for province in province_variants(province_raw):
            if province in invalid_geo:
                continue

            match = branch_map["exact"].get((municipality, province))
            if match:
                method = "exact_or_alias_province"
                break

    if not match and municipality not in invalid_geo:
        match = branch_map["municipality_only"].get(municipality)
        if match:
            method = "fallback_comune_univoco"

    fallback_match = None

    if not match and municipality not in invalid_geo:
        municipality_branch = MUNICIPALITY_BRANCH_FALLBACKS.get(municipality)
        if municipality_branch:
            fallback_match = {
                "branch": municipality_branch,
                "branch_candidates": "",
                "branch_confidence": "territoriale_comune",
                "method": "fallback_comune_territoriale",
            }

    if not match and not fallback_match:
        fallback_match = same_name_province_branch_fallback(record, branch_map)

    if not match and not fallback_match:
        fallback_match = territorial_branch_fallback(record)

    if match:
        record["branch"] = match["branch"] or "NON ASSEGNATA"
        record["branch_candidates"] = match["branch_candidates"]
        record["branch_confidence"] = match["branch_confidence"] or method
        record["branch_assignment_method"] = method
    elif fallback_match:
        record["branch"] = fallback_match["branch"]
        record["branch_candidates"] = fallback_match["branch_candidates"]
        record["branch_confidence"] = fallback_match["branch_confidence"]
        record["branch_assignment_method"] = fallback_match["method"]
    else:
        record["branch"] = "NON ASSEGNATA"
        record["branch_candidates"] = ""
        record["branch_confidence"] = "nessuna"
        record["branch_assignment_method"] = "none"

    return record


def main():
    anac_rows = [normalize(r, "national_anac_relevant_awards") for r in load_json(ROOT / "docs" / "data" / "national_anac_relevant_awards.json")]
    opencup_rows = [normalize(r, "national_operational_data") for r in load_json(ROOT / "docs" / "national_operational_data.json")]

    branch_map = load_branch_map()
    anac_rows = [apply_branch_assignment(r, branch_map) for r in anac_rows]
    opencup_rows = [apply_branch_assignment(r, branch_map) for r in opencup_rows]

    anac_cups = {clean(r.get("cup")).upper() for r in anac_rows if clean(r.get("cup"))}

    raw_records = []

    # Mantiene ogni affidamento ANAC come riga grezza autonoma
    for r in anac_rows:
        cup = clean(r.get("cup")).upper()
        cig = clean(r.get("cig")).upper()
        r["id"] = f"ANAC::{cup}::{cig}" if cig else f"ANAC::{cup}"
        r["source"] = "ANAC"
        r["sources"] = ["OpenCUP", "ANAC"]
        r["has_anac"] = True
        raw_records.append(r)

    # Aggiunge solo OpenCUP senza affidamento ANAC gi? presente
    for r in opencup_rows:
        cup = clean(r.get("cup")).upper()
        if cup and cup in anac_cups:
            continue

        r["id"] = f"OPENCUP::{cup}" if cup else key_for(r)
        r["source"] = "OpenCUP"
        r["sources"] = ["OpenCUP"]
        r["has_anac"] = False
        raw_records.append(r)

    records = group_projects(raw_records)

    records = [apply_quality_layer(r) for r in records]

    records.sort(key=lambda r: (
        -int(r.get("commercial_score") or 0),
        not r.get("has_anac"),
        -float(r.get("project_value") or 0)
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"[OK] master scritto: {OUT}")
    print(f"Righe grezze: {len(raw_records)}")
    print(f"Progetti master: {len(records)}")
    print(f"Con ANAC: {sum(1 for r in records if r.get('has_anac'))}")
    print(f"Senza ANAC: {sum(1 for r in records if not r.get('has_anac'))}")
    print(f"Con pi? affidamenti: {sum(1 for r in records if int(r.get('awards_count') or 0) > 1)}")
    print(f"CUP ANAC unici: {len(anac_cups)}")


if __name__ == "__main__":
    main()
