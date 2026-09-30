from __future__ import annotations

import argparse
import base64
import csv
import json
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "wind" / "input" / "projects.json"
WEB = ROOT / "wind" / "web"
OUT = ROOT / "docs" / "wind"
DATA = OUT / "data"
ASSETS = OUT / "assets"

STAGES = {f"E{i}" for i in range(9)}
GRADES = {"A1", "A2", "B", "C", "D"}
STATUSES = {"confirmed", "signal", "historical", "unknown"}
EXPECTED_SEED = {
    "andretta-bisaccia", "alia-sclafani", "serra-giannina", "serra-palino",
    "venusia", "alas", "carlentini", "greci-montaguto", "nulvi-ploaghe",
    "tricarico", "toritto", "volturino", "sava-maruggio", "lama-cupa",
    "fenice", "tarsia-ovest", "castelfranco-cer",
}


def load_source() -> tuple[dict, list[dict]]:
    if not INPUT.exists():
        raise ValueError(f"Sorgente mancante: {INPUT}")
    raw = json.loads(INPUT.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("projects"), list):
        raise ValueError("wind/input/projects.json deve contenere un oggetto con chiave projects")
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("Manca meta nel dataset sorgente")
    return meta, raw["projects"]


def source_map(project: dict) -> dict[str, dict]:
    return {s.get("id"): s for s in project.get("sources", []) if s.get("id")}


def validate(meta: dict, projects: list[dict]) -> None:
    ids: set[str] = set()
    for i, p in enumerate(projects, 1):
        required = (
            "id", "name", "mw", "bess_mw", "type", "region", "province",
            "municipalities", "developer", "stage", "stage_label", "status_note",
            "next", "timing", "relations", "gaps", "configs", "sources",
        )
        missing = [k for k in required if k not in p]
        if missing:
            raise ValueError(f"Record {i} {p.get('name', '?')}: campi mancanti {missing}")
        if p["id"] in ids:
            raise ValueError(f"ID duplicato: {p['id']}")
        ids.add(p["id"])
        if p["stage"] not in STAGES:
            raise ValueError(f"{p['id']}: stage non ammesso {p['stage']}")
        if not isinstance(p["mw"], (int, float)) or p["mw"] <= 0:
            raise ValueError(f"{p['id']}: MW eolici non validi")
        if not isinstance(p["bess_mw"], (int, float)) or p["bess_mw"] < 0:
            raise ValueError(f"{p['id']}: BESS MW non validi")
        if not isinstance(p["municipalities"], list):
            raise ValueError(f"{p['id']}: municipalities deve essere una lista")
        smap = source_map(p)
        if len(smap) != len([s for s in p.get("sources", []) if s.get("id")]):
            raise ValueError(f"{p['id']}: source id duplicato")
        for s in p.get("sources", []):
            url = s.get("url") or ""
            if url and not url.startswith(("http://", "https://")):
                raise ValueError(f"{p['id']}: URL fonte non valido: {url}")
        for rel in p.get("relations", []):
            if not rel.get("company") or not rel.get("role"):
                raise ValueError(f"{p['id']}: relazione azienda incompleta")
            if rel.get("confidence") not in GRADES:
                raise ValueError(f"{p['id']}: evidence grade relazione non valido")
            if rel.get("status") not in STATUSES:
                raise ValueError(f"{p['id']}: status relazione non valido")
            sid = rel.get("source_id")
            if sid and sid not in smap:
                raise ValueError(f"{p['id']}: source_id relazione non risolto: {sid}")
        for t in p.get("timing", []):
            if t.get("confidence") and t["confidence"] not in GRADES:
                raise ValueError(f"{p['id']}: evidence grade timing non valido")

    missing_seed = sorted(EXPECTED_SEED - ids)
    if missing_seed:
        raise ValueError("Seed minimo incompleto: " + ", ".join(missing_seed))

    scale = {x.get("code") for x in meta.get("maturity_scale", [])}
    if scale != STAGES:
        raise ValueError("maturity_scale deve contenere esattamente E0-E8")

    # Guardrail espliciti contro attribuzioni indebite emerse nel survey.
    by_id = {p["id"]: p for p in projects}
    def rels(pid: str, company: str) -> list[dict]:
        return [r for r in by_id[pid].get("relations", []) if r.get("company") == company]

    if any(r.get("status") == "confirmed" and "Civil BoP" in r.get("role", "")
           for r in rels("andretta-bisaccia", "Progeco Group")):
        raise ValueError("Progeco non puo essere promosso a Civil BoP senza nuova prova")
    if any(r.get("status") == "confirmed"
           for r in rels("serra-giannina", "D'Agostino Costruzioni Generali")):
        raise ValueError("D'Agostino su Serra Giannina deve restare segnale da confermare")
    if any(r.get("status") == "confirmed" for r in rels("alia-sclafani", "SOCEP")):
        raise ValueError("SOCEP su Alia deve restare incumbent storico, non contractor repowering")


