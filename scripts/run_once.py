import json
import sys
from pathlib import Path

# Rende importabile la cartella app/ anche quando lo script viene lanciato da scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import OUTPUT_JSON, OUTPUT_HTML, REPORTS_DIR
from app.models import ProjectRecord
from app.scoring import calculate_commercial_score


def build_demo_records() -> list[ProjectRecord]:
    records = [
        ProjectRecord(
            source="demo",
            external_id="DEMO-001",
            title="Impianto fotovoltaico dimostrativo",
            description="Progetto dimostrativo per testare struttura dati, scoring e report.",
            region="Emilia-Romagna",
            province="BO",
            municipality="Bologna",
            sector="fotovoltaico",
            category="energia",
            phase="progettazione",
            client="Committente demo",
            estimated_value_eur=2500000,
            power_mw=8.5,
            cup="DEMO-CUP",
            cig="DEMO-CIG",
            source_url="https://example.com",
        )
    ]

    for record in records:
        record.commercial_score = calculate_commercial_score(record)

    return records


def write_json(records: list[ProjectRecord]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "records": [r.model_dump() for r in records],
        "count": len(records),
    }
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(records: list[ProjectRecord]) -> None:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in records:
        rows.append(f"""
        <tr>
          <td>{r.commercial_score}</td>
          <td>{r.title}</td>
          <td>{r.region or ""}</td>
          <td>{r.province or ""}</td>
          <td>{r.municipality or ""}</td>
          <td>{r.sector or ""}</td>
          <td>{r.phase or ""}</td>
          <td>{r.estimated_value_eur or ""}</td>
          <td><a href="{r.source_url or "#"}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      background: #f6f7f9;
      color: #1f2933;
    }}
    h1 {{
      margin-bottom: 4px;
    }}
    .subtitle {{
      color: #617083;
      margin-bottom: 24px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
    }}
    tr:hover {{
      background: #f3f4f6;
    }}
  </style>
</head>
<body>
  <h1>Project Radar MVP</h1>
  <div class="subtitle">Radar commerciale progetti - versione iniziale</div>

  <table>
    <thead>
      <tr>
        <th>Score</th>
        <th>Progetto</th>
        <th>Regione</th>
        <th>Prov.</th>
        <th>Comune</th>
        <th>Settore</th>
        <th>Fase</th>
        <th>Valore €</th>
        <th>Fonte</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")


def main() -> None:
    records = build_demo_records()
    write_json(records)
    write_html(records)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Record generati: {len(records)}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"HTML: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
