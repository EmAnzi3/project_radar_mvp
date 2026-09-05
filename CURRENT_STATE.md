# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **v0.5.0**.

Merge v0.5:
- PR **#4 — Wind Radar v0.5 — canonical promotion e commercial enrichment**;
- merge commit `f2640616540e02448664677427698d808938520f`;
- GitHub Pages run `33972645972`: **SUCCESS**.

Stato: **mergiato e pubblicato da `master/docs`**.

## Baseline canonica v0.5

Il Radar canonico comprende:
- **51 progetti**;
- **11.202,52 MW wind** complessivi;
- i MW BESS restano sempre separati dai MW eolici;
- **34 progetti** sono stati promossi dal discovery v0.4 tramite promotion gate controllato;
- **9.705,62 MW wind** e **311 MW BESS** corrispondono ai 34 promossi.

I 17 seed storici restano invariati come baseline di regressione:
- **1.496,9 MW wind**;
- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope onshore coperti;
- **437,7 MW** in costruzione E7.

I nuovi promossi non ricevono contractor esecutivi per deduzione: in assenza di un award A1/A2 documentato, gli scope restano aperti e il ranking neutro resta `C / 50`.

## Promotion gate v0.5

Un candidato entra nel canonico solo se sono verificati:
1. identity reconciliation;
2. activity class `current`;
3. configurazione MW/WTG sufficientemente definita;
4. `site_type` esplicito;
5. stage E0–E8 sostenuto da fonte A1/A2;
6. scope profile applicabile onshore/offshore;
7. collision check con il canonico esistente.

Esito sui 38 candidati `current` della v0.4:
- **34 promoted**;
- **4 blocked** rimasti nel discovery:
  - Med Wind Grecale;
  - Rospo Offshore;
  - Sindia-Macomer 43,4 MW;
  - Le Chiancate.

## Correzioni canoniche rilevanti

- **Florinas Repowering resta E3**: VIA positiva / verifica di ottemperanza non equivalgono a prova dell'autorizzazione complessiva.
- **Lujentu**: comuni canonici corretti in **Nardò, Copertino e Galatina**.
- Nessuna coordinata viene simulata per i nuovi canonici privi di posizione territoriale affidabile.
- BESS sempre distinto dai MW wind.

## Commercial enrichment v0.5

Il layer commerciale copre **34/34 nuovi canonici** tramite registri additivi:
- `docs/wind/data/commercial-enrichment-v05.json`
- `docs/wind/data/commercial-enrichment-v05b.json`
- `docs/wind/data/commercial-enrichment-v05c.json`
- `docs/wind/data/commercial-enrichment-v05d.json`

Regola centrale:
- owner / developer / advisor / engineering / survey / project management = intelligence commerciale;
- **solo un ruolo esecutivo esplicito A1/A2 chiude uno scope**;
- B/C restano segnali;
- GlobalData resta lead/enrichment e non fonte canonica.

Enrichment verificati includono, tra gli altri:
- Kailia: Renantis / BlueFloat, WSP, RINA;
- Atis: Eni Plenitude, GBT Offshore;
- Parma A: BAUTEL per access/heavy-transport engineering;
- Poseidon / NURAX: Divento, Copenhagen Offshore Partners, iLStudio, NiceTechnology, 7Seas Windpower, senza dedurre Saipem;
- Lecce BETANRG: Leonardo Engineering; Siemens Gamesa SG 7.0-170 resta design reference e non OEM award;
- Tramontana: OWC + MPOWER per project design e WSP Italia per impact assessment/investigations, tutti non-execution.

## Scope profile

### Onshore
Core scope:
- Civil BoP;
- Electrical BoP;
- SSE/grid;
- fondazioni WTG;
- erection;
- logistics/heavy transport;
- dismantling per repowering.

### Offshore
Profilo dedicato:
- foundations / substructure / mooring;
- WTG installation offshore;
- inter-array cables;
- offshore substation / electrical platform;
- export cable + landfall;
- onshore SSE / grid;
- marine logistics / port / heavy lift;
- civil works onshore connection.

Gli scope offshore non vengono valutati meccanicamente con il profilo onshore.

