# D6 — letture concluse e memoria leggera protetta

## Politica richiesta dall'utente

I PDF sono materiale temporaneo di lettura, non un archivio da conservare. Restano informazioni, brevi estratti pertinenti, provenienza, versione SHA-256, esiti per campo/pagina, incongruenze e data del controllo. Una versione completata non viene riscaricata o reinterpretata a ogni run. Si controllano le modifiche a cadenza; 304 non trasferisce il corpo, un 200 identico per hash non ripete l'estrazione, contenuto cambiato riapre soltanto quel documento. Un errore di rete non cancella quanto già acquisito e non prova immutabilità della fonte.

Questa logica D5 è già stata verificata nel run 37326178418: comunicato RWE, HTTP304, zero byte e zero estrazioni. D6 la applica anche a due documenti completati dopo lettura testuale e visiva di tutte le pagine.

## Lotto letto integralmente

- Apecchio, `Avviso_Pubb_2.pdf`: **3 pagine**, SHA ec7e7029616eaff36d2a0b395553887554d749b9c0d62676534670b249dae5f9. Atto datato 01/10/2025, 29.400 kW nominali, VSE proponente e PEC societaria. Distinti impianto, connessioni, destinatari amministrativi e termine istruttorio. Nessun cronoprogramma costruzione o affidamento EPC presente nell'intera comunicazione.
- Gagliole, `WEGagliole_Modulo_L1_Avviso.pdf`: **9 pagine**, SHA 2f5c95162395ad8277986a4a7f5338808a8999e39971ab3cff04008708f28511. Data 16/12/2024 a p.9; lette integralmente le tabelle catastali pp.2–7. Matelica compare per l'area spazzata, non come sito di fondazione. Le opere connesse sono distinte dalle turbine. Posizione SE subordinata a benestare Terna nel testo del 2024, non situazione attuale accertata. Restano la contraddizione quattro turbine Nord/cinque sigle e l'assenza di un cronoprogramma lavori. Rappresentante e recapiti societari non sono un referente EPC.

Otto nuovi riscontri si aggiungono ai 27 precedenti. Dopo importazione e collaudo attesi: 35 riscontri, 3 versioni interamente lette (RWE + Apecchio + Gagliole), 14 pagine complessive di queste tre versioni. Questo non certifica tre fascicoli, né elimina le informazioni mancanti che vanno ricercate negli altri allegati. Nessun EPC assegnato dedotto; nessuna promozione canonica.

## Resistenza agli errori

Il database portabile è l'unica base autorevole. Un vecchio workspace non può sovrascrivere uno snapshot più recente. SQLite backup conserva anche transazioni già commesse in WAL. Ogni run usa uno spazio temporaneo e lo elimina in uscita, senza copiarne PDF o immagini nella memoria.

Lo snapshot viene costruito e validato in staging prima di sostituire atomicamente il DB precedente. Nessuna cancellazione preventiva della memoria buona. HTML/JSON sono viste rigenerabili. Un lock impedisce scritture concorrenti: un lock abbandonato richiede controllo esplicito, non viene ignorato. Il DB e le code persistono anche se un nuovo documento non si riesce a scaricare: il run fallisce esplicitamente senza pubblicare lo staging incompleto.

La modalità `--no-remote` proibisce anche l'acquisizione di un originale mancante, non soltanto i controlli periodici. Il riavvio di collaudo non può quindi nascondere download in un percorso dichiarato offline.

## Test e limiti

15 nuovi test locali su isolamento percorsi, lock, WAL, staging, errori disco e rifiuto di originali nell'output; validazione locale delle otto nuove evidenze contro gli originali/versioni/pagine. Il workflow verifica l'intera suite Windows/Linux e il riavvio senza originali. Gli esiti del nuovo commit vanno letti dai run, non anticipati.

Restano il lavoro documentale non completato, la ricerca effettiva degli EPC e dei referenti, l'attualità commerciale, ulteriori inventari e i limiti d'accesso già tracciati. La memoria va salvata con backup; la cache/retention14giorni di Actions non è un database di produzione garantito. Nessuna modifica al BAT, alla dashboard, al matcher o ai 51 canonici. PR9 sempre Draft e non mergiata.
