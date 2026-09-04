# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: MVP 17 progetti / 1.496,9 MW eolici.

Branch di lavoro corrente: `feat/wind-radar-enrichment-v0.3`.

Stato branch: enrichment / preview, **non mergiato e non pubblicato**.

### Baseline pubblicata

- 17 progetti;
- 1.496,9 MW eolici;
- BESS separato dal wind;
- scala maturità E0–E8;
- evidence grading A1/A2/B/C/D;
- GlobalData solo enrichment/lead source;
- mappa con confini regionali e marker territoriali indicativi;
- filtri, timeline, opportunità, contractor view, dettaglio progetto ed export CSV.

### Enrichment v0.3 in review

Obiettivo: trasformare il contractor gap binario in **scope coverage** e integrare contractor hunt, deep-document e una nuova classe di fonti pubbliche territoriali.

Core scope normalizzati:

1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per i repowering.

Metriche dopo l'enrichment corrente:

- **230,9 MW** con almeno uno scope esecutivo A1/A2 identificato;
- **8 / 108 scope applicabili** coperti A1/A2 = **7,4%**;
- il KPI MW indica soltanto la presenza di almeno uno scope confermato, non un BoP completamente assegnato;
- il secondo pass documentale aggiunge intelligence e soggetti tecnici, ma **non aumenta artificialmente gli scope esecutivi coperti**.

Nuove evidenze contractor/tecniche già censite:

- Carlentini: Gruppo Mammana A2 su fondazioni/getti; Hydro Engineering A2 su DL e foundation engineering/quality; BFP A2 su CSP/CSE;
- Venusia: EGM Project A2 su progettazione esecutiva / Direzione Lavori;
- Nulvi-Ploaghe: Hydro Engineering A2 su sviluppo/engineering;
- Tricarico: Vector Renewables A2 come LTA / construction monitoring;
- Serra Giannina: D’Agostino B come forte segnale di presenza construction/site, non Civil BoP confermato;
- Greci-Montaguto: RINA B come segnale Electrical & Quality Inspection;
- ALAS: Hydro Engineering A1 come progettista del Progetto Esecutivo Opere Civili, **non** Civil BoP;
- Fenice: ATS Engineering A1 come engineering/design, **non** contractor esecutivo.

### UI enrichment

Il branch aggiunge:

- KPI `MW con ≥1 scope esecutivo`;
- KPI `Scope esecutivi coperti`;
- chip scope coverage in Opportunità prioritarie;
- scheda progetto con Commercial Window, completezza intelligence, matrice scope, investigation queue e document intelligence;
- Contractor view arricchita con relazioni tecniche/esecutive senza promuovere segnali B/C a contractor confermati.

### Deep-document — full text acquisito

Già letti in profondità:

- Andretta-Bisaccia — Piano di cantierizzazione;
- Alia-Sclafani — cronoprogramma repowering;
- Serra Giannina — cronoprogramma BoP WTG-by-WTG;
- **ALAS — `PEALAS_PE_00016_01_00` Cronoprogramma dei lavori / Progetto Esecutivo Opere Civili**;
- **Toritto — `C24PU001WP010R00` Cronoprogramma**;
- **Fenice — REL101 Relazione Generale + REL102 Relazione tecnica impianto, integrazioni aprile 2026**;
- **Lama Cupa / connessione — `74402A` Cronoprogramma SE 380/150/36 kV Casamassima**.

### Risultati del secondo pass documentale

- **ALAS:** il cronoprogramma è una baseline pianificata emessa ad agosto 2024; contiene anchor cage, trasformatore, SSE/cavidotto, erection e COD pianificati, ma non va sovrapposto allo stato reale successivo comunicato da RWE. Hydro è progettista delle opere civili, non contractor esecutivo.
- **Toritto:** programma di **503 giorni relativi**. Apertura 1–10, strade/piazzole fino a ~214, fondazioni ~170–266, erection ~237–306, cavidotti 71–300, SSE 301–450, commissioning SSE 450–489, smobilizzo 489–503. Nessuna conversione a date finché manca un anchor reale di avvio cantiere.
- **Fenice:** REL101/102 confermano 51 WTG / 367,2 MW, ATS Engineering, opere civili, cavidotti e stazione/connessione; nessun contractor esecutivo e nessun cronoprogramma di costruzione trovato in questi due elaborati.
- **Lama Cupa:** `74402A` è nel corpus integrativo ma il frontespizio identifica FLYNIS PV 34 come committente e Brulli Trasmissione come engineering & construction della SE Casamassima. **Brulli non viene attribuita a Lama Cupa.** Il file è trattato come intelligence sull'infrastruttura RTN condivisa/relata e sulla `RdO e subappalto opere civili` della stazione.

I dati incrementali sono in `docs/wind/data/enrichment-docpass2-2026-09-04.json`.

### Nuova classe fonti: enti pubblici territoriali

Il radar inizia a interrogare sistematicamente, limitatamente ai 17 seed:

1. Regione — VIA/AU, trasparenza, pubblicità legale/albo, BUR/BURP;
2. Provincia/Città metropolitana — viabilità, attraversamenti, occupazioni, trasporti eccezionali;
3. Comune — Albo Pretorio, determine/delibere/ordinanze, SUAP/urbanistica, espropri, viabilità e Polizia Locale;
4. Terna/ANAS/gestori infrastrutturali;
5. portali corporate di proponenti/contractor come fonti dirette o lead, senza sostituire A1.

Primi riscontri:

- Comune di Ittiri pubblica documentazione specifica sul progetto ALAS e sui rapporti con Regione Sardegna;
- Regione Puglia espone Toritto, Fenice e Lama Cupa nel BURP e pubblica gli atti anche su Trasparenza e Albo Telematico;
- gli stessi elaborati Fenice/Andretta mostrano che viabilità, attraversamenti e trasporti richiedono atti di enti comunali/provinciali, rendendo questi portali fonti operative ad alto valore.

Audit: `docs/wind/research/2026-09-04-public-entity-source-pass.md`.

### Pass aperti prima di proporre merge

- integrare il secondo overlay documentale nella UI/drawer e validarlo;
- contractor hunt sui gap Priority 1 usando anche atti regionali/provinciali/comunali;
- cercare un cronoprogramma Fenice nel restante corpus MASE;
- cercare l'anchor reale di avvio Toritto quando emergerà;
- seguire la filiera della SE Casamassima senza trasferire automaticamente contractor condivisi a Lama Cupa;
- preview visuale desktop/mobile;
- audit puntuale delle coordinate territoriali contro corografie/layout ufficiali resta separato.

### Vincoli

Nessun merge e nessuna pubblicazione dell'enrichment finché non viene data approvazione esplicita.
