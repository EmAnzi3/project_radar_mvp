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
- **34 progetti** promossi dal discovery v0.4 tramite promotion gate controllato;
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
- owner/developer/advisor/engineering/survey non equivalgono a contractor esecutivo;
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

## Network v0.6

Stato corrente:
- **58 player commerciali** classificati per capability, priorità, relazione, fonti da monitorare e prossima azione;
- **31 nodi istituzionali/pubblici** censiti;
- **21 adapter istituzionali eseguibili**;
- Company Watch operativo sulle fonti dirette;
- Project Execution investigation queue operativa sui canonici E4–E7 con scope ancora aperti.

La tranche commerciale più recente aggiunge:
- Blu Costruzioni;
- EGM Project;
- Barone Costruzione;
- Gruppo Novello;
- La Molisana Trasporti;
- Pizzulo Costruzioni;
- SIMIC;
- F&C Wind Service.

Guard specifici:
- la referenza storica Blu su Carlentini **non** prova un ruolo nel repowering ERG corrente;
- la prossimità geografica/capability di Pizzulo rispetto ad Andretta-Bisaccia è un lead commerciale, **non** un award;
- EGM è collegata a Serra Giannina come presenza/engineering non-execution finché non emerge un ruolo esecutivo esplicito;
- capability Full BoP/EPC storica o generica non chiude scope su alcun canonico.

ESPE resta target A adiacente ad alto valore, senza attribuirle Full BoP utility-scale wind in assenza di prova.

## Architettura agent-style

Pattern riusato da `pv_agent_mvp` e adattato all'eolico:

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
- `scripts/run_wind_agents.py` — CLI operativa;
- `scripts/check_wind_v06_agents.py` — regressioni architetturali/probatorie.

Persistenza runtime separata dal canonico:
- `raw_findings`;
- `finding_events` con `new / changed / unchanged`;
- `source_cursors`;
- `watch_status` con ultimo tentativo/successo/errore.

## Adapter istituzionali eseguibili — 21

1. `mase-via` — MASE VIA;
2. `mase-provvedimenti` — MASE provvedimenti/esiti;
3. `terna-econnextion` — Terna Econnextion, solo market intelligence aggregata;
4. `lazio-regional` — Lazio VIA/PAUR;
5. `toscana-gea` — Toscana GeA;
6. `toscana-atos` — ATOS Toscana FER;
7. `sardegna-sira` — Sardegna SIRA;
8. `sicilia-sivvi` — Sicilia SI-VVI, prima tranche CSV;
9. `puglia-sistema-energia` — Sistema Puglia Energia;
10. `campania-viavas` — Campania VIA/PAUR;
11. `calabria-via` — Calabria VIA/PAUR;
12. `basilicata-via` — Basilicata VIA/Screening;
13. `emilia-romagna-regional` — Emilia-Romagna VIA/VAS;
14. `lombardia-regional` — Lombardia SILVIA;
15. `piemonte-regional` — Piemonte SKVIA;
16. `umbria-regional` — Umbria VIA/PAUR/Screening;
17. `veneto-regional` — Veneto VIA/VAS;
18. `abruzzo-via` — piattaforma Valutazioni Ambientali Abruzzo;
19. `liguria-via-procedimenti` — SIRAVIAVAS Liguria;
20. `marche-via-regional` — registro avvio procedimenti VIA Marche;
21. `molise-au-eolico` — canali regionali Eolico / Eolico-VIA nazionale Molise.

Abruzzo e Molise adottano una regola di trasparenza aggiuntiva: se il portale espone solo SPA/API e non sono parseabili righe progetto server-side, l'adapter emette un `source_channel_snapshot` non project-specific. Il canale risulta quindi osservato, ma non viene falsamente dichiarata acquisizione di dati progetto.

Liguria conserva un guard per le VIA nazionali presenti nel mirror regionale: prima di qualunque azione identitaria devono riconciliarsi con MASE.

Sistema Puglia usa high-water cursor persistente, forward probe e lookback breve invece di ripetere il backfill massivo.

## Company Watch

Il monitor commerciale usa le `watch_urls` dei 58 player:
- A/A+: 7 giorni;
- B: 14 giorni;
- C / universe refresh: 30 giorni, salvo override.

