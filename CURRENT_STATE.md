# Current State

## Fase corrente — D7: quattro letture parziali completate, collaudo da verificare (06/10/2026)

Branch `feat/wind-daily-discovery`, PR #9 OPEN/DRAFT. Nessun merge o pubblicazione autorizzati. Il sistema documentale resta separato dal BAT quotidiano, dal matcher `app/wind_agents` e da dati/layout `docs/wind`.

La richiesta dell'utente è conservare informazioni e memoria della lettura, non archiviare gli originali. I PDF servono soltanto come file temporanei. Le versioni completate sono riprese solo per controlli di modifica a cadenza o per un nuovo contenuto. Un errore della fonte non significa documento invariato, né cancella i risultati precedenti. Un documento letto integralmente non è un fascicolo completo.

### Ultimo checkpoint certificato prima di D7

HEAD D6 `080003fe36d81d794f5bf312aadf0bf8f73f9107`: document audit #7 `37338268849`, Wind checks #410 `37338268825`, live source smoke #228 `37338268977`, tutti SUCCESS. Artefatto `11357137966` recuperato e ispezionato: 35 riscontri, tre versioni completate / 14 pagine, 811 acquisizioni pendenti e 11 letture parziali. Riavvio offline senza acquisizioni; memoria priva di originali, immagini e testo integrale.

### D7 — lavoro interpretativo e modifica in collaudo

Lette integralmente, come testo e immagini, quattro versioni già parziali: avviso Poggio Tre Vescovi (3 pagine), avviso Sestino MASE 853190 (2), cronoprogramma Mercatello 1247385 (5), cronoprogramma Grecale 1181414 (12). Gli originali del precedente artefatto D4 sono stati usati temporaneamente dopo verifica degli SHA. I tre documenti conclusi in D6 non sono stati riletti.

`config/wind_document_followup_batch.json` aggiunge 20 riscontri e quattro attestazioni integrali / 22 pagine. Totali attesi **dopo** importazione e riavvio: 55 riscontri, sette versioni completate / 36 pagine, 811 acquisizioni pendenti e sette letture parziali. Prima di dichiararli persistiti leggere l'esito del nuovo pilot e ispezionare l'artefatto. Zero fascicoli completi e zero nuovi EPC certificati in questo lotto.

Riscontri: Engie proponente e Tiemes progettista a Mercatello; griglia di 22 mesi senza ancoraggio al calendario, opere Terna con tempi indefiniti nel documento. Grecale: 698,25 MW in immissione distinti da massimi 45 turbine/18,8 MW; incarico RINA ambientale; 36 mesi per ciclo completo OSS e circa sei mesi per trasporto/installazione non sono perimetri equivalenti. Allineamento con il Gantt da chiarire, non scadenza certa. Tre Vescovi: turbine, connessioni e accessi distinti; ENEL per il solo stallo AT, non EPC del parco. Sestino: RWE proponente e geografia per funzione; avviso non autorizzazione finale o programma lavori.

Le firme visibili non restituite da pypdf sono censite come metadati documentali trascritti visivamente, non come testo estratto o contatti commerciali. Nessuna verifica legale della firma dichiarata. Un solo nuovo recapito di contatto: casella e telefono generali RINA pubblicati, classificati corporate e non procurement Grecale.

Tredici nuovi test di contratto; i conteggi CI derivano dai manifesti e sono confrontati con gli ID/versioni realmente salvati. Si verifica anche che le versioni completate siano ancora le teste correnti e che il riavvio offline non acquisisca sorgenti. Il resoconto del primo passaggio è distinto da quello del riavvio. Riferimento: `docs/wind-document-followup.md`. Non anticipare l'esito del nuovo CI.

### Perimetro invariato

96 identità: 51 canoniche, 34 Discovery correnti, 4 da riconfermare, 7 escluse. Le 85 classificate correnti non sono altrettante nuove certificazioni commerciali. 57 gruppi di qualificazione: 4 collegati e 53 non collegati, non 53 progetti unici accertati. Audit obbligatorio anche sui 51 canonici. Il seed comprende i registri `discovery-census-v04*.json`; il matcher precedente non è modificato.

### Risultati precedenti preservati

