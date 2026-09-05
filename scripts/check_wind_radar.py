from __future__ import annotations

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "wind" / "data"
MANIFEST = DATA / "projects.json"
ENRICHMENT = DATA / "enrichment-2026-09-04.json"
ENRICHMENT2 = DATA / "enrichment-docpass2-2026-09-04.json"
CONTRACTOR_LEADS = DATA / "contractor-leads-2026-09-05.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] {message}")


def merge_overlay(project: dict, overlay: dict) -> dict:
    project = copy.deepcopy(project)
    project.setdefault("relations", [])
    project.setdefault("sources", [])
    for source in overlay.get("sources", []):
        if not any(item.get("id") == source.get("id") for item in project["sources"]):
            project["sources"].append(copy.deepcopy(source))
    for spec in overlay.get("relations", []):
        relation = {k: v for k, v in spec.items() if k not in {"action", "match"}}
        found = None
        if spec.get("action") == "upgrade_or_add" and spec.get("match"):
            match = spec["match"]
            for current in project["relations"]:
                if current.get("company") != match.get("company"):
                    continue
                role_contains = match.get("role_contains")
                if role_contains and role_contains not in str(current.get("role", "")):
                    continue
                found = current
                break
        if found is not None:
            found.update(copy.deepcopy(relation))
        elif not any(
            current.get("company") == relation.get("company")
            and current.get("role") == relation.get("role")
            and current.get("source_id") == relation.get("source_id")
            for current in project["relations"]
        ):
            project["relations"].append(copy.deepcopy(relation))
    return project


