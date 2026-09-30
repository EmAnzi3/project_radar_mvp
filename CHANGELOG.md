# CHANGELOG — Project Radar MVP

Formato consigliato: voci brevi, orientate a cosa cambia per il progetto.

## Unreleased

- 2026-09-30 — Consolidata l'architettura Wind Radar eliminando i builder concorrenti: `wind/input/projects.json` è il seed canonico, `wind/scripts/build_wind_radar.py` il builder unico e `wind/web/` la sorgente della UI.
- 2026-09-30 — Reso `aggiorna_wind_radar.bat` end-to-end: validazione ambiente/dati, build, master, relazioni progetto↔azienda, JSON/CSV, controlli Python/JS e preview standalone con esito SUCCESS/FAILURE.
- 2026-09-30 — Aggiunti master normalizzato e `project_company_relationships`, mantenendo wind/BESS separati e guardrail su Progeco, D'Agostino Serra Giannina e SOCEP Alia.
- 2026-09-30 — Completati i filtri operativi della dashboard: Provincia, OEM, contractor esecutivo noto/ignoto e anno lavori; marker mappa scalati anche sui MW; KPI esplicito dei progetti senza contractor.
- 2026-09-30 — Aggiunto workflow `Wind Radar MVP`: build e validazione completa, sincronizzazione controllata di `docs/wind/` e artifact navigabile `wind-radar-preview`. Run 36698564238 completamente verde.

- 2026-09-04 — Review Wind Radar: chiarita la precisione geografica (marker territoriali, non coordinate WTG), aggiunti tooltip a pipeline/timeline, scroll interno alle opportunità e contractor view compatta con selettore azienda.
- 2026-09-04 — Evoluto `docs/wind/` in un Wind Project & Contractor Radar operativo: seed verificato di 17 progetti / 1.496,9 MW eolici, schema E0–E8, MW wind/BESS separati, storico configurazioni, supply chain con fonte/confidenza, 7 KPI, mappa a marker progetto, timeline di cantiere, opportunità responsive, contractor view inversa, dettaglio progetto ed export CSV.
- 2026-09-04 — Sostituito il vecchio dataset monolitico `docs/wind/data.json` con manifest + metadata + 3 chunk progetto; rimossa la dipendenza da librerie JS esterne per la dashboard Wind.
- 2026-09-04 — Avviato `docs/wind/` con Wind Construction Radar MVP: seed iniziale di 15 progetti, filtri, mappa regionale, pipeline per maturità, timeline operativa, contractor view e schede progetto.
- 2026-06-02 — Aggiunti file minimi di manutenzione repository: `CURRENT_STATE.md`, `AGENTS.md`, `CHANGELOG.md` e `scripts/check_before_publish.ps1`.
