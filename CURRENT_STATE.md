# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **17 progetti / 1.496,9 MW wind**.  
Branch corrente: `feat/wind-radar-enrichment-v0.3`.  
Draft PR: **#2 — Wind Radar v0.3 — contractor hunt, scope coverage e document intelligence**.  
Stato: **non mergiato e non pubblicato**.

## Regola v0.3

Core scope:
1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per repowering.

Solo A1/A2 con `azienda + progetto + ruolo esecutivo` possono chiudere un core scope. B/C, engineering, DL, CSE, LTA, inspection, development, financing e site management restano intelligence.

## Metriche correnti

- **17 progetti / 1.496,9 MW wind**;
- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope applicabili coperti = **7,4%**;
- **437,7 MW in costruzione E7** dopo la correzione di Castelfranco/CER.

Coperture execution correnti:
- Serra Palino: Civil + Electrical;
- Venusia: Civil/site preparation;
- Carlentini: Foundation;
- Tarsia Ovest: Civil + Electrical + SSE/grid;
- Castelfranco/CER: SSE/grid.

## Pipeline E0–E8 — modello canonico

Audit completato il 05/09/2026 e registrato in:
`docs/wind/research/2026-09-05-stage-consistency-audit.md`

**E0–E8 è una scala interna del Radar**, non una nomenclatura tecnica universale. Le etichette usano terminologia di settore:
- **E0 Pre-sviluppo** — opportunità/progetto individuato e in valutazione preliminare; sviluppo strutturato non ancora sufficientemente verificato;
- **E1 Sviluppo** — developer/SPV e sviluppo osservabili, iter formale non ancora osservato;
- **E2 Iter autorizzativo** — VIA/AU/permitting formalmente avviato;
- **E3 Iter autorizzativo avanzato** — VIA favorevole o iter nelle fasi finali, ma autorizzazione complessiva non acquisita;
- **E4 Autorizzato** — principali autorizzazioni ottenute, senza FID/financial close/procurement sufficiente osservato;
- **E5 FID / investimento impegnato** — FID/financial close/altro commitment vincolante, procurement principale non ancora osservato;
- **E6 Procurement / affidamenti** — ordini/contratti principali osservati, lavori fisici non ancora provati;
- **E7 Costruzione** — lavori fisici in sito avviati;
- **E8 In esercizio** — commissioning/COD completato e impianto operativo.

Regola: il progetto assume **la fase più avanzata direttamente osservata**. Non serve avere una fonte distinta per ogni fase precedente. Le fasi a zero restano sempre visibili e non sono considerate “saltate”.

Distribuzione corrente:
- E0: 0
- E1: 0
- E2: 3
- E3: 2
- E4: 1
- E5: 0
- E6: 2
- E7: 9
- E8: 0

Correzione emersa dall'audit:
- **Castelfranco in Miscano / CER: E6 → E7**, perché Energy& documenta lavori fisici di revamping in corso.

Gli altri 16 stage sono risultati coerenti con le soglie canoniche.

UI pipeline:
- legenda mappa mostra tutte le 9 fasi, comprese quelle a zero;
- filtro, pipeline e badge progetto usano la tassonomia canonica centrale;
- fasi a zero mostrate come `nessun progetto`;
- nota esplicativa sul fatto che 0 ≠ fase saltata;
- browser test desktop 1440 px + mobile 390 px PASS anche con le nuove etichette E5/E6, nessun overflow e nessun errore console.

Regression guard: `scripts/check_wind_stages.py` protegge anche le nove label esatte e la coerenza del glossario.

## Contractor / technical intelligence consolidata

### Andretta-Bisaccia
- Edison Rinnovabili **18 WTG / 88,5 MW** come baseline operativa da riconciliare con pista Edison 13 WTG / 85,8 MW;
- Progeco Group / Progeco SE: **B — site/construction management & works supervision**, non Civil BoP;
- GEKO: engineering/cantierizzazione A1;
- apertura cantiere 02/11/2026; civili dal 13/11/2026;
- distinto MERAL 30 MW / 5 WTG negli stessi Comuni = collision guard.

### Serra Giannina
- corrente **42 MW / 6 WTG**, costruzione RWE avviata 21/05/2026;
- D'Agostino B construction/site presence; EGM Project B tecnica;
- nessun Civil/Foundation/Electrical/SSE A1/A2;
- 45 MW / 10 WTG = storico autorizzativo.

### ALAS
- RWE **66 MW / 10 WTG**;
- Hydro Engineering A1 progettista Progetto Esecutivo Opere Civili, non Civil BoP;
- impresa esecutrice nominale non trovata;
- distinto `Alas 2` RWE 50,4 MW / 7 WTG negli stessi Comuni.

### Greci-Montaguto
- ERG **43,8 MW**, costruzione marzo 2026 → estate 2027;
- Vestas OEM A2; RINA B inspection;
- Civil/Foundation/Dismantling/Logistics/SSE aperti.

### Nulvi-Ploaghe
- ERG **121,5 MW / 27 WTG**, autorizzato e Route-to-Market eligible;
- Hydro Engineering A2 development/engineering, non BoP;
- ERG/stampa confermano procurement locale rilevante ma senza nomi esecutivi verificati;
- DUVRI ERG 43,35 MW / 51 Vestas V52 escluso: sito legacy, non repowering;
- distinto Nulvi-Tergu 99 MW / FRI-EL Anglona = identity guard.

