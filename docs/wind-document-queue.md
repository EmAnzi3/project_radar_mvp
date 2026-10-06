# D4 — coda persistente e contenitori documentali

## Stato e perimetro

D4 non modifica i 51 progetti canonici, il BAT quotidiano, il matcher o la dashboard. Estende la SQLite documentale D1–D3 con attività di acquisizione e riferimenti per **tutte le 96 identità e tutti i 57 record di qualificazione**. I 53 non collegati non diventano nuovi progetti. Nessun campo commerciale è promosso automaticamente.

La coda rimane aperta anche quando il daily radar non produce novità. Riavvii e seed non cancellano stati, arretrati o cronologia dei tentativi. I documenti già acquisiti vengono riconosciuti solo se l'originale è presente e il suo hash è corretto. I limiti di lavorazione rinviano attività, non riducono il perimetro. La selezione distribuisce il lotto tra progetti, con priorità a cronoprogrammi, relazioni generali, sintesi e avvisi.

## Riferimenti mancanti e accesso

`missing_reference` significa URL assente nel registro, non documento inesistente. Un originale già fornito dall'utente può essere recuperato dalla Library o da una copia autorizzata; non si inventa una URL pubblica.

`host_review_required` significa che il dominio non è ancora ammesso dalla whitelist del pilota. Non è un test di irraggiungibilità della fonte. Le attività restano tracciate e i domini vanno verificati prima dell'abilitazione.

La navigazione delle schede MASE segue soltanto link di procedura realmente osservati e coerenti con l'ID oggetto della scheda. L'indice completo vale per una procedura. Il budget del pilota limita a un indice per progetto, mantenendo gli altri link osservati come attività ancora aperte. HTML acquisito non significa inventario esaustivo. Errori e limiti sono esposti nel rapporto.

## ZIP e P7M/CMS

Il contenuto viene riconosciuto dai byte, non dall'estensione. Gli ZIP sono aperti senza usare i nomi dei membri come percorsi sul filesystem. Sono rifiutati traversal, percorsi assoluti, symlink, duplicati di percorso ed elementi cifrati. Sono presenti limiti su numero di membri, dimensioni, espansione, profondità e tempo; i file non supportati restano conservati ma non eseguiti.

Per CMS/P7M si usa OpenSSL con verifica crittografica del contenuto e della firma, **senza validazione della catena di fiducia del certificato**. Non è una validazione legale/qualificata della firma, della revoca o della data di firma. Firma non verificabile, busta detached senza contenuto e dipendenza assente restano problemi espliciti: nessun fallback che disabiliti la verifica del contenuto.

Ogni file interno conserva l'impronta dell'involucro, il nome/indice del membro e la catena di estrazione. Le pagine PDF entrano nella coda di revisione visiva e restano da interpretare. L'apertura dei contenitori non produce nuovi EPC, contatti o cronoprogrammi validati. D3 non importa ancora riscontri su membri interni: la loro provenienza è disponibile nel rapporto D4 per l'integrazione successiva.

## Collaudo

Il test dei contenitori usa **fixture sintetiche**, inclusa una busta CMS firmata generata per il test. Non equivale ad aver letto un P7M reale del portale. Il lotto live estende invece l'acquisizione PDF ai riferimenti di Sestino, Mercatello, Andretta–Bisaccia e Poggio Tre Vescovi (RAW-038). I risultati effettivi sono nel rapporto del run; nessun esito live anticipato in questo documento.

Comando separato dal BAT:

```sh
python scripts/wind_document_queue.py --output reports/wind-document-audit --plan config/wind_document_queue_pilot.json --max-assets 6
```

`--seed-only` aggiorna la coda senza accessi esterni. `queue-report.html/json/md` espongono attività e ostacoli; `container_members` e `container_attempts` mantengono provenienza e tentativi. Le sorgenti D1–D3 e i loro riscontri restano invariati.

## Limiti aperti

La coda non certifica la lettura integrale; la revisione semantica e delle figure deve continuare. Gli originali Library non vengono pubblicati automaticamente in GitHub. Cache Actions e artifact a 14 giorni non sono un archivio permanente: occorre conservare SQLite e oggetti insieme in storage con backup per il rollout. **Fascicoli certificati completi: 0.**

Riferimenti tecnici: documentazione Python `zipfile` (decompression pitfalls); documentazione OpenSSL `cms -verify`, distinzione fra verifica del contenuto e `-noverify` della catena certificati.
