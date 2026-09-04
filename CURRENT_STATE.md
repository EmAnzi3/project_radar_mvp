# CURRENT STATE — Project Radar MVP

## Obiettivo

Radar commerciale multi-settore per gestire grandi moli di candidati, con logica di sharding e vista web filtrata.

Sul branch `feat/wind-radar-mvp` è presente un MVP isolato per il mercato eolico in `docs/wind/`.

## Workflow operativo

Acquisizione dati; normalizzazione; arricchimento; sharding logico per filiale/area; generazione sito consultabile.

Per il Wind Radar il seed è curato con separazione esplicita tra fatti confermati, segnali di intelligence e campi ancora aperti. GlobalData è solo enrichment/lead source e non prevale sulle fonti canoniche.

## File e cartelle critiche

- `scripts/build_master_dataset.py`
- `data/`
- `docs/`
- `docs/wind/index.html`
- `docs/wind/assets/app.js`
- `docs/wind/assets/style.css`
- `docs/wind/assets/italy-base.svg`
- `docs/wind/data/projects.json`
- `docs/wind/data/meta.json`
- `docs/wind/data/projects-1.json` … `projects-3.json`
- `reports/`
- `requirements.txt`

## Cose da non rompere

- Archivio completo e vista web non sono la stessa cosa.
- Non ridurre il numero di candidati pubblicabili senza esplicita richiesta.
- Preservare sharding logico per filiale.
- Evitare scroll orizzontale nelle viste operative.
- Nel Wind Radar non attribuire contractor come confermati senza evidenza sufficiente.
- Mantenere separati MW eolici ed eventuale BESS.
- Conservare le configurazioni storiche del progetto invece di sovrascrivere semplicemente MW/WTG.
- Usare esclusivamente la scala osservabile `E0–E8`, senza percentuali arbitrarie di maturità.

## Stato corrente

- Wind Radar MVP evoluto a **17 progetti seed / 1.496,9 MW eolici**.
- Dataset normalizzato e suddiviso in manifest + metadata + 3 chunk progetto.
- Dashboard con 7 KPI, mappa a marker progetto, pipeline per maturità, timeline di cantiere, opportunità prioritarie, contractor view inversa, schede progetto, filtri ed export CSV.
- KPI contractor rigoroso: contano solo relazioni esecutive `confirmed` A1/A2; B/C restano intelligence.
- `docs/wind/data.json` precedente rimosso per evitare una seconda fonte dati divergente.
- Main/master non modificato: lavoro isolato sul branch `feat/wind-radar-mvp`.
- Nessun merge o pubblicazione eseguiti.

## Problemi aperti

- consolidare i contractor mancanti, soprattutto sui progetti A+/A;
- completare localizzazione/area dove ancora n.d.;
- definire ingestione automatica Terna/MASE/Regioni;
- automatizzare storico delle configurazioni e delle milestone;
- ampliare il seed mantenendo la soglia di evidenza.

## Prossimo passo consigliato

1. revisionare la preview grafica del Wind Radar;
2. correggere UI/campi sulla base della revisione;
3. consolidare i contractor prioritari;
4. solo dopo progettare l'ingestione automatica;
5. eseguire `.\scripts\check_before_publish.ps1` prima di qualsiasi merge/pubblicazione in un ambiente PowerShell disponibile.
