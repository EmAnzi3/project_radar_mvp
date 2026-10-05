# Current State

## Fase corrente — audit documentale D1 / D2 / D3 (05/10/2026)

Branch `feat/wind-daily-discovery`, PR #9 OPEN/DRAFT, nessun merge autorizzato. Il motore documentale è additivo e separato dal BAT quotidiano, da `app/wind_agents` e dai dati/dashboard in `docs/wind`.

### Perimetro censito

- 96 identità registrate: 51 canoniche, 34 Discovery correnti, 4 da riconfermare, 7 escluse.
- 85 sono classificate correnti nei registri, non certificate come opportunità commerciali odierne.
- 57 gruppi di record da qualificare, di cui 4 già collegati e 53 non collegati. Non sono 53 progetti unici accertati.
- Audit obbligatorio anche sui 51 canonici. Un record incompleto attiva approfondimento, non una conclusione di indisponibilità del dato.
- Il seed documentale riunisce anche i due registri `discovery-census-v04*.json`; il matcher quotidiano precedente non è modificato da D1–D3.

### Stato dimostrato e limiti

D1 (`2f67b856368ef8a14c1e01b42e60ac244ed8c3a3`) conserva originali, SHA-256, testo per pagina e accessi in SQLite separata.

D2 (`2c8f2709d296c92ed8315eff6277c1597567dcf1`) ha completato l'indice di una procedura Med Wind Grecale: 49 pagine / 487 allegati. Il lotto ha acquisito 8 PDF / 336 pagine, incluso un originale da 102.737.107 byte / 148 pagine prima fermato dal limite interno D1. Inventario completo non significa allegati tutti acquisiti o letti. Il document audit pilot #2, i check #405 e il live source smoke #223 sono passati su D2.

D3 aggiunge riscontri interpretati con progetto, URL, SHA e pagina, regole sui ruoli aziendali/recapiti e cronoprogrammi. Lotto iniziale: 24 riscontri su Med Wind Grecale, Gagliole, Apecchio e Serra Giannina. Importazione atomica/idempotente, record immutabili, riesame esplicito quando manca un originale o cambia la versione acquisita. Test strutturali non equivalgono a prova automatica della correttezza semantica.

Il presente aggiornamento non anticipa l'esito CI del proprio commit: consultare i run associati alla HEAD. Fascicoli certificati completi: **0**. Nessun nuovo affidamento EPC certificato da questo lotto. Nessuna promozione o variazione del canonico.

Resta da completare: acquisizione/revisione dell'intero inventario, altre procedure e progetti, ZIP/P7M, lettura delle figure/tabelle, genealogia delle versioni e conferma dell'attualità commerciale. Cache Actions e artifact con retention 14 giorni non sostituiscono storage permanente con backup.

Riferimenti operativi:
- `docs/wind-document-audit.md`
- `docs/wind-document-inventory.md`
- `docs/wind-document-review.md`
- `scripts/wind_document_audit.py`, `scripts/wind_document_inventory.py`, `scripts/wind_document_review.py`
- `config/wind_document_review_pilot.json`

## Wind Project & Contractor Radar — baseline pubblicata invariata

Baseline pubblicata su `master`: **v0.5.0** (`f2640616540e02448664677427698d808938520f`).

- **51 progetti / 11.202,52 MW wind**;
- **17 seed originari / 1.496,9 MW**;
- **34 progetti integrati dopo promotion gate / 9.705,62 MW**;
- BESS sempre separato dai MW wind.

### Regola probatoria

Solo evidenza project-specific A1/A2 può chiudere uno scope esecutivo. Nessun contractor per deduzione; B/C restano segnali. Owner, developer, advisor, engineering, direzione lavori e supervisione non equivalgono a execution. Storico sullo stesso sito non implica award sul progetto corrente; OEM non implica BoP. Contatti pubblici professionali mantengono ruolo e data; recapiti personali non pertinenti non sono raccolti nel modello commerciale. Durate relative, obiettivi dichiarati e stime sono separati.

