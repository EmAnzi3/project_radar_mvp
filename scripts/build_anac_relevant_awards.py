import csv
import re
from collections import defaultdict
from html import escape
from pathlib import Path
from datetime import datetime


INPUT = Path("reports/anac_operational_enriched_step2.csv")
OUT_CSV = Path("reports/anac_relevant_awards.csv")
OUT_HTML = Path("docs/anac_relevant_awards.html")
OUT_ANOMALIES_CSV = Path("reports/anac_awards_anomalies.csv")
OUT_ANOMALIES_HTML = Path("docs/anac_awards_anomalies.html")

MIN_AWARD_AMOUNT = 100_000
MIN_REASONABLE_RATIO = 0.005   # 0,5%
MAX_REASONABLE_RATIO = 1.50    # 150%


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


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


def money(value):
    n = to_float(value)
    if not n:
        return ""
    return f"{n:,.0f} €".replace(",", ".")


def pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return ""


def txt(value):
    return escape(clean(value))


def classify_award_weight(award_amount, project_value):
    if not project_value or not award_amount:
        return "Non valutabile"

    ratio = award_amount / project_value

    if ratio >= 0.50:
        return "Appalto principale / molto rilevante"
    if ratio >= 0.10:
        return "Lotto rilevante"
    if ratio >= 0.01:
        return "Lotto / servizio significativo"

    return "Affidamento minore"


def load_rows():
    if not INPUT.exists():
        raise SystemExit(f"File non trovato: {INPUT}")

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))




def award_ratio_status(award_amount, project_value):
    if not project_value or project_value <= 0:
        return "anomalia", "Valore progetto assente o non valutabile"

    ratio = award_amount / project_value

    if ratio > MAX_REASONABLE_RATIO:
        return "anomalia", "Importo aggiudicazione superiore al 150% del valore progetto"

    if ratio < MIN_REASONABLE_RATIO:
        return "anomalia", "Importo aggiudicazione inferiore allo 0,5% del valore progetto"

    return "ok", "Rapporto importo/valore coerente"



def html_escape(value):
    import html
    return html.escape(clean(value))


