# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **17 progetti / 1.496,9 MW wind**.  
Branch corrente: `feat/wind-radar-enrichment-v0.3`.  
Draft PR: **#2 — Wind Radar v0.3 — contractor hunt, scope coverage e document intelligence**.  
Stato: **non mergiato e non pubblicato**.

## Obiettivo v0.3

Arricchire i 17 progetti esistenti con intelligence operativa senza dedurre contractor non provati.

Core scope:
1. Civil BoP;
2. Electrical BoP;
3. SSE / grid;
4. Fondazioni WTG;
5. Erection;
6. Logistics / heavy transport;
7. Dismantling per repowering.

Regola: solo A1/A2 con `azienda + progetto + ruolo esecutivo` possono chiudere un core scope. B/C, engineering, DL, CSE, LTA, inspection, development e site management restano intelligence.

## Metriche correnti

Invariate dopo il Priority 1 pass 5:

- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope applicabili coperti = **7,4%**;
- il KPI MW non implica BoP completo.

Coperture correnti:
- Serra Palino: Civil + Electrical;
- Venusia: Civil/site preparation;
- Carlentini: Foundation;
- Tarsia Ovest: Civil + Electrical + SSE/grid;
- Castelfranco/CER: SSE/grid.

## Contractor / technical intelligence consolidata

### Andretta-Bisaccia
- record operativo: Edison Rinnovabili **18 WTG / 88,5 MW**;
- Progeco Group / Progeco SE: **B — site/construction management & works supervision**;
- Progeco supervisiona civili, fondazioni, viabilità, cavidotti e civili SSE ma coordina imprese esecutrici/subappaltatori: non è Civil BoP per deduzione;
- GEKO: engineering/cantierizzazione A1;
- apertura cantiere 02/11/2026; civili dal 13/11/2026;
- core scope esecutivi ancora aperti.

Identity guards: pista 13 WTG / 85,8 MW distinta/correlata; distinto progetto MERAL 30 MW / 5 WTG negli stessi Comuni.

### Serra Giannina
- corrente: **42 MW / 6 WTG**;
- costruzione RWE avviata 21/05/2026;
- D'Agostino: **B — construction/site presence**;
- EGM Project: presenza tecnica B;
- nessuna fonte sufficiente per Civil BoP/Foundation/Electrical/SSE A1/A2.

Configurazione 45 MW / 10 WTG = storico autorizzativo.

### ALAS
- corrente: RWE **66 MW / 10 WTG**;
- Hydro Engineering: **A1 — progettista Progetto Esecutivo Opere Civili**, non Civil BoP;
- cantiere/basamenti confermati, impresa esecutrice nominale non trovata;
- distinto `Alas 2` RWE 50,4 MW / 7 WTG negli stessi Comuni: identity guard obbligatoria.

### Greci-Montaguto
- ERG: repowering **43,8 MW**, cantiere marzo 2026 → estate 2027;
- Vestas OEM A2;
- RINA B Electrical & Quality Inspection;
- Civil/Foundation/Dismantling/Logistics/SSE ancora aperti.

### Nulvi-Ploaghe
- ERG **121,5 MW / 27 WTG**, autorizzato e Route-to-Market eligible;
- Hydro Engineering A2 development/engineering, non BoP;
- ERG dichiara procurement locale rilevante ma senza nomi pubblici verificati;
- DUVRI ERG 43,35 MW / 51 Vestas V52 escluso formalmente: riguarda il sito legacy, non il repowering corrente;
- nuova identity guard: distinto **Nulvi-Tergu 99 MW / FRI-EL Anglona**, che coinvolge anche Nulvi/Ploaghe.

### Tricarico
- corrente: Adest **42 MW / 7 × Vestas V162-6MW**;
- Vector Renewables A2 LTA/construction monitoring, non esecutore;
- Vestas `WTG supply + installation`: **B / scope_hint erection**; fonte diretta Vestas non esplicita installation;
- non dedurre `Idoka promoter/owner = Idoka Civil BoP`;
- distinto Dolomiti Windfarm 79,2 MW / 12 WTG = identity guard.

### Venusia
- Idoka A2 Civil BoP / site preparation, fase civile dichiarata conclusa;
- EGM Project A2 engineering/DL;
- **Nordex Group A2 — OEM corrente**;
- **New Developments A2 — co-development / engineering & permitting**;
- Nordex OEM non chiude automaticamente Erection/Logistics;
- Electrical/SSE, Erection e Logistics ancora da provare.

### Serra Palino
- D'Agostino A2 Civil + Electrical/electromechanical;
- **Nordex Group A2 — OEM corrente**;
- SSE/grid, Erection, Logistics, Foundation ancora aperti come scope separati.

