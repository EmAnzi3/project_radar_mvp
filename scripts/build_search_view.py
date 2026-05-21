import csv
import json
import re
from pathlib import Path

INPUT = Path("reports/anac_relevant_awards.csv")
BRANCH_MAP = Path("config/municipality_to_branch.csv")

OUT_JSON = Path("docs/data/anac_relevant_awards.json")
OUT_BRANCH_TERRITORY = Path("docs/data/branch_territory.json")
OUT_HTML = Path("docs/search.html")


def clean(value):
    text = str(value or "")
    text = text.replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def norm(value):
    text = clean(value).upper()
    text = text.replace("'", " ")
    text = re.sub(r"[^A-ZÀ-ÖØ-Ý0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def load_branch_map():
    mapping = {}

    if not BRANCH_MAP.exists():
        print(f"[WARN] Mappa filiali non trovata: {BRANCH_MAP}")
        return mapping

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            municipality_norm = clean(row.get("municipality_norm"))
            province_norm = clean(row.get("province_norm"))

            if not municipality_norm or not province_norm:
                continue

            key = (municipality_norm, province_norm)

            mapping[key] = {
                "branch": clean(row.get("branch")),
                "branch_candidates": clean(row.get("branch_candidates")),
                "branch_confidence": clean(row.get("confidence")),
            }

    print(f"[OK] Mappa comuni → filiali: {len(mapping)} righe")
    return mapping



def build_branch_territory():
    """
    Costruisce la competenza territoriale completa da config/municipality_to_branch.csv,
    indipendentemente dai record disponibili nella vista ANAC.
    """
    territory = {}

    if not BRANCH_MAP.exists():
        return territory

    with BRANCH_MAP.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            branch = clean(row.get("branch"))
            candidates = clean(row.get("branch_candidates"))
            confidence = clean(row.get("confidence"))

            region = clean(row.get("region"))
            province = clean(row.get("province"))
            municipality = clean(row.get("municipality"))

            branches = []

            if branch and branch not in {"AMBIGUA", "NON ASSEGNATA"}:
                branches.append(branch)

            if branch == "AMBIGUA" and candidates:
                branches.extend([b.strip() for b in candidates.split("|") if b.strip()])

            for b in branches:
                territory.setdefault(b, [])

                territory[b].append({
                    "region": region,
                    "province": province,
                    "municipality": municipality,
                    "confidence": confidence,
                })

    # Deduplica
    clean_territory = {}

    for branch, rows in territory.items():
        seen = set()
        out = []

        for r in rows:
            key = (r["region"], r["province"], r["municipality"])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)

        clean_territory[branch] = out

    return clean_territory


def assign_branch(row, branch_map):
    key = (
        norm(row.get("municipality")),
        norm(row.get("province")),
    )

    match = branch_map.get(key)

    if not match:
        return {
            "branch": "NON ASSEGNATA",
            "branch_candidates": "",
            "branch_confidence": "nessuna",
        }

    return match


