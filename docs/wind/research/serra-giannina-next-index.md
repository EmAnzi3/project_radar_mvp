# Serra Giannina — controllo documentale MASE (15 ottobre 2026)

**Fonte ufficiale:** https://va.mite.gov.it/it-IT/Oggetti/Info/7112

Il portale MASE elenca la quarta procedura di verifica di ottemperanza **15213**
(istanza WEB-VOA - VOAVO00000291), presentata il 17 settembre 2026, istruttoria
tecnica avviata il 24 settembre 2026 e attualmente indicata come
**Istruttoria tecnica CTVIA**. Il contatto del responsabile del procedimento
indicato nella pagina è **Alessandra Dosa, va-5@mase.gov.it**:
recapito amministrativo del MASE, **non** contatto procurement di RWE.

Lo stato precedente copre 276 URL in tre indici (10237, 18510, 18807).
Gli **otto PDF** già verificati il 12 ottobre sono tracciati con SHA-256
in config/wind_serra_review.json, non devono essere dichiarati
nuove acquisizioni. La procedura 15213 NON è inclusa nel conteggio 276
e il suo URL di indice NON è ancora verificato.

Il nuovo script scripts/wind_serra_batch.py utilizza l'inventario
esistente e harvest_wind_project.py per l'acquisizione di batch limitati,
preselezionando documenti aggiornati, cronoprogrammi, affidamenti, computi
metrici e documenti esecutivi. Il report contiene SHA, pagine e
**passaggi candidati da verificare**, non informazioni commerciali accertate.

## Limiti
- La prova CI elabora massimo 3 nuovi documenti con fonti pubbliche.
- Il workflow non modifica canonico, sito, né la Draft PR #9.
- La memoria del batch è locale e conservata come artifact CI, non ancora
  persiste tra workflow differenti: il passo successivo sarà il meccanismo
  di persistenza approvato e verificato.
- Impossibile dichiarare completato il fascicolo: restano gli allegati non
  acquisiti, l'indice 15213 e gli incarichi EPC/BoP senza prova diretta.
- Nessuna API AI a pagamento e nessun OneDrive.
