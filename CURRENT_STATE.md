# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **v0.5.0**.

Merge v0.5:
- PR **#4 — Wind Radar v0.5 — canonical promotion e commercial enrichment**;
- merge commit `f2640616540e02448664677427698d808938520f`;
- GitHub Pages run `33972645972`: **SUCCESS**.

Stato produzione: **mergiato e pubblicato da `master/docs`**.

## Baseline canonica v0.5

Il Radar canonico comprende:
- **51 progetti**;
- **11.202,52 MW wind** complessivi;
- **34 progetti** promossi dal discovery v0.4;
- **9.705,62 MW wind + 311 MW BESS** relativi ai 34 promossi;
- BESS sempre separato dai MW wind.

I 17 seed storici restano baseline di regressione:
- **1.496,9 MW wind**;
- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope onshore coperti;
- **437,7 MW** in costruzione E7.

Restano blocked nel Discovery v0.5:
- Med Wind Grecale;
- Rospo Offshore;
- Sindia-Macomer 43,4 MW;
- Le Chiancate.

Regole canoniche invarianti:
- nessun contractor per deduzione;
- solo evidenza project-specific A1/A2 esplicita può chiudere uno scope esecutivo;
- B/C restano segnali;
- owner/developer/advisor/engineering/survey/supervisione non equivalgono a contractor esecutivo;
- VIA positiva non equivale ad AU/FID/procurement/cantiere;
- Terna aggregata non genera identità progetto;
- onshore/offshore usano scope profile distinti;
- nessuna coordinata simulata;
- GlobalData resta lead/enrichment non canonico.

# Fase corrente — v0.6

Branch:
`feat/wind-radar-v0.6-execution-intelligence`

Draft PR:
**#5 — Wind Radar v0.6 — execution intelligence e commercial timing**.

La PR resta **Draft**. Nessun merge o pubblicazione v0.6 senza revisione esplicita.

La v0.6 sviluppa tre reti collegate ma probatoriamente separate:
1. **Project Execution Intelligence**;
2. **Company / Commercial Network**;
3. **Institutional & Source Network**.

## Stato rete e runtime

Stato corrente:
- **61 player commerciali** nel Company Network;
- **31 nodi istituzionali/pubblici**;
- **21 adapter istituzionali eseguibili**;
- Company Watch operativo sulle fonti dirette;
- Project Execution investigation queue operativa sui canonici E4–E7 con scope aperti;
- workflow periodico predisposto, ma non attivo finché la Draft PR non entra nel branch di default.

Pattern agent-style riusato da `pv_agent_mvp` e adattato all'eolico:

`fonti -> agent/collector -> raw findings -> change history -> reconciliation/evidence gate -> canonico/UI`

Moduli principali:
- `app/wind_agents/base.py` — contract comune dei finding;
- `app/wind_agents/planner.py` — code/cadenze Institutional, Company e Project Execution;
- `app/wind_agents/state.py` — SQLite separato per raw finding, eventi, cursori e `watch_status`;
- `app/wind_agents/evidence.py` — gate probatorio centralizzato;
- `app/wind_agents/runner.py` — runner istituzionale resiliente e cadence-aware;
- `app/wind_agents/company_watch.py` — watch diretto player;
- `app/wind_agents/reconcile.py` — reconciliation conservativa + digest review-only;
- `app/wind_agents/execution_watch.py` — coda contractor-hunt E4–E7 per singolo scope;
- `scripts/run_wind_agents.py` — CLI operativa.

Persistenza runtime separata dal canonico:
- `raw_findings`;
- `finding_events` con `new / changed / unchanged`;
- `source_cursors`;
- `watch_status` con ultimo tentativo/successo/errore.

## Adapter istituzionali eseguibili — 21

1. `mase-via`;
2. `mase-provvedimenti`;
3. `terna-econnextion`;
4. `lazio-regional`;
5. `toscana-gea`;
6. `toscana-atos`;
7. `sardegna-sira`;
8. `sicilia-sivvi`;
9. `puglia-sistema-energia`;
10. `campania-viavas`;
11. `calabria-via`;
12. `basilicata-via`;
13. `emilia-romagna-regional`;
14. `lombardia-regional`;
15. `piemonte-regional`;
16. `umbria-regional`;
17. `veneto-regional`;
18. `abruzzo-via`;
19. `liguria-via-procedimenti`;
20. `marche-via-regional`;
21. `molise-au-eolico`.

Abruzzo e Molise usano un fallback trasparente `source_channel_snapshot` quando non sono disponibili righe progetto server-side. Liguria conserva il guard di riconciliazione MASE per le VIA nazionali del mirror regionale. Terna Econnextion resta market intelligence aggregata e non genera progetti/contractor/scope.

