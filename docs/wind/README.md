# Wind Project & Contractor Radar — MVP

## Scopo

Radar commerciale eolico italiano orientato alle fasi di costruzione e alla supply chain esecutiva. La vista serve a capire **dove**, **quanti MW**, **a che punto**, **quando entra il cantiere** e **chi realizza fisicamente le opere**.

## Struttura

- `index.html` — shell della dashboard;
- `assets/app.js` — filtri, KPI, mappa, timeline, viste progetto/contractor ed export CSV;
- `assets/style.css` — layout responsive senza tabella operativa a scroll orizzontale;
- `assets/review-fixes.js` / `review-fixes.css` — rifiniture della review: tooltip, precisione geografica, scroll opportunità e selettore contractor;
- `assets/italy-base.svg` — base cartografica locale;
- `data/projects.json` — manifest canonico;
- `data/meta.json` — scala E0–E8, evidenze A1–D e ruoli esecutivi;
- `data/projects-1.json` … `projects-3.json` — 17 record seed normalizzati.

Il vecchio `docs/wind/data.json` è stato rimosso per evitare due dataset divergenti. La dashboard non dipende da librerie JavaScript esterne.

## Seed MVP

Il dataset contiene 17 progetti:

- Andretta-Bisaccia;
- Alia-Sclafani;
- Serra Giannina;
- Serra Palino;
- Venusia;
- ALAS;
- Greci-Montaguto;
- Carlentini;
- Nulvi-Ploaghe;
- Tricarico;
- Tarsia Ovest;
- Fenice;
- Sava-Maruggio;
- Toritto;
- Volturino;
- Lama Cupa;
- Castelfranco in Miscano / CER.

## Modello dati

Ogni progetto conserva separatamente:

- identità e ID procedurali disponibili;
- geografia e coordinate indicative per la mappa;
- MW eolici e MW BESS separati;
- numero/potenza WTG quando disponibili;
- maturità osservabile `E0–E8`;
- timing per fase (`civil`, `sse`, `cables`, `wtg_delivery`, `erection`, `commissioning`, `cod`, ecc.);
- supply chain con `company`, `role`, `status`, `confidence` e `source_id`;
- contractor gap;
- configurazioni storiche con data e fonte;
- fonti/evidenze;
- eventuale nota GlobalData, marcata esclusivamente come enrichment/lead source.

### Precisione geografica

I marker della mappa MVP sono **riferimenti territoriali indicativi del progetto**. Non devono essere interpretati come coordinate delle singole WTG. La UI li segnala esplicitamente come proxy territoriali; una posizione viene promossa a layout verificato solo dopo riscontro su corografia/elaborato ufficiale.

### Scala maturità

- E0 Universe
- E1 Developing
- E2 Permitting
- E3 Advanced permitting
- E4 Authorized
- E5 Market committed
- E6 Procurement
- E7 Construction
- E8 Operating

Non vengono usate percentuali di avanzamento arbitrarie.

## Regola contractor

Un ruolo esecutivo non viene mai attribuito per deduzione. Il KPI **MW con contractor esecutivo** considera solo relazioni:

1. su un ruolo esecutivo definito in `meta.json`;
2. con `status = confirmed`;
3. con confidenza `A1` o `A2`.

I segnali `B` e `C` restano intelligence e non diventano assegnazioni contrattuali.

## Dashboard

La home include:

- 7 KPI operativi;
- mappa Italia con marker progetto e tooltip, con precisione geografica esplicitata;
- filtri per regione, E0–E8, tipo, developer, contractor, MW e finestra temporale;
- pipeline MW per maturità con tooltip;
- timeline di cantiere con tooltip per fase/data/confidenza;
- opportunità prioritarie responsive con scorrimento interno al box;
- contractor view inversa con selettore azienda → progetti → MW → ruolo → stato → timing;
- scheda progetto con anagrafica, timing, supply chain, gap, fonti e storico configurazioni;
- export CSV del filtro corrente.

## Prossimi passi

1. verificare i marker contro corografie/layout ufficiali e registrare il livello di precisione;
2. consolidare i contractor mancanti sui progetti A+/A;
3. aggiungere ingestione/normalizzazione Terna Econnextion, MASE e atti regionali;
4. automatizzare il versioning di configurazioni e milestone;
5. aggiungere alert su procurement, mobilitazione e nuovi segnali contractor;
6. estendere progressivamente il seed senza abbassare la soglia di evidenza.
