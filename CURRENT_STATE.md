# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **v0.5.0** (`f2640616540e02448664677427698d808938520f`).

Baseline canonica invariata:
- **51 progetti / 11.202,52 MW wind**;
- **17 seed originari / 1.496,9 MW**;
- **34 progetti integrati dopo promotion gate / 9.705,62 MW**;
- BESS sempre separato dai MW wind.

## Fase corrente — v0.6

Branch: `feat/wind-radar-v0.6-execution-intelligence`

Draft PR: **#5 — Wind Radar v0.6 — execution intelligence e commercial timing**.

La PR resta **Draft**. Nessun merge o pubblicazione senza autorizzazione esplicita.

### Regola probatoria

- solo evidenza **project-specific A1/A2** può chiudere uno scope esecutivo;
- nessun contractor per deduzione;
- B/C restano segnali;
- owner/developer/advisor/engineering/DL/supervision non equivalgono a execution;
- storico stesso sito non implica award sul progetto corrente;
- OEM non implica BoP;
- BESS resta separato dai MW wind.

## Runtime e network

- **61 player commerciali**;
- **31 nodi istituzionali/pubblici**;
- **21 adapter istituzionali eseguibili**;
- Company Watch operativo;
- Project Execution investigation queue sui canonici E4–E7 con scope aperti;
- SQLite operativo separato dal canonico per raw finding, history, cursori e `watch_status`;
- reconciliation conservativa e digest review-only;
- nessuna scrittura automatica nel canonico.

Player & Network Watch e Institutional & Source Watch **non sono più sezioni a piena pagina della dashboard**: alimentano il motore e sono documentati nella metodologia.

## Discovery — policy corrente

Discovery è una **coda tecnica interna**, non una vista pubblica.

Regola:
- promuovere nel canonico solo candidati con identità, attività corrente, configurazione e stage sufficientemente verificati;
- mantenere internamente i progetti reali ma incompleti;
- rimuovere dalla coda attiva falsi, duplicati o opportunità non più valide;
- conservare guardie negative solo quando servono a evitare reintroduzioni errate o collisioni di identità.

Triage corrente in `docs/wind/data/discovery-triage-v06.json`:
- **Med Wind Grecale** — reale/attivo, hold interno: 698,25 MW; MASE + GU confermano fino a 45 WTG ma non una configurazione finale univoca;
- **Rospo Offshore** — reale/attivo, hold interno: 1.005 MW + 350 MW BESS; exact 67×15 MW ancora privo di conferma A1/A2 sufficiente;
- **Sindia-Macomer 43,4 MW** — reale/attivo, hold interno: procedura MASE in istruttoria, configurazione WTG A1/A2 ancora da chiudere;
- **Le Chiancate** — reale/attivo, hold interno: vecchia istanza archiviata ma nuova istanza MASE del 08/06/2026 in verifica amministrativa; configurazione WTG ancora incompleta.

Nessuno dei quattro current viene cassato; nessuno viene esposto pubblicamente finché non supera il gate.

## UI v0.6 — results first

La home pubblica è ora orientata ai risultati:
- **51 progetti / 11.202,52 MW** canonici;
- origine del canonico: **17 seed + 34 integrati dopo validazione**;
- **12 progetti E4+ / 689,7 MW**;
- **9 progetti E7 / 437,7 MW**;
- **47 progetti / 11.068,62 MW senza contractor esecutivo A1/A2 attribuito**.

Discovery e le due viste Watch non occupano più spazio nella dashboard pubblica.

Restano visibili e operativi:
- KPI e filtri;
- mappa ECharts choropleth per provincia;
- stato per maturità E0–E8;
- calendario attività/milestone;
- opportunità prioritarie;
- Contractor view;
- metodologia con copertura del motore di intelligence.

## Mappa per provincia

- metriche: **MW eolici**, **N. progetti**, **MW E4+**;
- ogni progetto conteggiato una sola volta sulla provincia canonica principale;
- BESS separato;
- filtro Provincia dedicato;
- click mappa non sovrascrive la ricerca testuale;
- tooltip confinato e senza duplicazione della metrica selezionata;
- `roam`/zoom ECharts attivi.

## Browser review

Verifica reale desktop **1440×1100** e mobile **390×844** completata anche sulla nuova home results-first:
- Discovery visibile: **0 sezioni**;
- Player/Source Watch visibili: **0 sezioni**;
- Opportunità prioritarie presente;
- metodologia con 61 player / 31 nodi fonte / 21 adapter presente;
- nessun errore console;
- nessun overflow orizzontale desktop/mobile.

La review visiva precedente della mappa è stata approvata dall'utente; la nuova home results-first è in revisione tramite artifact locale.

## Project-specific enrichment v0.6

Le tranche `commercial-enrichment-v06.json`, `v06b.json`, `v06c.json` e `v06d.json` restano additive.

Principali punti:
- Andretta-Bisaccia: Progeco A2 site management/construction supervision, non execution award; configurazione MASE/Edison 18 WTG / 88,5 MW;
- Tricarico: UniCredit financial close e Vector Renewables LTA, nessun BoP dedotto;
- Nulvi-Ploaghe: ERG 27 WTG × 4,5 MW, procurement/execution principali ancora aperti;
- Serra Giannina: D'Agostino resta lead B, nessuno scope chiuso;
- Greci-Montaguto: PROGETTO ENERGIA A1 progettazione/executive design, non execution;
- Alia-Sclafani: PAS corrente 9 WTG / 55 MW, SOCEP storico non trasferito al repowering;
- Carlentini: Mammana foundation contractor A2 confirmed; nessuna estensione al full Civil BoP.

## Validazione

I validator v0.6 includono regressioni canoniche, promotion, commercial/institutional network, agent architecture, project-specific enrichment, mappa province e sintassi JS.

L'ultimo full live smoke completato prima delle modifiche UI results-first è **#64 — SUCCESS** su tutti i quattro gruppi. Le modifiche successive riguardano UI/documentazione/triage e non cambiano le implementazioni degli adapter live.

## Gate successivo

Il prossimo gate è la revisione dell'artifact **public/results-first**. Dopo approvazione esplicita: riallineamento finale PR body/CI e solo successivamente eventuale autorizzazione a merge/pubblicazione.

**Nessun merge e nessuna pubblicazione prima dell'approvazione esplicita.**
