import csv
import json
import re
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Optional


ALAYAN_SEGMENT_WEIGHTS = {
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
    "Servizi": 5,
    "Commercio": 3,
    "Trasporto": 3,
    "Altro": -10,
}


def clean_text(value) -> str:
    if value is None:
        return ""

    text = str(value)

    replacements = {
        "\x91": "'",
        "\x92": "'",
        "\x93": '"',
        "\x94": '"',
        "\x96": "-",
        "\x97": "-",
        "\xa0": " ",
        "": "'",
        "": '"',
        "": '"',
        "": "-",
        "": "-",
        "¿": "'",
        "�": "'",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return re.sub(r"\s+", " ", text).strip()




def field(record, name: str, default=None):
    """
    Accessor robusto:
    - dataclass / oggetto: getattr
    - dict: get
    """
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def record_text(record) -> str:
    return " ".join(
        clean_text(x).lower()
        for x in [
            field(record, "title"),
            field(record, "description"),
            field(record, "category"),
            field(record, "sector"),
            field(record, "client"),
            field(record, "ai_notes"),
        ]
        if x
    )


def extract_year_decision(record) -> Optional[int]:
    notes = clean_text(field(record, "ai_notes"))
    match = re.search(r"Anno decisione:\s*(\d{4})", notes, flags=re.IGNORECASE)

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def assign_alayan_segments(record) -> tuple[str, list[str]]:
    text = record_text(record)
    category = clean_text(field(record, "category")).lower()

    matches: set[str] = set()

    if contains_any(text, ["demolizione", "demolizioni", "demolire", "abbattimento", "rimozione fabbricato"]):
        matches.add("Demolizioni")

    if contains_any(text, [
        "fognatura", "fognario", "acquedotto", "rete idrica", "reti idriche",
        "acque reflue", "depurazione", "depuratore", "sottoservizi",
        "cavidotto", "cavidotti", "condotta", "collettore", "scarico",
    ]):
        matches.add("Impiantisti sottoservizi")

    if contains_any(text, [
        "strada", "strade", "viabilita", "viabilità", "pavimentazione stradale",
        "rotatoria", "marciapiede", "ponte", "pista ciclabile", "ciclabile",
        "illuminazione pubblica", "banchina stradale", "messa in sicurezza viaria",
    ]):
        matches.add("Lavori pubblici strade")

    if contains_any(text, [
        "verde", "parco", "giardino", "giardini", "alberature", "forestale",
        "arredo urbano", "area verde", "verde pubblico", "rinaturalizzazione",
    ]):
        matches.add("Verde")

    if contains_any(text, [
        "bonifica", "bonifiche", "rifiuti", "discarica", "trattamento rifiuti",
        "amianto", "inquinamento", "messa in sicurezza permanente",
    ]):
        matches.add("Bonifiche e gestione rifiuti")

    if contains_any(text, [
        "capannone", "magazzino", "logistica", "polo logistico", "area produttiva",
        "zona industriale", "stabilimento", "opificio", "impianto produttivo",
        "stoccaggio materiali",
    ]):
        matches.add("Industria")

    if contains_any(text, [
        "impianto elettrico", "impianti elettrici", "impianto termico",
        "impianti termici", "climatizzazione", "riscaldamento", "fotovoltaico",
        "efficientamento energetico", "centrale termica", "illuminazione",
        "antincendio", "impiantistico", "adeguamento impiantistico",
    ]):
        matches.add("Impiantisti")

    if contains_any(text, [
        "copertura", "manto di copertura", "tetto", "infissi", "serramenti",
        "facciata", "facciate", "rivestimenti", "finiture", "pavimentazione interna",
        "cartongesso", "intonaco", "tinteggiatura", "impermeabilizzazione",
        "completamento", "riqualificazione energetica",
    ]):
        matches.add("Completamento e finitura edifici")

    if contains_any(text, [
        "scuola", "scolastico", "asilo", "nido", "ospedale", "presidio sanitario",
        "casa della comunita", "casa della comunità", "rsa", "edificio",
        "fabbricato", "immobile", "palestra", "spogliatoi", "auditorium",
        "teatro", "biblioteca", "centro civico", "centro culturale", "alloggi",
        "edilizia residenziale", "municipio", "sede comunale", "caserma",
    ]):
        matches.add("Edilizia")

    if contains_any(text, [
        "agricoltura", "agricolo", "irriguo", "irrigazione", "rurale",
        "forestazione", "silvicoltura", "azienda agricola",
    ]):
        matches.add("Agricoltura / silvicoltura")

    if "infrastrutture / parcheggi" in category:
        matches.add("Lavori pubblici strade")

    if "ambiente / rifiuti / depurazione" in category:
        if contains_any(text, ["fognatura", "acquedotto", "depurazione", "acque reflue"]):
            matches.add("Impiantisti sottoservizi")
        else:
            matches.add("Bonifiche e gestione rifiuti")

    if "industriale / logistica" in category:
        matches.add("Industria")

    if category in {
        "scuole / formazione",
        "sanità / rsa",
        "sport / impianti sportivi",
        "cultura / centri civici",
        "edilizia pubblica",
        "residenziale pubblico / ers",
    }:
        matches.add("Edilizia")

    if "riqualificazione urbana" in category and not matches:
        matches.add("Edilizia")

    if not matches:
        matches.add("Altro")

    ordered = sorted(
        matches,
        key=lambda s: ALAYAN_SEGMENT_WEIGHTS.get(s, -10),
        reverse=True,
    )

    return ordered[0], ordered


def is_local_public_client(client) -> bool:
    c = clean_text(client).upper()

    markers = [
        "COMUNE",
        "PROVINCIA",
        "CITTA' METROPOLITANA",
        "CITTÀ METROPOLITANA",
        "REGIONE",
        "AZIENDA USL",
        "ASL",
        "AZIENDA OSPEDALIERA",
        "UNIONE DEI COMUNI",
    ]

    return any(m in c for m in markers)


def is_macro_national_project(record) -> bool:
    text = record_text(record)
    value = field(record, "estimated_value_eur") or 0

    macro_terms = [
        "autostrada", "autostradale", "ferrovia", "ferroviario",
        "alta velocità", "alta velocita", "concessione",
        "raccordo autostradale", "collegamento autostradale",
        "corridoio", "rete elettrica nazionale", "hvdc", "terna",
        "elettrodotto nazionale", "metropolitana",
    ]

    return value >= 100_000_000 and any(t in text for t in macro_terms)


def value_band(value) -> str:
    value = value or 0

    if value >= 100_000_000:
        return ">= 100M"
    if value >= 50_000_000:
        return "50M - 100M"
    if value >= 20_000_000:
        return "20M - 50M"
    if value >= 5_000_000:
        return "5M - 20M"
    if value >= 1_000_000:
        return "1M - 5M"
    if value >= 500_000:
        return "500k - 1M"
    if value >= 200_000:
        return "200k - 500k"
    return "< 200k"


def value_score(value) -> int:
    value = value or 0

    if value >= 500_000_000:
        return -20
    if value >= 100_000_000:
        return -10
    if value >= 50_000_000:
        return 8
    if value >= 20_000_000:
        return 20
    if value >= 5_000_000:
        return 30
    if value >= 1_000_000:
        return 28
    if value >= 500_000:
        return 18
    if value >= 200_000:
        return 10
    return -30


def year_score(year: Optional[int]) -> int:
    if year is None:
        return 0
    if year >= 2024:
        return 15
    if year >= 2022:
        return 12
    if year >= 2020:
        return 6
    if year >= 2018:
        return 0
    if year >= 2015:
        return -8
    return -15


def operational_score(record) -> tuple[int, str, list[str], Optional[int], bool]:
    primary_segment, segment_tags = assign_alayan_segments(record)
    year = extract_year_decision(record)
    macro = is_macro_national_project(record)

    value = field(record, "estimated_value_eur") or 0
    score = 0

    score += ALAYAN_SEGMENT_WEIGHTS.get(primary_segment, -10)
    score += value_score(value)
    score += year_score(year)

    client = clean_text(field(record, "client")).upper()

    if is_local_public_client(client):
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

    municipality = clean_text(field(record, "municipality")).upper()

    if municipality and municipality not in {"TUTTI", "TUTTE", "VARI", "DIVERSI"}:
        score += 10
    else:
        score -= 12

    status = clean_text(field(record, "status")).upper()

    if "CHIUSO" in status or "REVOCATO" in status or "CANCELLATO" in status:
        score -= 40
    elif "ATTIVO" in status:
        score += 8

    if clean_text(field(record, "category")) == "Altro":
        score -= 10

    if macro:
        score -= 25

    if field(record, "cup"):
        score += 2
    if field(record, "source_url"):
        score += 2

    return max(0, min(100, score)), primary_segment, segment_tags, year, macro


def money(value) -> str:
    if value is None:
        return ""
    return f"{float(value):,.0f} &euro;".replace(",", ".")


def txt(value) -> str:
    return escape(str(value or ""))


def record_to_dict(record) -> dict:
    if isinstance(record, dict):
        return dict(record)
    try:
        return asdict(record)
    except TypeError:
        return dict(record)


def write_operational_outputs(records: list, docs_dir: Path, reports_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    enriched = []

    for record in records:
        score, primary_segment, segment_tags, year, macro = operational_score(record)

        if macro:
            continue

        if score < 45:
            continue

        enriched.append({
            "record": record,
            "operational_score": score,
            "primary_segment": primary_segment,
            "segment_tags": segment_tags,
            "year_decision": year,
            "macro_project": macro,
            "value_band": value_band(field(record, "estimated_value_eur")),
        })

    enriched.sort(
        key=lambda x: (
            x["operational_score"],
            getattr(x["record"], "estimated_value_eur", None) or 0,
        ),
        reverse=True,
    )

    shortlist = enriched[:1000]
    dashboard = enriched[:250]

    with (reports_dir / "operational_shortlist.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "operational_score",
            "primary_segment",
            "segment_tags",
            "year_decision",
            "value_band",
            "cup",
            "title",
            "category",
            "region",
            "province",
            "municipality",
            "value_eur",
            "client",
            "source_url",
        ]

        writer = csv.DictWriter(f, delimiter=";", fieldnames=fieldnames)
        writer.writeheader()

        for item in shortlist:
            r = item["record"]
            writer.writerow({
                "operational_score": item["operational_score"],
                "primary_segment": item["primary_segment"],
                "segment_tags": " | ".join(item["segment_tags"]),
                "year_decision": item["year_decision"],
                "value_band": item["value_band"],
                "cup": getattr(r, "cup", None),
                "title": field(r, "title"),
                "category": field(r, "category"),
                "region": field(r, "region"),
                "province": field(r, "province"),
                "municipality": field(r, "municipality"),
                "value_eur": field(r, "estimated_value_eur"),
                "client": field(r, "client"),
                "source_url": field(r, "source_url"),
            })

    by_segment = {}

    for item in enriched:
        segment = item["primary_segment"]
        r = item["record"]

        by_segment.setdefault(segment, {
            "primary_segment": segment,
            "count": 0,
            "total_value_eur": 0,
            "avg_score": 0,
        })

        by_segment[segment]["count"] += 1
        by_segment[segment]["total_value_eur"] += field(r, "estimated_value_eur") or 0
        by_segment[segment]["avg_score"] += item["operational_score"]

    segment_rows = []

    for row in by_segment.values():
        count = row["count"] or 1
        row["avg_score"] = round(row["avg_score"] / count, 2)
        row["total_value_eur"] = round(row["total_value_eur"], 2)
        segment_rows.append(row)

    segment_rows.sort(key=lambda x: x["count"], reverse=True)

    with (reports_dir / "operational_by_segment.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            delimiter=";",
            fieldnames=["primary_segment", "count", "total_value_eur", "avg_score"],
        )
        writer.writeheader()
        writer.writerows(segment_rows)

    operational_json = {
        "source": "OpenCUP",
        "view": "operational",
        "total_input_candidates": len(records),
        "operational_candidates": len(enriched),
        "dashboard_count": len(dashboard),
        "criteria": {
            "exclude_macro_projects": True,
            "min_operational_score": 45,
            "preferred_value_range": "1M - 50M",
            "segment_model": "Alayan commercial segments",
        },
        "records": [
            {
                "operational_score": item["operational_score"],
                "primary_segment": item["primary_segment"],
                "segment_tags": item["segment_tags"],
                "year_decision": item["year_decision"],
                "value_band": item["value_band"],
                **record_to_dict(item["record"]),
            }
            for item in dashboard
        ],
    }

    (docs_dir / "operational_data.json").write_text(
        json.dumps(operational_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rows = []

    for item in dashboard:
        r = item["record"]

        rows.append(f"""
        <tr>
          <td class="score">{item["operational_score"]}</td>
          <td>
            <strong>{txt(field(r, "title", ""))}</strong>
            <div class="desc">{txt(field(r, "description", ""))}</div>
          </td>
          <td>{txt(item["primary_segment"])}</td>
          <td>{txt(field(r, "category", ""))}</td>
          <td>{txt(field(r, "region", ""))}</td>
          <td>{txt(field(r, "province", ""))}</td>
          <td>{txt(field(r, "municipality", ""))}</td>
          <td>{txt(item["year_decision"])}</td>
          <td>{txt(item["value_band"])}</td>
          <td>{money(field(r, "estimated_value_eur"))}</td>
          <td>{txt(field(r, "client", ""))}</td>
          <td>{txt(field(r, "cup", ""))}</td>
          <td><a href="{txt(field(r, "source_url", ""))}" target="_blank">Fonte</a></td>
        </tr>
        """)

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - Vista operativa</title>
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
      min-width: 1650px;
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
    a {{
      color: #0f766e;
      font-weight: bold;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <h1>Project Radar MVP - Vista operativa</h1>
  <div class="subtitle">Shortlist commerciale basata sui segmenti Alayan</div>

  <div class="meta">
    <div class="pill">Input candidati: {len(records)}</div>
    <div class="pill">Candidati operativi: {len(enriched)}</div>
    <div class="pill">Record mostrati: {len(dashboard)}</div>
    <div class="pill">Macro-progetti esclusi da questa vista</div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Score operativo</th>
          <th>Progetto</th>
          <th>Segmento Alayan</th>
          <th>Categoria progetto</th>
          <th>Regione</th>
          <th>Prov.</th>
          <th>Comune</th>
          <th>Anno</th>
          <th>Fascia valore</th>
          <th>Valore</th>
          <th>Committente</th>
          <th>CUP</th>
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

    (docs_dir / "operational.html").write_text(html, encoding="utf-8")

    print("[Operational] docs/operational.html")
    print("[Operational] docs/operational_data.json")
    print("[Operational] reports/operational_shortlist.csv")
    print("[Operational] reports/operational_by_segment.csv")