### Tricarico
- Adest **42 MW / 7 × Vestas V162-6MW**;
- Vestas OEM A2; `WTG supply + installation` resta B perché la fonte diretta non esplicita installation;
- Vector Renewables A2 LTA/construction monitoring, non esecutore;
- UniCredit green mini-perm project financing **46,5 mln €**, target operativo H2 2027;
- resta **E6**, perché non è ancora provato l'avvio fisico del cantiere;
- distinto Dolomiti Windfarm 79,2 MW / 12 WTG = identity guard.

### Venusia
- Idoka A2 Civil/site preparation, fase civile conclusa;
- EGM Project A2 engineering/DL;
- Nordex Group A2 OEM corrente;
- New Developments A2 co-development/engineering;
- record corretto a **8 WTG × 5,6 MW**;
- Electrical/SSE, Erection, Logistics e Foundation ancora da provare.

### Serra Palino
- D'Agostino A2 Civil + Electrical/electromechanical;
- Nordex Group A2 OEM corrente;
- SSE/grid, Erection, Logistics, Foundation ancora aperti.

### Tarsia Ovest
- RTI Idoka / Michelangelo Mammana / PLC / Delta A2 Civil + Electrical infrastructure;
- PLC A2 SSE/grid;
- Michelangelo Mammana B individual Civil hint;
- Concessioni Provincia Cosenza 85/2025 e 111/2025: cavi MT; 139/2026: possibile accesso SP176, non Logistics;
- distinta Deaway Solar sulla SP176 = collision guard.

### Castelfranco in Miscano / CER
- CER / Campana Energie Rinnovabili / IP Gruppo api — **CUP 9439 / Difesa Vecchia / 5 WTG**;
- **E7 Costruzione** dopo audit pipeline: Energy& documenta lavori fisici di revamping in corso;
- Vestas OEM A2; PLC A2 SSE/grid;
- Energy& resta B per scope: la prova dell'esistenza del cantiere non prova quali lavorazioni esegua materialmente Energy&;
- distinto Fri-El / progetto Miscano 29,4 MW / CUP 9207 = collision guard.

### Carlentini
- Gruppo Mammana Foundation/concrete; Hydro foundation engineering/quality + DL; BFP CSP/CSE;
- solo Foundation chiude un core scope.

### Alia-Sclafani
- 55 MW / 9 Vestas, E7;
- Staffetta 2019 = same-site historical config;
- FM Service Group = C candidate site-services, progetto non nominato.

### Fenice
- NVA Fenice 51 WTG / 367,2 MW, E3 iter autorizzativo avanzato / in attesa concerto;
- ATS Engineering A1 design, non contractor;
- REL101/REL102 letti; nessun cronoprogramma distinto emerso.

### Toritto
- 108 MW wind + 50 MW BESS, E2 iter autorizzativo/VIA;
- cronoprogramma 503 giorni solo relativo.

### Sava-Maruggio / Volturino / Lama Cupa
- Sava-Maruggio E3;
- Volturino E2;
- Lama Cupa E2;
- Brulli resta riferita alla SE Casamassima / FLYNIS PV 34, non al parco Lama Cupa.

## Deep-document acquisito

Full text già letto:
- Andretta-Bisaccia — Piano di cantierizzazione;
- Alia-Sclafani — cronoprogramma repowering;
- Serra Giannina — cronoprogramma BoP WTG-by-WTG;
- ALAS — `PEALAS_PE_00016_01_00`;
- Toritto — `C24PU001WP010R00`;
- Fenice — REL101 + REL102;
- Lama Cupa / connessione — `74402A` SE Casamassima.

## Pass conclusi il 5 settembre

- `docs/wind/research/2026-09-05-contractor-priority1-pass-5.md`
- `docs/wind/research/2026-09-05-public-pass-6.md`
- `docs/wind/research/2026-09-05-industry-press-pass-7.md`
- `docs/wind/research/2026-09-05-identity-reconciliation.md`
- `docs/wind/research/2026-09-05-v03-final-validation.md`
- `docs/wind/research/2026-09-05-glossary-validation.md`
- `docs/wind/research/2026-09-05-stage-consistency-audit.md`

## Glossario

Glossario ricercabile per utenti non tecnici, 37 termini / 9 categorie:
- `docs/wind/data/glossary.json`
- `docs/wind/assets/glossary.js`
- `docs/wind/assets/glossary.css`

Copre MW, WTG, BESS, BoP, SSE, COD, FID, OEM, EPC, RTI, DL, CSP/CSE, LTA, VIA, AU, MASE, MYTERNA, A1-D, E0-E8, scope, contractor gap, ecc. La voce E0–E8 chiarisce che i codici sono interni al Radar e riporta le nove etichette sector-aligned.

## Regression guards / verifiche

- `scripts/check_wind_radar.py`
- `scripts/check_wind_industry_press.py`
- `scripts/check_wind_stages.py`

Gate browser già eseguiti su desktop/mobile per v0.3, Industry intelligence, glossario e pipeline E0-E8.

## Stato

**v0.3 conclusa per enrichment/research, rappresentazione UI, glossario e normalizzazione pipeline; pronta per revisione utente e step successivi.**

Nessun merge e nessuna pubblicazione senza approvazione esplicita.