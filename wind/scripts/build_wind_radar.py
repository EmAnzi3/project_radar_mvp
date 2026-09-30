from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "wind" / "input" / "projects.json"
TEMPLATE = ROOT / "wind" / "template" / "index.template.html"
OUT_DIR = ROOT / "docs" / "wind"
OUT_JSON = OUT_DIR / "data.json"
OUT_HTML = OUT_DIR / "index.html"
OUT_CSV = OUT_DIR / "projects.csv"

REQUIRED = ("id", "project", "type", "mw_wind", "region", "province", "municipalities",
            "developer", "stage", "status", "commercial_focus", "confidence", "sources")

STAGE_ORDER = {
    "Construction": 0,
    "Pre-construction": 1,
    "Authorized": 2,
    "Advanced permitting": 3,
    "Permitting": 4,
    "Operating": 5,
}

def load_source() -> dict:
    if not INPUT.exists():
        raise FileNotFoundError(f"Manca il file sorgente: {INPUT}")
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), list):
        raise ValueError("projects.json deve contenere un oggetto con chiave 'projects' (lista).")
    return payload

def validate(projects: list[dict]) -> None:
    ids = set()
    for i, p in enumerate(projects, start=1):
        missing = [k for k in REQUIRED if k not in p]
        if missing:
            raise ValueError(f"Record {i} ({p.get('project','?')}): campi mancanti {missing}")
        if p["id"] in ids:
            raise ValueError(f"ID duplicato: {p['id']}")
        ids.add(p["id"])
        try:
            p["mw_wind"] = float(p.get("mw_wind") or 0)
            p["mw_bess"] = float(p.get("mw_bess") or 0)
        except Exception as exc:
            raise ValueError(f"MW non validi per {p['project']}") from exc
        if not isinstance(p.get("contractors", []), list):
            raise ValueError(f"contractors deve essere una lista per {p['project']}")
        if not isinstance(p.get("sources", []), list):
            raise ValueError(f"sources deve essere una lista per {p['project']}")

def commercial_window(stage: str) -> str:
    return {
        "Construction": "ATTIVO",
        "Pre-construction": "0–6 MESI",
        "Authorized": "PROCUREMENT",
        "Advanced permitting": "6–18 MESI",
        "Permitting": "SVILUPPO",
        "Operating": "O&M",
    }.get(stage, stage.upper() if stage else "N/D")

def build_payload(source: dict) -> dict:
    projects = source["projects"]
    validate(projects)

    for p in projects:
        p["commercial_window"] = commercial_window(p.get("stage", ""))
        p["contractor_names"] = sorted({c.get("company","").strip() for c in p.get("contractors", []) if c.get("company","").strip()})
        p["has_execution_contractor"] = any(
            c.get("role","").lower().find(x) >= 0
            for c in p.get("contractors", [])
            for x in ("opere civili", "boP".lower(), "fondazioni", "sse", "rtI".lower(), "preparazione sito")
        )
        p["source_count"] = len(p.get("sources", []))

    projects.sort(key=lambda p: (STAGE_ORDER.get(p.get("stage"), 99), -p.get("mw_wind", 0), p.get("project","")))

    total_mw = round(sum(p["mw_wind"] for p in projects), 1)
    active = [p for p in projects if p.get("stage") == "Construction"]
    pre = [p for p in projects if p.get("stage") == "Pre-construction"]
    authorized = [p for p in projects if p.get("stage") == "Authorized"]
    with_contractors = [p for p in projects if p.get("contractor_names")]

    by_region = defaultdict(lambda: {"projects": 0, "mw": 0.0})
    by_province = defaultdict(lambda: {"projects": 0, "mw": 0.0})
    by_stage = defaultdict(lambda: {"projects": 0, "mw": 0.0})
    contractors = defaultdict(lambda: {"projects": set(), "mw": 0.0, "roles": set()})

    for p in projects:
        by_region[p["region"]]["projects"] += 1
        by_region[p["region"]]["mw"] += p["mw_wind"]
        by_province[p["province"]]["projects"] += 1
        by_province[p["province"]]["mw"] += p["mw_wind"]
        by_stage[p["stage"]]["projects"] += 1
        by_stage[p["stage"]]["mw"] += p["mw_wind"]
        for c in p.get("contractors", []):
            name = c.get("company","").strip()
            if not name:
                continue
            contractors[name]["projects"].add(p["project"])
            contractors[name]["mw"] += p["mw_wind"]
            if c.get("role"):
                contractors[name]["roles"].add(c["role"])

    contractor_rows = [
        {"company": name, "projects": len(v["projects"]), "mw": round(v["mw"], 1),
         "roles": sorted(v["roles"]), "project_names": sorted(v["projects"])}
        for name, v in contractors.items()
    ]
    contractor_rows.sort(key=lambda x: (-x["projects"], -x["mw"], x["company"]))

    def rows(d):
        return sorted(
            [{"name": k, "projects": v["projects"], "mw": round(v["mw"], 1)} for k, v in d.items()],
            key=lambda x: (-x["mw"], x["name"])
        )

    return {
        "updated_at": source.get("updated_at", ""),
        "summary": {
            "projects": len(projects),
            "mw": total_mw,
            "construction_projects": len(active),
            "construction_mw": round(sum(p["mw_wind"] for p in active), 1),
            "preconstruction_projects": len(pre),
            "authorized_projects": len(authorized),
            "projects_with_contractors": len(with_contractors),
        },
        "by_region": rows(by_region),
        "by_province": rows(by_province),
        "by_stage": rows(by_stage),
        "contractors": contractor_rows,
        "projects": projects,
    }

def write_csv(projects: list[dict]) -> None:
    fields = [
        "project","type","mw_wind","mw_bess","region","province","municipalities","area",
        "developer","spv","myterna","stage","status","construction_window","erection_window",
        "cod_target","commercial_focus","confidence","contractor_names"
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        for p in projects:
            row = {k: p.get(k, "") for k in fields}
            row["contractor_names"] = " | ".join(p.get("contractor_names", []))
            w.writerow(row)

def main() -> int:
    source = load_source()
    payload = build_payload(source)
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Manca il template: {TEMPLATE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(payload["projects"])

    template = TEMPLATE.read_text(encoding="utf-8")
    marker = "__WIND_DATA__"
    if marker not in template:
        raise ValueError(f"Placeholder {marker} non trovato nel template.")
    html = template.replace(marker, json.dumps(payload, ensure_ascii=False))
    OUT_HTML.write_text(html, encoding="utf-8")

    s = payload["summary"]
    print(f"OK: {s['projects']} progetti | {s['mw']} MW | {s['construction_projects']} in costruzione")
    print(f"Dashboard: {OUT_HTML}")
    print(f"CSV:       {OUT_CSV}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        raise
