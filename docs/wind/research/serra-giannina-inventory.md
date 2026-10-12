# Serra Giannina — inventario MASE

Obiettivo: censire tutte le pagine documentali delle procedure ufficiali MASE note per l'opera 7112, senza affermare di averne già scaricato o letto gli allegati.

Procedure note: 10237 (VIA: 158 allegati da verificare), 18510 (VO: 23), 18807 (VO: 95). Ulteriore VO 15213 non ancora censita. Il programma deve confermare totali e paginazione prima di attribuire lo stato 'indice completo'.

Run: `python scripts/wind_mase_inventory.py --config config/wind_serra_mase.json --output reports/serra-inventory`.

Il successivo passo previsto è l'acquisizione incrementale degli allegati e l'analisi mirata di MW, cronoprogramma, ruoli aziende, recapiti professionali, P.IVA. Nessuna API AI a pagamento o OneDrive. Nessuna scrittura canonica.


## Lotto priorità (8 originali)

Una volta riconciliato l'inventario (276/276 riferimenti in tre procedure), la procedura separata `wind_serra_pdfs.yml` scarica otto PDF selezionati per rilevanza: `1433460`, `1433462`, `1402816`, `1375028`, `1406633`, `1374966`, `1406634`, `1374979`. Sono riferimenti presenti nel CSV di inventario, non URL indovinati.

Il run usa `scripts/harvest_wind_project.py` già presente nel progetto: conserva originali e testo per pagina in un pacchetto di lavoro, registra gli errori, confronta SHA e prova il riavvio offline. Le letture semantiche commerciali e la chiusura del fascicolo restano separate.