## Runtime quotidiano e network (non modificati da D1–D3)

- 61 player commerciali, 34 nodi istituzionali/pubblici, 24 adapter istituzionali eseguibili.
- Company Watch e Project Execution investigation queue sui canonici E4–E7 con scope aperti.
- SQLite operativo separato dal canonico per raw finding, history, cursori e `watch_status`.
- Reconciliation conservativa e digest review-only; nessuna scrittura automatica nel canonico.
- Gli snapshot tecnici di degrado fonte non sono nuovi progetti.

`aggiorna_wind_radar.bat` crea/riusa `.venv`, verifica le dipendenze, interroga i 24 adapter a ogni run e i player dovuti per cadenza. Persiste baseline/new/changed/unchanged, genera `reports/wind-agent/daily-discovery-latest.html`, `.csv`, `.json` e lo storico, aggiorna le code di indagine, scrive `docs/wind/data/local-run-status.json`, esegue i validator e apre report/dashboard. Il primo successo della fonte è baseline, non un elenco di nuovi progetti. `all` forza anche i player; `offline` non usa rete. Il BAT non esegue il nuovo audit documentale finché il rollout non è approvato.

## Discovery e revisione

Discovery resta interna. Promozione soltanto dopo identità, attività corrente, configurazione e stage verificati; conservare i progetti reali incompleti e le guardie negative utili. Med Wind Grecale, Rospo Offshore, Sindia-Macomer e Le Chiancate rimangono nel perimetro di revisione senza automatismi. La nuova analisi non considera la presenza nel registro una certificazione del fascicolo.

## Dashboard / UI v0.6 — stato precedente preservato

Dati mostrati dalla baseline: 51 progetti / 11.202,52 MW, origine 17 seed + 34 integrati, 12 E4+ / 689,7 MW, 9 E7 / 437,7 MW, 47 progetti / 11.068,62 MW senza contractor esecutivo A1/A2 attribuito. Sono KPI ereditati, non nuove verifiche di cantiere.

Restano KPI, filtri, mappa ECharts per provincia, maturità E0–E8, calendario, opportunità e Contractor view; Discovery e le viste Watch non occupano sezioni a piena pagina. La mappa mantiene filtro Provincia dedicato, metrica MW/progetti/MW E4+, conteggio per provincia principale, BESS separato, tooltip e rendering confinati, zoom attivo. D1–D3 non cambiano layout o filtri.

Le precedenti review desktop 1440×1100 e mobile 390×844 appartengono alla fase UI; non costituiscono una nuova verifica visiva di questo passaggio documentale. Ogni rollout pubblico richiede autorizzazione.

## Project-specific enrichment v0.6 — evidenze pregresse da conservare/riesaminare

Le tranche `commercial-enrichment-v06*.json` rimangono additive. Andretta-Bisaccia: Progeco come site management/supervisione, non execution; Tricarico: financial close UniCredit e Vector LTA, non BoP dedotto; Nulvi-Ploaghe: configurazione ERG, procurement aperto; Serra Giannina: D'Agostino lead B; Greci-Montaguto: PROGETTO ENERGIA progettazione, non execution; Alia-Sclafani: storico SOCEP non trasferito automaticamente al repowering; Carlentini: Mammana fondazioni, non estensione al full Civil BoP.

## Validazione e gate successivo

Conservare i validator Wind v0.5/v0.6, il controllo Windows e il live A/B su SQLite persistente. D1–D3 aggiungono i test `test_wind_document_*.py` e il workflow `wind_document_audit.yml`, che verifica accesso/inventario e riscontri su originali senza modifiche canoniche. Il prossimo risultato richiesto è estensione della copertura documentale e commerciale, non una promozione implicita del pilota.

**Nessun merge e nessuna pubblicazione senza approvazione esplicita.**
