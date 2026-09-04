# CURRENT STATE — Project Radar MVP

## Obiettivo

Radar commerciale multi-settore per gestire grandi moli di candidati, con logica di sharding e vista web filtrata.

Sul branch `feat/wind-radar-mvp` è presente anche un MVP isolato per il mercato eolico in `docs/wind/`.

## Workflow operativo

Acquisizione dati; normalizzazione; arricchimento; sharding logico per filiale/area; generazione sito consultabile.

Per il Wind Radar MVP il seed è attualmente curato manualmente dal probe e separa fatti confermati, forti evidenze e campi ancora aperti.

## File e cartelle critiche

- scripts/build_master_dataset.py
- data/
- docs/
- docs/wind/index.html
- docs/wind/data.json
- reports/
- requirements.txt

## Cose da non rompere

- Archivio completo e vista web non sono la stessa cosa.
- Non ridurre il numero di candidati pubblicabili senza esplicita richiesta.
- Preservare sharding logico per filiale.
- Evitare scroll orizzontale nelle viste operative.
- Nel Wind Radar non attribuire contractor come confermati senza evidenza sufficiente.
- Mantenere separati MW eolici ed eventuale BESS.

## Stato corrente

- Wind Radar: primo MVP grafico creato con seed di 15 progetti.
- Main/master non modificato: lavoro isolato sul branch `feat/wind-radar-mvp`.
- Nessun merge o pubblicazione eseguiti.

## Problemi aperti

- consolidare i contractor mancanti;
- completare localizzazione/area dove ancora n.d.;
- definire ingestione automatica Terna/MASE/Regioni;
- introdurre storico delle configurazioni e delle milestone.

## Prossimo passo consigliato

1. revisionare il primo output grafico;
2. correggere UI/campi sulla base della revisione;
3. consolidare il seed e solo dopo progettare l'ingestione automatica;
4. eseguire `.\scripts\check_before_publish.ps1` prima di qualsiasi merge/pubblicazione.

