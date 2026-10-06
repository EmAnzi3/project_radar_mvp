# D8 — estrazione commerciale incrementale

## Cambio di obiettivo richiesto il 6 ottobre 2026

Non è necessario leggere integralmente ogni allegato per qualificare un progetto commercialmente. D8 cerca solo: identità/potenza wind e BESS separati; ubicazione e superficie quando utile; proponente/SPV/developer; aziende con ruolo; iter; tempi dei lavori; contatti professionali espliciti; opere utili commercialmente. Niente trascrizione di firme, particelle, volumi o dettagli ambientali non pertinenti.

La coda D7 conta 825 allegati; solo tre procedure hanno inventari completi. Questi non sono tutti gli allegati di tutti i 96 progetti/identità e 57 gruppi da qualificare. D8 non finge di aver chiuso questo gap di censimento.

## Percorso operativo

`scripts/wind_document_fast.py` legge il ledger esistente **in sola lettura** e conserva una memoria commerciale separata, riutilizzabile localmente:

```text
python scripts/wind_document_fast.py --ledger reports/wind-document-memory/audit.sqlite --output reports/wind-commercial-memory --limit 50
```

La selezione passa su tutto l'inventario: cronoprogrammi/cantierizzazione/atti pertinenti, avvisi e relazioni di sintesi prima; documentazione di supporto dopo. Studi specialistici a priorità differita, non cancellati e non dichiarati letti. Etichette ambigue restano da investigare. Turnazione fra progetti, non 487 documenti Grecale prima di ogni altro progetto. Quattro lavoratori, massimo due acquisizioni simultanee per host iniziale; gli URL di ogni redirect sono comunque validati. Nessuna nuova dipendenza e nessun servizio a pagamento.

Ogni PDF temporaneo è trasformato in brevi passaggi pertinenti, pagina e impronta. Il testo nativo può essere percorso velocemente su tutte le pagine, ma solo passaggi limitati vengono conservati; nessun testo integrale o originale è archiviato. I passaggi vengono ordinati sull'intero documento per non fermarsi all'indice. Le pagine prive di testo, le copertine e i cronoprogrammi richiedono verifica visiva mirata quando utile. Le assenze di segnali non provano l'assenza di informazioni nel PDF.

Un passaggio estratto è un **candidato**, non una verità verificata. Progettista, produttore turbine, proponente ed EPC restano distinti; date relative non diventano calendario; contatti pubblici non diventano automaticamente procurement. Le conferme semantiche devono usare le evidenze già estratte, non richiedere una nuova lettura integrale. Le sette vecchie letture complete rimangono riutilizzate e non sono riclassificate per gonfiare i numeri.

## Incrementalità e guasti

- URL già elaborato e controllo non dovuto: nessuna chiamata esterna o estrazione.
- Modifica dei metadati dell'indice/versione: verifica mirata della sola risorsa.
- Controllo a cadenza: richiesta condizionale quando disponibile; 304 = zero corpo. Un HTTP200 con la stessa impronta non ripete l'estrazione.
- Nuovi byte: nuovo pacchetto, vecchi risultati conservati. Le pagine native con la stessa impronta riusano i passaggi, senza una nuova interpretazione.
- Stesso contenuto su più URL: un solo pacchetto testuale, ma identità/provenienza restano separate; nessun trasferimento automatico di fatti tra progetti.
- Errore di una fonte: conservazione di tutto il lavoro riuscito e delle vecchie evidenze, retry differito; nessun azzeramento dell'arretrato. Errori di accesso non significano assenza di novità.

La memoria viene salvata dopo **ogni documento**, non soltanto a fine lotto. Scrittore unico e lock esplicito. Il PDF temporaneo viene eliminato anche in caso d'errore. File voluminosi, ZIP/P7M e pagine non trattabili restano segnalati: non sono falsi successi. Il canale separato D2/D4 per contenitori resta disponibile, non viene dichiarato collaudato qui su documenti reali.

## Verifica del lavoro

Il resoconto distingue: inventariati; priorità; risorse raggiunte/errori; estrazioni native; pagine con passaggi; verifiche visive/di ruolo aperte; estrazioni evitate; nuovi fatti verificati (zero per il solo scanner). **Non modifica il conteggio dei documenti letti integralmente né quello dei fascicoli completi.**

Il collaudo locale iniziale, sugli originali temporanei D4 già disponibili di sei letture aperte, ha percorso 295 pagine in 18,612 secondi, con sei estrazioni e zero rete. Il riavvio ha riusato sei pacchetti con zero accessi e zero estrazioni. Questo misura l'estrazione nativa locale, non il download, la validazione semantica o una garanzia di prestazione sui portali. Gli originali sono stati rimossi. Ventisette test iniziali coprono cold/warm, 304/200, metadati cambiati, errori, duplicati, ruoli, priorità e salvaguardie; esiti CI da leggere nei run.

Il workflow separato `Wind commercial extraction` usa D7 come fixture di partenza e prova un lotto di 24 risorse e il riavvio offline sullo stesso lotto. Pubblica memoria e diagnostica anche in caso di errori parziali. La fixture Actions a 14 giorni non è una memoria di produzione garantita: la CLI può lavorare con il ledger persistente locale e va mantenuto il backup di entrambe le memorie leggere. Nessun archivio PDF richiesto.

PR9 OPEN/DRAFT; nessun merge. Nessuna modifica al BAT, dashboard, matcher o canonico. Il percorso rapido non è ancora attivato nel BAT quotidiano e non contiene un modello semantico autonomo che certifichi automaticamente gli affidamenti.