Sistema Puglia usa high-water cursor persistente, forward probe e lookback breve invece di ripetere un backfill massivo.

Sicilia SI-VVI usa un percorso resiliente: CSV ufficiale come prima fonte e fallback ufficiale SI-VVI/MapServer se il download CSV non è disponibile.

## Live validation

Il live smoke completo sul current branch è ora passato.

**Wind Radar live source smoke #36 — SUCCESS**:
- `national-market` — SUCCESS;
- `priority-regional` — SUCCESS;
- `centre-north` — SUCCESS;
- `south-islands` — SUCCESS.

Nel gruppo Sud/Isole:
- **268 finding** complessivi;
- **0 errori**;
- Calabria: **103 project-specific findings**;
- Sicilia: **164 project-specific findings**;
- Sardegna: **1 project-specific finding**;
- Basilicata, Campania e Sistema Puglia: `empty_success` nel pass osservato.

La Sicilia, che nel run precedente andava in timeout sul CSV, è quindi passata a `project_data` con 164 finding grazie alla strategia resiliente.

## Project-specific enrichment v0.6

I file additivi `commercial-enrichment-v06.json`, `v06b.json` e `v06c.json` conservano le nuove evidenze senza riscrivere il canonico v0.5.

### Andretta-Bisaccia
- Progeco Group: A2 project-specific per project management / construction supervision support; non execution award;
- MASE/Edison A1: configurazione corrente **18 WTG / 88,5 MW** e documentazione di avvio lavori;
- Vestas A2 resta configurazione/ordine OEM storico corrente ma non identifica i contractor BoP;
- Civil, Electrical, SSE/grid, erection, dismantling, logistics e foundations restano aperti.

### Carlentini
- Mammana Michelangelo S.p.A.: **Foundation contractor — A2 confirmed** sul repowering corrente;
- Hydro Engineering: **Direzione Lavori / foundation engineering & quality control — A2 confirmed**, non-execution;
- nessuna estensione automatica Mammana al full Civil BoP.

### Tricarico
- UniCredit: A2 financial-close signal da €46,5m;
- Vector Renewables: **Lender's Technical Advisor / construction monitoring — A2 confirmed**, non-execution;
- Vestas OEM A2;
- Civil, Electrical, SSE, erection, logistics e foundations restano aperti.

### Greci-Montaguto
- Regione Campania/BURC A1: configurazione corrente **6 × Vestas V136 4,5 MW + 4 × Vestas V117 4,2 MW**;
- Vestas A2: OEM + AOM 5000;
- ERG A2 kick-off: cantiere da **marzo 2026**, circa **40 persone medie**, commissioning delle nuove WTG previsto **estate 2027**;
- nessun nuovo contractor BoP dedotto.

### Nulvi-Ploaghe
- Hydro Engineering: development/engineering A2, non-execution;
- ERG: E4 / fully authorised / Route-to-Market eligible;
- nuovo segnale A2 developer-direct: **27 nuove WTG da 4,5 MW, investimento ~€170m, produzione ~300 GWh/anno**;
- tutti gli scope procurement/execution principali restano aperti.

### Serra Giannina
- EGM Project: A2 construction-phase technical / site follow-up, non-execution;
- D'Agostino Costruzioni Generali: B project-specific mobilisation lead;
- recruiting project-specific attribuito a D'Agostino copre Site Manager, assistenza cantiere, HSE/qualità, ambiente, amministrazione e ufficio tecnico: lead più forte, ma ancora B in assenza di award diretto RWE/D'Agostino;
- nessun Civil BoP chiuso per deduzione.

### Alia-Sclafani
- Comune di Alia A1: PAS corrente per **9 WTG / 55 MW**, con dismissione delle 30 turbine esistenti;
- Vestas A2: 9 WTG correnti e delivery H2 2026;
- SOCEP A2 è verificata come **same-site historical supplier** per piazzole, lavori di sottostazione e consolidamenti sul vecchio impianto Asja;
- SOCEP resta esplicitamente `historical`, non è un award sul repowering corrente.

## Company Watch

Il monitor commerciale usa le `watch_urls` dei 61 player:
- A/A+: 7 giorni;
- B: 14 giorni;
- C / universe refresh: 30 giorni, salvo override.

Un finding company-direct resta normalmente:
- `source_grade_ceiling = A2`;
- `project_specific = false`;
- `execution_scope = null`;
- layer `network_intelligence`.

Un link noto tra azienda e progetto aiuta la reconciliation, ma non trasforma automaticamente il finding in execution evidence.

