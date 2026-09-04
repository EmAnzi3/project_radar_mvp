from __future__ import annotations

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "wind" / "data"
MANIFEST = DATA / "projects.json"
ENRICHMENT = DATA / "enrichment-2026-09-04.json"


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
        relation = {key: value for key, value in spec.items() if key not in {"action", "match"}}
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
    projects: list[dict] = []
    for chunk in manifest["chunks"]:
        projects.extend(load_json(DATA / chunk))

    if len(projects) != 17:
        fail(f"seed Wind inatteso: {len(projects)} progetti, attesi 17")
    ids = [project["id"] for project in projects]
    if len(set(ids)) != len(ids):
        fail("ID progetto duplicati")
    total_mw = sum(float(project.get("mw") or 0) for project in projects)
    if not math.isclose(total_mw, 1496.9, abs_tol=0.01):
        fail(f"totale MW inatteso: {total_mw:.1f}, attesi 1496.9")

    stage_codes = {item["code"] for item in meta["maturity_scale"]}
    for project in projects:
        if project.get("stage") not in stage_codes:
            fail(f"stage non valido per {project['id']}: {project.get('stage')}")
        source_ids = {source.get("id") for source in project.get("sources", [])}
        refs = []
        if project.get("next", {}).get("source_id"):
            refs.append(project["next"]["source_id"])
        refs.extend(item.get("source_id") for item in project.get("timing", []) if item.get("source_id"))
        refs.extend(item.get("source_id") for item in project.get("relations", []) if item.get("source_id"))
        refs.extend(item.get("source_id") for item in project.get("configs", []) if item.get("source_id"))
        missing = sorted(set(refs) - source_ids)
        if missing:
            fail(f"source_id non risolti in {project['id']}: {', '.join(missing)}")

    if not ENRICHMENT.exists():
        print(f"[OK] seed Wind: 17 progetti / {total_mw:.1f} MW")
        print("[INFO] enrichment v0.3 non presente")
        return

    enrichment = load_json(ENRICHMENT)
    overlay_projects = enrichment.get("projects", {})
    if set(overlay_projects) != set(ids):
        fail("gli ID dell'enrichment non coincidono con i 17 seed")

    merged = [merge_overlay(project, overlay_projects.get(project["id"], {})) for project in projects]
    core_scopes = enrichment["method"]["core_scopes"]
    role_map = enrichment["method"]["scope_role_map"]

    def applicable(project: dict) -> list[dict]:
        is_repowering = "repowering" in str(project.get("type", "")).lower()
        return [
            scope
            for scope in core_scopes
            if scope["applicable"] == "all" or (scope["applicable"] == "repowering" and is_repowering)
        ]

    def scope_covered(project: dict, scope: dict) -> bool:
        roles = set(role_map[scope["id"]])
        return any(
            relation.get("role") in roles
            and relation.get("status") == "confirmed"
            and relation.get("confidence") in {"A1", "A2"}
            for relation in project.get("relations", [])
        )

    covered_slots = 0
    total_slots = 0
    projects_with_scope: list[dict] = []
    for project in merged:
        scopes = applicable(project)
        covered = [scope for scope in scopes if scope_covered(project, scope)]
        total_slots += len(scopes)
        covered_slots += len(covered)
        if covered:
            projects_with_scope.append(project)

        source_ids = {source.get("id") for source in project.get("sources", [])}
        missing = sorted(
            {
                relation.get("source_id")
                for relation in project.get("relations", [])
                if relation.get("source_id") and relation.get("source_id") not in source_ids
            }
        )
        if missing:
            fail(f"source_id enrichment non risolti in {project['id']}: {', '.join(missing)}")

    mw_with_scope = sum(float(project.get("mw") or 0) for project in projects_with_scope)

    # Regression guards: B/C signals must not close an execution scope.
    serra = next(project for project in merged if project["id"] == "serra-giannina")
    if any(scope_covered(serra, scope) for scope in applicable(serra)):
        fail("Serra Giannina: un segnale B sta chiudendo indebitamente uno scope")
    tricarico = next(project for project in merged if project["id"] == "tricarico")
    if any(scope_covered(tricarico, scope) for scope in applicable(tricarico)):
        fail("Tricarico: relazione societaria/advisory sta chiudendo indebitamente uno scope")
    carlentini = next(project for project in merged if project["id"] == "carlentini")
    carlentini_covered = {scope["id"] for scope in applicable(carlentini) if scope_covered(carlentini, scope)}
    if carlentini_covered != {"foundation"}:
        fail(f"Carlentini: coverage inattesa {sorted(carlentini_covered)}; attesa solo foundation")

    print(f"[OK] seed Wind: 17 progetti / {total_mw:.1f} MW")
    print(f"[OK] scope coverage: {covered_slots}/{total_slots} ({covered_slots / total_slots * 100:.1f}%)")
    print(f"[OK] MW con almeno uno scope A1/A2: {mw_with_scope:.1f}")
    print("[OK] segnali B/C separati dagli scope esecutivi confermati")


if __name__ == "__main__":
    main()
