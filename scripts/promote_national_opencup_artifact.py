import csv
import json
import zipfile
from pathlib import Path


ARTIFACT = Path("project-radar-output-national.zip")

COPIES = {
    "reports/operational_shortlist.csv": "reports/national_operational_shortlist.csv",
    "reports/operational_by_segment.csv": "reports/national_operational_by_segment.csv",
    "reports/top_projects.csv": "reports/national_top_projects.csv",
    "reports/top_mid_market.csv": "reports/national_top_mid_market.csv",
    "reports/top_local_public.csv": "reports/national_top_local_public.csv",
    "reports/top_by_category.csv": "reports/national_top_by_category.csv",
    "reports/diagnostics_by_region.csv": "reports/national_diagnostics_by_region.csv",
    "reports/diagnostics_by_category.csv": "reports/national_diagnostics_by_category.csv",
    "reports/diagnostics_by_value_band.csv": "reports/national_diagnostics_by_value_band.csv",
}

OUT_JSON = Path("docs/national_operational_data.json")
OUT_HTML = Path("docs/national_operational.html")
CSV_PATH = Path("reports/national_operational_shortlist.csv")


def clean(v):
    return str(v or "").strip()


def to_float(v):
    try:
        return float(str(v or "").replace(",", "."))
    except Exception:
        return 0.0


