from pathlib import Path
import json

ROOT = Path(".")
OUT = ROOT / "reports" / "master_projects.json"

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


def cup_year(cup):
    c = clean(cup)
    if len(c) < 6:
        return None
    yy = c[4:6]
    if not yy.isdigit():
        return None
    n = int(yy)
    return 2000 + n if n <= 40 else 1900 + n

def apply_quality_layer(r):
    flags = []
    score = 50

    value = float(r.get("project_value") or 0)
    title = clean(r.get("title")).upper()
    municipality = clean(r.get("municipality"))
    has_anac = bool(r.get("has_anac"))
    awards_count = int(r.get("awards_count") or 0)
    year = cup_year(r.get("cup"))

    if has_anac:
        score += 25
    else:
        flags.append("NO_ANAC_MATCH")
        score -= 8

    if awards_count > 1:
        score += min(12, awards_count * 2)

    if year:
        r["cup_year"] = year
        if year < 2015:
            flags.append("OLD_CUP")
            score -= 12
        elif year >= 2023:
            score += 8
    else:
        flags.append("CUP_YEAR_UNKNOWN")
        score -= 5

    generic_terms = [
        "TERRITORIO COMUNALE",
        "EDIFICI DEMANIALI",
        "EDIFICI SCOLASTICI",
        "SERVIZIO DI MANUTENZIONE",
        "MANUTENZIONE ORDINARIA",
        "VERDE",
        "RIFACIMENTO SERVIZI IGIENICI",
        "PIAZZALE",
        "ARREDAMENTO URBANO",
    ]

    if any(t in title for t in generic_terms):
        flags.append("GENERIC_OR_MAINTENANCE_TITLE")
        score -= 15

    if value >= 150_000_000 and not has_anac:
        flags.append("HIGH_VALUE_WITHOUT_ANAC")
        score -= 12

    if value >= 100_000_000 and year and year < 2015:
        flags.append("OLD_HIGH_VALUE")
        score -= 15

    if value >= 100_000_000 and any(t in title for t in [
        "SERVIZI IGIENICI",
        "VERDE",
        "MUNICIPIO",
        "PIAZZALE",
        "SCUOLA MEDIA",
        "URBANIZZAZIONE PRIMARIA",
    ]):
        flags.append("VALUE_SUSPICIOUS")
        score -= 25

    if r.get("branch") in ("", None):
        flags.append("BRANCH_MISSING")
        score -= 8

    if r.get("branch") == "AMBIGUA":
        flags.append("BRANCH_AMBIGUOUS")
        score -= 4

    if r.get("branch") == "NON ASSEGNATA":
        flags.append("BRANCH_NOT_ASSIGNED")
        score -= 10

    if value >= 50_000_000:
        score += 8
    elif value >= 10_000_000:
        score += 4

    score = max(0, min(100, int(score)))

    if score >= 75:
        reliability = "ALTA"
    elif score >= 50:
        reliability = "MEDIA"
    else:
        reliability = "BASSA"

    r["quality_flags"] = flags
    r["commercial_score"] = score
    r["data_reliability"] = reliability

    return r


def group_projects(rows):
    groups = {}

    for r in rows:
        cup = clean(r.get("cup")).upper()
        key = cup if cup else clean(r.get("id"))

        if key not in groups:
            groups[key] = []

        groups[key].append(r)

    out = []

    for key, items in groups.items():
        base = max(items, key=lambda x: float(x.get("project_value") or 0)).copy()

        awards = []
        contractors_seen = []

        for r in items:
            if r.get("has_anac"):
                award = {
                    "cig": r.get("cig", ""),
                    "contractors": r.get("contractors", ""),
                    "contractor_tax_codes": r.get("contractor_tax_codes", ""),
                    "award_amount_eur": r.get("award_amount_eur", ""),
                    "award_share_pct": r.get("award_share_pct", ""),
                    "award_weight": r.get("award_weight", ""),
                    "ratio_note": r.get("ratio_note", ""),
                    "award_date": r.get("award_date", ""),
                    "award_result": r.get("award_result", ""),
                    "award_criteria": r.get("award_criteria", ""),
                    "included_services": r.get("included_services", ""),
                    "id_aggiudicazione": r.get("id_aggiudicazione", "")
                }
                awards.append(award)

                for c in clean(r.get("contractors")).split("|"):
                    c = c.strip()
                    if c and c not in contractors_seen:
                        contractors_seen.append(c)

        base["awards"] = awards
        base["awards_count"] = len(awards)
        base["has_anac"] = bool(awards)
        base["contractors_summary"] = (
            contractors_seen[0] + (f" + altri {len(contractors_seen)-1} OE" if len(contractors_seen) > 1 else "")
            if contractors_seen else ""
        )

        # se il progetto ? OpenCUP puro, pulisce campi ANAC singoli
        if not awards:
            for k in [
                "cig", "contractors", "contractor_tax_codes",
                "award_date", "award_result", "award_amount_eur",
                "award_share_pct", "award_weight", "ratio_note"
            ]:
                base[k] = ""

        out.append(base)

    return out


def main():
    anac_rows = [normalize(r, "national_anac_relevant_awards") for r in load_json(ROOT / "docs" / "data" / "national_anac_relevant_awards.json")]
    opencup_rows = [normalize(r, "national_operational_data") for r in load_json(ROOT / "docs" / "national_operational_data.json")]

    anac_cups = {clean(r.get("cup")).upper() for r in anac_rows if clean(r.get("cup"))}

    raw_records = []

    # Mantiene ogni affidamento ANAC come riga grezza autonoma
    for r in anac_rows:
        cup = clean(r.get("cup")).upper()
        cig = clean(r.get("cig")).upper()
        r["id"] = f"ANAC::{cup}::{cig}" if cig else f"ANAC::{cup}"
        r["source"] = "ANAC"
        r["sources"] = ["OpenCUP", "ANAC"]
        r["has_anac"] = True
        raw_records.append(r)

    # Aggiunge solo OpenCUP senza affidamento ANAC gi? presente
    for r in opencup_rows:
        cup = clean(r.get("cup")).upper()
        if cup and cup in anac_cups:
            continue

        r["id"] = f"OPENCUP::{cup}" if cup else key_for(r)
        r["source"] = "OpenCUP"
        r["sources"] = ["OpenCUP"]
        r["has_anac"] = False
        raw_records.append(r)

    records = group_projects(raw_records)

    records = [apply_quality_layer(r) for r in records]

    records.sort(key=lambda r: (
        -int(r.get("commercial_score") or 0),
        not r.get("has_anac"),
        -float(r.get("project_value") or 0)
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"[OK] master scritto: {OUT}")
    print(f"Righe grezze: {len(raw_records)}")
    print(f"Progetti master: {len(records)}")
    print(f"Con ANAC: {sum(1 for r in records if r.get('has_anac'))}")
    print(f"Senza ANAC: {sum(1 for r in records if not r.get('has_anac'))}")
    print(f"Con pi? affidamenti: {sum(1 for r in records if int(r.get('awards_count') or 0) > 1)}")
    print(f"CUP ANAC unici: {len(anac_cups)}")


if __name__ == "__main__":
    main()
