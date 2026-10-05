# Current State

## Fase corrente — D5: memoria delle letture, non archivio PDF (05/10/2026)

Branch `feat/wind-daily-discovery`, PR #9 OPEN/DRAFT, nessun merge autorizzato. Il modulo documentale resta separato dal BAT quotidiano, da `app/wind_agents` e dai dati/dashboard in `docs/wind`.

La precisazione dell'utente modifica la politica precedente: i documenti sono file temporanei di lavoro. Una volta completata la lettura di una versione, si conservano informazioni, provenienza, impronta SHA-256, pagine/estratti utili, esiti e contraddizioni. Non si archivia permanentemente il PDF o il suo testo integrale. Il documento si rilegge quando cambia il contenuto, non a ogni run.

### Perimetro invariato

- 96 identità registrate: 51 canoniche, 34 Discovery correnti, 4 da riconfermare, 7 escluse.
- 85 classificate correnti nei registri: non sono 85 nuove certificazioni commerciali.
- 57 gruppi di qualificazione, 4 già collegati e 53 non collegati; i 53 non sono progetti unici accertati.
- Audit anche sui 51 canonici. I dati mancanti attivano approfondimento.
- Il seed documentale riunisce anche `discovery-census-v04*.json`; il matcher quotidiano non viene modificato.

### D5 implementata, validazione locale eseguita

- `scripts/wind_document_memory.py`: ricevute di evidenza, completamento esplicito per versione, rilascio file di lavoro e verifica condizionale delle modifiche.
- `scripts/wind_document_lifecycle.py`: migrazione una tantum e riavvio da memoria senza corpus originale.
- Primo documento completamente letto: comunicato RWE Serra Giannina, 2 pagine, versione SHA `9eb86b887b38da5012219a6ca62cd630ecf3b794523c310fa9f6d1c4b50acaed`. Non è il fascicolo completo del progetto.
- 27 riscontri conservati (24 D3 + 3 sul comunicato RWE) con brevi estratti e riferimenti; nessun contatto o ruolo EPC inventato.
- Snapshot locale di circa 2,2 MB, senza PDF, immagini, contenitori o testo integrale; i 13 documenti parziali e gli 811 ancora da acquisire restano in coda.
- 114 test locali superati: 82 precedenti invariati + 32 D5. Riavvio reale dello snapshot locale senza originali: zero acquisizioni, zero letture ripetute, nessun duplicato.
- I test HTTP sintetici verificano 304, 200 a hash invariato, contenuto cambiato, errori, redirect e budget. Il risultato della verifica HTTP live va letto nel run del commit, non dedotto dai test.

D5 distingue `unchanged_by_server` (304), `unchanged_by_hash`, `content_changed_review_required` e `remote_check_failed`. Il controllo è a cadenza, non a ogni run. In assenza di metadati affidabili può servire trasferire temporaneamente il file per confrontarne l'impronta, senza rieseguirne l'analisi se invariato. Un errore non cancella le informazioni precedenti.

Il workflow usa la memoria leggera nei nuovi cache/artifact. I vecchi artifact non vengono cancellati retroattivamente. Serve backup della memoria delle informazioni e delle code, non del corpus PDF. Le vecchie CLI D1–D4 restano strumenti diagnostici storici; il percorso corrente è il lifecycle D5. La coda di documenti non completati non viene spacciata per una serie di letture concluse.

**Fascicoli completi: 0. Nuovi affidamenti EPC certificati in D5: 0. Scritture canoniche: 0.** Il presente file non anticipa l'esito CI del proprio commit.

## Risultati precedenti preservati

D1 `2f67b856368ef8a14c1e01b42e60ac244ed8c3a3`: registro separato, acquisizione e testo per pagina.

D2 `2c8f2709d296c92ed8315eff6277c1597567dcf1`: Grecale, 49/49 pagine di indice e 487/487 allegati; superato il limite interno sul documento da 102.737.107 byte/148 pagine. Inventario completo non significa allegati letti.

D3 `d6f4038b82932e613381066402410e8246f74784`: 24 riscontri su Grecale, Gagliole, Apecchio, Serra Giannina; fonti/page anchor, ruoli e cronoprogrammi distinti. Le ricevute D5 permettono di conservare i riscontri già validati anche dopo il rilascio intenzionale dei file.