def strict_execution(meta: dict, rel: dict) -> bool:
    return (
        rel.get("role") in set(meta.get("execution_roles", []))
        and rel.get("status") == "confirmed"
        and rel.get("confidence") in {"A1", "A2"}
    )


def evidence_best(project: dict) -> str | None:
    order = {"A1": 0, "A2": 1, "B": 2, "C": 3, "D": 4}
    vals = [r.get("confidence") for r in project.get("relations", [])]
    vals += [t.get("confidence") for t in project.get("timing", [])]
    vals = [v for v in vals if v in order]
    return min(vals, key=lambda v: order[v]) if vals else None


def first_timing(project: dict, *needles: str) -> dict | None:
    for t in project.get("timing", []):
        label = (t.get("label") or "").lower()
        if any(n.lower() in label for n in needles):
            return t
    return None


def window_value(item: dict | None):
    if not item:
        return None
    return {
        "label": item.get("label"),
        "start": item.get("start"),
        "end": item.get("end"),
        "date": item.get("date"),
        "precision": item.get("precision"),
        "confidence": item.get("confidence"),
    }


def companies_for(project: dict, matcher) -> list[str]:
    out = []
    for r in project.get("relations", []):
        if matcher((r.get("role") or "").lower()) and r.get("company") not in out:
            out.append(r["company"])
    return out


def latest_source_date(project: dict) -> str | None:
    dates = sorted([s.get("date") for s in project.get("sources", []) if s.get("date")])
    return dates[-1] if dates else None


def master_record(project: dict, as_of: str | None) -> dict:
    civil = first_timing(project, "opere civili", "civil")
    foundation = first_timing(project, "fondaz")
    electrical = first_timing(project, "opere elettriche", "cavidotti", "sse")
    delivery = first_timing(project, "delivery", "consegna", "trasporto wtg")
    erection = first_timing(project, "erection", "montaggi elettromeccanici wtg")
    commissioning = first_timing(project, "commissioning", "energizzazione", "start-up")
    cod = first_timing(project, "cod", "entrata in esercizio", "messa in esercizio")

    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "wind_mw": project["mw"],
        "bess_mw": project["bess_mw"],
        "project_type": project["type"],
        "region": project["region"],
        "province": project["province"],
        "municipalities": project["municipalities"],
        "area_if_known": project.get("area"),
        "developer": project.get("developer"),
        "spv": project.get("spv"),
        "myterna_code": project.get("myterna"),
        "mase_project_id": project.get("mase_id"),
        "permitting_status": project.get("stage_label"),
        "project_status": project.get("status_note"),
        "maturity": project.get("stage"),
        "civil_start": (civil or {}).get("start") or (civil or {}).get("date"),
        "foundation_window": window_value(foundation),
        "electrical_start": (electrical or {}).get("start") or (electrical or {}).get("date"),
        "wtg_delivery_window": window_value(delivery),
        "erection_window": window_value(erection),
        "commissioning_window": window_value(commissioning),
        "cod": (cod or {}).get("date") or (cod or {}).get("end"),
        "civil_bop": companies_for(project, lambda r: "civil bop" in r),
        "electrical_bop": companies_for(project, lambda r: "electrical bop" in r or "electromechanical" in r),
        "erection_contractor": companies_for(project, lambda r: "erection" in r),
        "dismantling_contractor": companies_for(project, lambda r: "dismantl" in r),
        "logistics_contractor": companies_for(project, lambda r: "logistic" in r or "heavy transport" in r),
        "oem": companies_for(project, lambda r: r == "oem" or r.startswith("oem ")),
        "engineering": companies_for(project, lambda r: "engineering" in r),
        "direzione_lavori": companies_for(project, lambda r: "direzione" in r or "/ dl" in r),
        "site_management": companies_for(project, lambda r: "site management" in r or "supervision" in r),
        "last_update": project.get("last_update") or as_of or latest_source_date(project),
        "confidence": evidence_best(project),
        "sources": project.get("sources", []),
        "notes": project.get("status_note"),
    }


