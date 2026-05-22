import csv
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path

REPORTS_DIR = Path("reports")
DOCS_DIR = Path("docs")

INPUT_FILES = [
    REPORTS_DIR / "all_relevant_200k.csv",
]

OUT_CSV = REPORTS_DIR / "operational_shortlist.csv"
OUT_SEGMENTS = REPORTS_DIR / "operational_by_segment.csv"
OUT_JSON = DOCS_DIR / "operational_data.json"
OUT_HTML = DOCS_DIR / "operational.html"

SEGMENT_WEIGHTS = {
    "Edilizia": 30,
    "Completamento e finitura edifici": 25,
    "Impiantisti sottoservizi": 25,
    "Lavori pubblici strade": 24,
    "Industria": 18,
    "Demolizioni": 16,
    "Verde": 12,
    "Agricoltura / silvicoltura": 10,
    "Impiantisti": 10,
    "Bonifiche e gestione rifiuti": 8,
    "Altro": -10,
}


def clean(v):
    if v is None:
        return ""

    text = str(v)

    # Normalizzazioni sicure: niente replace su chiavi vuote.
    replacements = [
        ("\u2018", "'"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2013", "-"),
        ("\u2014", "-"),
        ("\u00a0", " "),
        ("\ufffd", "'"),
    ]

    for bad, good in replacements:
        if bad:
            text = text.replace(bad, good)

    return re.sub(r"\s+", " ", text).strip()


def norm(v):
    return clean(v).lower()

def to_float(v):
    if v is None:
        return 0.0
    text = str(v).replace("€", "").replace("&euro;", "").replace(" ", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return 0.0

def has(text, words):
    return any(w in text for w in words)

def row_text(row):
    return " ".join(
        norm(row.get(k))
        for k in ["title", "category", "client", "municipality", "province", "region"]
        if row.get(k)
    )

def assign_segment(row):
    text = row_text(row)
    category = norm(row.get("category"))
    matches = set()

    if has(text, ["demolizione", "demolizioni", "abbattimento"]):
        matches.add("Demolizioni")

    if has(text, ["fognatura", "acquedotto", "rete idrica", "acque reflue", "depurazione", "depuratore", "sottoservizi", "cavidotto", "condotta"]):
        matches.add("Impiantisti sottoservizi")

    if has(text, ["strada", "strade", "viabilita", "viabilità", "pavimentazione stradale", "rotatoria", "marciapiede", "ponte", "pista ciclabile", "illuminazione pubblica"]):
        matches.add("Lavori pubblici strade")

    if has(text, ["verde", "parco", "giardino", "giardini", "arredo urbano", "area verde", "verde pubblico"]):
        matches.add("Verde")

    if has(text, ["bonifica", "rifiuti", "discarica", "trattamento rifiuti", "amianto"]):
        matches.add("Bonifiche e gestione rifiuti")

    if has(text, ["capannone", "magazzino", "logistica", "area produttiva", "zona industriale", "stabilimento", "stoccaggio"]):
        matches.add("Industria")

    if has(text, ["impianto elettrico", "impianti elettrici", "impianto termico", "climatizzazione", "fotovoltaico", "efficientamento energetico", "centrale termica", "illuminazione", "antincendio", "impiantistico"]):
        matches.add("Impiantisti")

    if has(text, ["copertura", "tetto", "infissi", "serramenti", "facciata", "facciate", "rivestimenti", "finiture", "pavimentazione interna", "impermeabilizzazione", "completamento"]):
        matches.add("Completamento e finitura edifici")

    if has(text, ["scuola", "scolastico", "asilo", "nido", "ospedale", "casa della comunita", "casa della comunità", "rsa", "edificio", "fabbricato", "immobile", "palestra", "spogliatoi", "auditorium", "teatro", "biblioteca", "centro civico", "centro culturale", "alloggi", "municipio", "sede comunale"]):
        matches.add("Edilizia")

    if has(text, ["agricoltura", "agricolo", "irriguo", "irrigazione", "rurale", "forestazione", "silvicoltura"]):
        matches.add("Agricoltura / silvicoltura")

    if "infrastrutture / parcheggi" in category:
        matches.add("Lavori pubblici strade")
    if "ambiente / rifiuti / depurazione" in category:
        matches.add("Impiantisti sottoservizi")
    if "industriale / logistica" in category:
        matches.add("Industria")
    if category in {"scuole / formazione", "sanità / rsa", "sport / impianti sportivi", "cultura / centri civici", "edilizia pubblica", "residenziale pubblico / ers"}:
        matches.add("Edilizia")

    # Fallback da categoria progetto: se OpenCUP classifica una riqualificazione urbana,
    # per Alayan ? normalmente area Edilizia / interventi su patrimonio urbano.
    if "riqualificazione urbana" in category:
        matches.add("Edilizia")

    if "edilizia pubblica" in category:
        matches.add("Edilizia")

    if "cultura / centri civici" in category:
        matches.add("Edilizia")

    if "sanit? / rsa" in category:
        matches.add("Edilizia")

    if "sport / impianti sportivi" in category:
        matches.add("Edilizia")

    if "scuole / formazione" in category:
        matches.add("Edilizia")

    if "residenziale pubblico / ers" in category:
        matches.add("Edilizia")

    if not matches:
        matches.add("Altro")

    ordered = sorted(matches, key=lambda x: SEGMENT_WEIGHTS.get(x, -10), reverse=True)
    return ordered[0], ordered

def is_macro(row):
    value = to_float(row.get("value_eur"))
    text = row_text(row)
    macro_terms = ["autostrada", "autostradale", "ferrovia", "ferroviario", "alta velocità", "alta velocita", "concessione", "raccordo autostradale", "collegamento autostradale", "corridoio", "hvdc", "terna", "metropolitana"]
    return value >= 100_000_000 and has(text, macro_terms)

def is_local_client(client):
    c = clean(client).upper()
    markers = ["COMUNE", "PROVINCIA", "CITTA' METROPOLITANA", "CITTÀ METROPOLITANA", "REGIONE", "AZIENDA USL", "ASL", "AZIENDA OSPEDALIERA", "UNIONE DEI COMUNI"]
    return any(m in c for m in markers)

def value_band(value):
    if value >= 100_000_000: return ">= 100M"
    if value >= 50_000_000: return "50M - 100M"
    if value >= 20_000_000: return "20M - 50M"
    if value >= 5_000_000: return "5M - 20M"
    if value >= 1_000_000: return "1M - 5M"
    if value >= 500_000: return "500k - 1M"
    if value >= 200_000: return "200k - 500k"
    return "< 200k"

def value_score(value):
    if value >= 500_000_000: return -20
    if value >= 100_000_000: return -10
    if value >= 50_000_000: return 8
    if value >= 20_000_000: return 20
    if value >= 5_000_000: return 30
    if value >= 1_000_000: return 28
    if value >= 500_000: return 18
    if value >= 200_000: return 10
    return -30

def operational_score(row):
    value = to_float(row.get("value_eur"))
    segment, tags = assign_segment(row)
    score = SEGMENT_WEIGHTS.get(segment, -10) + value_score(value)

    client = clean(row.get("client")).upper()
    if is_local_client(client):
        if client.startswith("COMUNE"):
            score += 15
        elif "PROVINCIA" in client or "CITTA" in client or "CITTÀ" in client:
            score += 12
        elif "REGIONE" in client:
            score += 10
        elif "AZIENDA USL" in client or "ASL" in client or "AZIENDA OSPEDALIERA" in client:
            score += 10
        else:
            score += 8

    municipality = clean(row.get("municipality")).upper()
    if municipality and municipality not in {"TUTTI", "TUTTE", "VARI", "DIVERSI"}:
        score += 10
    else:
        score -= 12

    if clean(row.get("category")) == "Altro":
        score -= 10

    if is_macro(row):
        score -= 25

    if row.get("cup"):
        score += 2
    if row.get("source_url"):
        score += 2

    return max(0, min(100, score)), segment, tags

def read_csv(path):
    if not path.exists():
        print(f"[WARN] File non trovato: {path}")
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    print(f"[OK] {path}: {len(rows)} righe")
    return rows

def money(v):
    return f"{float(v):,.0f} €".replace(",", ".")

def txt(v):
    return escape(str(v or ""))

def main():
    rows = []
    for path in INPUT_FILES:
        rows.extend(read_csv(path))

    if not rows:
        raise SystemExit("ERRORE: nessun record letto.")

    by_key = {}
    for row in rows:
        key = clean(row.get("cup")) or clean(row.get("source_url")) or clean(row.get("title"))
        if not key:
            continue
        if key not in by_key or to_float(row.get("value_eur")) > to_float(by_key[key].get("value_eur")):
            by_key[key] = row

    deduped = list(by_key.values())
    enriched = []

    for row in deduped:
        status = clean(row.get("status")).upper()
        phase = clean(row.get("phase")).upper()

        # Vista operativa = solo opportunit? potenzialmente vive.
        # I progetti chiusi restano nei report generali, ma non nella shortlist commerciale.
        if (
            "CHIUSO" in status
            or "CHIUSO" in phase
            or "REVOCATO" in status
            or "REVOCATO" in phase
            or "CANCELLATO" in status
            or "CANCELLATO" in phase
            or "ANNULLATO" in status
            or "ANNULLATO" in phase
        ):
            continue

        score, segment, tags = operational_score(row)
        if is_macro(row):
            continue
        if score < 45:
            continue

        row = dict(row)
        row["operational_score"] = score
        row["primary_segment"] = segment
        row["segment_tags"] = " | ".join(tags)
        row["value_band"] = value_band(to_float(row.get("value_eur")))
        enriched.append(row)

    enriched.sort(key=lambda r: (int(r["operational_score"]), to_float(r.get("value_eur"))), reverse=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    fields = ["operational_score", "primary_segment", "segment_tags", "value_band", "score", "cup", "title", "category", "region", "province", "municipality", "phase", "status", "value_eur", "client", "source_url"]

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fields)
        writer.writeheader()
        for row in enriched:
            writer.writerow({k: row.get(k, "") for k in fields})

    by_segment = defaultdict(lambda: {"count": 0, "total": 0.0, "score": 0.0})
    for row in enriched:
        seg = row["primary_segment"]
        by_segment[seg]["count"] += 1
        by_segment[seg]["total"] += to_float(row.get("value_eur"))
        by_segment[seg]["score"] += int(row["operational_score"])

    with OUT_SEGMENTS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=["primary_segment", "count", "total_value_eur", "avg_score"])
        writer.writeheader()
        for seg, data in sorted(by_segment.items(), key=lambda x: x[1]["count"], reverse=True):
            count = data["count"] or 1
            writer.writerow({
                "primary_segment": seg,
                "count": data["count"],
                "total_value_eur": round(data["total"], 2),
                "avg_score": round(data["score"] / count, 2),
            })

    dashboard = enriched[:250]
    OUT_JSON.write_text(json.dumps({
        "source": "OpenCUP derived reports",
        "view": "operational",
        "input_rows": len(rows),
        "deduped_rows": len(deduped),
        "operational_candidates": len(enriched),
        "dashboard_count": len(dashboard),
        "records": dashboard,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    trs = []
    for r in dashboard:
        value = to_float(r.get("value_eur"))
        trs.append(f"""
        <tr>
          <td class="score">{txt(r.get("operational_score"))}</td>
          <td><strong>{txt(clean(r.get("title")))}</strong><div class="desc">Score OpenCUP: {txt(clean(r.get("score")))}</div></td>
          <td>{txt(r.get("primary_segment"))}</td>
          <td>{txt(r.get("category"))}</td>
          <td>{txt(r.get("region"))}</td>
          <td>{txt(r.get("province"))}</td>
          <td>{txt(r.get("municipality"))}</td>
          <td>{txt(r.get("phase"))}</td>
          <td>{txt(r.get("status"))}</td>
          <td>{txt(r.get("value_band"))}</td>
          <td>{money(value)}</td>
          <td>{txt(r.get("client"))}</td>
          <td>{txt(r.get("cup"))}</td>
          <td><a href="{txt(r.get("source_url"))}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - Vista operativa</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #1f2933; }}
    h1 {{ margin-bottom: 4px; }}
    .subtitle {{ color: #617083; margin-bottom: 16px; }}
    .meta {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; color: #4b5563; font-size: 14px; }}
    .pill {{ background: white; border: 1px solid #e5e7eb; padding: 8px 10px; border-radius: 999px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    .table-wrap {{ overflow-x: auto; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-radius: 12px; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 1700px; background: white; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ background: #111827; color: white; position: sticky; top: 0; z-index: 1; }}
    tr:hover {{ background: #f3f4f6; }}
    .score {{ font-weight: bold; font-size: 18px; }}
    .desc {{ color: #4b5563; font-size: 12px; margin-top: 5px; max-width: 520px; max-height: 62px; overflow: hidden; }}
    a {{ color: #0f766e; font-weight: bold; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>Project Radar MVP - Vista operativa</h1>
  <div class="subtitle">Shortlist commerciale derivata dai report OpenCUP e dai segmenti Alayan</div>
  <div class="meta">
    <div class="pill">Input rows: {len(rows)}</div>
    <div class="pill">Deduplicati: {len(deduped)}</div>
    <div class="pill">Candidati operativi: {len(enriched)}</div>
    <div class="pill">Record mostrati: {len(dashboard)}</div>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Score operativo</th><th>Progetto</th><th>Segmento Alayan</th><th>Categoria progetto</th>
          <th>Regione</th><th>Prov.</th><th>Comune</th><th>Fase</th><th>Stato</th><th>Fascia valore</th><th>Valore</th>
          <th>Committente</th><th>CUP</th><th>Fonte</th>
        </tr>
      </thead>
      <tbody>{''.join(trs)}</tbody>
    </table>
  </div>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"Input rows: {len(rows)}")
    print(f"Deduplicati: {len(deduped)}")
    print(f"Candidati operativi: {len(enriched)}")
    print(f"CSV: {OUT_CSV}")
    print(f"HTML: {OUT_HTML}")
    print(f"JSON: {OUT_JSON}")
    print(f"Segmenti: {OUT_SEGMENTS}")

if __name__ == "__main__":
    main()