## UI v0.5

La dashboard pubblicata include:
- 51 progetti canonici;
- filtri onshore/offshore;
- KPI e pipeline E0–E8;
- mappa con marker solo dove la posizione è verificata;
- timeline;
- opportunità prioritarie;
- Discovery separato dal canonico;
- Contractor view;
- commercial/supply-chain intelligence visibile nelle schede progetto.

I registri commerciali v0.5/a-b-c-d vengono uniti sia nella scheda progetto sia nella Contractor view.

## Validazione v0.5

Workflow **Wind Radar v0.5 checks** sul final head della PR:
- run `33972587617` — **SUCCESS**.

GitHub Pages dopo merge:
- run `33972645972` — **SUCCESS**.

Regression guards principali:
- `scripts/check_wind_radar.py`
- `scripts/check_wind_industry_press.py`
- `scripts/check_wind_stages.py`
- `scripts/check_wind_v04.py`
- `scripts/check_wind_v05.py`
- `scripts/check_wind_v05_enrichment.py`
- `scripts/wind_discovery_engine.py`

Audit:
- `docs/wind/research/2026-09-05-v05-promotion-audit.md`

Promotion gate machine-readable:
- `docs/wind/data/promotion-gate-v05.json`

## Prossima fase — v0.6

La priorità non è aumentare indiscriminatamente il numero di progetti, ma aumentare la **profondità commerciale ed esecutiva** sui 51 canonici.

Ordine di lavoro:
1. progetti E4–E7 e progetti con finestra di cantiere / procurement nei prossimi 12–18 mesi;
2. ricerca di award e contractor A1/A2 per singolo scope;
3. timing di civili, grid, fondazioni, erection, logistica e commissioning;
4. procurement/OEM solo quando documentato, senza deduzioni;
5. refresh dei 4 blocked e degli stale/rejected solo in presenza di nuova evidenza;
6. revisione del ranking commerciale solo dopo avere abbastanza evidenza oggettiva da superare il neutro `C / 50`.

### Architettura agent-style v0.6

La v0.6 riusa esplicitamente il pattern operativo già collaudato in `pv_agent_mvp`, adattato all'eolico:

`fonti -> agent/collector -> raw findings -> change history -> reconciliation/evidence gate -> canonico/UI`

Implementato nel branch:
- `app/wind_agents/base.py`: contract comune per gli agenti sorgente;
- `app/wind_agents/planner.py`: code separate per **Institutional Watch**, **Company Watch** e **Project Execution Watch**, con cadenze proprie;
- `app/wind_agents/state.py`: persistenza SQLite separata per raw findings e change events; il canonico non viene modificato automaticamente;
- `app/wind_agents/evidence.py`: gate strutturale unico, per cui solo evidenza project-specific A1/A2 può chiudere uno scope esecutivo;
- `app/wind_agents/adapters/mase.py`: primo adapter realmente eseguibile, che riusa il collector MASE esistente ma lo restringe a eolico / repowering / offshore;
- `app/wind_agents/runner.py` + `scripts/run_wind_agents.py`: orchestrazione e CLI;
- `scripts/check_wind_v06_agents.py`: regressione dedicata.

Il planner usa i registri v0.6 correnti:
- Company Network base + tranche B;
- Institutional Source Network base + tranche B;
- canonico progetti per generare la coda E4–E7 con scope ancora aperti.

Regola di trasparenza: un nodo fonte presente nel registry ma senza adapter eseguibile resta **visibile come lavoro dovuto**, non viene considerato falsamente monitorato.

Prossima estensione del motore:
1. portare/adattare dal PV Agent i collector regionali ad alta priorità, iniziando da Lazio, Toscana/ATOS, Sardegna, Sicilia, Puglia, Campania, Calabria e Basilicata;
2. aggiungere adapter company-watch per press/news/supplier pages dei player A;
3. riconciliare automaticamente i finding con canonico/discovery senza promozione automatica;
4. generare digest delle sole variazioni utili commercialmente.

Branch di lavoro v0.6:
`feat/wind-radar-v0.6-execution-intelligence`.

Nessun merge o pubblicazione v0.6 senza revisione esplicita.