def main():
    if not INPUT.exists():
        raise SystemExit(f"File non trovato: {INPUT}")

    branch_map = load_branch_map()

    records = []

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in reader:
            branch_data = assign_branch(row, branch_map)

            records.append({
                "branch": branch_data["branch"],
                "branch_candidates": branch_data["branch_candidates"],
                "branch_confidence": branch_data["branch_confidence"],

                "segment": clean(row.get("primary_segment")),
                "cup": clean(row.get("cup")),
                "cig": clean(row.get("cig")),
                "title": clean(row.get("title")),
                "category": clean(row.get("category")),
                "region": clean(row.get("region")),
                "province": clean(row.get("province")),
                "municipality": clean(row.get("municipality")),
                "project_value": to_float(row.get("value_eur")),
                "client": clean(row.get("client")),
                "contractors": clean(row.get("contractors")),
                "contractor_tax_codes": clean(row.get("contractor_tax_codes")),
                "award_date": clean(row.get("award_date")),
                "award_result": clean(row.get("award_result")),
                "source_url": clean(row.get("source_url")),
            })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    branch_territory = build_branch_territory()
    OUT_BRANCH_TERRITORY.write_text(json.dumps(branch_territory, ensure_ascii=False, indent=2), encoding="utf-8")

    html = """<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Project Radar MVP - Ricerca</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f6f7f9; color: #1f2933; }
    header { background: #111827; color: white; padding: 24px 30px; }
    header h1 { margin: 0 0 6px 0; font-size: 26px; }
    header p { margin: 0; color: #d1d5db; font-size: 14px; }
    main { padding: 24px 30px; }
    .filters { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    label { display: block; font-size: 12px; color: #617083; margin-bottom: 5px; }
    select, input { width: 100%; box-sizing: border-box; border: 1px solid #e5e7eb; border-radius: 9px; padding: 9px; font-size: 14px; background: white; }
    button { border: 0; background: #0f766e; color: white; border-radius: 9px; padding: 10px 12px; font-weight: bold; cursor: pointer; }
    .meta { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; color: #617083; font-size: 14px; }
    .pill { background: white; border: 1px solid #e5e7eb; border-radius: 999px; padding: 8px 10px; }
    .table-wrap {
      overflow: auto;
      background: white;
      border-radius: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      max-height: calc(100vh - 340px);
      min-height: 420px;
    }
    table { border-collapse: collapse; width: 100%; min-width: 1650px; }
    th, td { padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; font-size: 14px; }
    th {
      background: #111827;
      color: white;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    tr:hover { background: #f3f4f6; }
    .small { color: #617083; font-size: 12px; margin-top: 4px; }
    .warn { color: #92400e; font-weight: bold; }
    a { color: #0f766e; font-weight: bold; text-decoration: none; }
  
    .nowrap { white-space: nowrap; }
    .money { white-space: nowrap; min-width: 100px; }
    .award-col { white-space: nowrap; min-width: 110px; }
    .source-col { white-space: nowrap; min-width: 65px; }
    .contractors-col { min-width: 360px; max-width: 520px; }
    .oe-line { padding: 0 0 7px 0; margin: 0 0 7px 0; border-bottom: 1px solid #eef2f7; }
    .oe-line:last-child { border-bottom: 0; margin-bottom: 0; padding-bottom: 0; }
    .oe-name { font-weight: bold; overflow-wrap: anywhere; }
    .oe-tax { color: #617083; font-size: 12px; margin-top: 2px; }

  
    /* Desktop/tablet: tabella adattiva, niente fuga verso destra */
    @media (min-width: 761px) {
      .table-wrap {
        overflow-x: hidden;
      }

      table {
        width: 100%;
        min-width: 0 !important;
        table-layout: fixed;
      }

      th, td {
        overflow-wrap: anywhere;
        word-break: normal;
      }

      th:nth-child(1), td:nth-child(1) { width: 17%; }  /* Progetto */
      th:nth-child(2), td:nth-child(2) { width: 6%; }   /* Filiale */
      th:nth-child(3), td:nth-child(3) { width: 7%; }   /* Segmento */
      th:nth-child(4), td:nth-child(4) { width: 7%; }   /* Regione */
      th:nth-child(5), td:nth-child(5) { width: 7%; }   /* Provincia */
      th:nth-child(6), td:nth-child(6) { width: 7%; }   /* Comune */
      th:nth-child(7), td:nth-child(7) { width: 7%; }   /* Valore */
      th:nth-child(8), td:nth-child(8) { width: 12%; }  /* Committente */
      th:nth-child(9), td:nth-child(9) { width: 23%; }  /* Aggiudicatario */
      th:nth-child(10), td:nth-child(10) { width: 7%; } /* Aggiudicazione */
      th:nth-child(11), td:nth-child(11) { width: 4%; } /* Fonte */

      .contractors-col {
        min-width: 0 !important;
        max-width: none !important;
      }

      .money,
      .award-col,
      .source-col {
        white-space: nowrap;
      }

      .oe-line {
        overflow-wrap: anywhere;
      }
    }

  </style>
</head>
<body>
  <header>
    <h1>Project Radar MVP - Ricerca</h1>
    <p>Filtro rapido su progetti, filiali, committenti e aggiudicatari ANAC.</p>
  </header>

  <main>
    <section class="filters">
      <div><label>Filiale</label><select id="branch"></select></div>
      <div><label>Regione</label><select id="region"></select></div>
      <div><label>Provincia</label><select id="province"></select></div>
      <div><label>Comune</label><select id="municipality"></select></div>
      <div><label>Segmento Alayan</label><select id="segment"></select></div>
      <div><label>Valore min. progetto</label><input id="valueMin" type="number" min="0" step="100000" placeholder="es. 1000000"></div>
      <div><label>Valore max. progetto</label><input id="valueMax" type="number" min="0" step="100000" placeholder="es. 20000000"></div>
      <div><label>Data aggiud. da</label><input id="dateFrom" type="date"></div>
      <div><label>Data aggiud. a</label><input id="dateTo" type="date"></div>
      <div><label>Testo libero</label><input id="q" placeholder="progetto, committente, aggiudicatario, CUP, CIG"></div>
      <div><label>&nbsp;</label><button onclick="resetFilters()">Reset</button></div>
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
        <tbody id="tbody"></tbody>
      </table>
    </section>
  </main>

<script>
let records = [];
let branchTerritory = {};
let filtered = [];

const els = {
  branch: document.getElementById("branch"),
  region: document.getElementById("region"),
  province: document.getElementById("province"),
  municipality: document.getElementById("municipality"),
  segment: document.getElementById("segment"),
  valueMin: document.getElementById("valueMin"),
  valueMax: document.getElementById("valueMax"),
  dateFrom: document.getElementById("dateFrom"),
  dateTo: document.getElementById("dateTo"),
  q: document.getElementById("q"),
  tbody: document.getElementById("tbody"),
  total: document.getElementById("total"),
  shown: document.getElementById("shown")
};

function euro(value) {
  if (!value) return "";
  return Number(value).toLocaleString("it-IT", { maximumFractionDigits: 0 }) + " €";
}

function escapeHtml(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function splitPipe(value) {
  return String(value || "")
    .split("|")
    .map(x => x.trim())
    .filter(Boolean);
}

function pairedContractors(namesValue, taxValue) {
  const names = splitPipe(namesValue);
  const taxes = splitPipe(taxValue);

  if (!names.length) return "";

  return names.map((name, i) => {
    const tax = taxes[i] || "";
    return `
      <div class="oe-line">
        <div class="oe-name">${escapeHtml(name)}</div>
        ${tax ? `<div class="oe-tax">${escapeHtml(tax)}</div>` : ""}
      </div>
    `;
  }).join("");
}

function optionList(values) {
  return ["", ...Array.from(new Set(values.filter(Boolean))).sort()];
}

function fillSelect(select, values, label) {
  const current = select.value;
  select.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v || label;
    select.appendChild(opt);
  }
  if (values.includes(current)) select.value = current;
}

function recordBranchList(r) {
  const values = [];

  if (r.branch && r.branch !== "AMBIGUA" && r.branch !== "NON ASSEGNATA") {
    values.push(r.branch);
  }

  if (r.branch_candidates) {
    for (const b of r.branch_candidates.split("|").map(x => x.trim()).filter(Boolean)) {
      values.push(b);
    }
  }

  return Array.from(new Set(values));
}

function branchLabel(r) {
  if (r.branch === "AMBIGUA") {
    return `<span class="warn">AMBIGUA</span><div class="small">${escapeHtml(r.branch_candidates)}</div>`;
  }

  if (r.branch === "NON ASSEGNATA") {
    return `<span class="warn">NON ASSEGNATA</span>`;
  }

  return escapeHtml(r.branch);
}

function populateFilters() {
  const allBranches = [];
  for (const r of records) {
    for (const b of recordBranchList(r)) allBranches.push(b);
  }

  fillSelect(els.branch, optionList(allBranches), "Tutte");
  fillSelect(els.segment, optionList(records.map(r => r.segment)), "Tutti");
  updateDependentFilters();
}

function updateDependentFilters() {
  const branch = els.branch.value;

  let territorySubset = null;

  if (branch && branchTerritory[branch]) {
    territorySubset = branchTerritory[branch];
  }

  // Se c'? una filiale, i menu geografici vengono dalla competenza territoriale.
  // Se non c'? filiale, vengono dai record disponibili.
  const regionSource = territorySubset || records;

  fillSelect(els.region, optionList(regionSource.map(r => r.region)), "Tutte");

  const region = els.region.value;

  let provinceSource = regionSource;
  if (region) {
    provinceSource = provinceSource.filter(r => r.region === region);
  }

  fillSelect(els.province, optionList(provinceSource.map(r => r.province)), "Tutte");

  const province = els.province.value;

  let municipalitySource = regionSource;
  if (region) {
    municipalitySource = municipalitySource.filter(r => r.region === region);
  }
  if (province) {
    municipalitySource = municipalitySource.filter(r => r.province === province);
  }

  fillSelect(els.municipality, optionList(municipalitySource.map(r => r.municipality)), "Tutti");
}

function applyFilters() {
  const branch = els.branch.value;
  const region = els.region.value;
  const province = els.province.value;
  const municipality = els.municipality.value;
  const segment = els.segment.value;
  const valueMin = Number(els.valueMin.value || 0);
  const valueMax = Number(els.valueMax.value || 0);
  const dateFrom = els.dateFrom.value;
  const dateTo = els.dateTo.value;
  const q = els.q.value.trim().toLowerCase();

  filtered = records.filter(r => {
    if (branch && !recordBranchList(r).includes(branch)) return false;
    if (region && r.region !== region) return false;
    if (province && r.province !== province) return false;
    if (municipality && r.municipality !== municipality) return false;
    if (segment && r.segment !== segment) return false;

    if (valueMin && Number(r.project_value || 0) < valueMin) return false;
    if (valueMax && Number(r.project_value || 0) > valueMax) return false;

    if (dateFrom && (!r.award_date || r.award_date < dateFrom)) return false;
    if (dateTo && (!r.award_date || r.award_date > dateTo)) return false;

    if (q) {
      const blob = [
        r.title, r.client, r.contractors, r.contractor_tax_codes,
        r.cup, r.cig, r.municipality, r.province, r.region,
        r.branch, r.branch_candidates
      ].join(" ").toLowerCase();
      if (!blob.includes(q)) return false;
    }

    return true;
  });

  render();
}

function render() {
  const maxRows = 300;
  const rows = filtered.slice(0, maxRows);

  els.total.textContent = "Record totali: " + records.length;
  els.shown.textContent = "Risultati filtrati: " + filtered.length + " ? mostrati: " + rows.length;

  els.tbody.innerHTML = rows.map(r => `
    <tr>
      <td>
        <strong>${escapeHtml(r.title)}</strong>
        <div class="small">CUP: ${escapeHtml(r.cup)} - CIG: ${escapeHtml(r.cig)}</div>
      </td>

      <td>${branchLabel(r)}</td>

      <td>${escapeHtml(r.segment)}</td>

      <td>${escapeHtml(r.region)}</td>

      <td>${escapeHtml(r.province)}</td>

      <td>${escapeHtml(r.municipality)}</td>

      <td class="money">${euro(r.project_value)}</td>

      <td>${escapeHtml(r.client)}</td>

      <td class="contractors-col">${pairedContractors(r.contractors, r.contractor_tax_codes)}</td>

      <td class="award-col">
        ${escapeHtml(r.award_date)}
        <div class="small">${escapeHtml(r.award_result)}</div>
      </td>

      <td class="source-col">
        <a href="${escapeHtml(r.source_url)}" target="_blank">Fonte</a>
      </td>
    </tr>
  `).join("");
}

function resetFilters() {
  els.branch.value = "";
  els.region.value = "";
  els.province.value = "";
  els.municipality.value = "";
  els.segment.value = "";
  els.valueMin.value = "";
  els.valueMax.value = "";
  els.dateFrom.value = "";
  els.dateTo.value = "";
  els.q.value = "";
  updateDependentFilters();
  applyFilters();
}

els.branch.addEventListener("change", () => {
  updateDependentFilters();
  applyFilters();
});
els.region.addEventListener("change", () => { updateDependentFilters(); applyFilters(); });
els.province.addEventListener("change", () => { updateDependentFilters(); applyFilters(); });
els.municipality.addEventListener("change", applyFilters);
els.segment.addEventListener("change", applyFilters);
els.valueMin.addEventListener("input", applyFilters);
els.valueMax.addEventListener("input", applyFilters);
els.dateFrom.addEventListener("input", applyFilters);
els.dateTo.addEventListener("input", applyFilters);
els.q.addEventListener("input", applyFilters);

Promise.all([
  fetch("data/anac_relevant_awards.json").then(r => r.json()),
  fetch("data/branch_territory.json").then(r => r.json())
])
  .then(([data, territory]) => {
    records = data;
    branchTerritory = territory;
    filtered = data;
    populateFilters();
    applyFilters();
  })
  .catch(err => {
    els.tbody.innerHTML = `<tr><td colspan="11">Errore caricamento dati: ${escapeHtml(err)}</td></tr>`;
  });
</script>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"Record JSON: {len(records)}")
    print(f"JSON: {OUT_JSON}")
    print(f"Branch territory JSON: {OUT_BRANCH_TERRITORY}")
    print(f"HTML: {OUT_HTML}")


if __name__ == "__main__":
    main()
