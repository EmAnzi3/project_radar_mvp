# Wind Radar — audit coerenza pipeline E0–E8

Data: 2026-09-05  
Branch: `feat/wind-radar-enrichment-v0.3`

## Esito

La sensazione di salto tra le fasi era fondata, ma aveva **due cause diverse**:

1. la legenda mappa mostrava soltanto le fasi occupate, mentre la pipeline mostrava tutte le fasi E0–E8; con E0, E1, E5 ed E8 a zero, la mappa faceva apparire passaggi diretti tra codici non consecutivi;
2. `Castelfranco in Miscano / CER` era ancora classificato E6 Procurement nonostante la fonte diretta Energy& documenti lavori fisici di revamping in corso. Il record è stato corretto a **E7 Costruzione**.

Non sono emerse altre classificazioni da cambiare sui 16 progetti restanti.

## Modello canonico

La scala è ora unica e definita in `docs/wind/data/meta.json`:

| Fase | Etichetta | Soglia operativa |
|---|---|---|
| E0 | Universo | lead individuato, sviluppo non ancora sufficientemente verificato |
| E1 | Sviluppo | developer/SPV e sviluppo osservabili; iter autorizzativo formale non ancora osservato |
| E2 | Iter autorizzativo | VIA/AU/permitting formale avviato e in istruttoria |
| E3 | Iter autorizzativo avanzato | VIA favorevole o iter nelle fasi finali; autorizzazione complessiva non ancora acquisita |
| E4 | Autorizzato | principali autorizzazioni ottenute; nessun impegno vincolante/procurement osservato |
| E5 | Investimento impegnato | FID, financial close o altro impegno vincolante; procurement principale non ancora osservato |
| E6 | Acquisti / affidamenti | ordini/contratti WTG, BoP, rete o pacchetti principali; lavori fisici non ancora provati |
| E7 | Costruzione | lavori fisici in sito avviati |
| E8 | In esercizio | commissioning/COD completato e impianto operativo |

### Regola di avanzamento

Lo stage rappresenta **la fase più avanzata direttamente osservata**, non una checklist che richiede di avere evidenza separata di ogni fase precedente. Se viene documentato un cantiere E7, il progetto può essere classificato E7 anche se il Radar non ha registrato in precedenza una fonte specifica E5 o E6. Questo non significa che il progetto abbia saltato quelle fasi nella realtà; significa che il Radar fotografa lo stato corrente sulla base dell'evidenza disponibile.

## Audit 17/17

| Progetto | Stage | Motivo sintetico |
|---|---:|---|
| Andretta-Bisaccia | E6 | ordine WTG + piano cantierizzazione; apertura cantiere futura 02/11/2026 |
| Alia-Sclafani | E7 | opere civili/elettriche ed erection documentate in corso |
| Serra Giannina | E7 | RWE conferma avvio costruzione 21/05/2026 |
| Serra Palino | E7 | cantiere attivo e opere Civil/Electrical documentate |
| Venusia | E7 | attività civili concluse e sito predisposto per ingresso turbinista |
| ALAS | E7 | RWE conferma avvio costruzione nel 2026 |
| Greci-Montaguto | E7 | ERG conferma repowering in costruzione |
| Carlentini | E7 | repowering e fondazioni fisicamente in esecuzione |
| Nulvi-Ploaghe | E4 | completamente autorizzato; nessun procurement vincolante osservato |
| Tricarico | E6 | financial close + ordine Vestas; nessun avvio fisico del cantiere provato |
| Tarsia Ovest | E7 | Plenitude conferma avvio costruzione |
| Fenice | E3 | advanced permitting / in attesa concerto |
| Sava-Maruggio | E3 | VIA favorevole, autorizzazione complessiva ancora da seguire |
| Toritto | E2 | istruttoria tecnica MASE in corso |
| Volturino | E2 | permitting tecnico in corso |
| Lama Cupa | E2 | permitting in corso |
| Castelfranco in Miscano / CER | **E7** | Energy& documenta lavori fisici di revamping in corso; corretto da E6 |

## Distribuzione corrente

- E0 Universo: **0**
- E1 Sviluppo: **0**
- E2 Iter autorizzativo: **3**
- E3 Iter autorizzativo avanzato: **2**
- E4 Autorizzato: **1**
- E5 Investimento impegnato: **0**
- E6 Acquisti / affidamenti: **2**
- E7 Costruzione: **9**
- E8 In esercizio: **0**

Totale: **17 progetti**.

L'assenza di E0/E1 dipende anche dalla natura del seed corrente, costruito su progetti già sufficientemente identificati e in gran parte entrati nel permitting. E5 è vuoto perché i progetti con commitment commerciale osservato hanno già evidenza di procurement e passano quindi a E6. E8 è vuoto perché il Radar corrente è focalizzato sulla pipeline pre-operativa/costruzione.

## Correzioni UI

- la legenda mappa mostra ora **tutte le nove fasi**, comprese quelle con conteggio 0;
- pipeline, filtro e badge progetto leggono/mostrano la stessa tassonomia canonica;
- le fasi a zero sono esplicitamente indicate come `nessun progetto`;
- aggiunta nota: lo zero non equivale a fase saltata;
- etichette rese in italiano per leggibilità non tecnica;
- tooltip/aria-label riportano la definizione della soglia.

## Regression guard

Aggiunto `scripts/check_wind_stages.py`, che verifica:
- sequenza completa E0–E8;
- label + descrizione per ogni fase;
- stage validi per tutti i 17 seed;
- distribuzione corrente 0/0/3/2/1/0/2/9/0;
- guard specifici Andretta E6, Tricarico E6, Nulvi E4, Fenice E3, Toritto E2 e Castelfranco/CER E7.

## Browser validation

Preview Chromium/Playwright:
- desktop 1440 px: PASS;
- mobile 390 px: PASS;
- legenda completa 9/9;
- Castelfranco/CER visualizzato `E7 · Costruzione`;
- nessun overflow orizzontale;
- nessun errore console.