def main():
    if not ARTIFACT.exists():
        raise SystemExit(f"Artifact non trovato: {ARTIFACT}")

    with zipfile.ZipFile(ARTIFACT) as z:
        names = {n.replace("\\", "/"): n for n in z.namelist()}

        for src, dst in COPIES.items():
            if src not in names:
                print(f"[WARN] File non trovato: {src}")
                continue

            out = Path(dst)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(names[src]))
            print(f"[OK] {src} -> {dst}")

    if not CSV_PATH.exists():
        raise SystemExit(f"CSV nazionale non trovato: {CSV_PATH}")

    records = []
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            records.append({
                "score": clean(row.get("operational_score") or row.get("score")),
                "segment": clean(row.get("primary_segment")),
                "title": clean(row.get("title")),
                "category": clean(row.get("category")),
                "region": clean(row.get("region")),
                "province": clean(row.get("province")),
                "municipality": clean(row.get("municipality")),
                "value_eur": to_float(row.get("value_eur")),
                "client": clean(row.get("client")),
                "cup": clean(row.get("cup")),
                "source_url": clean(row.get("source_url")),
            })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    html = """<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - Vista operativa nazionale</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background:#f6f7f9; color:#1f2933; }
    header { background:#111827; color:white; padding:24px 30px; }
    header h1 { margin:0 0 6px 0; font-size:26px; }
    header p { margin:0; color:#d1d5db; font-size:14px; }
    main { padding:24px 30px; }
    .filters { background:white; border:1px solid #e5e7eb; border-radius:14px; padding:16px; display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:18px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
    label { display:block; font-size:12px; color:#617083; margin-bottom:5px; }
    select,input { width:100%; box-sizing:border-box; border:1px solid #e5e7eb; border-radius:9px; padding:8px; font-size:13px; background:white; }
    .meta { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; color:#617083; font-size:14px; }
    .pill { background:white; border:1px solid #e5e7eb; border-radius:999px; padding:8px 10px; }
    .table-wrap { overflow:auto; background:white; border-radius:14px; box-shadow:0 2px 8px rgba(0,0,0,.08); max-height:calc(100vh - 310px); min-height:420px; }
    table { border-collapse:collapse; width:100%; min-width:1350px; }
    th,td { padding:7px; border-bottom:1px solid #e5e7eb; text-align:left; vertical-align:top; font-size:12px; line-height:1.25; }
    th { background:#111827; color:white; position:sticky; top:0; z-index:5; white-space:nowrap; }
    .money { white-space:nowrap; }
    .small { color:#617083; font-size:11px; margin-top:3px; }
    a { color:#0f766e; font-weight:bold; text-decoration:none; white-space:nowrap; }
  </style>
</head>
<body>
<header>
  <h1>Project Radar MVP - Vista operativa nazionale</h1>
  <p>Shortlist nazionale OpenCUP per segmenti commerciali Alayan. Non include ancora l'arricchimento ANAC nazionale.</p>
</header>

<main>
  <section class="filters">
    <div><label>Regione</label><select id="region"></select></div>
    <div><label>Provincia</label><select id="province"></select></div>
    <div><label>Comune</label><select id="municipality"></select></div>
    <div><label>Segmento</label><select id="segment"></select></div>
    <div><label>Valore min.</label><input id="valueMin" type="number" min="0" step="1000000"></div>
    <div><label>Testo libero</label><input id="q" placeholder="progetto, committente, CUP"></div>
  </section>

  <section class="meta">
    <div class="pill" id="total"></div>
    <div class="pill" id="shown"></div>
    <div class="pill">Vista limitata ai primi 300 risultati filtrati</div>
  </section>

  <section class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Score</th>
          <th>Progetto</th>
          <th>Segmento</th>
          <th>Regione</th>
          <th>Provincia</th>
          <th>Comune</th>
          <th>Valore</th>
          <th>Committente</th>
          <th>Fonte</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </section>
</main>

<script>
let records = [];
let filtered = [];

const els = {
  region: document.getElementById("region"),
  province: document.getElementById("province"),
  municipality: document.getElementById("municipality"),
  segment: document.getElementById("segment"),
  valueMin: document.getElementById("valueMin"),
  q: document.getElementById("q"),
  tbody: document.getElementById("tbody"),
  total: document.getElementById("total"),
  shown: document.getElementById("shown")
};

function esc(s){return String(s||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
function euro(v){return v ? Number(v).toLocaleString("it-IT",{maximumFractionDigits:0})+" €" : "";}
function opts(values){return ["", ...Array.from(new Set(values.filter(Boolean))).sort()];}
function fill(sel, values, label){const cur=sel.value; sel.innerHTML=""; for(const v of values){const o=document.createElement("option"); o.value=v; o.textContent=v||label; sel.appendChild(o);} if(values.includes(cur)) sel.value=cur;}

function updateFilters(){
  fill(els.region, opts(records.map(r=>r.region)), "Tutte");
  let subset = records;
  if (els.region.value) subset = subset.filter(r=>r.region===els.region.value);
  fill(els.province, opts(subset.map(r=>r.province)), "Tutte");
  if (els.province.value) subset = subset.filter(r=>r.province===els.province.value);
  fill(els.municipality, opts(subset.map(r=>r.municipality)), "Tutti");
  fill(els.segment, opts(records.map(r=>r.segment)), "Tutti");
}

function apply(){
  const q = els.q.value.trim().toLowerCase();
  const min = Number(els.valueMin.value || 0);

  filtered = records.filter(r => {
    if (els.region.value && r.region !== els.region.value) return false;
    if (els.province.value && r.province !== els.province.value) return false;
    if (els.municipality.value && r.municipality !== els.municipality.value) return false;
    if (els.segment.value && r.segment !== els.segment.value) return false;
    if (min && Number(r.value_eur||0) < min) return false;
    if (q) {
      const blob = [r.title,r.client,r.cup,r.region,r.province,r.municipality,r.segment].join(" ").toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });

  render();
}

function render(){
  const rows = filtered.slice(0,300);
  els.total.textContent = "Record totali: " + records.length;
  els.shown.textContent = "Risultati filtrati: " + filtered.length + " - mostrati: " + rows.length;
  els.tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${esc(r.score)}</td>
      <td><strong>${esc(r.title)}</strong><div class="small">CUP: ${esc(r.cup)}</div></td>
      <td>${esc(r.segment)}</td>
      <td>${esc(r.region)}</td>
      <td>${esc(r.province)}</td>
      <td>${esc(r.municipality)}</td>
      <td class="money">${euro(r.value_eur)}</td>
      <td>${esc(r.client)}</td>
      <td><a href="${esc(r.source_url)}" target="_blank">Fonte</a></td>
    </tr>
  `).join("");
}

["region","province"].forEach(id => els[id].addEventListener("change", () => { updateFilters(); apply(); }));
["municipality","segment","valueMin","q"].forEach(id => els[id].addEventListener("input", apply));
["municipality","segment"].forEach(id => els[id].addEventListener("change", apply));

fetch("national_operational_data.json")
  .then(r => r.json())
  .then(data => { records=data; filtered=data; updateFilters(); apply(); });
</script>
</body>
</html>"""

    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"Record nazionali: {len(records)}")
    print(f"JSON: {OUT_JSON}")
    print(f"HTML: {OUT_HTML}")


if __name__ == "__main__":
    main()
