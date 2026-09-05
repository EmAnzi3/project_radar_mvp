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

Obiettivo: trasformare il contractor gap binario in **scope coverage** e integrare contractor hunt, deep-document e fonti pubbliche territoriali.

Core scope normalizzati:

1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per i repowering.

Metriche correnti:

- **230,9 MW** con almeno uno scope esecutivo A1/A2 identificato;
- **8 / 108 scope applicabili** coperti A1/A2 = **7,4%**;
- il KPI MW indica soltanto la presenza di almeno uno scope confermato, non un BoP completamente assegnato;
- i pass documentali e territoriali aumentano l'intelligence senza promuovere automaticamente segnali B/C o soggetti tecnici a contractor esecutivi.

Nuove evidenze contractor/tecniche già censite:

- Carlentini: Gruppo Mammana A2 su fondazioni/getti; Hydro Engineering A2 su DL e foundation engineering/quality; BFP A2 su CSP/CSE;
- Venusia: EGM Project A2 su progettazione esecutiva / Direzione Lavori;
- Nulvi-Ploaghe: Hydro Engineering A2 su sviluppo/engineering;
- Tricarico: Vector Renewables A2 come LTA / construction monitoring;
- **Tricarico: Vestas B `WTG supply + installation`, scope_hint erection** — fonte company-supplied descrive installazione, ma il comunicato diretto Vestas conferma solo ordine/delivery/commissioning; Erection resta quindi aperto;
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
- Contractor view unificata: relazioni base + enrichment + docpass2 + contractor leads, mantenendo segnali B/C separati dagli scope A1/A2;
- pannello `Deep document & public-source pass` nel drawer, alimentato anche dai registri di fonti regionali e comunali.

### Deep-document — full text acquisito

Già letti in profondità:

- Andretta-Bisaccia — Piano di cantierizzazione;
- Alia-Sclafani — cronoprogramma repowering;
- Serra Giannina — cronoprogramma BoP WTG-by-WTG;
- ALAS — `PEALAS_PE_00016_01_00` Cronoprogramma dei lavori / Progetto Esecutivo Opere Civili;
- Toritto — `C24PU001WP010R00` Cronoprogramma;
- Fenice — REL101 Relazione Generale + REL102 Relazione tecnica impianto, integrazioni aprile 2026;
- Lama Cupa / connessione — `74402A` Cronoprogramma SE 380/150/36 kV Casamassima.

Risultati principali:

- **ALAS:** cronoprogramma baseline agosto 2024; contiene fondazioni/piazzole, SSE/cavidotto, anchor cage, erection e COD, ma non sostituisce lo stato reale RWE 2026. Hydro è progettista, non Civil BoP.
- **Toritto:** programma di 503 giorni relativi; apertura 1–10, strade/piazzole fino a ~214, fondazioni ~170–266, erection ~237–306, cavidotti 71–300, SSE 301–450, commissioning SSE 450–489, smobilizzo 489–503. Nessuna data calendario senza anchor reale.
- **Fenice:** REL101/102 confermano 51 WTG / 367,2 MW, ATS Engineering, opere civili, cavidotti e stazione/connessione; nessun contractor esecutivo identificato.
- **Lama Cupa:** `74402A` riguarda la SE Casamassima, con FLYNIS PV 34 committente e Brulli Trasmissione engineering & construction. **Brulli non viene attribuita a Lama Cupa.**

### Fonti pubbliche territoriali

Il radar interroga sistematicamente, limitatamente ai 17 seed:

1. Regione — VIA/AU, trasparenza, pubblicità legale/albo, BUR/BURP;
2. Provincia/Città metropolitana — viabilità, attraversamenti, occupazioni, trasporti eccezionali;
3. Comune — Albo Pretorio, determine/delibere/ordinanze, SUAP/urbanistica, espropri, viabilità e Polizia Locale;
4. Terna/ANAS/gestori infrastrutturali;
5. portali corporate di proponenti/contractor come fonti dirette o lead, senza sostituire A1.

Registri:

- `docs/wind/data/public-entity-sources-2026-09-04.json`;
- `docs/wind/data/local-entity-sources-2026-09-04.json`;
- `docs/wind/data/contractor-leads-2026-09-05.json`;
- `docs/wind/research/2026-09-04-public-entity-source-pass.md`;
- `docs/wind/research/2026-09-05-local-source-pass-2.md`;
- `docs/wind/research/2026-09-05-identity-reconciliation.md`.

