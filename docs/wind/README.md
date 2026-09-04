# Wind Project & Contractor Radar

MVP operativo del radar eolico nazionale, isolato in `docs/wind/` e costruito per leggere la pipeline dal punto di vista commerciale e della supply chain esecutiva.

## Seed e KPI

- 17 progetti seed verificati;
- 1.496,9 MW eolici monitorati;
- BESS sempre separato dai MW wind;
- maturità osservabile `E0–E8`;
- evidence grading `A1/A2/B/C/D`;
- contractor esecutivo conteggiato nei KPI solo con ruolo esecutivo `confirmed` e confidenza `A1/A2`.

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

I marker usano coordinate territoriali indicative del progetto e **non** rappresentano le coordinate delle singole WTG. La promozione a layout verificato richiede una corografia o un elaborato ufficiale.

La basemap regionale viene disegnata sullo stesso piano WGS84 e sugli stessi bounds (`6.3–19 E`, `35.2–47.3 N`) usati dai marker. I confini regionali provengono dal dataset `geojson-italy`, derivato dai limiti amministrativi ISTAT e pubblicato in WGS84/CC-BY. Se la risorsa remota non è disponibile resta visibile la basemap locale di fallback.

## Contractor view

La vista inversa mostra una sola azienda alla volta. Il selettore:

- è ordinato alfabeticamente con locale italiano;
- viene ricostruito dall'insieme completo delle card disponibili nel filtro corrente;
- ignora e azzera l'eventuale valore ripristinato dal browser nel vecchio campo di ricerca nascosto, evitando il precedente caso in cui compariva soltanto `Vestas`.

Nel seed completo risultano 11 aziende/nodi distinti.

## Responsive

`Opportunità prioritarie` usa scroll interno su desktop, ma sotto i 760 px torna nello scroll normale della pagina per evitare scroll-trap su touch.

## Regole di attribuzione

Non assegnare mai un ruolo esecutivo per deduzione. Segnali B/C restano intelligence e non diventano affidamenti. GlobalData non è fonte canonica.

## Stato

MVP in Draft PR per preview/revisione. Nessun merge e nessuna pubblicazione senza approvazione esplicita.