- D1 `2f67b856368ef8a14c1e01b42e60ac244ed8c3a3`: registro, acquisizione e testo per pagina.
- D2 `2c8f2709d296c92ed8315eff6277c1597567dcf1`: Grecale 49/49 pagine e 487/487 allegati; testo dell'originale di 102.737.107 byte/148 pagine. Non 487 allegati già analizzati.
- D3 `d6f4038b82932e613381066402410e8246f74784`: 24 riscontri su quattro progetti/record. Le ricevute D5 conservano le informazioni dopo rilascio del file.
- D4 `cd31b2a04a4f7a1a22dba112b3322c8080319f30`: Sestino 179/179 e Mercatello 151/151 allegati; coda 825; 14 PDF/479 pagine estratte, non letture complete. Andretta 1419737 restituisce 404; 68 riferimenti richiedono whitelist review, 5 senza URL. Due originali utente recuperati dalla Library, non pubblicati. ZIP/CMS su fixture, non su P7M reali. Test 82, pilot4, checks407 e live225 PASS.
- D5 `ee443c18e060bf61b2617ecc8d8a264456a67d6f`: pilot #5 `37326178418`, checks408 e live226 SUCCESS. Memoria leggera senza originali, 27 riscontri, comunicato RWE Serra Giannina completato (2 pagine); controllo HTTP304, zero byte e zero estrazioni, riavvio senza acquisizioni.
- D6: Apecchio (3 pagine, 01/10/2025) e Gagliole (9, 16/12/2024) completati; otto nuovi riscontri, totale 35. Matelica per area spazzata, non fondazioni; contraddizione turbine Nord e benestare Terna richiesto nell'atto mantenuti. Nessun referente EPC dedotto dalle caselle societarie.

Le note D4 preservano la discordanza Andretta p.7/p.17 (2027/2028), i ruoli progettuali dalla copertina Sestino e le dipendenze rete Mercatello. D7 importa i propri riscontri con fonti/versioni; non dichiara importate o risolte tutte le altre note pregresse.

Il lifecycle mantiene staging, backup SQLite, sostituzione atomica del DB, priorità della memoria portabile sui workspace vecchi, lock e cleanup temporaneo anche in errore. La modalità offline vieta qualsiasi acquisizione. Cache/artifact a 14 giorni non sono un database persistente garantito: serve backup della memoria leggera, non del corpus PDF. I vecchi artifact non sono cancellati retroattivamente.

Restano acquisizione/lettura degli arretrati, fonti da ammettere dopo verifica, documenti utente/contenitori, figure e tabelle, attualità commerciale, EPC e referenti. Questo modulo non è un estrattore semantico universale che certifica autonomamente tutti gli allegati.

## Baseline pubblicata e vincoli probatori

Baseline v0.5.0 su master `f2640616540e02448664677427698d808938520f`: 51 progetti / 11.202,52 MW wind, 17 seed / 1.496,9 MW e 34 integrati / 9.705,62 MW. BESS separato.

Solo prova project-specific A1/A2 chiude uno scope execution. Owner/developer/advisor/engineering/DL/supervisione non equivalgono a EPC; storico sito e OEM non provano award corrente/BoP. Lead B/C restano segnali. Contatti solo professionali espliciti con ruolo/data, niente dati personali non pertinenti. Durate relative, obiettivi dichiarati e stime restano distinti.

## Runtime quotidiano e UI preservati

61 player, 34 nodi fonte, 24 adapter, Company Watch e Project Execution queue E4–E7; SQLite operativo separato. BAT: baseline/new/changed/unchanged, report HTML/CSV/JSON e dashboard; `all` forza player, `offline` non usa rete. D7 non è nel BAT. Discovery resta interna, promozione solo dopo verifica identità/attività/configurazione/stage; Grecale/Rospo/Sindia-Macomer/Le Chiancate nel perimetro senza automatismi.

KPI ereditati: 12 E4+ / 689,7 MW, 9 E7 / 437,7 MW, 47 progetti / 11.068,62 MW senza contractor A1/A2. Filtri, mappa provinciale confinata, calendario e Contractor view invariati; precedenti review1440/390 non certificano queste nuove evidenze.

Enrichment pregresso da preservare/riesaminare: Progeco/Andretta supervisione; UniCredit/Tricarico finanziamento e VectorLTA; ERG/Nulvi-Ploaghe configurazione; D'Agostino/Serra Giannina leadB; PROGETTOENERGIA/Greci-Montaguto progettazione; SOCEP storico non trasferito ad Alia-Sclafani; Mammana/Carlentini fondazioni, non fullCivilBoP.

Conservare validator Wind, Windows e live A/B. **Nessuna scrittura canonica, nessun merge o pubblicazione senza approvazione esplicita.**
