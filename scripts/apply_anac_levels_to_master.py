import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(".")
MASTER = ROOT / "reports" / "master_projects.json"

CUP_CIG = ROOT / "reports" / "national_anac_cup_cig_matches.csv"
STEP2 = ROOT / "reports" / "national_anac_operational_enriched_step2.csv"
RELEVANT = ROOT / "reports" / "national_anac_relevant_awards.csv"
ANOMALIES = ROOT / "reports" / "national_anac_awards_anomalies.csv"

OUT_STATS = ROOT / "docs" / "data" / "anac_level_stats.json"

MIN_AWARD_AMOUNT = 100_000
MIN_REASONABLE_RATIO = 0.005
MAX_REASONABLE_RATIO = 1.50


def clean(value):
    return str(value or "").strip()


def norm(value):
    return clean(value).upper()


def to_float(value):
    text = clean(value)
    text = text.replace("€", "").replace("&euro;", "").replace(" ", "")

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def read_csv(path):
    if not path.exists():
        print(f"[WARN] File mancante: {path}")
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ratio_status(award_amount, project_value):
    if not project_value or project_value <= 0:
        return "review"

    ratio = award_amount / project_value

    if ratio < MIN_REASONABLE_RATIO:
        return "review"

    if ratio > MAX_REASONABLE_RATIO:
        return "review"

    return "ok"


def build_indexes():
    match_cigs = defaultdict(set)
    enriched_cigs = defaultdict(set)
    confirmed_awards = Counter()
    small_awards = Counter()
    review_awards = Counter()

    print("[1/4] Leggo CUP-CIG match...")
    for row in read_csv(CUP_CIG):
        cup = norm(row.get("cup"))
        cig = norm(row.get("cig"))

        if cup and cig:
            match_cigs[cup].add(cig)

    print(f"[OK] CUP con CIG ANAC: {len(match_cigs):,}")

    print("[2/4] Leggo enriched step2 per <100k / da verificare...")
    for row in read_csv(STEP2):
        cup = norm(row.get("cup"))
        cig = norm(row.get("cig"))

        if not cup or not cig:
            continue

        enriched_cigs[cup].add(cig)

        result = norm(row.get("award_result"))
        award_amount = to_float(row.get("award_amount_eur"))
        project_value = to_float(row.get("value_eur"))

        if "AGGIUDICATA" not in result:
            review_awards[cup] += 1
            continue

        if award_amount <= 0:
            review_awards[cup] += 1
            continue

        if award_amount < MIN_AWARD_AMOUNT:
            small_awards[cup] += 1
            continue

        if ratio_status(award_amount, project_value) != "ok":
            review_awards[cup] += 1
            continue

    print(f"[OK] CUP con dati ANAC enriched: {len(enriched_cigs):,}")
    print(f"[OK] CUP con affidamenti <100k: {len(small_awards):,}")
    print(f"[OK] CUP con dati ANAC da verificare: {len(review_awards):,}")

    print("[3/4] Leggo relevant awards confermati...")
    for row in read_csv(RELEVANT):
        cup = norm(row.get("cup"))

        if cup:
            confirmed_awards[cup] += 1

    print(f"[OK] CUP con aggiudicatario ANAC >=100k: {len(confirmed_awards):,}")

    print("[4/4] Leggo anomalies...")
    for row in read_csv(ANOMALIES):
        cup = norm(row.get("cup"))

        if cup:
            review_awards[cup] += 1

    print(f"[OK] CUP con ANAC da verificare totale: {len(review_awards):,}")

    return {
        "match_cigs": match_cigs,
        "enriched_cigs": enriched_cigs,
        "confirmed_awards": confirmed_awards,
        "small_awards": small_awards,
        "review_awards": review_awards,
    }


