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

# Fase corrente — v0.6

Branch:
`feat/wind-radar-v0.6-execution-intelligence`

Draft PR:
**#5 — Wind Radar v0.6 — execution intelligence e commercial timing**.

Nessun merge o pubblicazione v0.6 senza revisione esplicita.

La v0.6 sviluppa tre reti collegate ma probatoriamente separate:
1. **Project Execution Intelligence**;
2. **Company / Commercial Network**;
3. **Institutional & Source Network**.

## Network v0.6

Stato registri:
- **50 player commerciali** classificati per capability/priorità;
- **31 nodi istituzionali/pubblici** censiti;
- le capability generiche aziendali non vengono mai trasformate in award di progetto;
- una fonte istituzionale è un canale: solo lo specifico atto project-specific può sostenere evidenza A1.

ESPE resta target commerciale A adiacente ad alto valore, senza attribuirle Full BoP utility-scale wind in assenza di prova.

## Architettura agent-style v0.6

La v0.6 riusa il pattern operativo già collaudato in `pv_agent_mvp`, adattato all'eolico:

`fonti -> agent/collector -> raw findings -> change history -> reconciliation/evidence gate -> canonico/UI`

Implementato:
- `app/wind_agents/base.py`: contract comune per i finding sorgente;
- `app/wind_agents/planner.py`: code e cataloghi separati per Institutional Watch, Company Watch e Project Execution Watch;
- `app/wind_agents/state.py`: SQLite separato per raw finding, eventi, cursori sorgente e runtime `watch_status`;
- `app/wind_agents/evidence.py`: solo evidenza project-specific A1/A2 può chiudere uno scope esecutivo;
- `app/wind_agents/runner.py`: runner istituzionale resiliente e cadence-aware;
- `app/wind_agents/company_watch.py`: monitor diretto delle fonti dei player commerciali;
- `app/wind_agents/reconcile.py`: reconciliation conservativa e digest review-only delle sole variazioni utili;
- `scripts/run_wind_agents.py`: CLI per plan, due queue, source run, company run e digest;
- `scripts/check_wind_v06_agents.py`: regressioni architetturali, probatorie e di reconciliation.

### Adapter istituzionali eseguibili — 17

Gli ID coincidono con il registry istituzionale:
1. `mase-via` — MASE VIA, eolico / repowering / offshore;
2. `mase-provvedimenti` — MASE provvedimenti/esiti, separando VIA positiva da autorizzazione complessiva;
3. `terna-econnextion` — Terna Econnextion, solo intelligence aggregata regionale;
4. `lazio-regional` — Regione Lazio VIA/PAUR;
5. `toscana-gea` — Regione Toscana GeA;
6. `toscana-atos` — ATOS Toscana FER;
7. `sardegna-sira` — Sardegna SIRA VIA/PAUR;
8. `sicilia-sivvi` — Sicilia SI-VVI, prima tranche CSV ufficiale;
9. `puglia-sistema-energia` — Sistema Puglia Energia;
10. `campania-viavas` — Regione Campania VIA/PAUR;
11. `calabria-via` — Regione Calabria VIA/PAUR;
12. `basilicata-via` — Regione Basilicata VIA/Screening;
13. `emilia-romagna-regional` — Emilia-Romagna VIA/VAS;
14. `lombardia-regional` — Lombardia SILVIA;
15. `piemonte-regional` — Piemonte SKVIA;
16. `umbria-regional` — Umbria VIA/PAUR/Screening;
17. `veneto-regional` — Veneto VIA/VAS, pagine annuali correnti.

Gli ultimi cinque riusano endpoint, flow HTTP e parser già maturati nel PV Agent ma sostituiscono i filtri fotovoltaici con selezione eolica. Restano **eseguibili**, non automaticamente dichiarati live-validati: la disponibilità corrente del portale viene attestata solo da un'esecuzione effettiva.

Sistema Puglia non ripete il backfill fisso di circa 1.500 ID ad ogni ciclo: usa un **high-water cursor persistente**, forward probe e lookback breve. Il backfill storico può essere eseguito separatamente.

Terna Econnextion è esplicitamente `market_intelligence`: i valori regionali aggregati non possono creare progetti, chiudere scope o attribuire contractor.

### Company Watch

Il monitor commerciale usa le `watch_urls` dei 50 player e applica le cadenze del registry:
- A/A+: 7 giorni;
- B: 14 giorni;
- C / universe refresh: 30 giorni, salvo override specifici.

