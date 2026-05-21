import re
import csv
from pathlib import Path
from collections import defaultdict

import pandas as pd
import pgeocode


INPUT_XLSX = Path("data/raw/CAP.xlsx")

OUT_CAP_TO_BRANCH = Path("config/cap_to_branch.csv")
OUT_CAP_TO_MUNICIPALITY = Path("config/cap_to_municipality.csv")
OUT_CAP_BRANCH_MUNICIPALITY = Path("config/cap_branch_municipality.csv")
OUT_MUNICIPALITY_TO_BRANCH = Path("config/municipality_to_branch.csv")

REPORT_CAP_BY_BRANCH = Path("reports/cap_by_branch.csv")
REPORT_AMBIGUOUS = Path("reports/municipality_branch_issues.csv")
REPORT_UNRESOLVED = Path("reports/cap_unresolved.csv")


def clean(value):
    # Gestisce NaN pandas/numpy/pgeocode evitando la stringa "nan"
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value or "").strip()

    if text.lower() in {"nan", "none", "null"}:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def clean_cap(value):
    text = str(value or "").strip()
    text = re.sub(r"\D+", "", text)

    if not text:
        return ""

    return text.zfill(5)


def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_columns(df):
    cols = list(df.columns)

    cap_col = None
    branch_col = None

    for col in cols:
        n = norm(col)
        if n == "CAP" or " CAP " in f" {n} ":
            cap_col = col
        if "FILIALE" in n or "RIFERIMENTO" in n or "NOME ACCOUNT" in n:
            branch_col = col

    if cap_col is None:
        # fallback: colonna che contiene più CAP plausibili
        best = None
        best_count = -1

        for col in cols:
            values = df[col].dropna().astype(str).head(200)
            count = sum(1 for v in values if re.fullmatch(r"\D*\d{5}\D*", v.strip()))
            if count > best_count:
                best = col
                best_count = count

        cap_col = best

    if branch_col is None:
        # fallback: prima colonna diversa da CAP
        for col in cols:
            if col != cap_col:
                branch_col = col
                break

    if cap_col is None or branch_col is None:
        raise SystemExit(f"Impossibile riconoscere colonne. Colonne trovate: {cols}")

    return cap_col, branch_col


def split_places(place_name):
    """
    GeoNames/pgeocode può restituire più località nello stesso CAP separate da virgola.
    Le esplodiamo in righe separate.
    """
    text = clean(place_name)
    if not text:
        return []

    parts = [clean(p) for p in text.split(",")]
    return [p for p in parts if p]


