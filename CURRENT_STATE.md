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

Invariate dopo Priority 1 + Public Pass 6 + Industry Press Pass 7:

- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope applicabili coperti = **7,4%**;
- il KPI MW indica presenza di almeno uno scope noto, non BoP completo.

Coperture correnti:
- Serra Palino: Civil + Electrical;
- Venusia: Civil/site preparation;
- Carlentini: Foundation;
- Tarsia Ovest: Civil + Electrical + SSE/grid;
- Castelfranco/CER: SSE/grid.

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
- ERG/stampa confermano circa **40 mln €** destinati a imprese/fornitori locali e circa 60 risorse locali durante la costruzione, ma nessun nome esecutivo verificato;
- DUVRI ERG 43,35 MW / 51 Vestas V52 escluso: sito legacy, non repowering;
- distinto Nulvi-Tergu 99 MW / FRI-EL Anglona = identity guard.

### Tricarico
- Adest **42 MW / 7 × Vestas V162-6MW**;
- Vestas OEM A2; `WTG supply + installation` resta B perché la fonte diretta non esplicita installation;
- Vector Renewables A2 LTA/construction monitoring, non esecutore;
- **Industry Pass 7:** UniCredit ha perfezionato il **green mini-perm project financing da 46,5 mln €** l'11/06/2026; costruzione/messa in esercizio finanziate e target operativo entro **H2 2027**. È market/financial intelligence, non execution scope;
- distinto Dolomiti Windfarm 79,2 MW / 12 WTG e precedente `Tricarico Italy` Siemens = collision/history guards.

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
- Michelangelo Mammana B individual Civil hint; manca originale diretto per upgrade;
- Concessioni Provincia Cosenza 85/2025 e 111/2025: cavi MT; 139/2026: possibile accesso SP176, ma titolo non prova Tarsia Ovest né Logistics;
- distinta Deaway Solar sulla SP176 = collision guard.

### Castelfranco in Miscano / CER
- CER / Campana Energie Rinnovabili / IP Gruppo api — **CUP 9439 / Difesa Vecchia / 5 WTG**;
- Vestas OEM A2; PLC A2 SSE/grid;
- Energy& B repowering engineering/site involvement, non Civil/Foundation/Dismantling/Erection per deduzione;
- **Industry Pass 7:** distinto **Fri-El / progetto Miscano 29,4 MW / CUP 9207**, stessa località e potenza quasi coincidente. Nessun atto/contractor/supply-chain può essere trasferito tra CUP 9207 e CUP 9439.

### Carlentini
- Gruppo Mammana Foundation/concrete; Hydro foundation engineering/quality + DL; BFP CSP/CSE;
- solo Foundation chiude un core scope;
- industry press non aggiunge nuovi soggetti.

### Alia-Sclafani
- corrente 55 MW / 9 Vestas, erection prevista 21/08/2026–05/11/2026;
- Staffetta 2019 riguarda un precedente potenziamento con due Gamesa G114: **same-site historical config**, non prova del repowering corrente;
- FM Service Group: vacancy portierato/vigilanza nell'area Alia-Sclafani = **C candidate site-services**, progetto non nominato, research-only.

### Fenice
- NVA Fenice 51 WTG / 367,2 MW, advanced permitting / in attesa concerto;
- ATS Engineering A1 design, non contractor;
- REL101/REL102 letti; nessun cronoprogramma distinto emerso nel corpus indicizzato;
- query `Fenice` da sola produce falsi positivi FuturaSun: usare sempre NVA Fenice / MYTERNA / Comuni.

### Toritto
- 108 MW wind + 50 MW BESS, permitting/VIA;
- cronoprogramma 503 giorni **solo relativo**;
- non cercare un anchor reale di cantiere finché non esiste autorizzazione/avvio lavori osservato.

### Sava-Maruggio / Volturino / Lama Cupa
- nessun nuovo lead contractor utile dal pass stampa;
- Lama Cupa: Brulli resta riferita alla SE Casamassima / FLYNIS PV 34, non al parco.

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

### Industry Press Pass 7

Audit **17/17** su pv magazine Italia, Rinnovabili.it, QualEnergia.it, Staffetta, Quotidiano Energia e stampa internazionale di settore, con query anche per BoP/foundation/SSE/erection/logistics/financing/supplier/commissioning.

Nuovo registro:
`docs/wind/data/industry-press-intelligence-2026-09-05.json`

Il drawer carica ora una sezione separata **Industry & market intelligence** tramite `docpass2-intelligence.js`. Financing, lead C, storico e identity collision non entrano nella Contractor View e non influiscono sugli execution scope.

Risultati materiali:
- Tricarico: financial close UniCredit 46,5 mln € + target H2 2027;
- Castelfranco/CER: nuovo collision guard CUP 9207 Fri-El/Miscano vs CUP 9439 CER/Difesa Vecchia;
- Alia-Sclafani: storico 2019 separato + candidate site-services C;
- Nulvi: procurement locale riconfermato ma fornitori ancora anonimi;
- 0 nuovi core execution scope A1/A2.

## Regression guards / verifiche

`scripts/check_wind_radar.py` continua a proteggere coverage e ruoli tecnici.

Nuovo `scripts/check_wind_industry_press.py` verifica che:
- il registro Industry contenga solo seed ammessi;
- non contenga `relations`, `scope_hint`, `execution_scope` o `covered_scope`;
- Tricarico mantenga il financial close A2 come market intelligence;
- Castelfranco mantenga collision guard A1 con fonti regionali;
- Alia site-services resti C;
- nessuna stampa di settore possa gonfiare automaticamente 8/108 o 230,9 MW.

Il runtime git/browser di questa sessione è limitato: non risolve il clone GitHub e Chromium blocca anche file/localhost. Non serve azione utente. I due validator end-to-end e la preview visuale finale restano gate obbligatori prima di proporre merge.

## Prossimo blocco

1. non ripetere Priority 1 / Industry Pass con le stesse query;
2. continuare solo su **nuove fonti site-specific**: subappalti, viabilità, trasporti, accessi, SUAP, pubblicazioni contractor/OEM;
3. quando il runtime lo consente, eseguire `python scripts/check_wind_radar.py` e `python scripts/check_wind_industry_press.py`;
4. preview visuale desktop/mobile finale del branch corrente;
5. solo dopo questi gate, presentare la v0.3 per revisione e decisione di merge.

## Vincoli

Nessun merge e nessuna pubblicazione senza approvazione esplicita.