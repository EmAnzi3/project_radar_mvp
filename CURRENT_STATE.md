# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **v0.5.0**.

- PR v0.5: **#4 — Wind Radar v0.5 — canonical promotion e commercial enrichment**
- merge commit: `f2640616540e02448664677427698d808938520f`
- produzione: `master/docs`
- baseline canonica invariata: **51 progetti / 11.202,52 MW wind**
- BESS sempre separato dai MW wind.

## Fase corrente — v0.6

Branch esistente:
`feat/wind-radar-v0.6-execution-intelligence`

Draft PR esistente:
**#5 — Wind Radar v0.6 — execution intelligence e commercial timing**.

La PR deve restare **Draft**. Nessun merge o pubblicazione senza revisione esplicita.

La v0.6 sviluppa tre reti collegate ma probatoriamente separate:
1. **Project Execution Intelligence**;
2. **Company / Commercial Network**;
3. **Institutional & Source Network**.

Pipeline:
`fonti -> agent/collector -> raw findings -> change history -> reconciliation/evidence gate -> canonico/UI`

### Regola probatoria invariabile

- solo evidenza **project-specific A1/A2** può chiudere uno scope esecutivo;
- nessun contractor per deduzione;
- B/C restano segnali;
- owner/developer/advisor/engineering/DL/supervision non equivalgono a execution;
- storico stesso sito non implica award sul progetto corrente;
- OEM non implica BoP;
- BESS resta separato dai MW wind;
- onshore/offshore mantengono scope profile distinti.

## Runtime e network

Stato corrente:
- **61 player commerciali**;
- **31 nodi istituzionali/pubblici**;
- **21 adapter istituzionali eseguibili**;
- Company Watch operativo;
- Project Execution investigation queue sui canonici E4–E7 con scope aperti;
- SQLite operativo separato dal canonico per raw finding, history, cursori e `watch_status`;
- reconciliation conservativa e digest review-only;
- nessuna scrittura automatica nel canonico.

Adapter eseguibili:
`mase-via`, `mase-provvedimenti`, `terna-econnextion`, `lazio-regional`, `toscana-gea`, `toscana-atos`, `sardegna-sira`, `sicilia-sivvi`, `puglia-sistema-energia`, `campania-viavas`, `calabria-via`, `basilicata-via`, `emilia-romagna-regional`, `lombardia-regional`, `piemonte-regional`, `umbria-regional`, `veneto-regional`, `abruzzo-via`, `liguria-via-procedimenti`, `marche-via-regional`, `molise-au-eolico`.

Il full live source smoke più recente sul runtime è **#56 — SUCCESS** su tutti i quattro gruppi:
- `national-market`;
- `priority-regional`;
- `centre-north`;
- `south-islands`.

## Project-specific enrichment v0.6

Le tranche `commercial-enrichment-v06.json`, `v06b.json`, `v06c.json` e `v06d.json` sono additive e non riscrivono silenziosamente il canonico v0.5.

### Andretta-Bisaccia
- Progeco Group: A2 project-specific per site management / construction supervision support, **non execution award**;
- MASE/Edison A1: configurazione corrente **18 WTG / 88,5 MW**;
- Vestas A2: OEM/configurazione, non BoP;
- Civil, Electrical, SSE/grid, erection, dismantling, logistics e foundations restano aperti.

### Tricarico
- UniCredit: A2 financial close da €46,5m;
- Vector Renewables: A2 Lender's Technical Advisor / construction monitoring, non execution;
- Vestas OEM;
- Civil, Electrical, SSE/grid, erection, logistics e foundations restano aperti.

### Nulvi-Ploaghe
- Hydro Engineering: development/engineering A2, non execution;
- ERG A2: fully authorised / Route-to-Market, **27 nuove WTG da 4,5 MW**, investimento ~€170m, produzione ~300 GWh/anno;
- procurement/execution principali ancora aperti.

### Serra Giannina
- EGM Project: construction-phase technical/site follow-up, non execution;
- D'Agostino Costruzioni Generali: lead project-specific rafforzato da recruiting e coinvolgimento diretto employee-level;
- il segnale D'Agostino resta **B**: nessun Civil BoP o altro scope viene chiuso senza fonte corporate/atto project-specific A1/A2.

