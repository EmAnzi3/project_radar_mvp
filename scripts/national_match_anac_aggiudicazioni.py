import csv
import zipfile
from pathlib import Path
from datetime import datetime


STEP1 = Path("reports/national_anac_operational_enriched_step1.csv")
AGGIUDICAZIONI_ZIP = Path("data/raw/anac/aggiudicazioni.zip")

OUT = Path("reports/national_anac_operational_enriched_step2.csv")
OUT_HTML = Path("docs/national_anac_enriched.html")


def clean(value):
    return str(value or "").strip()


def to_float(value):
    text = clean(value).replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def parse_date(value):
    value = clean(value)
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def detect_delimiter(sample: str) -> str:
    candidates = [";", ",", "|", "\t"]
    return max(candidates, key=lambda d: sample.count(d))


def load_step1():
    if not STEP1.exists():
        raise SystemExit(f"File non trovato: {STEP1}")

    rows = []
    cigs = set()

    with STEP1.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cig = clean(row.get("cig"))
            if not cig:
                continue

            rows.append(row)
            cigs.add(cig)

    return rows, cigs


def score_aggiudicazione(row):
    """
    Sceglie il record migliore se lo stesso CIG compare più volte.
    Priorità:
    - esito AGGIUDICATA / cod_esito 1
    - importo > 0
    - data più recente
    """
    score = 0

    esito = clean(row.get("esito")).upper()
    cod_esito = clean(row.get("cod_esito"))
    importo = to_float(row.get("importo_aggiudicazione"))
    data = parse_date(row.get("data_aggiudicazione_definitiva"))

    if "AGGIUDICATA" in esito:
        score += 100
    if cod_esito == "1":
        score += 100
    if importo > 0:
        score += 30

    if data:
        score += data.year

    return score


def load_aggiudicazioni(cigs):
    if not AGGIUDICAZIONI_ZIP.exists():
        raise SystemExit(
            f"File non trovato: {AGGIUDICAZIONI_ZIP}\n"
            "Scarica il dataset ANAC aggiudicazioni e salvalo come data/raw/anac/aggiudicazioni.zip"
        )

    best_by_cig = {}
    all_matches = 0
    scanned = 0

    with zipfile.ZipFile(AGGIUDICAZIONI_ZIP) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]

        if not csv_names:
            raise SystemExit("Nessun CSV trovato nello ZIP aggiudicazioni.")

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

                for row in reader:
                    scanned += 1

                    if scanned % 500_000 == 0:
                        print(f"Righe lette: {scanned:,} | CIG aggiudicazione trovati: {len(best_by_cig):,}")

                    cig = clean(row.get("cig"))
                    if cig not in cigs:
                        continue

                    all_matches += 1

                    current = best_by_cig.get(cig)
                    if current is None:
                        best_by_cig[cig] = row
                    else:
                        if score_aggiudicazione(row) > score_aggiudicazione(current):
                            best_by_cig[cig] = row

    print(f"Righe lette: {scanned:,}")
    print(f"Match aggiudicazioni grezzi: {all_matches:,}")
    print(f"CIG con dati aggiudicazione: {len(best_by_cig):,}")

    return best_by_cig


def html_escape(value):
    import html
    return html.escape(clean(value))


def money(value):
    n = to_float(value)
    if not n:
        return ""
    return f"{n:,.0f} €".replace(",", ".")


