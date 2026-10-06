# D3 — riscontri documentali tracciabili

D3 è un modulo separato dal BAT e dal dataset pubblicato. Importa riscontri forniti dopo una lettura esplicita, non trasforma automaticamente estrazioni o menzioni numeriche in fatti.

## Provenienza e persistenza

Ogni riscontro è legato a progetto/record, URL, SHA-256 dell'originale e pagina PDF (1-based, distinta dalla numerazione stampata). Il sistema verifica presenza e integrità del file, versione nel ledger, pagina e breve ancora testuale. Questi sono controlli di tracciabilità, non una dimostrazione automatica che l'interpretazione sia corretta. La lettura visiva ha una nota esplicita; testo estratto non significa revisione visiva.

`documentary_reviews` mantiene record immutabili nella SQLite D1/D2. Lo stesso lotto si importa in modo idempotente e atomico: un riferimento errato impedisce inserimenti parziali. Correzioni semantiche richiedono un nuovo ID; nessuna sovrascrittura silenziosa. Se cambia la versione in testa al documento o manca l'originale, l'export segnala la necessità di riesame. Il confronto riguarda la versione acquisita nel ledger, non una verifica live dell'attualità commerciale.

## Regole di significato

- Potenza nominale/in immissione, massimi progettuali e configurazione definitiva restano distinti. 45 WTG massime e fino a 18,8 MW non autorizzano a sostituire i 698,25 MW in immissione di Grecale con il loro prodotto.
- Un autore, progettista o gruppo societario non è un EPC affidatario. Un ruolo esecutivo richiede evidenza project-specific e una revisione esplicita dell'affidamento. Le capacità EPC di società del gruppo restano lead commerciali.
- Contatti: solo recapiti professionali presenti nel documento, con ruolo e ambito. Il contatto stampa non è procurement; l'indirizzo societario non è la casella personale del rappresentante. Residenza, data di nascita e codici fiscali personali non fanno parte del modello contatti.
- Le durate relative non ricevono date di calendario inventate. Obiettivi dichiarati da una società e stime analitiche sono categorie differenti. Un'eventuale stima richiede intervallo, ipotesi, dipendenze e riscontro di ancoraggio.
- Un'assenza di riscontro riguarda soltanto le pagine esaminate, non l'intero fascicolo. Contraddizioni e limiti restano visibili.

## Esecuzione e collaudo

Dopo il seed e l'acquisizione D2:

```sh
python scripts/wind_document_review.py --output reports/wind-document-audit --reviews config/wind_document_review_pilot.json
```

Output: `review-report.json` e `review-report.html`. Il collaudo usa 24 riscontri su quattro progetti/record: Med Wind Grecale, Gagliole, Apecchio e Serra Giannina. Nessun nuovo progetto viene contato/promosso automaticamente. Fascicoli certificati completi: zero.

I 487 allegati di Grecale sono l'inventario di una specifica procedura, non 487 allegati tutti letti. D2 ha acquisito otto PDF nel lotto di prova; D3 conserva le interpretazioni delle pagine selezionate. Il resto rimane da analizzare. ZIP/P7M, indici degli altri progetti, archivio di produzione con backup e revisione esaustiva delle pagine restano aperti.

La cache Actions e gli artifact (14 giorni) sono strumenti di collaudo, non storage permanente. Conservare SQLite e oggetti insieme. Nessun invio di email o contatto automatico con i referenti.