def relationship_rows(projects: list[dict]) -> list[dict]:
    rows = []
    for p in projects:
        smap = source_map(p)
        for r in p.get("relations", []):
            s = smap.get(r.get("source_id"), {})
            rows.append({
                "project_id": p["id"],
                "project_name": p["name"],
                "company": r.get("company"),
                "role": r.get("role"),
                "work_package": r.get("work_package") or r.get("role"),
                "status": r.get("status"),
                "confidence": r.get("confidence"),
                "source_id": r.get("source_id"),
                "source": s.get("url") or s.get("title"),
                "source_title": s.get("title"),
                "source_date": s.get("date"),
            })
    return rows


def summary(meta: dict, projects: list[dict]) -> dict:
    def stage_num(p: dict) -> int:
        return int(p["stage"][1:])
    return {
        "projects": len(projects),
        "wind_mw": round(sum(float(p["mw"]) for p in projects), 1),
        "bess_mw": round(sum(float(p["bess_mw"]) for p in projects), 1),
        "authorized_or_later_mw": round(sum(float(p["mw"]) for p in projects if stage_num(p) >= 4), 1),
        "construction_mw": round(sum(float(p["mw"]) for p in projects if p["stage"] == "E7"), 1),
        "projects_with_execution_contractor": sum(
            1 for p in projects if any(strict_execution(meta, r) for r in p.get("relations", []))
        ),
        "projects_without_execution_contractor": sum(
            1 for p in projects if not any(strict_execution(meta, r) for r in p.get("relations", []))
        ),
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=";", extrasaction="ignore", lineterminator="\\n")
        w.writeheader()
        for row in rows:
            cooked = {}
            for key in fieldnames:
                val = row.get(key)
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False, separators=(",", ":"))
                cooked[key] = "" if val is None else val
            w.writerow(cooked)


def copy_web() -> None:
    if not (WEB / "index.html").exists():
        raise ValueError("Manca wind/web/index.html")
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WEB / "index.html", OUT / "index.html")
    for src in (WEB / "assets").iterdir():
        if src.is_file():
            shutil.copy2(src, ASSETS / src.name)


def build_preview(meta: dict, projects: list[dict]) -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    style = (WEB / "assets" / "style.css").read_text(encoding="utf-8")
    review_css = (WEB / "assets" / "review-fixes.css").read_text(encoding="utf-8")
    app_js = (WEB / "assets" / "app.js").read_text(encoding="utf-8")
    review_js = (WEB / "assets" / "review-fixes.js").read_text(encoding="utf-8")
    direct_js = (WEB / "assets" / "contractor-direct-fix.js").read_text(encoding="utf-8")
    svg = (WEB / "assets" / "italy-base.svg").read_bytes()
    svg_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")

    html = html.replace('<link href="assets/style.css" rel="stylesheet"/>', f"<style>{style}</style>")
    html = html.replace('<link href="assets/review-fixes.css" rel="stylesheet"/>', f"<style>{review_css}</style>")
    html = html.replace('src="assets/italy-base.svg"', f'src="{svg_uri}"')
    bundle = json.dumps({"meta": meta, "projects": projects}, ensure_ascii=False, separators=(",", ":"))
    bundle = bundle.replace("</", "<\\/")
    scripts = (
        f"<script>window.WIND_INLINE={bundle};</script>"
        f"<script>{app_js}</script>"
        f"<script>{review_js}</script>"
        f"<script>{direct_js}</script>"
    )
    marker = (
        '<script src="assets/app.js"></script>'
        '<script src="assets/review-fixes.js"></script>'
        '<script src="assets/contractor-direct-fix.js"></script>'
    )
    if marker not in html:
        raise ValueError("Marker script non trovato in wind/web/index.html")
    html = html.replace(marker, scripts)
    (OUT / "preview.html").write_text(html, encoding="utf-8")


