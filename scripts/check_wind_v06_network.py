#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "wind" / "data"
registry = json.loads((DATA / "company-network-v06.json").read_text(encoding="utf-8"))
manifest = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
projects = []
for chunk in manifest["chunks"]:
    projects.extend(json.loads((DATA / chunk).read_text(encoding="utf-8")))
project_ids = {p["id"] for p in projects}
project_aliases = {"on-lama-cupa": "lama-cupa"}

assert registry["version"] == "0.6.0"
assert registry["monitoring"]["high_priority_cadence_days"] == 7
assert registry["monitoring"]["standard_cadence_days"] == 14
assert registry["monitoring"]["universe_refresh_days"] == 30
assert any("anev.org/soci" in s.get("url", "") for s in registry["discovery_sources"])

companies = registry["companies"]
assert len(companies) >= 30, f"network seed too small: {len(companies)}"
ids = [c["id"] for c in companies]
assert len(ids) == len(set(ids)), "duplicate company ids"

for c in companies:
    assert c["commercial_priority"] in {"A", "B", "C"}, c["id"]
    assert c.get("cluster"), c["id"]
    assert c.get("wind_relevance"), c["id"]
    assert c.get("relationship_status"), c["id"]
    for pid in c.get("project_links", []):
        canonical_pid = project_aliases.get(pid, pid)
        assert canonical_pid in project_ids, f"{c['id']}: unknown project link {pid}"
    for url in c.get("watch_urls", []):
        parsed = urlparse(url)
        assert parsed.scheme in {"http", "https"} and parsed.netloc, f"{c['id']}: invalid URL {url}"

by_id = {c["id"]: c for c in companies}
for required in ["espe", "plc", "tozzi-green", "fagioli", "mammoet", "vestas", "rwe", "erg", "edison-rinnovabili", "plenitude"]:
    assert required in by_id, f"missing required network node {required}"

espe = by_id["espe"]
assert espe["commercial_priority"] == "A"
assert espe["wind_relevance"] == "adjacent_high_value"
assert espe["project_links"] == [], "ESPE must not be project-linked without evidence"
assert "wind_full_bop" not in espe["cluster"], "ESPE must not be labelled proven utility-scale wind Full BoP"
assert any("fornitori" in u for u in espe["watch_urls"]), "ESPE supplier route must be monitored"

plc = by_id["plc"]
assert plc["commercial_priority"] == "A"
assert "wind_full_bop" in plc["cluster"]
assert set(plc["project_links"]) >= {"tarsia-ovest", "castelfranco-cer"}

tozzi = by_id["tozzi-green"]
assert tozzi["commercial_priority"] == "A"
assert "wind_epc" in tozzi["cluster"]

# Network intelligence must remain structurally separate from canonical execution relations.
# The presence of a company in this registry is not itself a canonical relation.
assert "companies" not in manifest

print(f"v0.6 company network OK: {len(companies)} players, {sum(c['commercial_priority']=='A' for c in companies)} priority A")
