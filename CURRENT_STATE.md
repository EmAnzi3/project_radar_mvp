# CURRENT STATE â€” Project Radar MVP

## Obiettivo

Radar commerciale multi-settore per gestire grandi moli di candidati, con logica di sharding e vista web filtrata.

## Workflow operativo

Acquisizione dati; normalizzazione; arricchimento; sharding logico per filiale/area; generazione sito consultabile.

## File e cartelle critiche

- scripts/build_master_dataset.py
- data/
- docs/
- reports/
- requirements.txt

## Cose da non rompere

- Archivio completo e vista web non sono la stessa cosa.
- Non ridurre il numero di candidati pubblicabili senza esplicita richiesta.
- Preservare sharding logico per filiale.
- Evitare scroll orizzontale nelle viste operative.

## Stato corrente

- Stato: da aggiornare dopo il prossimo giro operativo.
- Ultima verifica manuale: da compilare.
- Ultima pubblicazione: da compilare.
- Ultimo commit stabile noto: da compilare.

## Problemi aperti

- Da compilare.

## Prossimo passo consigliato

1. Eseguire `.\scripts\check_before_publish.ps1`.
2. Controllare `git status` e `git diff --check`.
3. Aggiornare questa pagina se cambia il workflow.
4. Committare con messaggio piccolo e tematico.