def write_awards_html(path, title, rows, input_count, shown_count, note, show_technical_columns=False):
    rows_html = []

    for r in rows[:shown_count]:
        rows_html.append(f"""
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
            <strong>{html_escape(r.get("contractors"))}</strong><br>
            <span class="small">{html_escape(r.get("contractor_tax_codes"))}</span>
          </td>
          {f'<td>{money(r.get("award_amount_eur"))}</td><td>{pct(r.get("award_share_pct"))}</td><td>{html_escape(r.get("award_weight"))}</td><td>{html_escape(r.get("ratio_note"))}</td>' if show_technical_columns else ''}
          <td>{html_escape(r.get("award_date"))}</td>
          <td>{html_escape(r.get("award_result"))}</td>
          <td><a href="{html_escape(r.get("source_url"))}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{html_escape(title)}</title>
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
      min-width: 2050px;
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
  <h1>{html_escape(title)}</h1>

  <div class="meta">
    <div class="pill">Input: {input_count}</div>
    <div class="pill">Record vista: {len(rows)}</div>
    <div class="pill">Mostrati: {min(len(rows), shown_count)}</div>
    <div class="pill">{html_escape(note)}</div>
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
          {('<th>Importo aggiud.</th><th>% su progetto</th><th>Peso affidamento</th><th>Nota rapporto</th>' if show_technical_columns else '')}
          <th>Data</th>
          <th>Esito</th>
          <th>Fonte</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main():
    rows = load_rows()
    print(f"Righe input: {len(rows)}")

    grouped = {}

    for row in rows:
        result = clean(row.get("award_result")).upper()
        award_amount = to_float(row.get("award_amount_eur"))

        if "AGGIUDICATA" not in result:
            continue

        if award_amount < MIN_AWARD_AMOUNT:
            continue

        cup = clean(row.get("cup"))
        cig = clean(row.get("cig"))

        if not cup or not cig:
            continue

        key = (cup, cig)

        if key not in grouped:
            project_value = to_float(row.get("value_eur"))
            ratio = award_amount / project_value if project_value else 0

            grouped[key] = {
                "cup": cup,
                "cig": cig,
                "title": clean(row.get("title")),
                "primary_segment": clean(row.get("primary_segment")),
                "category": clean(row.get("category")),
                "region": clean(row.get("region")),
                "province": clean(row.get("province")),
                "municipality": clean(row.get("municipality")),
                "value_eur": project_value,
                "client": clean(row.get("client")),
                "award_amount_eur": award_amount,
                "award_share_pct": ratio * 100,
                "award_weight": classify_award_weight(award_amount, project_value),
                "award_date": clean(row.get("award_date")),
                "award_result": clean(row.get("award_result")),
                "award_criteria": clean(row.get("award_criteria")),
                "award_discount": clean(row.get("award_discount")),
                "admitted_offers": clean(row.get("admitted_offers")),
                "bidders_count": clean(row.get("bidders_count")),
                "subcontracting": clean(row.get("subcontracting")),
                "included_services": clean(row.get("included_services")),
                "id_aggiudicazione": clean(row.get("id_aggiudicazione")),
                "source_url": clean(row.get("source_url")),
                "_contractors": {},
            }

        contractor_name = clean(row.get("contractor_name"))
        contractor_tax = clean(row.get("contractor_tax_code") or row.get("contractor_vat"))
        contractor_role = clean(row.get("contractor_role"))

        if contractor_name:
            ckey = (contractor_name, contractor_tax, contractor_role)
            grouped[key]["_contractors"][ckey] = {
                "name": contractor_name,
                "tax": contractor_tax,
                "role": contractor_role,
            }

    output = []

    for item in grouped.values():
        contractors = list(item.pop("_contractors").values())

        contractor_names = []
        contractor_ids = []

        for c in contractors:
            label = c["name"]
            if c["role"]:
                label += f" ({c['role']})"
            contractor_names.append(label)

            if c["tax"]:
                contractor_ids.append(c["tax"])

        item["contractors"] = " | ".join(contractor_names)
        item["contractor_tax_codes"] = " | ".join(sorted(set(contractor_ids)))

        output.append(item)

    # Split tra affidamenti coerenti e anomalie/multi-progetto.
    relevant = []
    anomalies = []

    for r in output:
        status, note = award_ratio_status(
            r["award_amount_eur"],
            r["value_eur"],
        )
        r["ratio_note"] = note

        if status == "ok":
            relevant.append(r)
        else:
            anomalies.append(r)

    relevant.sort(
        key=lambda r: (
            r["award_amount_eur"],
            r["award_share_pct"],
            r["value_eur"],
        ),
        reverse=True,
    )

    anomalies.sort(
        key=lambda r: (
            abs(r["award_share_pct"] - 100),
            r["award_amount_eur"],
        ),
        reverse=True,
    )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "primary_segment",
        "cup",
        "cig",
        "title",
        "category",
        "region",
        "province",
        "municipality",
        "value_eur",
        "client",
        "contractors",
        "contractor_tax_codes",
        "award_amount_eur",
        "award_share_pct",
        "award_weight",
        "ratio_note",
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
    ]

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(relevant)

    with OUT_ANOMALIES_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(anomalies)

    write_awards_html(
        OUT_HTML,
        "Project Radar MVP - ANAC relevant awards",
        relevant,
        input_count=len(rows),
        shown_count=500,
        note="Affidamenti filtrati e normalizzati per uso commerciale",
        show_technical_columns=False,
    )

    write_awards_html(
        OUT_ANOMALIES_HTML,
        "Project Radar MVP - ANAC award anomalies",
        anomalies,
        input_count=len(rows),
        shown_count=500,
        note="CIG multi-progetto, importi fuori scala o affidamenti troppo piccoli rispetto al progetto",
        show_technical_columns=True,
    )

    print(f"Righe input: {len(rows)}")
    print(f"Affidamenti rilevanti: {len(relevant)}")
    print(f"Anomalie / fuori range: {len(anomalies)}")
    print(f"CSV relevant: {OUT_CSV}")
    print(f"HTML relevant: {OUT_HTML}")
    print(f"CSV anomalie: {OUT_ANOMALIES_CSV}")
    print(f"HTML anomalie: {OUT_ANOMALIES_HTML}")


if __name__ == "__main__":
    main()
