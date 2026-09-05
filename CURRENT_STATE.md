# Current State

## Wind Project & Contractor Radar

Baseline pubblicata su `master`: **v0.3**, merge commit `5cb4f00c3d9206e3b08eb224dd8751928ac44022`.

Baseline canonica pubblicata:
- **17 progetti / 1.496,9 MW wind**;
- **230,9 MW** con almeno uno scope esecutivo A1/A2;
- **8 / 108** core scope applicabili coperti = **7,4%**;
- **437,7 MW** in costruzione E7.

Branch corrente: `feat/wind-radar-v0.4-discovery-refresh`.
Draft PR: **#3 — Wind Radar v0.4 — discovery, refresh engine e onshore/offshore**.
Stato: **Draft, non mergiato e non pubblicato**.

## Obiettivo v0.4

Trasformare il Radar da seed curato di 17 progetti a sistema di discovery/refresh riproducibile, mantenendo separati:
1. dataset canonico;
2. candidati discovery;
3. guardie storiche/rejected;
4. change detection;
5. promotion gate.

La v0.4 include **onshore + offshore**. L'offshore non viene escluso a priori.

## Site type

Campo canonico v0.4:
- `onshore`
- `offshore`

I 17 record v0.3 privi del campo esplicito ricevono fallback legacy `onshore`. Ogni nuovo record dovrà dichiarare `site_type`.

UI:
- `Onshore + offshore`
- `Onshore`
- `Offshore`

Il campo `type` resta separato e continua a indicare Greenfield, Repowering, Greenfield + BESS ecc.

## Discovery corpus al 05/09/2026

Tre registri:
- `docs/wind/data/discovery-v04.json`
- `docs/wind/data/discovery-census-v04.json`
- `docs/wind/data/discovery-census-v04b.json`

Totale:
- **47 candidati distinti**;
- **38 current**;
- **4 stale_scoping**;
- **5 rejected / guardie**.

Current:
- **28 onshore**;
- **10 offshore**;
- **11.538,67 MW wind**;
- **661 MW BESS**, separati dai MW wind.

Stale scoping:
- 4 offshore;
- **3.195 MW wind**;
- ultimo avanzamento individuato nel 2022–2023 senza procedura successiva trovata nel pass corrente.

Rejected/guardie:
- 5 candidati;
- **1.195,4 MW wind**;
- non entrano nella pipeline corrente.

Importante: il discovery corpus **non modifica** i KPI canonici v0.3.

## Limite fonte MASE

Alcune rotte di ricerca del portale MASE riportano temporanea disabilitazione per revisione dei requisiti di sicurezza informatica. La v0.4 è quindi un **censimento corrente indicizzato e refreshable**, non una dichiarazione di completezza assoluta di ogni pratica storica MASE.

Il motore è predisposto per estendere il corpus senza cambiare identità o perdere storico quando le rotte tornano pienamente interrogabili.

Audit: `docs/wind/research/2026-09-05-v04-discovery-census-audit.md`.

## Activity class

- `current`: procedura recente/in corso o evidenza ufficiale recente;
- `stale_scoping`: scoping datato senza procedura successiva trovata;
- `rejected`: archiviazione/esito negativo conservato come guardia.

`status != rejected` non viene più usato come sinonimo di progetto attivo.

## Identity reconciliation

Regole: `docs/wind/data/identity-rules-v04.json`.

Priorità:
1. `explicit_identity_group`;
2. `MYTERNA`;
3. operation anchor MASE;
4. fallback `site_type + nome + area` normalizzati.

Gli ID procedura MASE non sono identità progetto.
MW, BESS, WTG, developer/SPV, stage e stato procedura sono campi mutabili e appartengono al change fingerprint, non all'identità.

Identity guards già protette:
- NURAX: più procedure = una opera da 462 MW;
- Atis: scoping + VIA = una opera;
- Poseidon: scoping/PUA/oggetto 2026 = una opera da 1.008 MW;
- Kailia: 900 MW corrente vs 1.170/1.176 MW storico = una identità con config change;
- Le Chiancate: istanza 14717 archiviata + nuova 14943 = una opera da 86,4 MW;
- Nulvi-Sedini WPD distinto da ERG Nulvi-Ploaghe e FRI-EL Nulvi-Tergu;
- SV9 Monte Camulera: classificato onshore nonostante label MASE offshore incoerente;
- rejected non riattivati senza nuova procedura distinta.

## Change / refresh engine

Script: `scripts/wind_discovery_engine.py`.

Funzioni:
- combina i tre registri;
- genera `identity_key` stabile;
- genera `change_fingerprint`;
- distingue current/stale/rejected;
- produce eventi `baseline`, `discovered`, `changed`, `missing_from_refresh`;
- con `--write` aggiorna index derivato e refresh log.

Baseline refresh:
`docs/wind/data/refresh-log-v04.json`.

## Scope profile

File: `docs/wind/data/scope-profiles-v04.json`.

### Onshore
Restano i 7 core scope v0.3:
Civil BoP; Electrical BoP; SSE/grid; fondazioni WTG; erection; logistics/heavy transport; dismantling per repowering.

### Offshore
Profilo distinto:
- foundations / substructure / mooring;
- WTG installation offshore;
- inter-array cables;
- offshore substation quando applicabile;
- export cable + landfall;
- onshore SSE/grid;
- marine logistics / port / heavy lift;
- opere civili onshore di connessione quando applicabili;
- dismantling/decommissioning per repowering.

Gli offshore non entrano nel denominatore 8/108 del canonico onshore.

## UI v0.4

Nuova sezione:
**Discovery · nuovi progetti da verificare**.

Regole:
- separata dai KPI canonici;
- segue filtro Ambito, ricerca e stage hint quando disponibile;
- mostra current/stale/rejected;
- 12 candidati visibili di default, `Mostra tutti` per evitare una pagina eccessivamente lunga;
- non alimenta Contractor View né scope coverage.

Test browser locale con corpus equivalente completo di 47 candidati:
- desktop 1440 px: PASS;
- mobile 390 px: PASS;
- nessun overflow orizzontale;
- default 38 current / 4 stale / 5 rejected;
- Offshore: 10 current / 4 stale / 2 rejected;
- Onshore: 28 current / 0 stale / 3 rejected.

## Validazione

Regression guards:
- `scripts/check_wind_radar.py`
- `scripts/check_wind_industry_press.py`
- `scripts/check_wind_stages.py`
- `scripts/check_wind_v04.py`
- `scripts/wind_discovery_engine.py`

Workflow riproducibile:
`.github/workflows/check_wind_v04.yml`.

Il workflow esegue anche `node --check` su JS core e discovery.

## Promotion gate

Nessun candidato discovery viene promosso automaticamente.

Per entrare nel canonico servono:
1. identity reconciliation;
2. stato corrente verificato;
3. MW/WTG canonici;
4. `site_type` esplicito;
5. stage E0–E8 sostenuto da fonte;
6. scope profile applicabile;
7. collision check con i record esistenti.

## Stato v0.4

Architettura, discovery corpus, identity/change engine, scope profile offshore e UI Discovery implementati. Resta come gate finale l'esito dei regression check riproducibili sul branch e la sincronizzazione conclusiva della Draft PR #3.

Nessun merge e nessuna pubblicazione senza approvazione esplicita.