def classify_record(cup, indexes):
    match_count = len(indexes["match_cigs"].get(cup, set()))
    enriched_count = len(indexes["enriched_cigs"].get(cup, set()))
    confirmed_count = int(indexes["confirmed_awards"].get(cup, 0))
    small_count = int(indexes["small_awards"].get(cup, 0))
    review_count = int(indexes["review_awards"].get(cup, 0))

    if confirmed_count:
        level = "confirmed"
        label = "Aggiudicatario ANAC >=100k"
        detail = f"{confirmed_count} affidamento/i ANAC coerente/i con importo >=100k."
    elif small_count:
        level = "small"
        label = "Affidamento ANAC <100k"
        detail = f"{small_count} affidamento/i ANAC sotto soglia 100k."
    elif review_count or enriched_count:
        level = "review"
        label = "ANAC da verificare"
        detail = f"Dati ANAC presenti, ma non classificati come aggiudicatario confermato."
    elif match_count:
        level = "technical"
        label = "CIG ANAC collegato"
        detail = f"{match_count} CIG collegato/i al CUP nei dati ANAC."
    else:
        level = "none"
        label = "Nessun match ANAC"
        detail = ""

    return {
        "anac_level": level,
        "anac_level_label": label,
        "anac_level_detail": detail,
        "anac_match_cig_count": match_count,
        "anac_enriched_cig_count": enriched_count,
        "anac_confirmed_awards_count": confirmed_count,
        "anac_small_awards_count": small_count,
        "anac_review_awards_count": review_count,
    }


def pct(part, total):
    return round((part / total) * 100, 2) if total else 0.0


def main():
    if not MASTER.exists():
        raise SystemExit(f"Manca master: {MASTER}")

    indexes = build_indexes()

    records = json.loads(MASTER.read_text(encoding="utf-8"))

    if not isinstance(records, list):
        raise SystemExit("Formato master inatteso: attesa lista record.")

    level_counter = Counter()
    technical_total = 0
    enriched_total = 0
    confirmed_total = 0

    for record in records:
        cup = norm(record.get("cup"))
        data = classify_record(cup, indexes)

        record.update(data)

        level_counter[data["anac_level"]] += 1

        if data["anac_match_cig_count"] > 0:
            technical_total += 1

        if data["anac_enriched_cig_count"] > 0:
            enriched_total += 1

        if data["anac_confirmed_awards_count"] > 0:
            confirmed_total += 1

    MASTER.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(records)

    stats = {
        "total_records": total,
        "funnel": {
            "technical_match_projects": technical_total,
            "technical_match_pct": pct(technical_total, total),
            "enriched_projects": enriched_total,
            "enriched_pct": pct(enriched_total, total),
            "confirmed_projects": confirmed_total,
            "confirmed_pct": pct(confirmed_total, total),
        },
        "exclusive_levels": {
            level: {
                "count": count,
                "pct": pct(count, total),
            }
            for level, count in sorted(level_counter.items())
        },
        "labels": {
            "none": "Nessun match ANAC",
            "technical": "CIG ANAC collegato",
            "small": "Affidamento ANAC <100k",
            "review": "ANAC da verificare",
            "confirmed": "Aggiudicatario ANAC >=100k",
        },
    }

    OUT_STATS.parent.mkdir(parents=True, exist_ok=True)
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print("")
    print("[OK] Livelli ANAC applicati al master.")
    print(f"Master: {MASTER}")
    print(f"Stats: {OUT_STATS}")
    print("")
    print("Funnel progressivo:")
    print(f"CIG ANAC collegato: {technical_total:,} ({pct(technical_total, total)}%)")
    print(f"Dati ANAC con affidamento: {enriched_total:,} ({pct(enriched_total, total)}%)")
    print(f"Aggiudicatario ANAC >=100k: {confirmed_total:,} ({pct(confirmed_total, total)}%)")
    print("")
    print("Livelli esclusivi:")
    for level, count in level_counter.most_common():
        print(f"{level}: {count:,} ({pct(count, total)}%)")


if __name__ == "__main__":
    main()
