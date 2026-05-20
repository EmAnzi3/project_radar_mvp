from app.models import ProjectRecord


STRATEGIC_SECTORS = {
    "fotovoltaico",
    "agrivoltaico",
    "energia",
    "eolico",
    "bess",
    "edilizia pubblica",
    "scuole",
    "impianti sportivi",
    "rsa",
    "sanità",
    "riqualificazione urbana",
    "rifiuti",
    "depurazione",
    "logistica",
}


GOOD_PHASES = {
    "programmazione",
    "progettazione",
    "progetto di fattibilità",
    "pfte",
    "via",
    "autorizzazione",
    "gara",
    "appalto",
}


def calculate_commercial_score(project: ProjectRecord) -> int:
    score = 0

    text = " ".join(
        str(x or "").lower()
        for x in [
            project.title,
            project.description,
            project.sector,
            project.category,
            project.phase,
            project.intervention_type,
        ]
    )

    if any(s in text for s in STRATEGIC_SECTORS):
        score += 25

    if project.estimated_value_eur:
        if project.estimated_value_eur >= 5_000_000:
            score += 30
        elif project.estimated_value_eur >= 1_000_000:
            score += 20
        elif project.estimated_value_eur >= 300_000:
            score += 10

    if project.power_mw:
        if project.power_mw >= 10:
            score += 25
        elif project.power_mw >= 1:
            score += 15

    if project.phase and any(p in project.phase.lower() for p in GOOD_PHASES):
        score += 20

    if project.contractor:
        score += 10

    if project.designer or project.rup:
        score += 10

    if project.cup or project.cig:
        score += 5

    if not project.municipality:
        score -= 5

    if not project.description:
        score -= 10

    return max(0, min(score, 100))
