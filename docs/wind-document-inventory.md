# D2 - inventario completo e accesso documentale verificabile

Il modulo e' additivo e non modifica dashboard, BAT giornaliero, matcher o canonico.

## Perimetro

Censimento D1 invariato: 96 identita' (51 canoniche, 34 Discovery correnti, 4 da riconfermare, 7 escluse); 57 record di qualificazione, di cui 53 non collegati. Le classificazioni sono ereditate, non nuova certificazione commerciale.

D2 estende `audit.sqlite`, mantenendo originali, versioni e tentativi D1. `inventory_runs`, `inventory_pages` e `inventory_members` descrivono lo snapshot di una specifica procedura, non tutte le procedure della stessa opera.

## Inventario

Il parser MASE registra titolo, nome file, sezione, codice, data, scala, dimensione dichiarata e URL di ogni allegato. La navigazione usa il parametro di pagina osservato in collegamenti della stessa procedura e mantiene eventuali filtri. Ogni pagina deve esporre il numero atteso e contatori coerenti; ripetizioni, contatori cambiati, risposte bloccate, pagine mancanti e limiti di lavorazione impediscono `complete_index`.

`complete_index` richiede tutte le pagine dichiarate e il numero esatto di allegati unici dichiarato dal portale. Non significa che gli allegati siano gia' letti. Tutti restano nell'inventario, anche se il pilota elabora solo una selezione prioritaria.

## File voluminosi

Trasferimento a blocchi su disco, limite separato per file, riserva di spazio, limite temporale e controllo della lunghezza. I file parziali non diventano originali acquisiti. Ripresa tramite Range solo con ETag forte o Last-Modified: un 206 deve riferirsi all'offset e al suffisso completo; un 200 riavvia il trasferimento. URL e redirect restano soggetti alla whitelist D1. Nessun aggiramento di autenticazione o CAPTCHA.

Il limite del pilota e' 256 MiB per il documento MASE 1181568: non un limite di accessibilita' del portale. File oltre i limiti sono segnalati e mantenuti in coda. ZIP/P7M richiedono ancora il percorso di apertura/verifica: non si dichiara letto il contenuto dell'involucro.

## Lettura e pagine visuali

Il testo e' estratto da file con provenienza SHA-256 e numero di pagina; le menzioni numeriche sono osservazioni non validate. Tutte le pagine entrano nella coda visuale, comprese quelle ricche di testo. La presenza di immagini/Form e il poco testo sono solo indizi di priorita', non rilevatori esaustivi di tabelle/disegni.

Il pilota rende un numero limitato di pagine per documento. `rendered_pending_review` non e' una revisione umana/semantica. Non si deducono EPC, ruoli, recapiti o cronoprogrammi da una semplice occorrenza o dal superamento dei test. Fascicoli certificati completi: zero fino a successiva verifica esplicita.

## Esecuzione

Dopo il seed D1, eseguire `python scripts/wind_document_inventory.py --output reports/wind-document-audit --plan config/wind_document_inventory_pilot.json`. Lo stesso archivio conserva i progressi; `--skip-inventory` riutilizza l'indice gia' salvato e non lo riconferma come aggiornato. Il warm pass riusa gli originali verificati con hash.

La cache Actions e gli artifact consentono continuita' operativa del collaudo, ma non costituiscono un archivio di produzione garantito: la cache puo' essere eliminata e gli artifact scadono dopo 14 giorni. E' necessario conservare l'intera cartella con SQLite, originali e renders in uno storage persistente con backup prima del rollout completo.

## Risultati

`inventory.csv`: elenco allegati e stato di acquisizione. `inventory-report.json`: tentativi, conteggi e coda visuale. `inventory-report.html`: confronto contatori e galleria di pagine da leggere. `report.json` D1 resta disponibile. Nessuna promozione automatica e nessuna scrittura nei progetti pubblicati.
