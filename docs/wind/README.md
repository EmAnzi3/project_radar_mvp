# Wind Construction Radar — MVP

## Scopo

Radar commerciale per il mercato eolico italiano, con priorità alle informazioni utili per intercettare il cantiere e le imprese esecutrici.

## Campi chiave

- MW eolici, con BESS separato;
- Regione, Provincia, Comuni e area coinvolta quando disponibile;
- stato/maturità commerciale;
- developer e SPV;
- Civil BoP, Electrical BoP, OEM, erection/logistics;
- altre aziende coinvolte con ruolo e livello di evidenza;
- milestone operative: apertura cantiere, civili, cavidotti/SSE, consegna WTG, erection, COD;
- prossima milestone e fonti.

## Regola di qualità

Un contractor non viene attribuito come confermato senza evidenza sufficiente. I segnali forti ma non contrattuali restano esplicitamente marcati come tali.

## Seed dataset

Il primo dataset contiene 15 progetti emersi dal probe del 4 settembre 2026, inclusi i tre casi documentali approfonditi:

- Andretta-Bisaccia;
- Alia-Sclafani;
- Serra Giannina.

## Vista grafica

`index.html` include:

- KPI dinamici;
- filtri per Regione, fase, tipo e stato contractor;
- mappa regionale per MW;
- pipeline MW per maturità;
- timeline di civili / erection / COD;
- contractor & intelligence nodes;
- tabella filtrabile;
- scheda progetto laterale con timeline, catena esecutiva e fonti.

## Prossimi passi

1. consolidare e verificare il seed dataset;
2. completare i contractor mancanti sui progetti prioritari;
3. introdurre ingestione normalizzata da Terna/MASE/Regioni;
4. mantenere storico delle configurazioni e delle milestone;
5. aggiungere vista contractor → progetti e alert su nuovi segnali di procurement/mobilitazione.
