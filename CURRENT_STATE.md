# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **17 progetti / 1.496,9 MW wind**.  
Branch corrente: `feat/wind-radar-enrichment-v0.3`.  
Draft PR: **#2 — Wind Radar v0.3 — contractor hunt, scope coverage e document intelligence**.  
Stato: **non mergiato e non pubblicato**.

## Regola metodologica v0.3

Core scope:
1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per repowering.

Solo A1/A2 con `azienda + progetto + ruolo esecutivo` possono chiudere un core scope. B/C, engineering, DL, CSE, LTA, inspection, development, financing e site management restano intelligence.

## Metriche correnti

Invariate dopo Priority 1 + Public Pass 6 + Industry Press Pass 7 + glossario:

- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope applicabili coperti = **7,4%**;
- il KPI MW indica presenza di almeno uno scope noto, non BoP completo.

Coperture correnti:
- Serra Palino: Civil + Electrical;
- Venusia: Civil/site preparation;
- Carlentini: Foundation;
- Tarsia Ovest: Civil + Electrical + SSE/grid;
- Castelfranco/CER: SSE/grid.

## Intelligence consolidata

- **Andretta-Bisaccia** — Edison 18 WTG / 88,5 MW come baseline operativa da riconciliare con pista Edison 13 WTG / 85,8 MW; Progeco B site/construction management; GEKO A1 engineering/cantierizzazione; apertura cantiere 02/11/2026.
- **Serra Giannina** — 42 MW / 6 WTG, costruzione RWE avviata; D'Agostino B site presence; EGM B tecnica; nessun BoP A1/A2.
- **ALAS** — 66 MW / 10 WTG; Hydro A1 progettista opere civili, non Civil BoP; distinta Alas 2 50,4 MW / 7 WTG.
- **Greci-Montaguto** — 43,8 MW, costruzione marzo 2026 → estate 2027; Vestas OEM A2; RINA B inspection.
- **Nulvi-Ploaghe** — 121,5 MW / 27 WTG; Hydro A2 development/engineering; circa 40 mln € a imprese/fornitori locali ma nessun nome esecutivo verificato; DUVRI legacy escluso; distinto Nulvi-Tergu.
- **Tricarico** — 42 MW / 7 Vestas V162-6MW; installation Vestas resta B; Vector A2 LTA/construction monitoring; UniCredit financial close 46,5 mln €, target operativo H2 2027; distinto Dolomiti Windfarm 79,2 MW.
- **Venusia** — Idoka A2 Civil; EGM A2 engineering/DL; Nordex OEM A2; New Developments A2; record corretto a 8 × 5,6 MW.
- **Serra Palino** — D'Agostino A2 Civil + Electrical/electromechanical; Nordex OEM A2.
- **Tarsia Ovest** — RTI A2 Civil + Electrical; PLC A2 SSE/grid; Michelangelo Mammana B civil hint; Concessione 139/2026 resta access lead, non Logistics.
- **Castelfranco/CER** — CER / CUP 9439 / 5 WTG; Vestas OEM A2; PLC A2 SSE/grid; Energy& B; distinto Fri-El / Miscano 29,4 MW / CUP 9207.
- **Carlentini** — Gruppo Mammana Foundation/concrete; Hydro foundation engineering/quality + DL; BFP CSP/CSE; solo Foundation chiude scope.
- **Alia-Sclafani** — 55 MW / 9 Vestas; storico Staffetta 2019 separato dal repowering corrente; FM Service Group resta C candidate site-services.
- **Fenice** — NVA Fenice 51 WTG / 367,2 MW; ATS Engineering A1 design, non contractor; REL101/REL102 letti; nessun cronoprogramma distinto emerso.
- **Toritto** — 108 MW wind + 50 MW BESS; permitting/VIA; cronoprogramma 503 giorni solo relativo.
- **Sava-Maruggio / Volturino / Lama Cupa** — nessun nuovo lead contractor utile; Brulli resta riferita alla SE Casamassima / FLYNIS PV 34, non a Lama Cupa.

## Pass conclusi il 5 settembre

- `docs/wind/research/2026-09-05-contractor-priority1-pass-5.md`
- `docs/wind/research/2026-09-05-public-pass-6.md`
- `docs/wind/research/2026-09-05-industry-press-pass-7.md`
- `docs/wind/research/2026-09-05-identity-reconciliation.md`
- `docs/wind/research/2026-09-05-v03-final-validation.md`
- `docs/wind/research/2026-09-05-glossary-validation.md`

## Industry & market intelligence

Audit 17/17 su pv magazine Italia, Rinnovabili.it, QualEnergia.it, Staffetta, Quotidiano Energia e stampa internazionale.

Registro:
`docs/wind/data/industry-press-intelligence-2026-09-05.json`

Il drawer mostra una sezione separata **Industry & market intelligence**. Financing, lead C, storico e identity collision non entrano nella Contractor View e non influiscono sugli execution scope.

## Glossario per utenti non tecnici

Aggiunto nella v0.3:
- `docs/wind/data/glossary.json` — **37 termini**;
- `docs/wind/assets/glossary.js`;
- `docs/wind/assets/glossary.css`;
- pulsante **Glossario** accanto a **Legenda fonti A1–D**.

Categorie: Impianto, Cantiere, Rete, Tempi, Mercato, Soggetti, Ruoli tecnici, Autorizzazioni, Metodo Radar.

Le definizioni usano linguaggio comune e chiariscono esplicitamente le distinzioni utili a evitare false interpretazioni, ad esempio OEM ≠ erection, DL/LTA ≠ esecutore, RTI ≠ scope individuale.

### Validazione glossario

PASS desktop 1440 px + mobile 390 px:
- 37 termini / 9 categorie;
- ricerca funzionante (`BoP`, `WTG`, `autorizzazione`, `OEM`);
- singolare/plurale corretto;
- `Esc` chiude e restituisce il focus;
- nessun overflow orizzontale;
- JavaScript passa `node --check`.

## Final validation v0.3

Data/regression gate:
- 17 progetti / 1.496,9 MW;
- 8/108 scope / 230,9 MW invariati;
- guardie Progeco, Vestas-installation, Nordex, Mammana, Energy&, Carlentini, ALAS, Fenice e Lama Cupa passate;
- Industry registry privo di chiavi che possano trasformare il discovery layer in execution scope.

Browser gate Chromium/Playwright:
- desktop: Tricarico, Castelfranco/CER, Alia-Sclafani, Venusia e glossario verificati;
- mobile 390 px: Tricarico, Venusia e glossario verificati;
- nessun overflow orizzontale;
- nessun errore console attribuibile alle nuove funzioni;
- KPI visivi coerenti con 230,9 MW e 8/108.

## Stato

**v0.3 conclusa per enrichment/research, rappresentazione UI e glossario; pronta per revisione utente e step successivi.**

La PR resta **Draft, non mergiata e non pubblicata**. Nessun merge senza approvazione esplicita.