### Greci-Montaguto
- Regione Campania/BURC A1: configurazione corrente **6 × Vestas V136 4,5 MW + 4 × Vestas V117 4,2 MW**;
- Vestas A2: OEM + AOM 5000;
- ERG A2: construction start marzo 2026, circa 40 persone medie, commissioning previsto estate 2027;
- `v06d`: **PROGETTO ENERGIA S.r.l.** A1 project-specific per progettazione/executive design, esplicitamente non execution;
- nessun nuovo contractor BoP attribuito.

### Alia-Sclafani
- Comune di Alia A1: PAS corrente **9 WTG / 55 MW**, rimozione 30 turbine esistenti;
- Vestas A2: 9 WTG correnti;
- SOCEP A2: same-site historical supplier, mantenuta `historical` e non attribuita al repowering corrente.

### Carlentini
- Mammana Michelangelo S.p.A.: **Foundation contractor A2 confirmed** sul repowering corrente;
- Hydro Engineering: DL / foundation engineering & quality control A2, non execution;
- Mammana non viene estesa automaticamente al full Civil BoP.

La tranche `v06d` **non chiude alcun nuovo scope execution**.

## UI v0.6 — mappa per provincia

La vecchia mappa a marker è stata sostituita nella vista utente da una **choropleth ECharts delle province italiane**, ispirata a `EmAnzi3/pv_echarts`.

Caratteristiche:
- GeoJSON province Openpolis con fallback;
- alias provincia normalizzati;
- metriche: **MW eolici**, **N. progetti**, **MW E4+**;
- ogni progetto conteggiato una sola volta sulla provincia canonica principale;
- BESS separato;
- tooltip con MW, progetti, E4+, E7, priorità A/A+, gap execution e top project;
- `roam`/zoom ECharts;
- **filtro Provincia dedicato**: il click sulla mappa non sovrascrive più la ricerca testuale;
- `Mostra tutte` rimuove solo il filtro provincia e preserva gli altri filtri;
- reset filtri coerente.

### Browser review eseguita

Verifica reale completata su preview locale del branch:
- desktop **1440 × 1100**;
- mobile **390 × 844**;
- 51 progetti / 29 province rappresentate;
- rendering ECharts `map` effettivo, `visualMap` e `roam` attivi;
- nessun overflow orizzontale desktop/mobile;
- ricerca testuale + Provincia combinabili senza perdita del testo;
- click provincia, `Mostra tutte`, reset e cambio metrica verificati;
- nessun errore console attribuibile al Radar;
- tooltip inizialmente troppo alto/tagliato sul bordo inferiore: corretto con `confine:true`, larghezza bounded e rimozione della metrica duplicata; successiva verifica desktop/mobile superata.

La preview tecnica non modifica `master` e il workflow temporaneo usato per costruire il bundle è stato rimosso dal branch dopo la review.

## Validazione

Prima della rifinitura tooltip:
- **Wind Radar v0.6 checks #227 — SUCCESS**;
- **Wind Radar live source smoke #56 — SUCCESS**.

Le modifiche UI successive sono coperte dal validator `scripts/check_wind_v06_map.py`, che ora verifica anche:
- filtro Provincia dedicato;
- ricerca testuale preservata;
- tooltip confinato;
- larghezza tooltip bounded;
- nessuna duplicazione della metrica selezionata.

Il numero del check sul current head finale è riportato nel body della Draft PR #5 dopo il completamento della CI di closeout.

## Gate successivo

Il codice e la review tecnica desktop/mobile sono completati. Il prossimo gate è **revisione visiva dell'utente sulla Draft PR / preview**.

Restano volutamente aperti i contractor hunt A1/A2 sui pacchetti non ancora provati di Andretta-Bisaccia, Tricarico, Nulvi-Ploaghe, Serra Giannina, Greci-Montaguto, Alia-Sclafani e sugli altri E4–E7 prioritari: la mancanza di un award verificato non viene colmata per deduzione.

**Nessun merge e nessuna pubblicazione prima dell'approvazione esplicita.**
