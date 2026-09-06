# Wind Project & Contractor Radar

MVP operativo del radar eolico nazionale, isolato in `docs/wind/` e costruito per leggere la pipeline dal punto di vista commerciale e della supply chain esecutiva.

## Portafoglio canonico e Discovery

Il Radar canonico corrente contiene:

- **51 progetti / 11.202,52 MW eolici**;
- **17 seed originari / 1.496,9 MW**;
- **34 progetti promossi dal Discovery v0.4 / 9.705,62 MW**, più **311 MW BESS** mantenuti separati;
- **441 MW BESS** complessivi nel canonico, sempre separati dai MW wind;
- maturità osservabile `E0–E8`;
- evidence grading `A1/A2/B/C/D`;
- contractor esecutivo conteggiato nei KPI solo con ruolo esecutivo `confirmed` e confidenza `A1/A2`.

Il Discovery non è un secondo conteggio del portafoglio: i 34 promossi sono già assorbiti nei 51 canonici. Restano fuori dal canonico **4 candidati current** (1.833,05 MW), oltre a 4 scoping datati e 5 record di guardia/esclusione.

## Dataset

Il manifest canonico è `data/projects.json`, con metadati in `data/meta.json` e progetti suddivisi in chunk. GlobalData è esclusivamente enrichment/lead source e non prevale su atti, developer, contractor o documentazione di cantiere.

Ogni progetto conserva, dove disponibili:

- anagrafica e potenza wind/BESS;
- developer/SPV e identificativi;
- fase E0–E8;
- timing e milestone;
- relazioni progetto ↔ azienda con ruolo, stato, fonte e confidenza;
- contractor gap;
- storico delle configurazioni MW/WTG;
- fonti/evidenze.

## Mappa

La vista principale usa una **choropleth ECharts per provincia**. Ogni progetto viene aggregato una sola volta sulla provincia canonica principale per evitare duplicazioni dei MW; per l’offshore la provincia è un riferimento amministrativo/territoriale e non rappresenta il footprint delle WTG in mare. I MW BESS restano separati. La precedente mappa a marker è mantenuta solo come compatibilità DOM nascosta.

## Contractor view

La vista inversa mostra una sola azienda alla volta. Il selettore:

- è ordinato alfabeticamente con locale italiano;
- viene ricostruito dall'insieme completo delle card disponibili nel filtro corrente;
- ignora e azzera l'eventuale valore ripristinato dal browser nel vecchio campo di ricerca nascosto, evitando il precedente caso in cui compariva soltanto `Vestas`.

## Responsive

`Opportunità prioritarie` usa scroll interno su desktop, ma sotto i 760 px torna nello scroll normale della pagina per evitare scroll-trap su touch.

## Regole di attribuzione

Non assegnare mai un ruolo esecutivo per deduzione. Segnali B/C restano intelligence e non diventano affidamenti. GlobalData non è fonte canonica.

## Stato

MVP in Draft PR per preview/revisione. Nessun merge e nessuna pubblicazione senza approvazione esplicita.
