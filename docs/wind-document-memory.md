# D5 — leggere una volta, conservare le informazioni

La precisazione dell'utente sostituisce la precedente roadmap di archiviazione permanente degli originali. Il runtime documentale D5 conserva memoria, non un deposito PDF. Il download è temporaneo e necessario per estrazione/rendering; i byte non sono dati da pubblicare o archiviare indefinitamente.

## Stati e confini

- Nuovo documento/versione: lettura e verifica aperte.
- Riscontri parziali: informazioni con prova salvate; NON significa documento interamente letto.
- Versione letta: tutte le pagine verificate testualmente/visivamente e i sei ambiti (identità, MW, localizzazione, aziende, contatti, cronoprogramma) hanno un esito motivato. Non trovato significa solo non trovato in quel documento.
- Documento invariato: riuso della memoria, nessuna nuova estrazione o interpretazione.
- Contenuto cambiato: nuova versione e nuova lettura; le vecchie informazioni restano storicizzate con necessità di riesame.
- Errore 403/404/timeout o limite dimensionale: impossibilità di verificare, NON file immutato, NON perdita della lettura precedente.

Una lettura completata è una dichiarazione esplicita dell'operatore accompagnata dai riscontri, non un risultato dedotto da un HTTP 200 o da un test verde. Completare un documento non certifica tutto il fascicolo o l'attualità commerciale.

## Memoria leggera

Il registro mantiene URL, progetto, impronta SHA-256, metadati disponibili, data della verifica, esiti di lettura, informazioni estratte, pagine, brevi estratti probatori e contraddizioni. I riscontri D3 già verificati vengono migrati una volta in ricevute di provenienza immutabili. Le ricevute sono controlli di integrità/coerenza del registro, non firme qualificate né certificazioni automatiche della verità di un'affermazione.

Il PDF non è più un requisito per riesportare informazioni già validate. Un'affermazione nuova o modificata non può riciclare la ricevuta di un'altra: senza evidenza il sistema rifiuta l'importazione.

Il completamento rilascia l'originale di lavoro, le immagini e il testo integrale della versione, dopo avere salvato gli estratti necessari. Un hash condiviso con utilizzi ancora da leggere non viene rimosso prematuramente. Il percorso dei contenitori resta distinto e non viene chiuso senza la revisione dei membri.

Lo snapshot portabile conserva solo SQLite e rapporti leggeri: **nessun PDF, immagine, ZIP/P7M o testo integrale**. Le pagine ancora da leggere mantengono impronta/stato e passano a `review_pending_source_not_cached`: non sono dichiarate complete e potranno richiedere il file temporaneo quando riprende la lettura. Questa necessità non deve provocare un download a ogni run.

## Verifica modifiche

I controlli sono a cadenza (default sette giorni, separata dal BAT), non a ogni ripetizione del pilota. ETag forte preferito, altrimenti Last-Modified. Il GET condizionale può ricevere 304: nessun corpo trasferito e nessuna lettura. Se il server ignora i validatori o non ne fornisce di utilizzabili, il confronto richiede un trasferimento temporaneo a blocchi e SHA-256: stesso hash implica zero parsing/rendering; hash diverso riapre solo quel documento. Non si promette zero trasferimenti su fonti prive di metadati affidabili.

Semantica di riferimento: RFC 9110, §§13.1.2, 13.1.3 e 15.4.5. Il risultato `unchanged_by_server` è una dichiarazione del server, distinto da `unchanged_by_hash`. I redirect vengono rivalidati; un errore HTML con HTTP 200 non sostituisce il precedente documento leggibile.

## Integrazione

`scripts/wind_document_memory.py` estende D1–D4 tramite adattatori isolati. Le vecchie CLI rimangono strumenti diagnostici storici; il workflow documentale usa ora `wind_document_lifecycle.py`, non il ripetuto download del lotto originale.

Il primo run migra la vecchia memoria D4 se disponibile. I successivi ripristinano soltanto la memoria leggera; cache e artifact del nuovo workflow non contengono gli originali. I vecchi artifact già prodotti non vengono cancellati retroattivamente. La memoria, essendo necessaria per non ripetere il lavoro, richiede backup; non serve invece un backup del corpus PDF.

Il pilota D5 completa la lettura delle due pagine del comunicato RWE Serra Giannina, mantenendo 27 riscontri complessivi. È una chiusura documentale reale e circoscritta: EPC non nominato in quel comunicato non significa EPC non assegnato. I 13 documenti parziali e gli 811 allegati ancora da acquisire della base D4 restano aperti, senza duplicare progetti o certificare fascicoli.

Il workflow testa anche il riavvio con soli metadati e nessun originale. La verifica della fonte può essere degradata senza cancellare la memoria: lo stato viene pubblicato nel rapporto. Canonico, dashboard e BAT quotidiano restano invariati. Nessun merge senza approvazione.

## Comando del modulo (non richiesto all'utente in questa fase)

```
python scripts/wind_document_lifecycle.py --output reports/wind-document-audit --memory reports/wind-document-memory
```

Il rollout massivo e l'integrazione nel BAT verranno eseguiti dopo il collaudo. La lettura di documenti nuovi continua a richiedere revisione semantica/visiva: D5 non introduce un modello che certifica automaticamente tutti gli allegati.
