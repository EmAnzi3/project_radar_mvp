# Current State

## Fase corrente — D6: leggere una volta, conservare risultati e versione (05/10/2026)

Branch `feat/wind-daily-discovery`, PR #9 OPEN/DRAFT. Nessun merge o pubblicazione autorizzati. Il sistema documentale resta separato dal BAT quotidiano, dal matcher `app/wind_agents` e da dati/layout `docs/wind`.

La richiesta dell'utente è conservare informazioni e memoria della lettura, non archiviare gli originali. I PDF servono soltanto come file temporanei. Le versioni completate sono riprese solo per controlli di modifica a cadenza o per un nuovo contenuto. Un errore della fonte non significa documento invariato, né cancella i risultati precedenti. Un documento letto integralmente non è un fascicolo completo.

### Perimetro invariato

96 identità: 51 canoniche, 34 Discovery correnti, 4 da riconfermare, 7 escluse. Le 85 classificate correnti non sono altrettante nuove certificazioni commerciali. 57 gruppi di qualificazione: 4 collegati e 53 non collegati, non 53 progetti unici accertati. Audit obbligatorio anche sui 51 canonici. Il seed documentale comprende i registri `discovery-census-v04*.json`; il matcher precedente non è modificato.

### Checkpoint già verificato D5

HEAD D5 `ee443c18e060bf61b2617ecc8d8a264456a67d6f`: document audit #5 `37326178418`, Wind checks #408 e live source smoke #226 SUCCESS. Artefatto `11352147856`: memoria di circa 2,2MB senza originali o testo integrale, 27 riscontri, 1 versione completamente letta (comunicato RWE Serra Giannina di 2 pagine). Il controllo HTTP reale ha restituito304, zero byte trasferiti, zero estrazioni. Il riavvio senza originali ha prodotto zero acquisizioni. I 13 documenti parziali e gli 811 ancora da acquisire sono rimasti in coda.

### Estensione D6

Apecchio: lette tutte le 3 pagine dell'atto del 01/10/2025. Gagliole: lette tutte le 9 pagine dell'avviso del 16/12/2024, incluse tabelle catastali e pagina finale. Otto riscontri aggiunti con URL/SHA/pagina; totali attesi dopo collaudo: 35 riscontri e 3 versioni completate (14 pagine), nessun fascicolo completo e nessun nuovo affidamento EPC. Non anticipare gli esiti CI del nuovo commit.

La lettura Gagliole distingue comuni delle turbine, connessioni e area spazzata a Matelica; conserva la contraddizione sulle turbine Nord e il benestare Terna richiesto nel documento, senza dichiararlo tuttora mancante. I recapiti sono caselle societarie esplicite, non email dedotte o contatti EPC. I termini istruttori non diventano cronoprogrammi lavori.

`scripts/wind_document_lifecycle.py` ora usa staging, backup SQLite e sostituzione atomica del DB. La memoria portabile prevale su workspace vecchi. Lock contro scritture concorrenti, percorsi separati, nessuna cancellazione preventiva dell'ultima memoria buona. Lo spazio di lettura è temporaneo e viene rimosso anche a fine run fallito. La modalità offline vieta qualsiasi acquisizione mancante.

15 nuovi test locali sui guard di persistenza/lock/WAL, oltre alla validazione delle nuove evidenze contro le versioni reali. Il workflow verifica suite Linux/Windows, preflight, importazione e riavvio offline. Rif. `docs/wind-document-read-once.md`; file `config/wind_document_read_once_{reviews,completed}.json`.

### Risultati precedenti preservati

- D1 `2f67b856368ef8a14c1e01b42e60ac244ed8c3a3`: registro, acquisizione e testo per pagina.
- D2 `2c8f2709d296c92ed8315eff6277c1597567dcf1`: Grecale49/49 pagine e487/487 allegati; letto come testo anche l'originale di102.737.107 byte/148 pagine. Non487 allegati già analizzati.
- D3 `d6f4038b82932e613381066402410e8246f74784`: 24 riscontri su quattro progetti/record. Ricevute D5 preservano le informazioni dopo rilascio del file.
- D4 `cd31b2a04a4f7a1a22dba112b3322c8080319f30`: Sestino179/179 e Mercatello151/151 allegati; coda825; 14 PDF/479 pagine estratte, non letture complete. Metadato Andretta1419737 restituisce404; 68 riferimenti richiedono whitelist review, 5 senzaURL. Due originali utente recuperati dalla Library e non pubblicati. ZIP/CMS provati su fixture, non su P7M reali. Test82, pilot4, checks407 e live225 PASS.

Le note D4 conservano incongruenza date Andretta (p.7 vs Gantt17: 2027/2028), ruoli progettuali dalla copertina scansita Sestino e dipendenze rete Mercatello. Non sono promosse automaticamente.

Resta acquisizione e lettura degli arretrati, fonti da ammettere dopo verifica, documenti utente/contenitori, figure/tabelle, attualità commerciale, EPC e referenti. D6 non implementa un estrattore semantico universale né certifica autonomamente tutti gli allegati. Cache/artifact14giorni non sono un database persistente garantito: serve backup della memoria leggera, non del corpus PDF. I vecchi artifact non sono cancellati retroattivamente.

## Baseline pubblicata e vincoli probatori

Baseline v0.5.0 su master `f2640616540e02448664677427698d808938520f`: 51 progetti/11.202,52MW wind, 17 seed/1.496,9MW e34 integrati/9.705,62MW. BESS separato.

Solo prova project-specific A1/A2 chiude uno scope execution. Owner/developer/advisor/engineering/DL/supervisione non equivalgono a EPC; storico sito e OEM non provano award corrente/BoP. Lead B/C restano segnali. Contatti solo professionali espliciti con ruolo/data, niente dati personali non pertinenti. Durate relative, obiettivi dichiarati e stime restano distinti.

## Runtime quotidiano e UI preservati

61 player, 34 nodi fonte, 24 adapter, Company Watch e Project Execution queue E4–E7; SQLite operativo separato. BAT: baseline/new/changed/unchanged, report HTML/CSV/JSON e dashboard; `all` forza player, `offline` non usa rete. D6 non è nel BAT. Discovery resta interna, promozione soltanto dopo verifica di identità/attività/configurazione/stage; Grecale/Rospo/Sindia-Macomer/LeChiancate nel perimetro senza automatismi.

KPI ereditati: 12 E4+/689,7MW, 9 E7/437,7MW, 47 progetti/11.068,62MW senza contractor A1/A2. Filtri, mappa provinciale confinata, calendario e Contractor view invariati; precedenti review1440/390 non certificano queste nuove evidenze.

Enrichment pregresso da preservare/riesaminare: Progeco/Andretta supervisione; UniCredit/Tricarico finanziamento e VectorLTA; ERG/Nulvi-Ploaghe configurazione; D'Agostino/SerraGiannina leadB; PROGETTOENERGIA/Greci-Montaguto progettazione; SOCEP storico non trasferito ad Alia-Sclafani; Mammana/Carlentini fondazioni, non fullCivilBoP.

Conservare validator Wind, Windows e live A/B. **Nessuna scrittura canonica, nessun merge o pubblicazione senza approvazione esplicita.**
