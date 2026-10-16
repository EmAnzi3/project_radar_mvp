# Serra Giannina — revisione incrementale del 15 ottobre 2026

## Risultato verificabile

| Misura | Primo lotto | Secondo lotto | Totale |
|---|---:|---:|---:|
| Riferimenti MASE acquisiti | 8 | 24 | 32 |
| PDF distinti per SHA-256 | 8 | 22 | 30 |
| PDF distinti con analisi mirata | 8 riusati | 22 nuovi | 30 |
| Fallimenti nel secondo lotto | — | 0 | — |

Gli URL 1395173/1385044 restituiscono lo stesso PDF; anche 1433468/1420190 sono identici. Non sono quattro nuove letture. I 22 PDF nuovi contengono complessivamente 247 pagine: l'analisi è delle pagine selezionate esplicitate nella memoria, non lettura integrale. Gli otto hash già analizzati sono riusati, senza ripetere l'analisi.

Inventario aggiornato: **279 riferimenti unici, quattro indici completi e 30 pagine indice**. La procedura **15213** corrisponde all'indice documentale **19356** (associazione verificata nella riga della pagina ufficiale opera 7112). Il quarto indice contiene tre allegati; nessuno di questi tre è acquisito in questa tranche.

Residuo: **247 riferimenti da acquisire = 244 dei primi tre indici + 3 del quarto**. Il numero dei contenuti distinti del residuo è sconosciuto finché non si scaricano. Fascicolo non completo.

## Nuove informazioni commerciali

| Informazione | Fonte e pagina PDF | Limite probatorio |
|---|---|---|
| Ing. Antonia Rianò, referente RWE per chiarimenti: +39 349 9341765, antonia.raino@rwe.com | [1433468, p.14](https://va.mite.gov.it/File/Documento/1433468#page=14), lettera RWE 11/05/2026 | Referente tecnico della lettera, non buyer attestato. Cognome ed email hanno grafie diverse nella fonte; conservati esattamente. |
| D’Agostino Angelo Antonio Costruzioni Generali S.p.A.: procedura operativa stabilizzazione a calce per viabilità e piazzole, P.IVA 02461490647, +39 0825 973589, dagostinocostruzioni@pec.it | [1433468, p.4](https://va.mite.gov.it/File/Documento/1433468#page=4) | Intestazione di procedura specifica di cantiere; non contratto full Civil BoP, EPC o prova dello stato effettivo delle lavorazioni. |
| STE Energy S.r.l., +39 049 2963900, e SINT S.r.l., +39 0424 568457, info@sint.eu | [1375034, p.1](https://va.mite.gov.it/File/Documento/1375034#page=1) | STE nel cartiglio della sottostazione; SINT esplicitamente progettazione elettromeccanica. Nessun award SSE/grid dedotto. P.IVA non verificate. |
| Sei turbine Nordex N163/6.X da 7 MW, 5 mozzi 113 m e 1 a 108 m | [1375027, p.7](https://va.mite.gov.it/File/Documento/1375027#page=7) | Configurazione nel capitolato, non ordine OEM documentato. |
| Cinque WTG in Genzano e PESG_05 in Banzi | [1375027, p.7](https://va.mite.gov.it/File/Documento/1375027#page=7) | Ubicazione comunale, nessuna coordinata puntuale ricavata o inventata. |
| Mezzi d'opera e noleggi con conducenti contemplati dal capitolato | [1375027, pp.15–16](https://va.mite.gov.it/File/Documento/1375027#page=15) | Ambiti da qualificare commercialmente, non una domanda di noleggio aperta. |
| PEC progettista EGM: egmproject@pec.it | [1375027, p.2](https://va.mite.gov.it/File/Documento/1375027#page=2) | Recapito societario, non procurement. |
| RWE richiama AU 1092 del 30/07/2025 e variazione 17–18/02/2026: 7→6 WTG e 31,5→42 MW | [1433468, p.13](https://va.mite.gov.it/File/Documento/1433468#page=13) | Dichiarazione proponente nella lettera, non lettura dell'atto AU integrale. |

Nessun nuovo termine certo di fine lavori o COD. Restano il Gantt relativo già analizzato e l'obiettivo RWE di produzione dal 2027. Nessun nuovo contratto EPC/BoP/fondazioni/erection/trasporti è attribuito.

## Incongruenza conservata

[Relazione materiali 1375039](https://va.mite.gov.it/File/Documento/1375039#page=4): titolo Serra Giannina, ma testo a p.4 riferito a Serra Palino (FG). Esteyco Energía compare nel documento tecnico (p.2); non trasferire da questo documento geografia, incarichi o affidamenti del diverso progetto.

## Persistenza e riavvio

- `serra-inventory.json`: inventario ufficiale dei quattro indici; `serra-inventory-baseline.json`: confronto con il precedente inventario.
- `serra-acquisition-ledger.json`: tutti i 32 URL acquisiti, hash, dimensioni e run di provenienza. Originali nel pacchetto di acquisizione; non nel dataset pubblico.
- `serra-document-memory.json`: 30 revisioni semantiche per hash, con pagine lette, estratti probatori e limiti. Versioni precedenti conservate.
- `scripts/wind_document_memory.py`: documento nuovo/modificato in coda mirata; stesso hash già analizzato = salta lettura del testo. Estrazione non conta mai come analisi. Un errore di accesso non sostituisce una precedente revisione valida.
- `config/serra_terzo_lotto_config.json`: 24 riferimenti ancora non acquisiti, prioritariamente i tre della procedura 15213. Configurazione pronta; nessuna acquisizione del terzo lotto rivendicata.

Fonti di esecuzione: [secondo lotto](https://github.com/EmAnzi3/project_radar_mvp/actions/runs/38699291090), [inventario quattro indici](https://github.com/EmAnzi3/project_radar_mvp/actions/runs/38699828286). I pacchetti di acquisizione hanno scadenza; l'inventario, gli hash, gli estratti e la memoria persistono nel repository. Anche dopo un nuovo download, lo stesso hash non richiede una nuova analisi semantica.

## Perimetro e controlli

Solo la scheda canonica Serra Giannina è aggiornata. Gli altri 50 progetti sono invariati; totale 51 progetti / 11.202,52 MW. PR #9 esclusa, nessun merge o pubblicazione. Chiave EGM riallineata al Company Network, ragione sociale legale mantenuta nel registro P.IVA. Il censimento ora fallisce se anche un solo indice configurato resta incompleto.

Controlli: suite Python e check pre-pubblicazione PowerShell, validator Wind commerciale/canonico/mappa, rigenerazione idempotente, verifica reale schede desktop 1440×1000 e mobile 390×844 con link fonte/pagina, nessun errore JavaScript o overflow. Nessuna API AI a pagamento e nessun OneDrive.
