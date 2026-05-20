import json
import sys
from pathlib import Path
from html import escape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import OUTPUT_JSON, OUTPUT_HTML, REPORTS_DIR, BASE_DIR
from app.collectors.opencup import collect_opencup
from app.models import ProjectRecord
from app.scoring import calculate_commercial_score
from app.storage import (
    collect_source_file_signatures,
    count_records,
    finish_run,
    load_records,
    save_records,
    save_source_file_signatures,
    source_is_unchanged,
    start_run,
)


SOURCE_NAME = "OpenCUP"
RAW_OPENCUP_DIR = BASE_DIR / "data" / "raw" / "opencup"
DASHBOARD_LIMIT = 120


def build_demo_records() -> list[ProjectRecord]:
    records = [
        ProjectRecord(
            source="demo",
            external_id="DEMO-NII-LIKE-001",
            title="Riqualificazione edificio scolastico dimostrativo",
            description="Progetto dimostrativo Nii-like per testare struttura dati, scoring e report generalista.",
            region="Emilia-Romagna",
            province="BO",
            municipality="Bologna",
            sector="Lavori pubblici",
            category="Scuole / formazione",
            intervention_type="riqualificazione",
            phase="programmazione / progetto attivo",
            status="ATTIVO",
            client="Comune demo",
            client_type="pubblico",
            estimated_value_eur=2500000,
            cup="DEMO-CUP",
            source_url="https://example.com",
            enrichment_status="demo",
        )
    ]

    for record in records:
        record.commercial_score = calculate_commercial_score(record)

    return records


def refresh_database_if_needed() -> tuple[list[ProjectRecord], int, str]:
    source_files = collect_source_file_signatures(SOURCE_NAME, RAW_OPENCUP_DIR)
    active_in_db = count_records(SOURCE_NAME, only_active=True)

    if source_files and active_in_db > 0 and source_is_unchanged(SOURCE_NAME, source_files):
        print(f"[DB] Dataset OpenCUP invariato. Carico vista da SQLite.")
        records = load_records(SOURCE_NAME, limit=DASHBOARD_LIMIT, only_active=True)
        return records, active_in_db, "cache"

    print("[DB] Dataset nuovo o non ancora processato. Avvio scansione completa OpenCUP.")

    run_id = start_run(SOURCE_NAME, note="full scan OpenCUP")

    try:
        all_records = collect_opencup(max_records=None)

        if not all_records:
            print("[WARN] Nessun record reale trovato. Uso record demo di fallback.")
            all_records = build_demo_records()

        for record in all_records:
            record.commercial_score = calculate_commercial_score(record)

        all_records.sort(
            key=lambda r: (
                r.commercial_score,
                r.estimated_value_eur or 0,
                r.last_seen or "",
            ),
            reverse=True,
        )

        saved_count = save_records(all_records, SOURCE_NAME, run_id)
        finish_run(run_id, saved_count)

        if source_files:
            save_source_file_signatures(SOURCE_NAME, source_files)

        active_total = count_records(SOURCE_NAME, only_active=True)
        records = load_records(SOURCE_NAME, limit=DASHBOARD_LIMIT, only_active=True)

        print(f"[DB] Record candidati attivi salvati: {active_total:,}")
        print(f"[DB] Vista dashboard: primi {len(records)} record.")

        return records, active_total, "full_scan"

    except Exception:
        finish_run(run_id, 0)
        raise


def write_json(records: list[ProjectRecord], total_active: int, mode: str) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "source": SOURCE_NAME,
        "mode": mode,
        "dashboard_count": len(records),
        "total_active_in_db": total_active,
        "records": [r.model_dump() for r in records],
    }
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _money(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):,.0f} &euro;".replace(",", ".")
    except Exception:
        return str(value)


def _txt(value) -> str:
    return escape(str(value or ""))


def _contractor_block(r: ProjectRecord) -> str:
    parts = []

    if r.contractor_name or r.contractor:
        parts.append(f"<strong>{_txt(r.contractor_name or r.contractor)}</strong>")

    vat_parts = []
    if r.contractor_vat:
        vat_parts.append(f"P.IVA: {_txt(r.contractor_vat)}")
    if r.contractor_tax_code and r.contractor_tax_code != r.contractor_vat:
        vat_parts.append(f"CF: {_txt(r.contractor_tax_code)}")
    if vat_parts:
        parts.append("<br>".join(vat_parts))

    address = " ".join(
        x for x in [
            r.contractor_address,
            r.contractor_city,
            f"({r.contractor_province})" if r.contractor_province else None,
        ]
        if x
    )
    if address:
        parts.append(_txt(address))

    contacts = []
    if r.contractor_pec:
        contacts.append(f"PEC: {_txt(r.contractor_pec)}")
    if r.contractor_email:
        contacts.append(f"Email: {_txt(r.contractor_email)}")
    if r.contractor_phone:
        contacts.append(f"Tel: {_txt(r.contractor_phone)}")
    if contacts:
        parts.append("<br>".join(contacts))

    return "<br>".join(parts)


