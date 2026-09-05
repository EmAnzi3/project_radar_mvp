#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "wind" / "data"

manifest = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
meta = json.loads((DATA / manifest["meta"]).read_text(encoding="utf-8"))
projects = []
for chunk in manifest["chunks"]:
    projects.extend(json.loads((DATA / chunk).read_text(encoding="utf-8")))
by_id = {p["id"]: p for p in projects}

payload = json.loads((DATA / "commercial-enrichment-v06.json").read_text(encoding="utf-8"))
assert payload["version"] == "0.6.0-commercial-enrichment"
assert set(payload["projects"]).issubset(by_id), set(payload["projects"]) - set(by_id)
assert {"andretta-bisaccia", "carlentini"}.issubset(payload["projects"])

execution_roles = set(meta.get("execution_roles") or [])

# Andretta: current supervision/staffing signal is project-specific but non-execution.
andretta = payload["projects"]["andretta-bisaccia"]
andretta_relations = andretta.get("relations") or []
assert len(andretta_relations) == 1, andretta_relations
progeco = andretta_relations[0]
assert progeco["company"] == "Progeco Group / Progeco SE"
assert progeco["confidence"] == "A2"
assert progeco["status"] == "signal", "support recruitment must not be represented as confirmed execution"
assert progeco["role"] not in execution_roles, "project-support relation must not close execution scope"
assert "supervision" in progeco["role"].lower()
assert any(s.get("type") == "project-support-recruitment" for s in andretta.get("signals") or [])
assert any("24-month" in s.get("title", "") for s in andretta.get("signals") or [])

# Carlentini: direct project-participant evidence now explicitly names Mammana
# as executor of current WTG foundation concrete works. This is the one v0.6
# relation allowed to close an execution scope in this tranche; it must not be
# widened to the whole Civil BoP.
carlentini = payload["projects"]["carlentini"]
car_relations = carlentini.get("relations") or []
foundation = next(r for r in car_relations if r.get("company") == "Mammana Michelangelo S.p.A.")
hydro = next(r for r in car_relations if r.get("company") == "Hydro Engineering")
assert foundation["role"] == "Foundation contractor"
assert foundation["role"] in execution_roles
assert foundation["status"] == "confirmed"
assert foundation["confidence"] == "A2"
assert "full Civil BoP" in foundation["scope"], "scope note must preserve the no-overreach guard"
assert hydro["confidence"] == "A2"
assert hydro["status"] == "confirmed"
assert hydro["role"] not in execution_roles, "Direzione Lavori / engineering must remain non-execution"
assert any(s.get("type") == "foundation-execution" for s in carlentini.get("signals") or [])
assert any(s.get("type") == "construction-progress" for s in carlentini.get("signals") or [])

# All current commercial-enrichment sources must be attributable and navigable.
for project_id, project_payload in payload["projects"].items():
    sources = project_payload.get("sources") or []
    assert sources, f"{project_id}: no sources"
    for source in sources:
        assert source.get("grade") in {"A1", "A2", "B", "C"}, (project_id, source)
        parsed = urlparse(source.get("url") or "")
        assert parsed.scheme in {"http", "https"} and parsed.netloc, (project_id, source)

# Additive enrichment must not silently rewrite the canonical relation graph.
canonical_andretta = by_id["andretta-bisaccia"]
assert not any(
    r.get("company") == "Progeco Group / Progeco SE"
    for r in (canonical_andretta.get("relations") or [])
), "v0.6 support signal must stay in additive commercial enrichment"

canonical_carlentini = by_id["carlentini"]
assert any(
    r.get("company") == "Gruppo Mammana" and r.get("confidence") == "B"
    for r in (canonical_carlentini.get("relations") or [])
), "historical seed signal must remain unchanged; v0.6 A2 upgrade is additive and reversible"

execution_relations = [
    (project_id, relation)
    for project_id, project_payload in payload["projects"].items()
    for relation in project_payload.get("relations") or []
    if relation.get("role") in execution_roles
    and relation.get("status") == "confirmed"
    and relation.get("confidence") in {"A1", "A2"}
]
assert len(execution_relations) == 1, execution_relations
assert execution_relations[0][0] == "carlentini"

print(
    f"v0.6 commercial enrichment OK: {len(payload['projects'])} projects, "
    f"{len(execution_relations)} A1/A2 execution relation; Carlentini foundation contractor confirmed"
)