### Pass locale/pubblico 2026-09-05

- **Andretta-Bisaccia:** identity reconciliation chiusa. Il record operativo resta Edison Rinnovabili **18 WTG / 88,5 MW**. Il procedimento regionale 13 WTG / 85,8 MW è una pista amministrativa/progettuale distinta e correlata, non un aggiornamento del record corrente.
- **ALAS:** identity guard tra `ALAS` 66 MW e il distinto `Alas 2` 50,4 MW negli stessi comuni; nessun atto o contractor viene trasferito tra i due senza verifica di procedura/configurazione. Nessuna ordinanza locale viabilità/mezzi pesanti attribuita con certezza finora.
- **Serra Giannina:** gli elaborati esecutivi MASE 2026 confermano la configurazione corrente **42 MW / 6 WTG**; configurazioni precedenti restano storico amministrativo.
- **Tarsia Ovest:** ricostruita la catena locale/amministrativa PLT → Eni Plenitude. Comune di Tarsia: convenzione PLT 2023 e ordine del giorno 01/12/2025 per la nuova convenzione con Plenitude; Regione Calabria: voltura 2025 e variante 2026. Resta da recuperare la delibera finale 2025 con allegato convenzione.
- **Nulvi-Ploaghe:** Comune di Osilo, Delibera Consiglio n.29 del 30/07/2026, dedicata al potenziamento. Le ordinanze Osilo 2026 indicizzate non mostrano ancora un atto chiaramente attribuibile al cantiere eolico. Il progetto resta Priority 1 perché ERG dichiara un rilevante ricorso a imprese/fornitori locali senza ancora nominarli.
- **Tricarico:** genealogia amministrativa `Corona Prima`/Adest separata dalle configurazioni storiche; il record corrente resta 42 MW. Il nuovo lead Vestas installation resta B; nessuna deduzione `Idoka proprietaria = Idoka Civil BoP`.
- **Greci-Montaguto:** variante, espropri e cantiere sono confermati, ma Civil BoP/fondazioni restano aperti; un framework Hydro–ERG non viene attribuito perché non project-specific.

### Regola identity/versioning

Ogni fonte viene classificata rispetto al record operativo (`same-project-current`, `same-project-historical-config`, `same-project-current-plus-parallel-track`, ecc.). MW/WTG non vengono mai sovrascritti automaticamente sulla sola base del nome/località.

### Stato contractor hunt

Il pass del 5 settembre **non chiude nuovi scope esecutivi A1/A2**. I target con maggior valore investigativo restano:

- Nulvi-Ploaghe — procurement locale dichiarato, fornitori non nominati;
- ALAS — cantiere attivo, impresa esecutrice non identificata;
- Serra Giannina — D’Agostino resta forte segnale B;
- Greci-Montaguto — cantiere attivo, BoP/fondazioni aperti;
- Tricarico — Vestas installation B da confermare direttamente; Civil/Electrical BoP aperti.

### Verifiche correnti

- 17 progetti / 1.496,9 MW invariati;
- scope coverage invariata **8/108**;
- MW con ≥1 scope A1/A2 invariati **230,9 MW**;
- Vestas/Tricarico installation resta B e non chiude Erection;
- Carlentini chiude solo Foundation;
- Hydro ALAS e ATS Fenice non chiudono scope esecutivi;
- Brulli non è attribuita a Lama Cupa;
- preview standalone verificata in browser: Contractor view unificata mostra Vestas/Tricarico come `signal · B`, KPI 230,9 MW e 8/108, senza errori console.

### Pass aperti prima di proporre merge

- recuperare delibera finale + convenzione 2025 Tarsia–Plenitude;
- cercare Nulvi/Ploaghe/Osilo: ordinanze viabilità, occupazioni e trasporti eccezionali;
- cercare Ittiri/Villanova Monteleone: atti locali ALAS su viabilità/mezzi pesanti/cantiere;
- cercare Greci/Montaguto e Provincia Avellino: viabilità e trasporti del repowering;
- cercare Tricarico/Adest: apertura cantiere, connessione e accessi + conferma diretta Vestas installation;
- cercare un cronoprogramma Fenice nel restante corpus MASE;
- cercare l'anchor reale di avvio Toritto;
- completare preview visuale mobile del nuovo pannello;
- audit coordinate territoriali contro corografie/layout ufficiali resta separato.

### Vincoli

Nessun merge e nessuna pubblicazione dell'enrichment finché non viene data approvazione esplicita.
