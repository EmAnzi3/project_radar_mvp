from pathlib import Path
import json

ROOT = Path(".")
OUT = ROOT / "docs" / "data" / "master_projects.json"

SOURCES = [
    ROOT / "docs" / "data" / "national_anac_relevant_awards.json",
    ROOT / "docs" / "national_operational_data.json",
]

def clean(v):
    if v is None:
        return ""
    return str(v).strip()

def load_json(path):
    if not path.exists():
        print(f"[SKIP] manca: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("records", [])
    print(f"[OK] {path}: {len(data)} record")
    return data

def key_for(r):
    cup = clean(r.get("cup")).upper()
    cig = clean(r.get("cig")).upper()
    title = clean(r.get("title")).upper()
    municipality = clean(r.get("municipality")).upper()
    if cup and cig:
        return f"CUP_CIG::{cup}::{cig}"
    if cup:
        return f"CUP::{cup}"
    return f"TITLE::{title}::{municipality}"

def normalize(r, source_name):
    return {
        "id": "",
        "source": source_name,
        "sources": [source_name],
        "branch": clean(r.get("branch") or r.get("assigned_branch") or r.get("filiale")),
        "branch_candidates": clean(r.get("branch_candidates")),
        "branch_confidence": clean(r.get("branch_confidence")),
        "segment": clean(r.get("segment") or r.get("primary_segment")),
        "cup": clean(r.get("cup")),
        "cig": clean(r.get("cig")),
        "title": clean(r.get("title")),
        "category": clean(r.get("category")),
        "region": clean(r.get("region")),
        "province": clean(r.get("province")),
        "municipality": clean(r.get("municipality")),
        "address": clean(
            r.get("INDIRIZZO_INTERVENTO")
            or r.get("indirizzo_intervento")
            or r.get("indirizzo")
            or r.get("address")
        ),
        "project_value": r.get("project_value") or r.get("value_eur") or r.get("value") or 0,
        "client": clean(r.get("client")),
        "contractors": clean(r.get("contractors") or r.get("contractor_name")),
        "contractor_tax_codes": clean(r.get("contractor_tax_codes") or r.get("contractor_tax_code")),
        "award_date": clean(r.get("award_date")),
        "award_result": clean(r.get("award_result")),
        "source_url": clean(r.get("source_url") or r.get("url")),
        "has_anac": bool(clean(r.get("cig")) or clean(r.get("contractors")) or clean(r.get("award_date"))),
    }

def merge_record(base, incoming):
    for k, v in incoming.items():
        if k == "sources":
            base["sources"] = sorted(set(base.get("sources", []) + incoming.get("sources", [])))
            continue

        if k == "has_anac":
            base[k] = bool(base.get(k)) or bool(v)
            continue

        if not base.get(k) and v:
            base[k] = v

    # Se il record ANAC ha dati più forti, privilegiali
    if incoming.get("has_anac"):
        for k in ["cig", "contractors", "contractor_tax_codes", "award_date", "award_result"]:
            if incoming.get(k):
                base[k] = incoming[k]
        base["has_anac"] = True

    return base

def main():
    anac_rows = [normalize(r, "anac_relevant_awards") for r in load_json(ROOT / "docs" / "data" / "national_anac_relevant_awards.json")]
    opencup_rows = [normalize(r, "national_operational_data") for r in load_json(ROOT / "docs" / "national_operational_data.json")]

    anac_cups = {clean(r.get("cup")).upper() for r in anac_rows if clean(r.get("cup"))}

    records = []

    # Mantiene ogni affidamento ANAC come riga autonoma
    for r in anac_rows:
        cup = clean(r.get("cup")).upper()
        cig = clean(r.get("cig")).upper()
        r["id"] = f"ANAC::{cup}::{cig}" if cig else f"ANAC::{cup}"
        r["source"] = "ANAC"
        r["sources"] = ["OpenCUP", "ANAC"]
        r["has_anac"] = True
        records.append(r)

    # Aggiunge solo OpenCUP senza affidamento ANAC gi? presente
    for r in opencup_rows:
        cup = clean(r.get("cup")).upper()
        if cup and cup in anac_cups:
            continue

        r["id"] = f"OPENCUP::{cup}" if cup else key_for(r)
        r["source"] = "OpenCUP"
        r["sources"] = ["OpenCUP"]
        r["has_anac"] = False
        records.append(r)

    records.sort(key=lambda r: (
        not r.get("has_anac"),
        -float(r.get("project_value") or 0)
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"[OK] master scritto: {OUT}")
    print(f"Record master: {len(records)}")
    print(f"Con ANAC: {sum(1 for r in records if r.get('has_anac'))}")
    print(f"Senza ANAC: {sum(1 for r in records if not r.get('has_anac'))}")
    print(f"CUP ANAC unici: {len(anac_cups)}")


if __name__ == "__main__":
    main()