D4 `cd31b2a04a4f7a1a22dba112b3322c8080319f30`: inventari Sestino 179/179 e Mercatello 151/151; coda825, 14 PDF acquisiti/479 pagine estratte. Il metadato Andretta 1419737 ha restituito404; 68 riferimenti richiedono revisione della whitelist, 5 non hanno URL. Due file forniti dall'utente sono stati recuperati dalla Library senza pubblicarli in GitHub. ZIP/CMS testati su fixture, nessun P7M reale dichiarato letto. Test82, pilot4, checks407 e live225 passati.

Le note operative D4 segnalano la contraddizione delle opere civili Andretta tra pagina7 e Gantt17 (2027/2028), i ruoli progettuali sulla copertina scansita Sestino e le dipendenze di rete Mercatello. Non sono state promosse automaticamente.

Resta da completare la lettura degli arretrati, l'ampliamento controllato delle fonti, l'integrazione delle evidenze da documenti utente/contenitori, la revisione delle figure e la verifica di attualità commerciale/affidamenti. D5 non introduce un estrattore semantico che certifichi autonomamente tutti gli allegati.

Riferimenti: `docs/wind-document-audit.md`, `docs/wind-document-inventory.md`, `docs/wind-document-review.md`, `docs/wind-document-queue.md`, `docs/wind-document-memory.md`.

## Baseline pubblicata e regole probatorie

Baseline pubblicata v0.5.0 su master: `f2640616540e02448664677427698d808938520f`.

- 51 progetti / 11.202,52 MW wind.
- 17 seed / 1.496,9 MW; 34 integrati / 9.705,62 MW.
- BESS sempre separato.

Solo prova project-specific A1/A2 chiude uno scope esecutivo. Owner/developer/advisor/engineering/DL/supervision non equivalgono a execution. Storico sullo stesso sito non implica award corrente; OEM non implica BoP. Lead B/C restano segnali. Contatti solo professionali espliciti, con ruolo e data, niente recapiti dedotti o dati personali non pertinenti. Durate relative, obiettivi dichiarati e stime restano distinte.

## Runtime quotidiano (invariato)

61 player commerciali, 34 nodi fonte, 24 adapter istituzionali; Company Watch e Project Execution queue sugli E4–E7; SQLite operativo/raw/history separato dal canonico. `aggiorna_wind_radar.bat` interroga gli adapter, i player dovuti per cadenza, persiste baseline/new/changed/unchanged, genera `daily-discovery-latest.html/csv/json`, aggiorna status e apre dashboard/report. La baseline e gli snapshot tecnici di degrado non sono nuove opportunità. `all` forza i player; `offline` non usa rete. D5 non è ancora incorporata nel BAT.

Discovery resta interna; promozione solo con identità, attività, configurazione e stage verificati. Grecale, Rospo, Sindia-Macomer e Le Chiancate restano nel perimetro di revisione senza automatismi.

## Dashboard e intelligence pregresse (preservate)

KPI ereditati, non nuova verifica di cantiere: 51 progetti, 12 E4+/689,7 MW, 9 E7/437,7 MW, 47 progetti/11.068,62 MW senza contractor esecutivo A1/A2 attribuito. Restano filtri, mappa provinciale ECharts confinata, maturità E0–E8, calendario, opportunità e Contractor view. Nessun cambio grafico in D5. Le precedenti review desktop1440/mobile390 appartengono alla fase UI, non certificano le nuove evidenze.

Le tranche di enrichment restano additive: Progeco/Andretta supervisione, non execution; UniCredit/Tricarico financial close e Vector LTA, non BoP; configurazione ERG Nulvi-Ploaghe, procurement aperto; D'Agostino/Serra Giannina lead B; PROGETTO ENERGIA/Greci-Montaguto progettazione; storico SOCEP non trasferito al repowering Alia-Sclafani; Mammana/Carlentini fondazioni, non full Civil BoP.

Conservare validator Wind, Windows e live A/B. **Nessun merge o pubblicazione senza approvazione esplicita.**
