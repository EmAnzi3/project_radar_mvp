import csv
import html
import re
from pathlib import Path


BRANCH_MAP = Path("config/municipality_to_branch.csv")

PAGES = [
    {
        "input": Path("reports/national_anac_relevant_awards.csv"),
        "output": Path("docs/national_anac_relevant_awards.html"),
        "title": "Project Radar MVP - ANAC nazionale - Affidamenti rilevanti",
        "subtitle": "Affidamenti ANAC nazionali filtrati per uso commerciale.",
        "limit": 500,
    },
    {
        "input": Path("reports/national_anac_awards_anomalies.csv"),
        "output": Path("docs/national_anac_awards_anomalies.html"),
        "title": "Project Radar MVP - ANAC nazionale - Anomalie",
        "subtitle": "Casi anomali separati dalla vista principale.",
        "limit": 500,
    },
    {
        "input": Path("reports/national_anac_operational_enriched_step2.csv"),
        "output": Path("docs/national_anac_enriched.html"),
        "title": "Project Radar MVP - ANAC nazionale - Arricchimento",
        "subtitle": "Vista tecnica di controllo su CUP, CIG, aggiudicatari e aggiudicazioni.",
        "limit": 500,
    },
]


REPLACEMENTS = {
    "\ufeff": "",
    "\u00a0": " ",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "": "'",
    "": '"',
    "": '"',
    "": "-",
    "": "-",
    "Ã¨": "è",
    "Ã©": "é",
    "Ã ": "à",
    "Ã²": "ò",
    "Ã¹": "ù",
    "Ã¬": "ì",
}


def clean(value):
    text = "" if value is None else str(value)

    for old, new in REPLACEMENTS.items():
        # Guardia fondamentale: mai fare replace su stringa vuota.
        if old:
            text = text.replace(old, new)

    return re.sub(r"\s+", " ", text).strip()


def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def esc(value):
    return html.escape(clean(value), quote=True)


def get(row, *names):
    for name in names:
        value = clean(row.get(name, ""))
        if value:
            return value
    return ""


def to_float(value):
    text = clean(value)
    text = text.replace("€", "").replace(" ", "")

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return 0.0


def euro(value):
    num = to_float(value)
    if not num:
        return ""
    return f"{num:,.0f}".replace(",", ".") + " €"


def display_branch(value):
    branch = clean(value)
    if branch.upper() == "SALERNO":
        return "Salerno"
    if branch == "Roma Aurealia":
        return "Roma Aurelia"
    return branch


def load_branch_map():
    mapping = {}

    if not BRANCH_MAP.exists():
        return mapping

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            municipality = clean(row.get("municipality"))
            province = clean(row.get("province"))
            municipality_norm = clean(row.get("municipality_norm")) or norm(municipality)
            province_norm = clean(row.get("province_norm")) or norm(province)

            if not municipality_norm or not province_norm:
                continue

            branch = display_branch(row.get("branch"))
            candidates = clean(row.get("branch_candidates"))

            if candidates:
                candidates = " | ".join(
                    display_branch(x.strip())
                    for x in candidates.split("|")
                    if x.strip()
                )

            mapping[(municipality_norm, province_norm)] = {
                "branch": branch,
                "branch_candidates": candidates,
            }

    return mapping


def assign_branch(row, branch_map):
    municipality = get(row, "municipality", "comune")
    province = get(row, "province", "provincia", "prov")

    match = branch_map.get((norm(municipality), norm(province)))

    if not match:
        return "NON ASSEGNATA", ""

    return clean(match.get("branch")), clean(match.get("branch_candidates"))


def branch_cell(branch, candidates):
    if branch == "AMBIGUA":
        return f'<span class="warn">AMBIGUA</span><div class="small">{esc(candidates)}</div>'

    if not branch or branch == "NON ASSEGNATA":
        return '<span class="warn">NON ASSEGNATA</span>'

    return esc(branch)


def split_pipe(value):
    return [clean(x) for x in clean(value).split("|") if clean(x)]


