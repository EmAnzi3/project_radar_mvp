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

Obiettivo: trasformare il contractor gap binario in **scope coverage** e integrare la prima passata sistematica contractor hunt + deep-document.

Core scope normalizzati:

1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per i repowering.

Metriche dopo il primo enrichment:

- **230,9 MW** con almeno uno scope esecutivo A1/A2 identificato;
- **8 / 108 scope applicabili** coperti A1/A2 = **7,4%**;
- il KPI MW indica soltanto la presenza di almeno uno scope confermato, non un BoP completamente assegnato.

Nuove evidenze principali:

- Carlentini: Gruppo Mammana A2 su fondazioni/getti; Hydro Engineering A2 su DL e foundation engineering/quality; BFP A2 su CSP/CSE;
- Venusia: EGM Project A2 su progettazione esecutiva / Direzione Lavori;
- Nulvi-Ploaghe: Hydro Engineering A2 su sviluppo/engineering;
- Tricarico: Vector Renewables A2 come LTA / construction monitoring;
- Serra Giannina: D’Agostino B come forte segnale di presenza construction/site, non Civil BoP confermato;
- Greci-Montaguto: RINA B come segnale Electrical & Quality Inspection.

### UI enrichment

Il branch aggiunge:

- KPI `MW con ≥1 scope esecutivo`;
- KPI `Scope esecutivi coperti`;
- chip scope coverage in Opportunità prioritarie;
- scheda progetto con Commercial Window, completezza intelligence, matrice scope, investigation queue e document intelligence;
- Contractor view arricchita con le nuove relazioni tecniche/esecutive senza promuovere i segnali B/C a contractor confermati.

### Deep-document

Già letti in profondità:

- Andretta-Bisaccia — Piano di cantierizzazione;
- Alia-Sclafani — cronoprogramma repowering;
- Serra Giannina — cronoprogramma BoP WTG-by-WTG.

Documenti prioritari identificati ma full text ancora da acquisire:

- Toritto — `Cronoprogramma Impianto Eolico Toritto`;
- Lama Cupa — `74402A.pdf` Cronoprogramma delle Attività + Piano Tecnico delle Opere / planimetrie;
- ALAS — Elenco Elaborati progetto opere civili e relativi elaborati esecutivi;
- Fenice — Relazione Generale e Relazione Tecnica integrate 24/04/2026.

Audit completo: `docs/wind/research/2026-09-04-contractor-deep-doc-pass.md`.

### Pass aperti prima di proporre merge

- verifica tecnica del layer enrichment e dei nuovi KPI;
- preview visuale desktop/mobile;
- acquisizione dei PDF Toritto/Lama Cupa se disponibili;
- ulteriore contractor hunt sui gap ad alta priorità;
- audit puntuale delle coordinate territoriali contro corografie/layout ufficiali resta separato.

### Vincoli

Nessun merge e nessuna pubblicazione dell'enrichment finché non viene data approvazione esplicita.
