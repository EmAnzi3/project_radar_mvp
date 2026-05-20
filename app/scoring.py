from app.models import ProjectRecord


HIGH_VALUE_CATEGORIES = {
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


GOOD_PHASES = {
    "programmazione",
    "progetto attivo",
    "progettazione",
    "gara",
    "appalto",
    "affidamento",
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
            project.status,
            project.intervention_type,
        ]
    )

    if project.category in HIGH_VALUE_CATEGORIES:
        score += 25

    if project.estimated_value_eur:
        if project.estimated_value_eur >= 10_000_000:
            score += 35
        elif project.estimated_value_eur >= 5_000_000:
            score += 30
        elif project.estimated_value_eur >= 1_000_000:
            score += 22
        elif project.estimated_value_eur >= 300_000:
            score += 12
        elif project.estimated_value_eur >= 200_000:
            score += 6
        else:
            score -= 20

    if project.phase and any(p in project.phase.lower() for p in GOOD_PHASES):
        score += 20

    if project.intervention_type:
        score += 10

    if project.client:
        score += 8

    if project.contractor:
        score += 10

    if project.designer or project.rup:
        score += 8

    if project.cup or project.cig:
        score += 5

    if project.region:
        score += 3

    if project.province:
        score += 3

    if project.municipality:
        score += 4

    if "lavori pubblici" in text:
        score += 10

    if "contributo" in text or "incentivo" in text or "voucher" in text:
        score -= 20

    if not project.description:
        score -= 10

    return max(0, min(score, 100))
