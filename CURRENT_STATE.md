# Current State

## Wind Project & Contractor Radar MVP

Branch di lavoro: `feat/wind-radar-mvp`.

Stato: Draft / preview, non pubblicato e non mergiato.

### Seed operativo

- 17 progetti;
- 1.496,9 MW eolici;
- BESS separato dal wind;
- scala maturità E0–E8;
- evidence grading A1/A2/B/C/D;
- GlobalData solo enrichment/lead source.

### Funzioni presenti

- 7 KPI operativi;
- filtri per regione, maturità, tipo, developer, contractor, MW e finestra temporale;
- mappa progetti;
- pipeline per maturità con tooltip;
- timeline di cantiere con tooltip;
- opportunità prioritarie;
- contractor view inversa;
- scheda progetto con timing, supply chain, gap, storico configurazioni e fonti;
- export CSV.

### Review 04/09/2026

Correzioni applicate dopo la revisione visuale:

- mappa: piano marker e base cartografica allineati sul medesimo canvas/bounds WGS84;
- aggiunti confini regionali derivati dai limiti amministrativi ISTAT tramite `geojson-italy`, proiettati con la stessa trasformazione usata dai marker;
- i marker restano proxy territoriali e non coordinate WTG/layout verificati;
- `Opportunità prioritarie`: scroll interno desktop, nessuno scroll verticale annidato su mobile;
- `Contractor view`: selettore alfabetico compatto; corretto il bug causato dal valore ripristinato dal browser nel vecchio campo nascosto che poteva ridurre l'elenco alla sola `Vestas`;
- seed completo contractor: 11 aziende/nodi distinti.

### Verifiche

- 17 ID progetto univoci;
- totale wind 1.496,9 MW;
- stage ammessi E0–E8;
- riferimenti fonte risolti;
- KPI contractor esecutivo rigoroso = 133,9 MW;
- JavaScript della preview standalone validato con `node --check`;
- elenco contractor derivato dal seed: 11 nominativi distinti, non solo Vestas.

### Pass aperto

Audit puntuale delle coordinate territoriali dei 17 progetti contro corografie/layout ufficiali. Questo pass riguarda la precisione del dato geografico, non il rendering cartografico.

### Vincoli

Nessuna modifica a `master`, nessun merge e nessuna pubblicazione finché non viene data approvazione esplicita.
