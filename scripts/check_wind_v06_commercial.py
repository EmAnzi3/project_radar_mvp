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

execution_roles = set(meta.get("execution_roles") or [])
andretta = payload["projects"]["andretta-bisaccia"]
relations = andretta.get("relations") or []
assert len(relations) == 1, relations
progeco = relations[0]
assert progeco["company"] == "Progeco Group / Progeco SE"
assert progeco["confidence"] == "A2"
assert progeco["status"] == "signal", "support recruitment must not be represented as confirmed execution"
assert progeco["role"] not in execution_roles, "project-support relation must not close execution scope"
assert "supervision" in progeco["role"].lower()

signals = andretta.get("signals") or []
assert any(s.get("type") == "project-support-recruitment" for s in signals)
assert any("24-month" in s.get("title", "") for s in signals)

sources = andretta.get("sources") or []
assert sources and all(s.get("grade") in {"A1", "A2", "B", "C"} for s in sources)
for source in sources:
    parsed = urlparse(source.get("url") or "")
    assert parsed.scheme in {"http", "https"} and parsed.netloc, source

# The canonical project remains untouched by this enrichment.
canonical = by_id["andretta-bisaccia"]
assert not any(
    r.get("company") == "Progeco Group / Progeco SE"
    for r in (canonical.get("relations") or [])
), "v0.6 support signal must stay in additive commercial enrichment, not canonical execution relations"

print(
    f"v0.6 commercial enrichment OK: {len(payload['projects'])} project, "
    f"{len(relations)} relation, {len(signals)} signals; Progeco remains non-execution"
)
