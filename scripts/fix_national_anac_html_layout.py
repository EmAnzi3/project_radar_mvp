import re
from pathlib import Path


FILES = [
    Path("docs/national_anac_enriched.html"),
    Path("docs/national_anac_relevant_awards.html"),
    Path("docs/national_anac_awards_anomalies.html"),
]


CSS = """
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f6f7f9;
      color: #1f2933;
    }

    h1 {
      margin: 0;
      padding: 22px 28px 6px 28px;
      background: #111827;
      color: white;
      font-size: 24px;
    }

    .meta {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      padding: 14px 28px;
      margin: 0;
      background: #111827;
      color: #d1d5db;
    }

    .pill {
      background: white;
      color: #1f2933;
      padding: 7px 10px;
      border: 1px solid #e5e7eb;
      border-radius: 999px;
      font-size: 12px;
    }

    .wrap {
      overflow: auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,.08);
      max-height: calc(100vh - 155px);
      min-height: 420px;
      margin: 18px 20px 24px 20px;
    }

    table {
      border-collapse: collapse;
      width: 100%;
      min-width: 0 !important;
      table-layout: fixed;
    }

    th, td {
      padding: 6px 7px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
      font-size: 11.5px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    th {
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
      z-index: 5;
      white-space: nowrap;
      overflow-wrap: normal;
    }

    .small {
      color: #6b7280;
      font-size: 10.5px;
      line-height: 1.2;
    }

    a {
      color: #0f766e;
      font-weight: bold;
      text-decoration: none;
      white-space: nowrap;
    }

    tr:hover {
      background: #f3f4f6;
    }

    /* Larghezze per le viste ANAC */
    th:nth-child(1), td:nth-child(1) { width: 8%; }    /* Segmento */
    th:nth-child(2), td:nth-child(2) { width: 24%; }   /* Progetto */
    th:nth-child(3), td:nth-child(3) { width: 8%; }    /* Comune */
    th:nth-child(4), td:nth-child(4) { width: 7%; }    /* Provincia */
    th:nth-child(5), td:nth-child(5) { width: 8%; }    /* Valore progetto */
    th:nth-child(6), td:nth-child(6) { width: 13%; }   /* Committente */
    th:nth-child(7), td:nth-child(7) { width: 22%; }   /* Aggiudicatario */
    th:nth-child(8), td:nth-child(8) { width: 7%; }    /* Importo/Data */
    th:nth-child(9), td:nth-child(9) { width: 7%; }    /* Data/Esito */
    th:nth-child(10), td:nth-child(10) { width: 5%; }  /* Fonte */

    td:nth-child(5),
    td:nth-child(8),
    td:nth-child(9),
    td:nth-child(10) {
      white-space: nowrap;
    }

    @media (max-width: 1200px) {
      th, td {
        font-size: 10.8px;
        padding: 5px 6px;
      }

      .small {
        font-size: 10px;
      }

      .wrap {
        margin: 14px 12px 20px 12px;
      }
    }
"""


def replace_style(text: str) -> str:
    return re.sub(
        r"<style>.*?</style>",
        "<style>\n" + CSS + "\n  </style>",
        text,
        flags=re.DOTALL,
    )


def remove_anomaly_technical_columns(text: str) -> str:
    # Header: toglie solo le tre colonne tecniche, mantiene Importo aggiud.
    text = re.sub(
        r"\s*<th>% su progetto</th>\s*<th>Peso affidamento</th>\s*<th>Nota rapporto</th>",
        "",
        text,
        flags=re.DOTALL,
    )

    # Righe: dopo Importo aggiud. elimina % / Peso / Nota prima della Data.
    text = re.sub(
        r"(<td>[^<]*€</td>)\s*<td>[^<]*%</td>\s*<td>.*?</td>\s*<td>.*?</td>\s*(<td>\d{4}-\d{2}-\d{2}</td>)",
        r"\1\n          \2",
        text,
        flags=re.DOTALL,
    )

    # Aggiorna pill descrittiva
    text = text.replace(
        "CIG multi-progetto, importi fuori scala o affidamenti troppo piccoli rispetto al progetto",
        "Casi anomali separati dalla vista principale"
    )

    return text


def compact_relevant_view(text: str) -> str:
    # Nella vista commerciale nazionale non serve Esito separato: è quasi sempre AGGIUDICATA.
    # Lo manteniamo per ora per non rischiare di rompere righe già generate.
    return text


def main():
    for p in FILES:
        if not p.exists():
            print(f"[WARN] File non trovato: {p}")
            continue

        text = p.read_text(encoding="utf-8")
        text = replace_style(text)

        if p.name == "national_anac_awards_anomalies.html":
            text = remove_anomaly_technical_columns(text)

        if p.name == "national_anac_relevant_awards.html":
            text = compact_relevant_view(text)

        p.write_text(text, encoding="utf-8")
        print(f"[OK] sistemato: {p}")


if __name__ == "__main__":
    main()
