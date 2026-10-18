# Pilot Crawl4AI — acquisizione mirata MASE

Esperimento **separato** dal dataset canonico di Wind Radar. Non modifica progetti, PR #9, PR #14, stage o contractor. La scansione non è ricorsiva illimitata.

## Obiettivo
Partendo dall'URL pubblico di una scheda/procedura MASE, estrarre:
- link delle pagine correlate e PDF raggiungibili;
- candidate mention di MW, WTG, proponente, progettisti, aziende esecutrici, cronoprogrammi e atti;
- URL esatto, estratto testuale, tipo documento e posizione nella **trascrizione** (non pagina PDF);
- fallimenti e documenti non letti, senza dichiarare copertura inesistente.

## Installazione (ambiente locale separato)
```powershell
py -m venv .venv-crawl4ai
.venv-crawl4ai\Scripts\python -m pip install crawl4ai
.venv-crawl4ai\Scripts\python -m crawl4ai-setup
```

Verificare gli eventuali prerequisiti browser della versione installata nella documentazione ufficiale: https://docs.crawl4ai.com/.

## Esempio di esecuzione
Sostituire l'URL con la scheda pubblica reale del progetto, non con una pagina generica di ricerca:

```powershell
.venv-crawl4ai\Scripts\python experiments/crawl4ai_mase_pilot.py --project "Serra Giannina" --url "https://URL_PUBBLICO_DELLA_SCHEDA_MASE" --max-pages 3 --max-pdf 3
```

Per allegati ospitati da un host diverso usare `--allow-domain dominio.istituzionale.it` solo dopo averne verificato l'appartenenza alla procedura. Il report predefinito è `reports/wind-agent/crawl4ai-mase-pilot.json`. Non pubblicare output contenenti dati personali incidentalmente rilevati.

## Criteri di accettazione
1. Ogni finding contiene URL, citazione e stato `candidate_not_verified`.
2. PDF non letti ed errori sono registrati, non spacciati per documenti analizzati.
3. Nessun finding promuove contractor/EPC/BoP né modifica il canonico.
4. La revisione umana confronta il testo estratto con l'originale (pagina, contesto, identità del progetto).
5. Il benchmark va confrontato con l'inventario/download e la lettura documentale già presenti per Serra, per misurare **copertura addizionale**, non ripetere lavoro.

## Limiti attuali (intenzionali)
Il prototipo cerca *menzioni*, non estrae ancora relazioni e ruoli validati. Lo hash rappresenta il testo estratto, non i byte originali del PDF; non soddisfa la catena di custodia dei PDF già adottata nel progetto. Non esegue OCR affidabile su scansioni né interpreta disegni. Le pagine PDF e i contratti necessitano della pipeline documentale esistente. Non eseguire su sistemi che richiedono autenticazione o su documenti non pubblici.