def main() -> None:
    manifest = load_json(MANIFEST)
    meta = load_json(DATA / manifest["meta"])
    projects = []
    for chunk in manifest["chunks"]:
        projects.extend(load_json(DATA / chunk))

    if len(projects) != 17:
        fail(f"seed Wind inatteso: {len(projects)} progetti, attesi 17")
    ids = [p["id"] for p in projects]
    if len(set(ids)) != len(ids):
        fail("ID progetto duplicati")
    total_mw = sum(float(p.get("mw") or 0) for p in projects)
    if not math.isclose(total_mw, 1496.9, abs_tol=0.01):
        fail(f"totale MW inatteso: {total_mw:.1f}, attesi 1496.9")

    stage_codes = {item["code"] for item in meta["maturity_scale"]}
    for project in projects:
        if project.get("stage") not in stage_codes:
            fail(f"stage non valido per {project['id']}: {project.get('stage')}")
        source_ids = {s.get("id") for s in project.get("sources", [])}
        refs = []
        if project.get("next", {}).get("source_id"):
            refs.append(project["next"]["source_id"])
        refs += [x.get("source_id") for x in project.get("timing", []) if x.get("source_id")]
        refs += [x.get("source_id") for x in project.get("relations", []) if x.get("source_id")]
        refs += [x.get("source_id") for x in project.get("configs", []) if x.get("source_id")]
        missing = sorted(set(refs) - source_ids)
        if missing:
            fail(f"source_id non risolti in {project['id']}: {', '.join(missing)}")

    enrichment = load_json(ENRICHMENT)
    if set(enrichment.get("projects", {})) != set(ids):
        fail("gli ID dell'enrichment non coincidono con i 17 seed")
    merged = [merge_overlay(p, enrichment["projects"].get(p["id"], {})) for p in projects]

    if ENRICHMENT2.exists():
        docpass = load_json(ENRICHMENT2)
        expected_docpass = {"alas", "toritto", "fenice", "lama-cupa"}
        if set(docpass.get("projects", {})) != expected_docpass:
            fail(f"docpass2: ID inattesi {sorted(docpass.get('projects', {}))}")
        merged = [merge_overlay(p, docpass["projects"].get(p["id"], {})) for p in merged]

    if CONTRACTOR_LEADS.exists():
        leads = load_json(CONTRACTOR_LEADS)
        expected_leads = {"andretta-bisaccia", "tricarico", "venusia", "serra-palino", "tarsia-ovest"}
        if set(leads.get("projects", {})) != expected_leads:
            fail(f"contractor leads: ID inattesi {sorted(leads.get('projects', {}))}")
        merged = [merge_overlay(p, leads["projects"].get(p["id"], {})) for p in merged]

    core_scopes = enrichment["method"]["core_scopes"]
    role_map = enrichment["method"]["scope_role_map"]

    def applicable(project: dict) -> list[dict]:
        repowering = "repowering" in str(project.get("type", "")).lower()
        return [s for s in core_scopes if s["applicable"] == "all" or (s["applicable"] == "repowering" and repowering)]

    def scope_covered(project: dict, scope: dict) -> bool:
        roles = set(role_map[scope["id"]])
        return any(
            r.get("role") in roles
            and r.get("status") == "confirmed"
            and r.get("confidence") in {"A1", "A2"}
            for r in project.get("relations", [])
        )

    def project(project_id: str) -> dict:
        return next(p for p in merged if p["id"] == project_id)

    def coverage(project_id: str) -> set[str]:
        p = project(project_id)
        return {s["id"] for s in applicable(p) if scope_covered(p, s)}

    covered_slots = 0
    total_slots = 0
    with_scope = []
    for p in merged:
        scopes = applicable(p)
        covered = [s for s in scopes if scope_covered(p, s)]
        covered_slots += len(covered)
        total_slots += len(scopes)
        if covered:
            with_scope.append(p)
        source_ids = {s.get("id") for s in p.get("sources", [])}
        missing = sorted({r.get("source_id") for r in p.get("relations", []) if r.get("source_id") and r.get("source_id") not in source_ids})
        if missing:
            fail(f"source_id enrichment non risolti in {p['id']}: {', '.join(missing)}")

    # Regression guards: segnali e ruoli tecnici non devono gonfiare gli scope esecutivi.
    andretta = project("andretta-bisaccia")
    progeco = [r for r in andretta.get("relations", []) if r.get("source_id") == "andr-progeco-site-manager"]
    if len(progeco) != 1 or progeco[0].get("confidence") != "B" or progeco[0].get("status") != "signal":
        fail("Andretta-Bisaccia: Progeco deve esistere una volta e restare signal/B")
    if coverage("andretta-bisaccia"):
        fail("Andretta-Bisaccia: site management Progeco sta chiudendo indebitamente uno scope")

    tri = project("tricarico")
    tri_install = [r for r in tri.get("relations", []) if r.get("source_id") == "tri-vestas-install-lead"]
    if len(tri_install) != 1 or tri_install[0].get("confidence") != "B" or tri_install[0].get("scope_hint") != "erection":
        fail("Tricarico: Vestas installation deve restare B con scope_hint erection")
    if coverage("tricarico"):
        fail("Tricarico: un lead/advisory sta chiudendo indebitamente uno scope")

    venusia = project("venusia")
    if coverage("venusia") != {"civil"}:
        fail(f"Venusia: coverage inattesa {sorted(coverage('venusia'))}; attesa solo civil")
    nordex_ven = [r for r in venusia.get("relations", []) if r.get("source_id") == "ven-rwe-ceo-nordex"]
    newdev = [r for r in venusia.get("relations", []) if r.get("source_id") == "ven-newdev-cosviluppo"]
    if len(nordex_ven) != 1 or nordex_ven[0].get("role") != "OEM" or nordex_ven[0].get("confidence") != "A2":
        fail("Venusia: Nordex OEM A2 mancante o duplicato")
    if len(newdev) != 1 or newdev[0].get("confidence") != "A2":
        fail("Venusia: New Developments co-development A2 mancante o duplicato")

    if coverage("serra-palino") != {"civil", "electrical"}:
        fail(f"Serra Palino: coverage inattesa {sorted(coverage('serra-palino'))}")
    nordex_sp = [r for r in project("serra-palino").get("relations", []) if r.get("source_id") == "sp-rwe-ceo-nordex"]
    if len(nordex_sp) != 1 or nordex_sp[0].get("role") != "OEM" or nordex_sp[0].get("confidence") != "A2":
        fail("Serra Palino: Nordex OEM A2 mancante o duplicato")

    if coverage("tarsia-ovest") != {"civil", "electrical", "sse_grid"}:
        fail(f"Tarsia Ovest: coverage inattesa {sorted(coverage('tarsia-ovest'))}")
    mammana = [r for r in project("tarsia-ovest").get("relations", []) if r.get("source_id") == "tars-mammana-civil-lead"]
    if len(mammana) != 1 or mammana[0].get("confidence") != "B" or mammana[0].get("scope_hint") != "civil":
        fail("Tarsia Ovest: Mammana individual civil deve restare B con scope_hint civil")

    if coverage("serra-giannina"):
        fail("Serra Giannina: un segnale B sta chiudendo indebitamente uno scope")
    if coverage("carlentini") != {"foundation"}:
        fail(f"Carlentini: coverage inattesa {sorted(coverage('carlentini'))}; attesa solo foundation")
    if coverage("alas"):
        fail("ALAS: progettazione Hydro sta chiudendo indebitamente uno scope")
    if coverage("fenice"):
        fail("Fenice: engineering ATS sta chiudendo indebitamente uno scope")
    if any(r.get("company") == "Brulli Trasmissione" for r in project("lama-cupa").get("relations", [])):
        fail("Lama Cupa: Brulli è stata attribuita al parco invece che alla SE condivisa")

    mw_with_scope = sum(float(p.get("mw") or 0) for p in with_scope)
    if covered_slots != 8 or total_slots != 108:
        fail(f"scope coverage inattesa: {covered_slots}/{total_slots}; attesa 8/108")
    if not math.isclose(mw_with_scope, 230.9, abs_tol=0.01):
        fail(f"MW con scope inattesi: {mw_with_scope:.1f}; attesi 230.9")

    print(f"[OK] seed Wind: 17 progetti / {total_mw:.1f} MW")
    print(f"[OK] scope coverage: {covered_slots}/{total_slots} ({covered_slots / total_slots * 100:.1f}%)")
    print(f"[OK] MW con almeno uno scope A1/A2: {mw_with_scope:.1f}")
    print("[OK] Priority 1 leads: Progeco/Vestas/Mammana restano segnali; Nordex OEM e New Developments non gonfiano gli scope")
    print("[OK] ruoli tecnici/engineering separati dagli scope esecutivi confermati")


if __name__ == "__main__":
    main()
