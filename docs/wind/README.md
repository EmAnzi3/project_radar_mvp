# Wind Project & Contractor Radar

MVP operativo del radar eolico nazionale, isolato in `docs/wind/` e orientato alla domanda commerciale: quali progetti diventeranno cantieri, quando, dove e chi eseguirà fisicamente le opere.

## Stato seed

- 17 progetti;
- 1.496,9 MW eolici;
- 130 MW BESS, sempre separati dai MW wind;
- maturità osservabile `E0–E8`;
- evidence grading `A1/A2/B/C/D`;
- relazioni progetto ↔ azienda con ruolo, stato e fonte.

Il KPI “contractor esecutivo” conta solo relazioni con ruolo esecutivo, stato `confirmed` e confidenza `A1/A2`. Segnali B/C restano intelligence e non vengono promossi a contratto.

## Navigazione

La dashboard offre KPI, filtri, mappa, pipeline per maturità, timeline, opportunità, contractor view inversa e scheda progetto con fonti e storico configurazioni.

I marker cartografici sono riferimenti territoriali quando non sono disponibili coordinate di layout verificate; non rappresentano automaticamente le singole WTG.

## Output dati

- `data/projects.json` — manifest della dashboard;
- `data/master.json` — master normalizzato;
- `data/project_company_relationships.json` — relazione progetto ↔ azienda;
- `projects.csv` e `project_company_relationships.csv` — export;
- `preview.html` — file standalone navigabile.

## Fonti

Atti pubblici, developer, OEM e contractor prevalgono sulle fonti di enrichment. GlobalData è usata esclusivamente come lead/enrichment.

## Generazione

La sorgente non è questa cartella: il dataset canonico è `wind/input/projects.json`, il builder è `wind/scripts/build_wind_radar.py` e il web source è `wind/web/`.