Per ridurre falsi cambi, non conserva l'intera pagina dinamica: estrae heading e segmenti contenenti segnali wind/commerciali (award, contract, construction, BoP, civili, elettrico, grid, fondazioni, erection, logistica, commissioning, procurement ecc.).

Un finding da fonte diretta aziendale resta:
- `source_grade_ceiling = A2`;
- `project_specific = false`;
- `execution_scope = null`;
- layer `network_intelligence`.

Quindi **non chiude scope** finché non emerge successiva evidenza esplicita project-specific sul ruolo esecutivo.

## Reconciliation e digest

`app/wind_agents/reconcile.py` confronta esclusivamente i finding `new/changed` con:
- i 51 progetti canonici;
- i candidati del Discovery ancora separati dal canonico.

Segnali usati per il match:
- nome progetto;
- URL sorgente;
- comuni/area;
- potenza MW;
- developer/proponente;
- regione;
- link progetto già registrati nel Company Network come indizio, non come prova.

Una corrispondenza può essere marcata `high_confidence_match` solo con identità forte, punteggio e margine sufficienti. Il flag resta **advisory**: nessuna reconciliation modifica automaticamente canonico, Discovery, stage, priority, scope o contractor.

Inoltre un finding company-direct con `project_specific=false` **non può diventare auto-reconciled execution evidence**, anche se il registry contiene un link al progetto.

Il digest classifica le variazioni in:
- `canonical_update_review`;
- `discovery_refresh_review`;
- `new_project_lead`;
- `company_project_signal`;
- `company_network_update`;
- `market_intelligence`.

Le variazioni su progetti E4–E7 e A/A+ ricevono maggiore peso commerciale; gli snapshot aziendali vuoti restano nello storico ma non entrano nel digest operativo.

## Esecuzione periodica

È predisposto `.github/workflows/wind_agent_watch.yml`:
- trigger giornaliero alle 05:40 UTC;
- il trigger giornaliero non significa controllo giornaliero di tutto: `--due` applica le cadenze 1/3/7/14/30 giorni;
- stato SQLite persistente via cache GitHub Actions;
- un singolo portale indisponibile viene registrato come errore ma non interrompe gli altri watch;
- esecuzione source watch + company watch;
- generazione automatica di `reports/wind-agent/digest.json` dai soli finding nuovi/modificati;
- report JSON, GitHub Step Summary e artifact di run, retention 30 giorni;
- nessuna scrittura automatica del canonico e nessun commit automatico.

**Importante:** il workflow `schedule` diventa operativo solo quando il file è presente sul branch di default. Finché la v0.6 resta nella Draft PR #5, è configurazione da revisionare, non un monitor schedulato già attivo.

## Regola di trasparenza sui test

Il workflow PR verifica:
- import e sintassi;
- registrazione dei 17 adapter contro il registry;
- planner e cadence state;
- persistence `new / changed / unchanged`;
- cursori/high-water;
- gate probatorio;
- reconciliation conservativa e divieto di auto-reconciliation per company snapshot non project-specific;
- lettura degli eventi di run e digest review-only;
- regressioni v0.3/v0.4/v0.5.

Non equivale a una prova live che ogni portale esterno sia raggiungibile in quel momento. Un adapter è dichiarato **eseguibile**, ma la sua disponibilità live viene attestata solo da un run effettivo contro la fonte.

## Lavoro ancora aperto v0.6

1. completare dettaglio/GIS Sicilia oltre alla prima tranche CSV;
2. aggiungere gli ulteriori canali istituzionali ancora censiti ma senza adapter, con priorità ai gap territoriali utili (Abruzzo, Liguria, Marche, Molise);
3. sviluppare un **Project Execution Watch specifico** che trasformi i match in code di indagine per scope, senza scrivere automaticamente evidenza;
4. continuare la contractor hunt A1/A2 sui progetti E4–E7, in particolare Andretta-Bisaccia, Tricarico, Nulvi-Ploaghe, Serra Giannina, Greci-Montaguto, Carlentini e Alia-Sclafani;
5. completare il census ANEV/non-ANEV e ampliare il network commerciale quando emergono nuovi player dalle fonti istituzionali e dai documenti di progetto;
6. effettuare run live controllati dei 17 adapter e correggere eventuali drift dei portali prima di proporre l'attivazione schedulata su `master`.
