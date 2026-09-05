from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIND = ROOT / "docs" / "wind"
DATA = WIND / "data"


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] {message}")


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def main() -> None:
    allowed = {"onshore", "offshore"}

    registry = load_json(DATA / "discovery-v04.json")
    if set(registry.get("allowed_site_types", [])) != allowed:
        fail("discovery registry: allowed_site_types inattesi")

    statuses = set(registry.get("workflow", []))
    required_statuses = {
        "discovered",
        "identity_checked",
        "evidence_enriched",
        "canonical_candidate",
        "accepted",
        "needs_reconciliation",
        "rejected",
    }
    if statuses != required_statuses:
        fail("discovery registry: workflow incompleto")

    required = set(registry.get("candidate_required_fields", []))
    for candidate in registry.get("candidates", []):
        missing = required - set(candidate)
        if missing:
            fail(f"{candidate.get('candidate_id', '?')}: campi discovery mancanti {sorted(missing)}")
        if candidate["site_type"] not in allowed:
            fail(f"{candidate['candidate_id']}: site_type non canonico {candidate['site_type']}")
        if candidate["status"] not in statuses:
            fail(f"{candidate['candidate_id']}: status discovery non canonico {candidate['status']}")
        if not candidate.get("sources"):
            fail(f"{candidate['candidate_id']}: almeno una fonte discovery è obbligatoria")

    manifest = load_json(DATA / "projects.json")
    projects = []
    for chunk in manifest["chunks"]:
        projects.extend(load_json(DATA / chunk))
    if not projects:
        fail("dataset canonico vuoto")

    invalid_site_types = [
        (p.get("id"), p.get("site_type"))
        for p in projects
        if p.get("site_type") is not None and p.get("site_type") not in allowed
    ]
    if invalid_site_types:
        fail(f"site_type canonici non validi: {invalid_site_types}")

    index = (WIND / "index.html").read_text(encoding="utf-8")
    app = (WIND / "assets" / "app.js").read_text(encoding="utf-8")

    for token in ['id="siteType"', 'value="onshore"', 'value="offshore"']:
        if token not in index:
            fail(f"selettore onshore/offshore incompleto: manca {token}")

    if "p.site_type||'onshore'" not in app:
        fail("fallback legacy site_type=onshore mancante")
    if "projects.length!==17" in app:
        fail("frontend ancora bloccato sul seed esatto di 17 progetti")
    if "site_type" not in app or "siteType" not in app:
        fail("site_type non cablato nel frontend/export")

    explicit = sum(1 for p in projects if p.get("site_type") in allowed)
    legacy = len(projects) - explicit
    print(f"[OK] dataset canonico: {len(projects)} progetti; {explicit} site_type espliciti, {legacy} legacy -> onshore")
    print("[OK] selector Onshore + offshore / Onshore / Offshore presente")
    print("[OK] frontend non più vincolato a 17 progetti")
    print(f"[OK] discovery registry: {len(registry.get('candidates', []))} candidati")


if __name__ == "__main__":
    main()