def main():
    step1_rows, target_cigs = load_step1()
    print(f"Righe step1: {len(step1_rows):,}")
    print(f"CIG target: {len(target_cigs):,}")

    aggiudicazioni = load_aggiudicazioni(target_cigs)

    enriched = []

    for row in step1_rows:
        cig = clean(row.get("cig"))
        agg = aggiudicazioni.get(cig, {})

        enriched.append({
            **row,
            "award_date": clean(agg.get("data_aggiudicazione_definitiva")),
            "award_result": clean(agg.get("esito")),
            "award_result_code": clean(agg.get("cod_esito")),
            "award_criteria": clean(agg.get("criterio_aggiudicazione")),
            "award_notice_date": clean(agg.get("data_comunicazione_esito")),
            "award_amount_eur": clean(agg.get("importo_aggiudicazione")),
            "award_discount": clean(agg.get("ribasso_aggiudicazione")),
            "admitted_offers": clean(agg.get("numero_offerte_ammesse")),
            "excluded_offers": clean(agg.get("numero_offerte_escluse")),
            "bidders_count": clean(agg.get("num_imprese_offerenti")),
            "subcontracting": clean(agg.get("flag_subappalto")),
            "id_aggiudicazione": clean(agg.get("id_aggiudicazione")),
            "included_services": clean(agg.get("PRESTAZIONI_COMPRESE")),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "cup",
        "cups",
        "cig",
        "title",
        "primary_segment",
        "category",
        "region",
        "province",
        "municipality",
        "value_eur",
        "client",
        "contractor_name",
        "contractor_tax_code",
        "contractor_vat",
        "contractor_role",
        "award_amount_eur",
        "award_date",
        "award_result",
        "award_criteria",
        "award_discount",
        "admitted_offers",
        "bidders_count",
        "subcontracting",
        "included_services",
        "id_aggiudicazione",
        "source_url",
        "source_dataset",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched)

    print(f"Output: {OUT}")
    print(f"Righe arricchite: {len(enriched):,}")

    # HTML leggero, primi 500 con importo o esito aggiudicazione
    html_rows = []
    display = [
        r for r in enriched
        if clean(r.get("award_result")) or clean(r.get("award_amount_eur"))
    ][:500]

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    for r in display:
        html_rows.append(f"""
        <tr>
          <td>{html_escape(r.get("primary_segment"))}</td>
          <td>
            <strong>{html_escape(r.get("title"))}</strong><br>
            <span class="small">CUP: {html_escape(r.get("cup"))} | CIG: {html_escape(r.get("cig"))}</span>
          </td>
          <td>{html_escape(r.get("municipality"))}</td>
          <td>{html_escape(r.get("province"))}</td>
          <td>{money(r.get("value_eur"))}</td>
          <td>{html_escape(r.get("client"))}</td>
          <td>
            <strong>{html_escape(r.get("contractor_name"))}</strong><br>
            <span class="small">{html_escape(r.get("contractor_tax_code") or r.get("contractor_vat"))}</span><br>
            <span class="small">{html_escape(r.get("contractor_role"))}</span>
          </td>
          <td>{money(r.get("award_amount_eur"))}</td>
          <td>{html_escape(r.get("award_date"))}</td>
          <td>{html_escape(r.get("award_result"))}</td>
          <td><a href="{html_escape(r.get("source_url"))}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - National ANAC enriched</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      background: #f6f7f9;
      color: #1f2933;
    }}
    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin: 18px 0;
    }}
    .pill {{
      background: white;
      padding: 8px 10px;
      border: 1px solid #e5e7eb;
      border-radius: 999px;
    }}
    .wrap {{
      overflow-x: auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,.08);
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 1700px;
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
    }}
    .small {{
      color: #6b7280;
      font-size: 12px;
    }}
    a {{
      color: #0f766e;
      font-weight: bold;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <h1>Project Radar MVP - National ANAC enriched</h1>
  <div class="meta">
    <div class="pill">Righe step1: {len(step1_rows)}</div>
    <div class="pill">CIG con aggiudicazione: {len(aggiudicazioni)}</div>
    <div class="pill">Righe mostrate: {len(display)}</div>
  </div>
  <div class="wrap">
    <table>
      <thead>
        <tr>
          <th>Segmento</th>
          <th>Progetto</th>
          <th>Comune</th>
          <th>Prov.</th>
          <th>Valore progetto</th>
          <th>Committente</th>
          <th>Aggiudicatario / OE</th>
          <th>Importo aggiud.</th>
          <th>Data</th>
          <th>Esito</th>
          <th>Fonte</th>
        </tr>
      </thead>
      <tbody>
        {''.join(html_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML: {OUT_HTML}")


if __name__ == "__main__":
    main()