def contractors_cell(row):
    names_value = get(row, "contractors", "contractor_name", "contractor", "aggiudicatario")
    tax_value = get(row, "contractor_tax_codes", "contractor_tax_code", "tax_codes", "cf_piva")
    role_value = get(row, "contractor_role")

    names = split_pipe(names_value)
    taxes = split_pipe(tax_value)

    if not names:
        return ""

    parts = []

    for i, name in enumerate(names):
        tax = taxes[i] if i < len(taxes) else ""

        detail = tax
        if role_value and len(names) == 1:
            detail = f"{detail} - {role_value}" if detail else role_value

        parts.append(
            '<div class="oe-line">'
            f'<div class="oe-name">{esc(name)}</div>'
            + (f'<div class="oe-tax">{esc(detail)}</div>' if detail else "")
            + '</div>'
        )

    return "\n".join(parts)


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def build_html(page, rows, branch_map):
    rendered_rows = []

    for row in rows[:page["limit"]]:
        branch, candidates = assign_branch(row, branch_map)

        title = get(row, "title", "project_title", "progetto")
        cup = get(row, "cup", "CUP")
        cig = get(row, "cig", "CIG")
        segment = get(row, "primary_segment", "segment", "segmento")
        region = get(row, "region", "regione")
        province = get(row, "province", "provincia", "prov")
        municipality = get(row, "municipality", "comune")
        value = get(row, "value_eur", "project_value", "project_value_eur", "valore_progetto")
        client = get(row, "client", "committente")
        award_date = get(row, "award_date", "data_aggiudicazione", "data_aggiudicazione_definitiva")
        award_result = get(row, "award_result", "esito")
        source_url = get(row, "source_url", "url")

        rendered_rows.append(f"""
        <tr>
          <td>
            <strong>{esc(title)}</strong>
            <div class="small">CUP: {esc(cup)} - CIG: {esc(cig)}</div>
          </td>
          <td>{branch_cell(branch, candidates)}</td>
          <td>{esc(segment)}</td>
          <td>{esc(region)}</td>
          <td>{esc(province)}</td>
          <td>{esc(municipality)}</td>
          <td class="money">{euro(value)}</td>
          <td>{esc(client)}</td>
          <td class="contractors-col">{contractors_cell(row)}</td>
          <td class="award-col">
            {esc(award_date)}
            <div class="small">{esc(award_result)}</div>
          </td>
          <td class="source-col">
            <a href="{esc(source_url)}" target="_blank">Fonte</a>
          </td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{esc(page["title"])}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --bg: #f6f7f9;
      --text: #1f2933;
      --muted: #617083;
      --border: #e5e7eb;
      --dark: #111827;
      --accent: #0f766e;
    }}

    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      background: var(--bg);
      color: var(--text);
    }}

    header {{
      background: var(--dark);
      color: white;
      padding: 24px 30px;
    }}

    header h1 {{
      margin: 0 0 6px 0;
      font-size: 26px;
    }}

    header p {{
      margin: 0;
      color: #d1d5db;
      font-size: 14px;
    }}

    main {{
      padding: 18px 20px 22px 20px;
    }}

    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 14px;
    }}

    .pill {{
      background: white;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 8px 10px;
    }}

    .table-wrap {{
      overflow-y: auto;
      overflow-x: hidden;
      background: white;
      border-radius: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      max-height: calc(100vh - 195px);
      min-height: 420px;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 0;
      table-layout: fixed;
      background: white;
    }}

    th, td {{
      padding: 5px 5px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      font-size: 10.4px;
      line-height: 1.22;
    }}

    th {{
      background: var(--dark);
      color: white;
      position: sticky;
      top: 0;
      z-index: 5;
      white-space: normal;
      overflow-wrap: normal;
      word-break: normal;
      line-height: 1.15;
    }}

    td {{
      overflow-wrap: anywhere;
    }}

    tr:hover {{
      background: #f3f4f6;
    }}

    .small {{
      color: var(--muted);
      font-size: 10.5px;
      line-height: 1.2;
      margin-top: 3px;
    }}

    .warn {{
      color: #92400e;
      font-weight: bold;
    }}

    .money {{
      white-space: nowrap;
    }}

    .award-col {{
      white-space: normal;
    }}

    .source-col {{
      white-space: nowrap;
    }}

    .contractors-col {{
      min-width: 0;
      max-width: none;
    }}

    th:nth-child(1), td:nth-child(1) {{ width: 16%; }}   /* Progetto */
    th:nth-child(2), td:nth-child(2) {{ width: 7%; }}    /* Filiale */
    th:nth-child(3), td:nth-child(3) {{ width: 6%; }}    /* Segmento */
    th:nth-child(4), td:nth-child(4) {{ width: 6%; }}    /* Regione */
    th:nth-child(5), td:nth-child(5) {{ width: 7%; }}    /* Provincia */
    th:nth-child(6), td:nth-child(6) {{ width: 7%; }}    /* Comune */
    th:nth-child(7), td:nth-child(7) {{ width: 6.5%; }}  /* Valore */
    th:nth-child(8), td:nth-child(8) {{ width: 11%; }}   /* Committente */
    th:nth-child(9), td:nth-child(9) {{ width: 22%; }}   /* Aggiudicatario */
    th:nth-child(10), td:nth-child(10) {{ width: 7%; }}  /* Aggiudicazione */
    th:nth-child(11), td:nth-child(11) {{ width: 4.5%; }}/* Fonte */

    .oe-line {{
      padding: 0 0 5px 0;
      margin: 0 0 5px 0;
      border-bottom: 1px solid #eef2f7;
    }}

    .oe-line:last-child {{
      border-bottom: 0;
      margin-bottom: 0;
      padding-bottom: 0;
    }}

    .oe-name {{
      font-weight: bold;
      overflow-wrap: anywhere;
    }}

    .oe-tax {{
      color: var(--muted);
      font-size: 10.5px;
      margin-top: 2px;
    }}

    a {{
      color: var(--accent);
      font-weight: bold;
      text-decoration: none;
      white-space: nowrap;
    }}

    @media (max-width: 1450px) {{
      header {{
        padding: 18px 22px;
      }}

      header h1 {{
        font-size: 22px;
      }}

      main {{
        padding: 14px 12px 18px 12px;
      }}

      th, td {{
        font-size: 9.7px;
        padding: 4px 4px;
      }}

      .small,
      .oe-tax {{
        font-size: 9px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{esc(page["title"])}</h1>
    <p>{esc(page["subtitle"])}</p>
  </header>

  <main>
    <section class="meta">
      <div class="pill">Record totali: {len(rows)}</div>
      <div class="pill">Righe mostrate: {min(len(rows), page["limit"])}</div>
      <div class="pill">Stesse colonne operative della ricerca filiali</div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Progetto</th>
            <th>Filiale</th>
            <th>Segmento</th>
            <th>Regione</th>
            <th>Provincia</th>
            <th>Comune</th>
            <th>Valore</th>
            <th>Committente</th>
            <th>Aggiudicatario / OE</th>
            <th>Aggiudicazione</th>
            <th>Fonte</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rendered_rows)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def main():
    branch_map = load_branch_map()

    for page in PAGES:
        if not page["input"].exists():
            print(f"[WARN] CSV non trovato: {page['input']}")
            continue

        rows = read_rows(page["input"])
        output = build_html(page, rows, branch_map)

        # Guardia anti-corruzione: se compare il pattern ---P---R, blocca tutto.
        if "---P---" in output or "---------------" in output:
            raise SystemExit("ERRORE: output corrotto rilevato. File non scritto.")

        page["output"].parent.mkdir(parents=True, exist_ok=True)
        page["output"].write_text(output, encoding="utf-8")
        print(f"[OK] {page['input']} -> {page['output']} ({len(rows)} righe)")


if __name__ == "__main__":
    main()
