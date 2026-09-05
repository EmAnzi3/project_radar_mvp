# CHANGELOG — Project Radar MVP

Formato consigliato: voci brevi, orientate a cosa cambia per il progetto.

## Unreleased

- 2026-09-05 — Avviata **Wind Radar v0.6 — execution intelligence**: nuova baseline di lavoro dai 51 canonici pubblicati in v0.5, priorità a progetti E4–E7 e finestre di procurement/cantiere nei prossimi 12–18 mesi, con ricerca contractor A1/A2 per singolo scope e revisione del ranking solo su evidenza oggettiva.

## v0.5.0 — 2026-09-05

- Promossi **34/38 candidati current** dal discovery v0.4 al canonico tramite promotion gate controllato; il Radar passa a **51 progetti / 11.202,52 MW wind**. I 34 promossi valgono **9.705,62 MW wind + 311 MW BESS**, con BESS sempre separato.
- Restano blocked nel discovery: Med Wind Grecale, Rospo Offshore, Sindia-Macomer 43,4 MW e Le Chiancate.
- Introdotto commercial enrichment completo sui 34 promossi, mantenendo separati owner/developer/advisor/engineering/survey dai contractor esecutivi. Nessun nuovo scope viene chiuso senza evidenza A1/A2 esplicita.
- Aggiunto profilo scope offshore dedicato; corretti Florinas Repowering (E3) e Lujentu (Nardò, Copertino, Galatina).
- La UI carica tutte le tranche commerciali v0.5 nella scheda progetto e nella Contractor view; corretto anche il rendering ridondante “nessun progetto” nella pipeline E0–E8.
- PR #4 mergiata su `master` con commit `f2640616540e02448664677427698d808938520f`; GitHub Pages run `33972645972` **SUCCESS**.

## v0.4.x / v0.3.x — 2026-09-04/05

- 2026-09-05 — Wind contractor lead Tricarico: aggiunto segnale **B** Vestas `WTG supply + installation` dalla fonte company-supplied Rinnovabili.it, corroborata dal comunicato diretto Vestas per ordine/delivery/commissioning; lo scope erection resta aperto finché l'installazione non è confermata da fonte diretta. La Contractor view ora integra anche docpass2 e contractor leads senza alterare la scope coverage A1/A2.
- 2026-09-05 — Wind public/local source pass 2: riconciliata l'identità di Andretta-Bisaccia, aggiunto identity guard ALAS/Alas 2 e genealogia Tricarico/Corona Prima, ricostruita la catena PLT→Plenitude per Tarsia Ovest, aggiunti Comune di Osilo/Nulvi-Ploaghe e nuovi atti territoriali; nessun nuovo scope esecutivo A1/A2 chiuso senza prova diretta.
- 2026-09-04 — Wind document pass 2: acquisiti e letti i cronoprogrammi ALAS e Toritto, REL101/REL102 Fenice e `74402A` SE Casamassima; aggiunti Hydro A1 come progettista opere civili ALAS e ATS Engineering A1 come engineering Fenice senza chiudere scope esecutivi; avviata la nuova classe fonti enti pubblici regionali/provinciali/comunali sui 17 seed.
- 2026-09-04 — Wind enrichment v0.3: contractor hunt + deep-document sui 17 seed, introduzione della scope coverage (**230,9 MW** con almeno uno scope esecutivo A1/A2; **8/108** scope applicabili coperti), Commercial Window, investigation queue, document intelligence e nuove evidenze su Carlentini, Venusia, Nulvi-Ploaghe, Tricarico, Serra Giannina e Greci-Montaguto.
- 2026-09-04 — Review Wind Radar: chiarita la precisione geografica (marker territoriali, non coordinate WTG), aggiunti tooltip a pipeline/timeline, scroll interno alle opportunità e contractor view compatta con selettore azienda.
- 2026-09-04 — Evoluto `docs/wind/` in un Wind Project & Contractor Radar operativo: seed verificato di 17 progetti / 1.496,9 MW eolici, schema E0–E8, MW wind/BESS separati, storico configurazioni, supply chain con fonte/confidenza, 7 KPI, mappa a marker progetto, timeline di cantiere, opportunità responsive, contractor view inversa, dettaglio progetto ed export CSV.
- 2026-09-04 — Sostituito il vecchio dataset monolitico `docs/wind/data.json` con manifest + metadata + 3 chunk progetto; rimossa la dipendenza da librerie JS esterne per la dashboard Wind.
- 2026-09-04 — Avviato `docs/wind/` con Wind Construction Radar MVP: seed iniziale di 15 progetti, filtri, mappa regionale, pipeline per maturità, contractor view e schede progetto.

## Repository maintenance

- 2026-06-02 — Aggiunti file minimi di manutenzione repository: `CURRENT_STATE.md`, `AGENTS.md`, `CHANGELOG.md` e `scripts/check_before_publish.ps1`.
