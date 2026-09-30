# Wind Radar Italia

Radar commerciale eolico costruito sulla stessa logica operativa dei radar esistenti.

## Avvio

Doppio clic su:

```text
aggiorna_wind_radar.bat
```

Il BAT:

1. crea/riusa `.venv`;
2. legge `wind/input/projects.json`;
3. valida i record;
4. genera:
   - `docs/wind/index.html`
   - `docs/wind/data.json`
   - `docs/wind/projects.csv`
5. apre automaticamente la dashboard.

Non richiede pacchetti Python esterni.

## Dati rilevati

Il radar privilegia le informazioni utili commercialmente:

- MW eolici e BESS separati;
- regione, provincia, comuni e area/località quando disponibile;
- greenfield / repowering;
- stato e maturità;
- developer e SPV;
- MYTERNA quando noto;
- finestra opere civili;
- finestra erection;
- COD / commissioning;
- contractor e ruolo;
- livello di confidenza dell'associazione;
- focus commerciale;
- fonti.

Non vengono modellati computi metrici, volumi di calcestruzzo o quantità di scavo.

## Aggiornare i progetti

Il master manuale iniziale è:

```text
wind/input/projects.json
```

Ogni record contiene i campi usati dalla dashboard. Lasciare vuote le date non note: non forzare una falsa precisione.

Le associazioni contractor devono distinguere tra:

- confermato;
- forte evidenza / da confermare;
- incumbent storico;
- engineering / DL / supervisione;
- OEM.

## Dashboard

La pagina contiene:

- KPI;
- pipeline per maturità;
- MW per regione;
- contractor network;
- timeline delle milestone con data esatta;
- tabella completa filtrabile;
- export CSV;
- link alle fonti.

## Evoluzione prevista

Il master JSON è volutamente separato dalla raccolta fonti. In questo modo il radar è già usabile ora e potrà essere alimentato successivamente da:

- Terna / Econnextion;
- MASE VIA;
- Regioni / BUR / PAUR / AU;
- GSE / FER-X;
- developer;
- contractor / RTI / vendor assessment;
- job posting e documentazione di cantiere.

La dashboard non deve dipendere direttamente dallo scraping delle fonti.
