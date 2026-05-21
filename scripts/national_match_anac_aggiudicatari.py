import csv
import re
import zipfile
from pathlib import Path


CIG_TARGETS = Path("reports/national_anac_cig_targets.csv")
CUP_CIG_SUMMARY = Path("reports/national_anac_cup_cig_summary.csv")
AGGIUDICATARI_ZIP = Path("data/raw/anac/aggiudicatari.zip")

OUT = Path("reports/national_anac_cig_aggiudicatari_matches.csv")
OUT_ENRICHED = Path("reports/national_anac_operational_enriched_step1.csv")


def clean(value):
    return str(value or "").strip()


def norm_col(value):
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def detect_delimiter(sample: str) -> str:
    candidates = [";", ",", "|", "\t"]
    return max(candidates, key=lambda d: sample.count(d))


def load_cig_targets():
    if not CIG_TARGETS.exists():
        raise SystemExit(f"File CIG target non trovato: {CIG_TARGETS}")

    cigs = set()
    cig_to_cups = {}

    with CIG_TARGETS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cig = clean(row.get("cig"))
            if not cig:
                continue

            cigs.add(cig)
            cig_to_cups[cig] = clean(row.get("cups"))

    return cigs, cig_to_cups


def load_cup_summary():
    if not CUP_CIG_SUMMARY.exists():
        return {}

    out = {}

    with CUP_CIG_SUMMARY.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cup = clean(row.get("cup"))
            if cup:
                out[cup] = row

    return out


def find_col(fieldnames, candidates):
    if not fieldnames:
        return None

    normalized = {norm_col(name): name for name in fieldnames}

    for c in candidates:
        key = norm_col(c)
        if key in normalized:
            return normalized[key]

    # fallback: candidato contenuto nel nome colonna
    for raw_key, original in normalized.items():
        for c in candidates:
            key = norm_col(c)
            if key and key in raw_key:
                return original

    return None


def first_existing(row, cols):
    for col in cols:
        if col and clean(row.get(col)):
            return clean(row.get(col))
    return ""


def main():
    cigs, cig_to_cups = load_cig_targets()
    cup_summary = load_cup_summary()

    print(f"CIG target: {len(cigs):,}")

    if not AGGIUDICATARI_ZIP.exists():
        raise SystemExit(
            f"File non trovato: {AGGIUDICATARI_ZIP}\n"
            "Scarica il dataset ANAC Aggiudicatari CSV e salvalo come data/raw/anac/aggiudicatari.zip"
        )

    matches = []
    scanned = 0

    with zipfile.ZipFile(AGGIUDICATARI_ZIP) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]

        if not csv_names:
            raise SystemExit("Nessun CSV trovato nello ZIP aggiudicatari.")

        print(f"CSV nello ZIP: {csv_names}")

        for csv_name in csv_names:
            print(f"Leggo: {csv_name}")

            with z.open(csv_name) as raw:
                sample = raw.read(8192).decode("utf-8-sig", errors="ignore")
                delimiter = detect_delimiter(sample)

            with z.open(csv_name) as raw:
                wrapper = (line.decode("utf-8-sig", errors="ignore") for line in raw)
                reader = csv.DictReader(wrapper, delimiter=delimiter)

                print("Campi:", reader.fieldnames)

                cig_col = find_col(reader.fieldnames, [
                    "CIG",
                    "codice_cig",
                    "codice identificativo gara",
                ])

                denom_col = find_col(reader.fieldnames, [
                    "denominazione",
                    "denominazione aggiudicatario",
                    "ragione sociale",
                    "ragione_sociale",
                    "operatore economico",
                    "aggiudicatario",
                    "denominazione operatore economico",
                ])

                cf_col = find_col(reader.fieldnames, [
                    "codice fiscale",
                    "codice_fiscale",
                    "cf",
                    "codice fiscale aggiudicatario",
                    "codice fiscale operatore economico",
                    "codice fiscale oe",
                    "codicefiscale",
                ])

                piva_col = find_col(reader.fieldnames, [
                    "partita iva",
                    "partita_iva",
                    "piva",
                    "p.iva",
                    "partita iva aggiudicatario",
                    "partita iva operatore economico",
                    "partitaiva",
                ])

                role_col = find_col(reader.fieldnames, [
                    "ruolo",
                    "ruolo operatore",
                    "tipo ruolo",
                    "tipo soggetto",
                ])

                if not cig_col:
                    raise SystemExit("Colonna CIG non trovata nel dataset aggiudicatari.")

                print(f"Colonna CIG: {cig_col}")
                print(f"Colonna denominazione: {denom_col}")
                print(f"Colonna CF: {cf_col}")
                print(f"Colonna PIVA: {piva_col}")
                print(f"Colonna ruolo: {role_col}")

                for row in reader:
                    scanned += 1

                    if scanned % 500_000 == 0:
                        print(f"Righe lette: {scanned:,} | match: {len(matches):,}")

                    cig = clean(row.get(cig_col))
                    if cig not in cigs:
                        continue

                    matches.append({
                        "cig": cig,
                        "cups": cig_to_cups.get(cig, ""),
                        "contractor_name": first_existing(row, [denom_col]),
                        "contractor_tax_code": first_existing(row, [cf_col]),
                        "contractor_vat": first_existing(row, [piva_col]),
                        "contractor_role": first_existing(row, [role_col]),
                        "source_dataset": csv_name,
                    })

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cig",
            "cups",
            "contractor_name",
            "contractor_tax_code",
            "contractor_vat",
            "contractor_role",
            "source_dataset",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    # Join leggero: ogni match CIG→aggiudicatario viene collegato ai CUP e ai metadati OpenCUP.
    enriched_rows = []

    for m in matches:
        cups = [x.strip() for x in clean(m.get("cups")).split("|") if x.strip()]

        if not cups:
            enriched_rows.append({
                **m,
                "cup": "",
                "operational_score": "",
                "primary_segment": "",
                "title": "",
                "category": "",
                "region": "",
                "province": "",
                "municipality": "",
                "value_eur": "",
                "client": "",
                "source_url": "",
            })
            continue

        for cup in cups:
            meta = cup_summary.get(cup, {})
            enriched_rows.append({
                **m,
                "cup": cup,
                "operational_score": clean(meta.get("operational_score")),
                "primary_segment": clean(meta.get("primary_segment")),
                "title": clean(meta.get("title")),
                "category": clean(meta.get("category")),
                "region": clean(meta.get("region")),
                "province": clean(meta.get("province")),
                "municipality": clean(meta.get("municipality")),
                "value_eur": clean(meta.get("value_eur")),
                "client": clean(meta.get("client")),
                "source_url": clean(meta.get("source_url")),
            })

    with OUT_ENRICHED.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "cup",
            "cups",
            "cig",
            "contractor_name",
            "contractor_tax_code",
            "contractor_vat",
            "contractor_role",
            "operational_score",
            "primary_segment",
            "title",
            "category",
            "region",
            "province",
            "municipality",
            "value_eur",
            "client",
            "source_url",
            "source_dataset",
        ]
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    unique_contractors = {
        (
            clean(m.get("contractor_name")),
            clean(m.get("contractor_tax_code")),
            clean(m.get("contractor_vat")),
        )
        for m in matches
        if clean(m.get("contractor_name"))
    }

    print(f"Righe lette: {scanned:,}")
    print(f"Match CIG→aggiudicatario trovati: {len(matches):,}")
    print(f"Aggiudicatari unici stimati: {len(unique_contractors):,}")
    print(f"Output match: {OUT}")
    print(f"Output enriched: {OUT_ENRICHED}")


if __name__ == "__main__":
    main()
