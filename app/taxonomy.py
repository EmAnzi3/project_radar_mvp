import re


NII_LIKE_CATEGORIES = {
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
        "ospedale", "poliambulatorio", "distretto sanitario", "sanitario"
    ],
    "Cultura / centri civici": [
        "biblioteca", "teatro", "auditorium", "centro culturale",
        "centro civico", "museo", "sala polivalente", "polo culturale"
    ],
    "Riqualificazione urbana": [
        "riqualificazione", "rigenerazione urbana", "arredo urbano",
        "parco", "piazza", "verde pubblico", "area dismessa", "recupero area"
    ],
    "Edilizia pubblica": [
        "edificio pubblico", "municipio", "sede comunale", "uffici pubblici",
        "fabbricato", "immobile comunale", "edificio polifunzionale"
    ],
    "Infrastrutture / parcheggi": [
        "parcheggio", "strada", "viabilità", "marciapiede", "ponte",
        "rotatoria", "urbanizzazione", "pista ciclabile"
    ],
    "Ambiente / rifiuti / depurazione": [
        "rifiuti", "depuratore", "depurazione", "fognatura", "acquedotto",
        "bonifica", "discarica", "trattamento rifiuti"
    ],
    "Industriale / logistica": [
        "magazzino", "logistica", "capannone", "area produttiva",
        "zona industriale", "polo produttivo"
    ],
    "Energia": [
        "fotovoltaico", "agrivoltaico", "eolico", "energia", "bess",
        "accumulo", "biometano"
    ],
    "Residenziale pubblico / ERS": [
        "edilizia residenziale", "alloggi", "ers", "housing",
        "case popolari", "social housing"
    ],
}


EXCLUDE_LIGHT_PROJECTS = [
    "acquisto arredi",
    "acquisto attrezzature",
    "fornitura libri",
    "contributo",
    "contributi",
    "agevolazione",
    "agevolazioni",
    "agevolazioni fiscali",
    "premio assicurativo",
    "premi assicurativi",
    "raccolto",
    "animali",
    "sottomisura 17.1",
    "indennit? compensative",
    "indennita compensative",
    "compensazioni",
    "sostegno al reddito",
    "voucher",
    "corso di formazione",
    "servizio civile",
    "acquisto servizi reali",
    "attivita' di ricerca",
    "attivit? di ricerca",
    "progetti di ricerca",
    "ricerca sviluppo tecnologico",
    "nuova gamma di elettrodomestici",
    "spese materiale",
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def classify_nii_category(*values: str | None) -> str:
    text = " ".join(clean_text(v).lower() for v in values if v)

    for category, keywords in NII_LIKE_CATEGORIES.items():
        if any(k in text for k in keywords):
            return category

    return "Altro"


def is_nii_like_project(*values: str | None) -> bool:
    text = " ".join(clean_text(v).lower() for v in values if v)

    if any(x in text for x in EXCLUDE_LIGHT_PROJECTS):
        return False

    category = classify_nii_category(text)
    if category != "Altro":
        return True

    # fallback: lavori pubblici / manutenzioni / costruzioni con parole chiave operative
    generic_work_words = [
        "lavori", "realizzazione", "costruzione", "ristrutturazione",
        "manutenzione straordinaria", "messa in sicurezza",
        "adeguamento sismico", "efficientamento energetico"
    ]
    return any(w in text for w in generic_work_words)


def infer_intervention_type(*values: str | None) -> str | None:
    text = " ".join(clean_text(v).lower() for v in values if v)

    if "nuova costruzione" in text or "realizzazione" in text or "costruzione" in text:
        return "nuova costruzione"
    if "ristrutturazione" in text:
        return "ristrutturazione"
    if "riqualificazione" in text:
        return "riqualificazione"
    if "manutenzione straordinaria" in text:
        return "manutenzione straordinaria"
    if "messa in sicurezza" in text:
        return "messa in sicurezza"
    if "efficientamento" in text:
        return "efficientamento energetico"

    return None


def infer_phase_from_opencup(status: str | None, year_decision: str | None = None) -> str:
    status_text = clean_text(status).upper()

    if "ATTIVO" in status_text:
        return "programmazione / progetto attivo"
    if "CHIUSO" in status_text:
        return "chiuso"
    if "REVOCATO" in status_text or "CANCELLATO" in status_text:
        return "revocato / cancellato"

    return "programmazione"
