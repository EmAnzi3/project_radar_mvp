# Project Radar MVP

Radar operativo per progetti e opportunità infrastrutturali in Italia.

## Wind Project & Contractor Radar

La baseline pubblicata resta **v0.5.0** su `master`.

La v0.6 è in lavorazione sulla Draft PR **#5 — Wind Radar v0.6 — execution intelligence e commercial timing** e non deve essere mergiata o pubblicata senza revisione esplicita.

### Baseline canonica

- 51 progetti canonici;
- 11.202,52 MW wind;
- BESS sempre separato dai MW wind;
- maturità E0–E8;
- scope onshore/offshore distinti.

### Regola probatoria

Uno scope esecutivo viene chiuso solo con evidenza **project-specific A1/A2** esplicita. Owner, developer, advisor, engineering, DL, supervision, recruiting, capability generale e storico stesso sito non implicano un award di execution.

### v0.6

La v0.6 aggiunge:
- Company / Commercial Network;
- Institutional & Source Network;
- agent/collector con raw findings e change history separati dal canonico;
- evidence gate centralizzato;
- reconciliation conservativa e digest review-only;
- Project Execution investigation queue E4–E7;
- contractor intelligence additiva;
- mappa ECharts choropleth per provincia con filtro Provincia dedicato e metriche MW wind / N. progetti / MW E4+.

La review browser della mappa province è stata eseguita su desktop e mobile. Il click provincia non sovrascrive più la ricerca libera; tooltip, reset, clear e metriche sono coperti da validator dedicati.

Per lo stato operativo aggiornato vedere `CURRENT_STATE.md` e `CHANGELOG.md`.

## Struttura repository

- `docs/wind/` — dashboard Wind Radar e dati canonici/enrichment;
- `app/wind_agents/` — runtime agent-style per fonti istituzionali, company watch e reconciliation;
- `scripts/check_wind_*.py` — regressioni e validator;
- `scripts/run_wind_agents.py` — CLI operativa;
- `CURRENT_STATE.md` — stato corrente;
- `CHANGELOG.md` — evoluzione del progetto.

## Governance

- nessuna scrittura automatica nel canonico;
- nessun contractor per deduzione;
- nessun merge/pubblicazione della Draft PR #5 senza approvazione esplicita.
