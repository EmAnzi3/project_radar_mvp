import json
from pathlib import Path
from urllib.parse import quote


BRANCH_TERRITORY = Path("docs/data/branch_territory.json")
OUT_HTML = Path("docs/branches.html")


AREA_ORDER = ["Nord-Ovest", "Nord-Est", "Centro", "Sud", "Altro"]


BRANCH_TO_AREA = {
    # Nord-Ovest
    "Albenga": "Nord-Ovest",
    "Genova": "Nord-Ovest",
    "Cuneo": "Nord-Ovest",
    "Torino": "Nord-Ovest",
    "Brescia": "Nord-Ovest",
    "Bergamo": "Nord-Ovest",
    "Sondrio": "Nord-Ovest",
    "Lecco": "Nord-Ovest",
    "Milano Sud": "Nord-Ovest",
    "Milano Nord": "Nord-Ovest",
    "Milano Ovest": "Nord-Ovest",
    "Milano Est": "Nord-Ovest",

    # Nord-Est
    "Padova": "Nord-Est",
    "Treviso": "Nord-Est",
    "Verona": "Nord-Est",
    "Venezia": "Nord-Est",
    "Trento": "Nord-Est",
    "Bolzano": "Nord-Est",
    "Udine": "Nord-Est",

    # Centro
    "Firenze": "Centro",
    "Lucca": "Centro",
    "Livorno": "Centro",
    "Bologna": "Centro",
    "Rimini": "Centro",
    "Parma": "Centro",
    "Sassuolo": "Centro",
    "Perugia": "Centro",
    "Cagliari": "Centro",
    "Sassari": "Centro",

    # Sud
    "Roma Nomentana": "Sud",
    "Roma Aurelia": "Sud",
    "Roma Aurealia": "Sud",
    "Frosinone": "Sud",
    "Napoli": "Sud",
    "Salerno": "Sud",
    "Bari": "Sud",
    "Cosenza": "Sud",
    "Catania": "Sud",
}


def clean(value):
    return str(value or "").strip()


def display_branch(branch):
    branch = clean(branch)

    fixes = {
        "SALERNO": "Salerno",
        "Roma Aurealia": "Roma Aurelia",
    }

    return fixes.get(branch, branch)


def branch_area(branch):
    branch = display_branch(branch)
    return BRANCH_TO_AREA.get(branch, "Altro")


def main():
    if not BRANCH_TERRITORY.exists():
        raise SystemExit(f"File non trovato: {BRANCH_TERRITORY}")

    data = json.loads(BRANCH_TERRITORY.read_text(encoding="utf-8"))

    branches = []

    for raw_branch, rows in data.items():
        branch = display_branch(raw_branch)
        area = branch_area(branch)

        regions = sorted(set(clean(r.get("region")) for r in rows if clean(r.get("region"))))
        provinces = sorted(set(clean(r.get("province")) for r in rows if clean(r.get("province"))))
        municipalities = sorted(set(clean(r.get("municipality")) for r in rows if clean(r.get("municipality"))))

        branches.append({
            "branch_raw": raw_branch,
            "branch": branch,
            "area": area,
            "regions": regions,
            "provinces": provinces,
            "municipalities_count": len(municipalities),
            "territory_count": len(rows),
            "url": f"search.html?branch={quote(branch)}",
        })

    branches.sort(
        key=lambda x: (
            AREA_ORDER.index(x["area"]) if x["area"] in AREA_ORDER else 99,
            x["branch"].lower(),
        )
    )

    grouped = {area: [] for area in AREA_ORDER}

    for b in branches:
        grouped.setdefault(b["area"], []).append(b)

    sections = []

    for area in AREA_ORDER:
        items = grouped.get(area, [])
        if not items:
            continue

        cards = []

        for b in items:
            region_text = ", ".join(b["regions"]) if b["regions"] else "ND"
            province_text = ", ".join(b["provinces"][:12])

            if len(b["provinces"]) > 12:
                province_text += f" +{len(b['provinces']) - 12}"

            cards.append(f"""
        <div class="card">
          <h2>{b["branch"]}</h2>
          <p><strong>Regioni:</strong> {region_text}</p>
          <p><strong>Province:</strong> {province_text or "ND"}</p>
          <p class="muted">{b["municipalities_count"]} comuni/località mappati</p>
          <a href="{b["url"]}">Apri ricerca filiale</a>
        </div>
            """)

        sections.append(f"""
    <section class="area-section">
      <h2>{area}</h2>
      <div class="grid">
        {''.join(cards)}
      </div>
    </section>
        """)

    unmapped = sorted(b["branch"] for b in branches if b["area"] == "Altro")

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - Filiali</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --bg: #f6f7f9;
      --card: #ffffff;
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
      padding: 26px 32px;
    }}

    header h1 {{
      margin: 0 0 8px 0;
      font-size: 28px;
    }}

    header p {{
      margin: 0;
      color: #d1d5db;
      font-size: 15px;
    }}

    main {{
      padding: 26px 32px;
      max-width: 1280px;
      margin: 0 auto;
    }}

    .top-actions {{
      margin-bottom: 22px;
    }}

    .top-actions a {{
      display: inline-block;
      background: var(--accent);
      color: white;
      text-decoration: none;
      padding: 10px 13px;
      border-radius: 10px;
      font-weight: bold;
      font-size: 14px;
      margin-right: 8px;
    }}

    .area-section {{
      margin: 28px 0 34px 0;
    }}

    .area-section h2 {{
      font-size: 22px;
      margin: 0 0 14px 0;
      border-bottom: 2px solid var(--border);
      padding-bottom: 8px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}

    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}

    .card h2 {{
      margin: 0 0 10px 0;
      font-size: 19px;
    }}

    .card p {{
      margin: 0 0 8px 0;
      color: var(--text);
      font-size: 14px;
      line-height: 1.35;
    }}

    .card .muted {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}

    .card a {{
      display: inline-block;
      color: white;
      background: var(--accent);
      padding: 9px 12px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: bold;
      font-size: 14px;
    }}

    .warning {{
      background: #fff7ed;
      border: 1px solid #fed7aa;
      color: #7c2d12;
      padding: 12px 14px;
      border-radius: 12px;
      margin-bottom: 18px;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Project Radar MVP - Filiali</h1>
    <p>Accesso diretto alla ricerca filtrata per filiale, raggruppata per Area Manager.</p>
  </header>

  <main>
    <div class="top-actions">
      <a href="home.html">Home</a>
      <a href="search.html">Ricerca completa</a>
    </div>

    {f'<div class="warning"><strong>Filiali non mappate:</strong> {", ".join(unmapped)}</div>' if unmapped else ''}

    {''.join(sections)}
  </main>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"Filiali generate: {len(branches)}")
    for area in AREA_ORDER:
        if grouped.get(area):
            print(f"{area}: {len(grouped[area])}")

    if unmapped:
        print(f"ATTENZIONE - Filiali non mappate: {', '.join(unmapped)}")

    print(f"Output: {OUT_HTML}")


if __name__ == "__main__":
    main()