## Reconciliation e digest

`app/wind_agents/reconcile.py` confronta i finding `new/changed` con canonico e Discovery usando nome, URL, geografia, MW, developer/proponente, regione e link di registry.

`high_confidence_match` resta advisory: nessuna write automatica su canonico/Discovery e nessun cambio automatico di stage, priority, scope o contractor.

Digest action types:
- `canonical_update_review`;
- `discovery_refresh_review`;
- `new_project_lead`;
- `company_project_signal`;
- `company_network_update`;
- `market_intelligence`.

## Project Execution investigation queue

`app/wind_agents/execution_watch.py` trasforma i canonici E4–E7 con scope aperti in una coda ordinata per urgenza considerando stage, priorità, milestone e numero di gap.

Priorità corrente della contractor hunt:
1. Andretta-Bisaccia;
2. Tricarico;
3. Nulvi-Ploaghe;
4. Serra Giannina;
5. Greci-Montaguto;
6. Alia-Sclafani.

La queue è investigativa: nessun contractor viene confermato senza A1/A2 project-specific.

## UI v0.6 — mappa province

La precedente mappa a marker puntuali non scala più con il numero crescente di progetti.

Sul branch v0.6 è stata sostituita, nella vista principale, da una **choropleth per provincia** ispirata a `EmAnzi3/pv_echarts`:
- ECharts 5;
- GeoJSON province Openpolis;
- normalizzazione dei nomi provincia con alias compatibili con `pv_echarts`;
- metriche selezionabili: **MW eolici**, **N. progetti**, **MW E4+**;
- tooltip con MW, numero progetti, E4+, E7, priorità A/A+, progetti senza contractor esecutivo A1/A2 e BESS separato;
- click sulla provincia applica la provincia come filtro al Radar;
- ogni progetto viene conteggiato una sola volta sulla provincia canonica principale per evitare duplicazioni MW;
- offshore trattato come aggregazione amministrativa/territoriale, non footprint delle WTG in mare;
- fallback ordinato per provincia se ECharts/GeoJSON non sono disponibili.

File:
- `docs/wind/assets/province-map-v06.js`;
- `docs/wind/assets/province-map-v06.css`;
- `scripts/check_wind_v06_map.py`.

La vecchia mappa marker resta solo come compatibilità DOM nascosta per non alterare il runtime legacy prima del refactor completo; non è più la visualizzazione mostrata all'utente.

## Validazione current head

**Wind Radar v0.6 checks #219 — SUCCESS**.

Valida fra l'altro:
- regressioni v0.3/v0.4/v0.5;
- canonico v0.5 invariato;
- Company Network;
- Institutional Network;
- 21 adapter e planner/cadenze;
- raw/history persistence, cursori e evidence gate;
- reconciliation/digest ed execution queue;
- project-specific commercial enrichment v0.6/v0.6b;
- deep enrichment v0.6c;
- mappa province v0.6;
- sintassi JavaScript.

Un check verde dimostra coerenza del codice e delle regressioni. La disponibilità live delle fonti è coperta separatamente dal live smoke.

## Workflow periodico predisposto

`.github/workflows/wind_agent_watch.yml` prevede:
- trigger giornaliero 05:40 UTC;
- source/company watch solo se `due`;
- SQLite persistente via cache;
- resilienza al guasto di una singola fonte;
- `institutional-run.json`;
- `company-run.json`;
- `execution-queue.json`;
- `digest.json`;
- GitHub Step Summary + artifact 30 giorni;
- nessuna scrittura automatica del canonico;
- nessun commit automatico.

**Lo schedule non è ancora attivo**: diventerà operativo solo dopo eventuale approvazione e merge della v0.6.

## Lavoro ancora aperto v0.6

1. continuare la contractor hunt A1/A2 sui pacchetti di Andretta-Bisaccia, Tricarico, Nulvi-Ploaghe, Serra Giannina, Greci-Montaguto e Alia-Sclafani;
2. cercare una fonte diretta RWE/D'Agostino che elevi o smentisca il B-signal Serra Giannina;
3. verificare gli `empty_success` di Basilicata, Campania e Sistema Puglia per distinguere assenza reale di nuovi record da copertura del parser ancora migliorabile;
4. approfondire SPA/API Abruzzo e Molise e i percorsi AU/BUR regionali;
5. completare dettaglio/GIS Sicilia oltre la prima acquisizione project-level;
6. continuare l'ampliamento ANEV/non-ANEV del network commerciale;
7. eseguire preview/browser review desktop+mobile della nuova mappa province e delle altre modifiche UI prima di qualunque merge.