### Tarsia Ovest
- RTI Idoka / Michelangelo Mammana / PLC / Delta: A2 Civil + Electrical infrastructure;
- PLC A2 SSE/grid;
- **Michelangelo Mammana B — Civil works individual RTI scope / scope_hint civil** da contenuto Gruppo Mammana del 20/11/2025 ripubblicato; manca l'originale diretto per upgrade A2;
- nome normalizzato su `Michelangelo Mammana` per evitare duplicati Contractor View;
- atti Provincia di Cosenza: Concessioni 85/2025 e 111/2025 per cavi MT; Concessione 139/2026 possibile accesso di cantiere da confermare sul provvedimento integrale.

### Castelfranco in Miscano / CER
- Campana Energie Rinnovabili / IP Gruppo api;
- Vestas OEM A2, 29 MW / 5 WTG;
- PLC A2 SSE/grid;
- **Energy& B — repowering engineering / site involvement**: coinvolgimento diretto sul `Parco Eolico CER`, ma perimetro contrattuale non separato dalle lavorazioni complessive;
- non attribuire a Energy& Dismantling, Foundation, Civil o Erection dalla sola descrizione delle fasi di cantiere;
- identity guard: distinto `Fontana Occhione - Difesa Vecchia` da 24 MW a Ginestra degli Schiavoni e altri progetti che attraversano Castelfranco con opere di connessione. Per il seed usare CER / CUP 9439 / Castelfranco-Montefalcone / 5 WTG.

### Carlentini
- Gruppo Mammana A2 Foundation / concrete works;
- Hydro Engineering A2 foundation engineering/quality + DL;
- BFP A2 CSP/CSE;
- solo Foundation chiude un core scope.

### Fenice
- 51 WTG / 367,2 MW;
- ATS Engineering A1 engineering/design, non contractor;
- REL101/REL102 letti; cronoprogramma di costruzione ancora da trovare.

### Lama Cupa
- Brulli Trasmissione riguarda la SE Casamassima / FLYNIS PV 34;
- non attribuita al parco Lama Cupa.

## Deep-document acquisito

Full text già letto:
- Andretta-Bisaccia — Piano di cantierizzazione;
- Alia-Sclafani — cronoprogramma repowering;
- Serra Giannina — cronoprogramma BoP WTG-by-WTG;
- ALAS — `PEALAS_PE_00016_01_00`;
- Toritto — `C24PU001WP010R00`;
- Fenice — REL101 + REL102;
- Lama Cupa / connessione — `74402A` SE Casamassima.

Andretta-Bisaccia e ALAS sono stati nuovamente recuperati dalla Library in questa sessione: nessun re-upload necessario.

## Priority 1 pass 5

Giro investigativo sulle fonti correnti concluso e registrato in:

`docs/wind/research/2026-09-05-contractor-priority1-pass-5.md`

Esito:
- nuovi soggetti nominali: Nordex Venusia/Serra Palino; New Developments Venusia; Energy& CER;
- primo split individuale RTI Tarsia: Mammana → civil B;
- nuove identity guard Nulvi-Tergu e Castelfranco/Difesa Vecchia;
- falsi positivi esclusi;
- **0 nuovi core scope A1/A2**, quindi metriche invariate.

Il pass non va ripetuto con le stesse query: i prossimi upgrade richiedono nuove pubblicazioni o atti di cantiere più specifici.

## UI / regression guards

`contractor-leads-2026-09-05.json` ora include:
- Andretta-Bisaccia;
- Tricarico;
- Venusia;
- Serra Palino;
- Tarsia Ovest;
- Castelfranco/CER.

`scripts/check_wind_radar.py` verifica che:
- Progeco resti B e non chiuda Andretta;
- Vestas installation resti B e non chiuda Tricarico;
- Nordex/New Developments non gonfino Venusia;
- Mammana Tarsia sia normalizzato e resti B civil hint;
- Energy& CER resti B e Castelfranco chiuda solo SSE/grid;
- Serra Giannina resti senza scope confermati;
- Carlentini chiuda solo Foundation;
- Hydro ALAS, ATS Fenice e Brulli/Lama Cupa non chiudano scope;
- KPI restino **8/108** e **230,9 MW**.

Il runtime di questa sessione non risolve `github.com` via `git`, quindi il checker end-to-end non può essere lanciato dal clone locale. Non serve azione utente: il controllo va rieseguito quando il runtime repository sarà disponibile.

## Prossimo blocco di lavoro

Non più ripetizione del Priority 1 hunt corrente. Ora:

1. preview visuale desktop/mobile con i nuovi lead e controllo Contractor View;
2. verificare che `Michelangelo Mammana` non compaia duplicato;
3. verificare che Energy& sia mostrata come `signal · B`, non scope coperto;
4. verificare Nordex/New Developments come relazioni A2 non esecutive;
5. continuare solo su nuove fonti site-specific: atti viabilità/trasporti/SUAPEE/subappalti e pubblicazioni successive;
6. Fenice: ricerca cronoprogramma nel restante corpus MASE;
7. Toritto: anchor reale di avvio.

## Vincoli

Nessun merge e nessuna pubblicazione finché non viene data approvazione esplicita.