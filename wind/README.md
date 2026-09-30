# Wind Radar Italia

Radar commerciale eolico isolato nel branch `feat/wind-radar-mvp`.

## Entry point Windows

Eseguire:

```text
aggiorna_wind_radar.bat
```

Il BAT usa solo Python standard library e:

1. crea/riusa `.venv`;
2. verifica la sintassi del builder;
3. legge e valida `wind/input/projects.json`;
4. genera master, relazioni progetto↔azienda, JSON e CSV;
5. rigenera la dashboard in `docs/wind/`;
6. crea `docs/wind/preview.html`, standalone e apribile direttamente;
7. riesegue i controlli sugli output;
8. controlla il JavaScript con Node.js se disponibile;
9. termina con `SUCCESS` o `FAILURE`.

## Sorgenti canoniche

- dati: `wind/input/projects.json`;
- builder: `wind/scripts/build_wind_radar.py`;
- web source: `wind/web/`.

Non modificare direttamente un output generato per introdurre una correzione persistente: correggere prima la sorgente o il builder.

## Output

- `docs/wind/index.html` — dashboard per hosting statico/GitHub Pages;
- `docs/wind/preview.html` — preview standalone;
- `docs/wind/data/projects.json` + chunk — dataset dashboard;
- `docs/wind/data/master.json` — master normalizzato;
- `docs/wind/data/project_company_relationships.json` — relazione progetto ↔ azienda;
- `docs/wind/projects.csv`;
- `docs/wind/project_company_relationships.csv`.

## Regole dati

- MW eolici e BESS restano separati;
- maturità `E0–E8`;
- evidenze `A1/A2/B/C/D`;
- una relazione B/C è un segnale, non un affidamento;
- GlobalData è solo enrichment/lead source;
- dati mancanti restano null/unknown, senza falsa precisione;
- le coordinate della mappa possono essere proxy territoriali e non coordinate WTG.

## Guardrail

Il builder blocca regressioni note: Progeco non può essere promosso a Civil BoP su Andretta senza nuova prova; D'Agostino su Serra Giannina resta segnale finché non emerge una prova A1/A2; SOCEP su Alia resta incumbent storico e non contractor del repowering corrente.

## CI

Il workflow `.github/workflows/wind-radar-mvp.yml` ricostruisce e valida l'MVP sul branch. Solo dopo compilazione, build, validazione, controllo JavaScript e pre-publish check aggiorna gli output `docs/wind/` e pubblica l'artifact `wind-radar-preview`.