def _contact_block(r: ProjectRecord) -> str:
    parts = []

    if r.rup:
        parts.append(f"<strong>RUP:</strong> {_txt(r.rup)}")
    elif r.contact_name:
        parts.append(f"<strong>{_txt(r.contact_name)}</strong>")

    if r.contact_role:
        parts.append(_txt(r.contact_role))

    if r.contact_email:
        parts.append(f"Email: {_txt(r.contact_email)}")
    if r.contact_phone:
        parts.append(f"Tel: {_txt(r.contact_phone)}")

    return "<br>".join(parts)


def write_html(records: list[ProjectRecord], total_active: int, mode: str) -> None:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in records:
        fonte = f'<a href="{_txt(r.source_url)}" target="_blank">Fonte</a>' if r.source_url else ""
        award_source = f'<br><a href="{_txt(r.award_source_url)}" target="_blank">Esito</a>' if r.award_source_url else ""

        rows.append(f"""
        <tr>
          <td class="score">{r.commercial_score}</td>
          <td>
            <strong>{_txt(r.title)}</strong>
            <div class="desc">{_txt(r.description)}</div>
            <div class="small">{_txt(r.enrichment_status)}</div>
          </td>
          <td>{_txt(r.category)}</td>
          <td>{_txt(r.region)}</td>
          <td>{_txt(r.province)}</td>
          <td>{_txt(r.municipality)}</td>
          <td>{_txt(r.phase)}</td>
          <td>{_txt(r.status)}</td>
          <td>{_money(r.estimated_value_eur)}</td>
          <td>{_money(r.award_amount_eur)}</td>
          <td>{_txt(r.client)}</td>
          <td>{_contractor_block(r)}</td>
          <td>{_contact_block(r)}</td>
          <td>{_txt(r.cup)}</td>
          <td>{_txt(r.cig)}</td>
          <td>{fonte}{award_source}</td>
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
      margin-bottom: 16px;
    }}
    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 18px;
      color: #4b5563;
      font-size: 14px;
    }}
    .pill {{
      background: white;
      border: 1px solid #e5e7eb;
      padding: 8px 10px;
      border-radius: 999px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .table-wrap {{
      overflow-x: auto;
      background: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border-radius: 12px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 1900px;
      background: white;
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      font-size: 14px;
      vertical-align: top;
    }}
    th {{
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    tr:hover {{
      background: #f3f4f6;
    }}
    .score {{
      font-weight: bold;
      font-size: 18px;
    }}
    .desc {{
      color: #4b5563;
      font-size: 12px;
      margin-top: 5px;
      max-width: 520px;
      max-height: 62px;
      overflow: hidden;
    }}
    .small {{
      color: #6b7280;
      font-size: 11px;
      margin-top: 6px;
      font-style: italic;
    }}
    a {{
      color: #0f766e;
      font-weight: bold;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <h1>Project Radar MVP</h1>
  <div class="subtitle">Radar generalista progetti/opere - fonte principale OpenCUP</div>

  <div class="meta">
    <div class="pill">Modalità: {mode}</div>
    <div class="pill">Record attivi in DB: {total_active}</div>
    <div class="pill">Record mostrati: {len(records)}</div>
    <div class="pill">Vista: migliori {DASHBOARD_LIMIT} per score e valore</div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Score</th>
          <th>Progetto</th>
          <th>Categoria radar</th>
          <th>Regione</th>
          <th>Prov.</th>
          <th>Comune</th>
          <th>Fase</th>
          <th>Stato</th>
          <th>Valore stimato</th>
          <th>Importo aggiud.</th>
          <th>Committente</th>
          <th>Azienda incaricata</th>
          <th>Referente / RUP</th>
          <th>CUP</th>
          <th>CIG</th>
          <th>Fonte</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")


def main() -> None:
    records, total_active, mode = refresh_database_if_needed()
    write_json(records, total_active, mode)
    write_html(records, total_active, mode)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Modalità: {mode}")
    print(f"Record attivi in DB: {total_active}")
    print(f"Record dashboard: {len(records)}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"HTML: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
