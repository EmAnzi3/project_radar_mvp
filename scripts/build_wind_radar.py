from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "wind_projects.csv"
OUT_DIR = ROOT / "docs" / "wind"
OUT_JSON = OUT_DIR / "data.json"

DATE_FIELDS = [
    "construction_start", "civil_start", "civil_end", "electrical_start", "electrical_end",
    "wtg_delivery_start", "wtg_delivery_end", "erection_start", "erection_end",
    "commissioning_start", "commissioning_end", "cod"
]
FLOAT_FIELDS = ["mw_wind", "bess_mw", "area_ha"]
ROLE_FIELDS = [
    ("civil_bop", "Civil BoP"),
    ("electrical_bop", "Electrical BoP"),
    ("oem", "OEM"),
    ("engineering_dl", "Engineering / DL"),
    ("supervision", "Supervision"),
    ("dismantling", "Dismantling"),
    ("logistics", "Logistics"),
]


def clean(value: str | None) -> str:
    return (value or "").strip()


def split_pipe(value: str | None) -> list[str]:
    return [x.strip() for x in clean(value).split("|") if x.strip()]


def number(value: str | None):
    value = clean(value).replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_date(value: str | None):
    value = clean(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Data non valida: {value}")


def iso(value):
    return value.isoformat() if isinstance(value, date) else None


def active_phase(project: dict, today: date) -> str:
    windows = [
        ("Commissioning", "commissioning_start", "commissioning_end"),
        ("Erection WTG", "erection_start", "erection_end"),
        ("Consegna WTG", "wtg_delivery_start", "wtg_delivery_end"),
        ("Opere elettriche", "electrical_start", "electrical_end"),
        ("Opere civili", "civil_start", "civil_end"),
    ]
    for label, start_key, end_key in windows:
        start = project.get("_dates", {}).get(start_key)
        end = project.get("_dates", {}).get(end_key)
        if start and end and start <= today <= end:
            return label
    construction = project.get("_dates", {}).get("construction_start")
    cod = project.get("_dates", {}).get("cod")
    if construction and today < construction:
        return "Pre-cantiere"
    if cod and today > cod:
        return "Operativo / post-COD"
    return project.get("stage_label") or "Da verificare"


def build():
    if not SOURCE.exists():
        raise SystemExit(f"File sorgente non trovato: {SOURCE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    projects = []

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        required = {"id", "project", "region", "mw_wind", "stage_code", "stage_label"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit("Colonne obbligatorie mancanti: " + ", ".join(sorted(missing)))

        for row in reader:
            p = {k: clean(v) for k, v in row.items()}
            for key in FLOAT_FIELDS:
                p[key] = number(row.get(key))

            p["municipalities"] = split_pipe(row.get("municipalities"))
            p["sources"] = split_pipe(row.get("sources"))
            p["_dates"] = {key: parse_date(row.get(key)) for key in DATE_FIELDS}
            for key in DATE_FIELDS:
                p[key] = iso(p["_dates"][key])

            contractors = []
            for key, role in ROLE_FIELDS:
                for company in split_pipe(row.get(key)):
                    contractors.append({"company": company, "role": role})
            p["contractors"] = contractors
            p["active_phase"] = active_phase(p, today)
            projects.append(p)

    projects.sort(key=lambda p: (
        p.get("cod") or "9999-12-31",
        -(p.get("mw_wind") or 0),
        p.get("project") or ""
    ))

    region_mw = defaultdict(float)
    stage_mw = defaultdict(float)
    stage_counts = Counter()
    contractor_projects = defaultdict(set)
    contractor_roles = defaultdict(set)

    for p in projects:
        mw = p.get("mw_wind") or 0
        region_mw[p.get("region") or "N/D"] += mw
        stage_counts[p.get("stage_label") or "N/D"] += 1
        stage_mw[p.get("stage_label") or "N/D"] += mw
        for c in p["contractors"]:
            contractor_projects[c["company"]].add(p["id"])
            contractor_roles[c["company"]].add(c["role"])

    contractors = [
        {
            "company": name,
            "projects": len(contractor_projects[name]),
            "roles": sorted(contractor_roles[name]),
        }
        for name in contractor_projects
    ]
    contractors.sort(key=lambda x: (-x["projects"], x["company"]))

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "as_of": today.isoformat(),
        "summary": {
            "projects": len(projects),
            "mw_wind": round(sum(p.get("mw_wind") or 0 for p in projects), 1),
            "mw_bess": round(sum(p.get("bess_mw") or 0 for p in projects), 1),
            "with_executor": sum(1 for p in projects if any(c["role"] in {"Civil BoP", "Electrical BoP"} for c in p["contractors"])),
            "procurement_watch": sum(1 for p in projects if p.get("stage_code") in {"E5", "E6"}),
        },
        "region_mw": [
            {"region": k, "mw": round(v, 1)}
            for k, v in sorted(region_mw.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "stage_mix": [
            {"stage": k, "projects": stage_counts[k], "mw": round(stage_mw[k], 1)}
            for k in sorted(stage_counts)
        ],
        "contractors": contractors,
        "projects": projects,
    }

    # remove private helper dates
    for p in payload["projects"]:
        p.pop("_dates", None)

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Wind radar aggiornato: {len(projects)} progetti, {payload['summary']['mw_wind']} MW")
    print(f"[OK] Output: {OUT_JSON}")


if __name__ == "__main__":
    build()