def main():
    if not INPUT_XLSX.exists():
        raise SystemExit(f"File non trovato: {INPUT_XLSX}")

    print(f"Leggo: {INPUT_XLSX}")
    df = pd.read_excel(INPUT_XLSX)

    cap_col, branch_col = detect_columns(df)
    print(f"Colonna CAP: {cap_col}")
    print(f"Colonna filiale: {branch_col}")

    cap_branch_rows = []
    seen_caps = {}

    for _, row in df.iterrows():
        cap = clean_cap(row.get(cap_col))
        branch = clean(row.get(branch_col))

        if not cap or not branch:
            continue

        previous = seen_caps.get(cap)
        if previous and previous != branch:
            print(f"[WARN] CAP duplicato su più filiali: {cap} → {previous} / {branch}")

        seen_caps[cap] = branch

    for cap, branch in sorted(seen_caps.items()):
        cap_branch_rows.append({
            "cap": cap,
            "branch": branch,
        })

    print(f"CAP unici nel cappario: {len(cap_branch_rows)}")
    print(f"Filiali nel cappario: {len(set(r['branch'] for r in cap_branch_rows))}")

    OUT_CAP_TO_BRANCH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_CAP_TO_BRANCH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=["cap", "branch"])
        writer.writeheader()
        writer.writerows(cap_branch_rows)

    # CAP → Comune/Provincia/Regione tramite pgeocode
    print("Interrogo pgeocode per CAP italiani...")
    nomi = pgeocode.Nominatim("IT", unique=True)

    cap_geo_rows = []
    cap_branch_geo_rows = []
    unresolved_rows = []

    for item in cap_branch_rows:
        cap = item["cap"]
        branch = item["branch"]

        result = nomi.query_postal_code(cap)

        place_name = clean(getattr(result, "place_name", ""))
        region = clean(getattr(result, "state_name", ""))
        province = clean(getattr(result, "county_name", ""))
        province_code = clean(getattr(result, "county_code", ""))
        latitude = clean(getattr(result, "latitude", ""))
        longitude = clean(getattr(result, "longitude", ""))
        accuracy = clean(getattr(result, "accuracy", ""))

        places = split_places(place_name)

        if not places:
            unresolved_rows.append({
                "cap": cap,
                "branch": branch,
                "reason": "CAP non risolto da pgeocode",
            })
            continue

        for municipality in places:
            geo_row = {
                "cap": cap,
                "municipality": municipality,
                "municipality_norm": norm(municipality),
                "province": province,
                "province_norm": norm(province),
                "province_code": province_code,
                "region": region,
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
            }

            cap_geo_rows.append(geo_row)

            cap_branch_geo_rows.append({
                **geo_row,
                "branch": branch,
            })

    with OUT_CAP_TO_MUNICIPALITY.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cap",
            "municipality",
            "municipality_norm",
            "province",
            "province_norm",
            "province_code",
            "region",
            "latitude",
            "longitude",
            "accuracy",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cap_geo_rows)

    with OUT_CAP_BRANCH_MUNICIPALITY.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cap",
            "branch",
            "municipality",
            "municipality_norm",
            "province",
            "province_norm",
            "province_code",
            "region",
            "latitude",
            "longitude",
            "accuracy",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cap_branch_geo_rows)

    # Comune/Provincia → filiale
    grouped = defaultdict(lambda: {
        "caps": set(),
        "branches": set(),
        "municipality": "",
        "province": "",
        "province_code": "",
        "region": "",
    })

    for row in cap_branch_geo_rows:
        key = (row["municipality_norm"], row["province_norm"])

        grouped[key]["municipality"] = row["municipality"]
        grouped[key]["province"] = row["province"]
        grouped[key]["province_code"] = row["province_code"]
        grouped[key]["region"] = row["region"]
        grouped[key]["caps"].add(row["cap"])
        grouped[key]["branches"].add(row["branch"])

    municipality_rows = []
    issue_rows = []

    for (municipality_norm, province_norm), data in grouped.items():
        branches = sorted(data["branches"])
        caps = sorted(data["caps"])

        if len(branches) == 1:
            branch = branches[0]
            confidence = "alta"
            branch_candidates = branch
        else:
            branch = "AMBIGUA"
            confidence = "bassa"
            branch_candidates = " | ".join(branches)

            issue_rows.append({
                "municipality": data["municipality"],
                "province": data["province"],
                "region": data["region"],
                "caps": " | ".join(caps),
                "branch_candidates": branch_candidates,
                "issue": "Comune/CAP associato a più filiali",
            })

        municipality_rows.append({
            "municipality": data["municipality"],
            "municipality_norm": municipality_norm,
            "province": data["province"],
            "province_norm": province_norm,
            "province_code": data["province_code"],
            "region": data["region"],
            "branch": branch,
            "branch_candidates": branch_candidates,
            "confidence": confidence,
            "caps": " | ".join(caps),
        })

    municipality_rows.sort(key=lambda r: (r["region"], r["province"], r["municipality"]))

    with OUT_MUNICIPALITY_TO_BRANCH.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "municipality",
            "municipality_norm",
            "province",
            "province_norm",
            "province_code",
            "region",
            "branch",
            "branch_candidates",
            "confidence",
            "caps",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(municipality_rows)

    # Report CAP per filiale
    by_branch = defaultdict(int)

    for row in cap_branch_rows:
        by_branch[row["branch"]] += 1

    REPORT_CAP_BY_BRANCH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_CAP_BY_BRANCH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=["branch", "cap_count"])
        writer.writeheader()

        for branch, count in sorted(by_branch.items(), key=lambda x: x[1], reverse=True):
            writer.writerow({
                "branch": branch,
                "cap_count": count,
            })

    with REPORT_AMBIGUOUS.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["municipality", "province", "region", "caps", "branch_candidates", "issue"]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(issue_rows)

    with REPORT_UNRESOLVED.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["cap", "branch", "reason"]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unresolved_rows)

    print()
    print("Output generati:")
    print(f"- {OUT_CAP_TO_BRANCH}")
    print(f"- {OUT_CAP_TO_MUNICIPALITY}")
    print(f"- {OUT_CAP_BRANCH_MUNICIPALITY}")
    print(f"- {OUT_MUNICIPALITY_TO_BRANCH}")
    print(f"- {REPORT_CAP_BY_BRANCH}")
    print(f"- {REPORT_AMBIGUOUS}")
    print(f"- {REPORT_UNRESOLVED}")
    print()
    print(f"CAP risolti: {len(set(r['cap'] for r in cap_branch_geo_rows))}")
    print(f"CAP non risolti: {len(unresolved_rows)}")
    print(f"Comuni/province mappati: {len(municipality_rows)}")
    print(f"Comuni ambigui: {len(issue_rows)}")


if __name__ == "__main__":
    main()