class Parser(HTMLParser):
    pass


def build() -> dict:
    meta, projects = load_source()
    validate(meta, projects)
    copy_web()
    DATA.mkdir(parents=True, exist_ok=True)

    chunk_size = 6
    chunk_names = []
    for old in DATA.glob("projects-*.json"):
        old.unlink()
    for i in range(0, len(projects), chunk_size):
        name = f"projects-{i // chunk_size + 1}.json"
        chunk_names.append(name)
        (DATA / name).write_text(
            json.dumps(projects[i:i + chunk_size], ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    (DATA / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (DATA / "projects.json").write_text(
        json.dumps({"meta": "meta.json", "chunks": chunk_names}, separators=(",", ":")),
        encoding="utf-8",
    )

    masters = [master_record(p, meta.get("as_of")) for p in projects]
    rels = relationship_rows(projects)
    stats = summary(meta, projects)
    (DATA / "master.json").write_text(
        json.dumps({"summary": stats, "projects": masters}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DATA / "project_company_relationships.json").write_text(
        json.dumps(rels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "data.json").write_text(
        json.dumps({"meta": meta, "summary": stats, "projects": projects}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    project_fields = [
        "project_id", "project_name", "wind_mw", "bess_mw", "project_type", "region",
        "province", "municipalities", "developer", "spv", "maturity", "project_status",
        "civil_start", "electrical_start", "cod", "confidence",
    ]
    write_csv(OUT / "projects.csv", project_fields, masters)
    rel_fields = [
        "project_id", "project_name", "company", "role", "work_package", "status",
        "confidence", "source", "source_date",
    ]
    write_csv(OUT / "project_company_relationships.csv", rel_fields, rels)
    build_preview(meta, projects)
    return stats


def check_outputs() -> None:
    required = [
        OUT / "index.html", OUT / "preview.html", OUT / "data.json", OUT / "projects.csv",
        DATA / "meta.json", DATA / "projects.json", DATA / "master.json",
        DATA / "project_company_relationships.json",
        ASSETS / "app.js", ASSETS / "style.css",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise ValueError("Output mancanti: " + ", ".join(missing))

    manifest = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
    meta = json.loads((DATA / manifest["meta"]).read_text(encoding="utf-8"))
    projects = []
    for name in manifest["chunks"]:
        projects.extend(json.loads((DATA / name).read_text(encoding="utf-8")))
    validate(meta, projects)
    if len(projects) < len(EXPECTED_SEED):
        raise ValueError("Output seed incompleto")

    for path in [OUT / "index.html", OUT / "preview.html"]:
        Parser().feed(path.read_text(encoding="utf-8"))
    preview = (OUT / "preview.html").read_text(encoding="utf-8")
    if 'window.WIND_INLINE=' not in preview:
        raise ValueError("preview.html non contiene il bundle dati inline")
    if 'src="assets/' in preview or 'href="assets/' in preview:
        raise ValueError("preview.html dipende ancora da asset locali")
    if not (OUT / "index.html").read_text(encoding="utf-8").find("data/projects.json") == -1:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Wind Project & Contractor Radar")
    parser.add_argument("--check-only", action="store_true", help="Valida gli output esistenti senza rigenerare")
    args = parser.parse_args()
    if args.check_only:
        check_outputs()
        print("[SUCCESS] Wind Radar: output validi")
        return 0

    stats = build()
    check_outputs()
    print(
        "[SUCCESS] Wind Radar aggiornato: "
        f"{stats['projects']} progetti | {stats['wind_mw']} MW wind | "
        f"{stats['bess_mw']} MW BESS | {stats['projects_with_execution_contractor']} con contractor esecutivo A1/A2"
    )
    print(f"[SUCCESS] Dashboard: {OUT / 'index.html'}")
    print(f"[SUCCESS] Preview standalone: {OUT / 'preview.html'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FAILURE] {exc}", file=sys.stderr)
        raise SystemExit(1)
