# Current State

## Wind Project & Contractor Radar MVP

Branch di lavoro: `feat/wind-radar-mvp`.

Stato: **MVP end-to-end funzionante in Draft/preview**, non mergiato e non pubblicato su `master`.

### Architettura canonica

- dataset sorgente: `wind/input/projects.json`;
- builder unico: `wind/scripts/build_wind_radar.py`;
- sorgente web: `wind/web/`;
- launcher Windows: `aggiorna_wind_radar.bat`;
- output statici: `docs/wind/`;
- workflow di validazione: `.github/workflows/wind-radar-mvp.yml`.

Le precedenti implementazioni concorrenti sono state consolidate: il BAT non può più rigenerare la vecchia dashboard semplificata sopra quella avanzata.

### Seed operativo al 30/09/2026

- 17 progetti;
- 1.496,9 MW eolici;
- 130 MW BESS, separati dai MW wind;
- 689,7 MW in fase E4 o successiva;
- 408,7 MW in costruzione E7;
- 4 progetti / 133,9 MW con contractor esecutivo confermato A1/A2;
- 13 progetti con contractor esecutivo ancora da identificare;
- 25 relazioni progetto ↔ azienda;
- 15 aziende/nodi distinti nel seed;
- maturità E0–E8;
- evidence grading A1/A2/B/C/D.

### Guardrail intelligence

- Progeco su Andretta-Bisaccia = supervisione/site management; non Civil BoP;
- D'Agostino su Serra Giannina = segnale B da confermare; non contratto;
- SOCEP su Alia-Sclafani = incumbent storico; non contractor del repowering corrente;
- F.lli Pisci su ALAS = segnale operativo/civile B;
- Energy& su Venusia = site-management signal;
- GlobalData = solo enrichment/lead source.

Il builder blocca promozioni indebite note da segnale a contractor confermato.

### Dashboard

Presenti:

- KPI operativi;
- ricerca full-text;
- filtri Regione, Provincia, maturità, tipo, developer, contractor, OEM, contractor esecutivo noto/ignoto, anno lavori, MW e finestra temporale;
- mappa con marker dimensionati anche in funzione dei MW e colore per E0–E8;
- pipeline per maturità;
- timeline di cantiere;
- opportunità prioritarie;
- contractor view inversa azienda → progetti;
- scheda progetto con timing, supply chain, gap, storico configurazioni e fonti;
- export CSV.

### Output generati

- `docs/wind/index.html` — dashboard per hosting statico;
- `docs/wind/preview.html` — preview standalone apribile direttamente;
- `docs/wind/data/master.json` — master normalizzato;
- `docs/wind/data/project_company_relationships.json` — relazioni azienda/progetto;
- manifest + chunk JSON per la UI;
- `docs/wind/projects.csv`;
- `docs/wind/project_company_relationships.csv`.

### BAT

`aggiorna_wind_radar.bat`:

1. crea/riusa `.venv`;
2. verifica Python;
3. compila sintatticamente il builder;
4. valida il seed;
5. genera master, relazioni, JSON, CSV e web output;
6. esegue `--check-only`;
7. esegue `node --check` se Node.js è disponibile;
8. termina esplicitamente con SUCCESS/FAILURE;
9. apre `docs/wind/preview.html`.

### Verifica automatica

Ultimo run validato:

- GitHub Actions run `36698564238`;
- compile builder: SUCCESS;
- build: SUCCESS;
- output validation: SUCCESS;
- JavaScript syntax: SUCCESS;
- repository pre-publish: SUCCESS;
- commit output generati: SUCCESS;
- artifact `wind-radar-preview`: SUCCESS.

Il workflow mantiene gli output `docs/wind/` sincronizzati con sorgente e builder e usa `[skip ci]` sul commit generato per evitare loop.

### Passi aperti successivi all'MVP

1. audit puntuale delle coordinate territoriali contro corografie/layout ufficiali;
2. collector automatici Terna/Econnextion, MASE, Regioni/BUR e fonti contractor;
3. enrichment continuo delle finestre lavori e dei contractor mancanti.

### Vincoli

Nessuna modifica a `master`, nessun merge e nessuna pubblicazione finché non viene data approvazione esplicita.
