# D7 — chiusura di quattro letture parziali (6 ottobre 2026)

## Base verificata prima di questa modifica

HEAD D6 `080003fe36d81d794f5bf312aadf0bf8f73f9107`: document pilot #7 (`37338268849`), Wind checks #410 e live source smoke #228 SUCCESS. Artefatto `11357137966` ispezionato: 35 riscontri, tre versioni completate / 14 pagine, 811 acquisizioni pendenti e 11 letture parziali. Memoria priva di PDF, immagini e testo integrale.

## Lettura effettivamente eseguita

Gli originali sono stati recuperati temporaneamente dal precedente artefatto D4 `11348179963`, verificati contro gli SHA della memoria e letti pagina per pagina, come testo e come immagine. Non sono stati riletti i tre documenti già conclusi. Nessun originale viene inserito nel repository o nella nuova memoria.

| Documento | ID documento | Pagine PDF |
|---|---|---:|
| Poggio Tre Vescovi, avviso VIA | acaa2e6b8915ac07df4227a9 | 3 |
| Sestino, avviso VIA MASE 853190 | 55458f03f76705332d4d5846 | 2 |
| Mercatello, cronoprogramma MASE 1247385 | 77da2bc471782369c725ac2a | 5 |
| Grecale, cronoprogramma MASE 1181414 | d916412a419362d1e5848918 | 12 |

Il batch contiene **20 nuovi riscontri e quattro attestazioni integrali / 22 pagine**. Ogni attestazione include un esito per identità, potenza, localizzazione, aziende, contatti e cronoprogramma. Le due letture parziali del Gantt Grecale già registrate in D3 sono riusate tramite i loro ID immutabili, non duplicate o sostituite.

I totali attesi dopo importazione e riavvio sono **55 riscontri, sette versioni completate / 36 pagine**, 811 acquisizioni pendenti e sette letture parziali. Questi sono target verificabili del batch: prima di dichiararli persistiti occorre leggere l’esito del nuovo pilot e ispezionarne l’artefatto. Un documento completato non certifica un fascicolo: restano zero fascicoli completi e zero nuovi EPC assegnati da questo lotto.

## Riscontri commercialmente rilevanti e limiti

- **Mercatello:** Engie Mercatello proponente e Tiemes progettista. La tavola ha 22 mesi relativi, attività parallele e due righe RTN in capo a Terna con tempi da definire. Non si sommano i gruppi come durata del progetto e non si assegna un COD di calendario. La data di emissione 4 novembre 2024 è distinta dal riquadro firma 17 febbraio 2025; il doppio separatore in copertina è conservato e la normalizzazione corroborata dai footer.
- **Grecale:** 45 turbine e 18,8 MW sono massimi; 698,25 MW è la potenza nominale in immissione. I 190 aerogeneratori dell’elenco generale non sono il lotto Grecale. RINA ha incarico ambientale, non un EPC provato. Il testo distingue 36 mesi per FEED/costruzione/installazione delle OSS da circa sei mesi per trasporto/installazione in sito. Il loro allineamento con il Gantt resta da chiarire; le barre già lette arrivano alla colonna 24, non alla fine dell’asse 36. Nessuna data assoluta dedotta.
- **Poggio Tre Vescovi:** turbine a Badia Tedalda, connessioni anche a Casteldelci, viabilità anche a Verghereto. ENEL è nominata per il nuovo stallo della cabina primaria, non come costruttore del parco. Avviso procedurale, non autorizzazione finale o avanzamento cantiere.
- **Sestino:** turbine a Sestino; gli altri tre comuni riguardano le connessioni. RWE proponente, nessun affidamento esecutivo o programma lavori nell’avviso. Domanda, firma e pubblicazione restano eventi distinti.

I riquadri firma di Tre Vescovi, Sestino e Mercatello contengono nomi e date non restituiti dall’estrazione pypdf. Sono registrati come **metadati trascritti visivamente**, con pagina, SHA e nota di lettura; non si finge una citazione testuale del nome e non si certifica la firma digitale. Non diventano contatti commerciali o incarichi odierni. L’unico nuovo recapito di contatto è la casella/telefono generali RINA pubblicati nel footer, esplicitamente classificati corporate, non procurement Grecale.

## Collaudo e persistenza

Tredici nuovi test di contratto controllano il batch, i riferimenti, le pagine, la separazione dei ruoli, la geografia, i tempi relativi e i metadati visivi. Non sostituiscono la lettura interpretativa. Il pilot valida anche originali/versioni/ancore, importa atomicamente, rilascia le sorgenti e riparte offline dalla sola memoria.

I conteggi CI sono ora ricavati dai manifesti effettivamente caricati e confrontati con gli ID/versioni salvati, anziché restare fissati ai tre documenti D6. Il controllo distingue anche versioni completate storiche da versioni ancora correnti. La traccia del primo passaggio rimane temporanea e alimenta il riepilogo del run; la memoria contiene solo i cinque file leggeri già ammessi.

Nessuna modifica a `docs/wind`, `app/wind_agents`, BAT giornaliero o canonico; nessun merge o pubblicazione. PR #9 resta OPEN/DRAFT. Cache e artifact a 14 giorni restano supporti di collaudo, non un backup durevole garantito. Le sette letture residue, gli 811 allegati non acquisiti, i limiti di accesso e gli inventari ulteriori restano lavoro aperto.