Per ridurre falsi cambi vengono conservati heading e segmenti con segnali eolici/commerciali: award, contract, construction, BoP, civili, elettrico, grid, fondazioni, erection, logistica, commissioning, procurement, partnership, supplier ecc.

Un finding company-direct resta:
- `source_grade_ceiling = A2`;
- `project_specific = false`;
- `execution_scope = null`;
- layer `network_intelligence`.

Un link già noto tra azienda e progetto aiuta la reconciliation, ma **non trasforma** il finding in execution evidence.

## Reconciliation e digest

`app/wind_agents/reconcile.py` confronta i finding `new/changed` con canonico e Discovery usando:
- nome progetto;
- URL fonte;
- geografia;
- MW;
- developer/proponente;
- regione;
- link di registry come indizio.

`high_confidence_match` richiede identità forte, punteggio e margine sufficienti. Il risultato resta advisory: nessuna write automatica su canonico/Discovery, nessun cambio di stage/priority/scope/contractor.

Digest action types:
- `canonical_update_review`;
- `discovery_refresh_review`;
- `new_project_lead`;
- `company_project_signal`;
- `company_network_update`;
- `market_intelligence`.

## Project Execution investigation queue

`app/wind_agents/execution_watch.py` trasforma i canonici E4–E7 con scope aperti in una coda di indagine ordinata per urgenza.

L'urgenza considera:
- stage E4–E7;
- priorità A+/A/B;
- prossima milestone entro 30/90/180 giorni;
- numero di scope ancora aperti.

Per ogni gap viene generato un playbook di ricerca specifico. Esempi:
- Civil BoP → developer/tender, AU/PAUR, civil EPC watch;
- Electrical BoP/SSE → grid specs, Terna/connection acts, electrical EPC;
- Erection → OEM news, heavy-lift/erection player, site mobilisation;
- Logistics → transport/access plan, heavy transport player, atti stradali locali;
- offshore → T&I, cable procurement, OSS, port/marine logistics, landfall.

Il comando CLI è:
`python scripts/run_wind_agents.py execution-queue`

La queue è investigativa: **nessun contractor viene confermato senza A1/A2 project-specific**.

## Workflow periodico predisposto

`.github/workflows/wind_agent_watch.yml` prevede:
- trigger giornaliero 05:40 UTC;
- esecuzione solo dei source/company watch effettivamente `due`;
- SQLite persistente via cache;
- resilienza al guasto di un singolo portale;
- `institutional-run.json`;
- `company-run.json`;
- `execution-queue.json`;
- `digest.json`;
- GitHub Step Summary + artifact 30 giorni;
- nessuna scrittura automatica del canonico;
- nessun commit automatico.

**Lo schedule non è ancora attivo**: diventerà operativo solo se il workflow entrerà nel branch di default dopo approvazione della v0.6.

## Validazione e trasparenza

Il workflow PR verifica:
- regressioni v0.3/v0.4/v0.5;
- Company Network;
- Institutional Network;
- import/sintassi adapter;
- allineamento adapter/registry;
- planner/cadenze;
- raw/history persistence;
- cursori/high-water;
- evidence gate;
- reconciliation/digest;
- execution investigation queue;
- JavaScript UI.

Un check verde dimostra coerenza del codice e delle regressioni, **non** che tutti i portali esterni siano raggiungibili live. Ogni adapter resta `eseguibile` finché un run live non ne attesta il comportamento corrente.

## Lavoro ancora aperto v0.6

1. effettuare **run live controllati dei 21 adapter** e correggere eventuali drift;
2. approfondire gli endpoint SPA/API di Abruzzo e Molise per evitare, quando possibile, il solo channel snapshot;
3. completare dettaglio/GIS Sicilia;
4. continuare la contractor hunt A1/A2 su Andretta-Bisaccia, Tricarico, Nulvi-Ploaghe, Serra Giannina, Greci-Montaguto, Carlentini e Alia-Sclafani;
5. usare la nuova execution queue per guidare la ricerca documentale per singolo scope;
6. ampliare ulteriormente il census ANEV/non-ANEV e incorporare nuovi player trovati nei documenti di progetto e nelle fonti istituzionali.
