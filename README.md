# project_radar_mvp

Radar commerciale per progetti e infrastrutture in Italia.

## Wind Project & Contractor Radar

Baseline pubblicata: **v0.5.0**.

Il Wind Radar integra:
- progetti eolici onshore e offshore da fonti pubbliche;
- normalizzazione di identità, MW, WTG, stage E0–E8 e timing;
- separazione rigorosa tra MW wind e BESS;
- supply-chain intelligence con ruolo, fonte e livello di confidenza;
- scope esecutivi chiusi solo con evidenza A1/A2 esplicita;
- Discovery separato dal dataset canonico;
- dashboard HTML con KPI, filtri, mappa, timeline, opportunità e Contractor view.

Baseline canonica v0.5:
- **51 progetti**;
- **11.202,52 MW wind**;
- 34 progetti promossi dal discovery v0.4;
- 4 candidati ancora blocked nel discovery.

Dashboard Wind:
- `docs/wind/index.html`

Stato operativo dettagliato:
- `CURRENT_STATE.md`

### Sviluppo v0.6

La v0.6 aggiunge un motore agent-style derivato da `pv_agent_mvp`, mantenendo raw finding, storico variazioni, planner/cadenze, reconciliation ed evidence gate separati dal canonico.

Stato corrente della Draft PR #5:
- **58 player commerciali** nel Company Network;
- **31 nodi istituzionali** nel Source Network;
- **21 adapter istituzionali eseguibili**: MASE VIA, MASE Provvedimenti, Terna Econnextion, Lazio, Toscana GeA, ATOS Toscana, Sardegna SIRA, Sicilia SI-VVI, Sistema Puglia, Campania, Calabria, Basilicata, Emilia-Romagna, Lombardia, Piemonte, Umbria, Veneto, Abruzzo, Liguria, Marche e Molise;
- Company Watch diretto sulle `watch_urls` con cadenze 7/14/30 giorni;
- stato runtime persistente per `new / changed / unchanged`, cursori sorgente e ultimo successo/errore;
- reconciliation conservativa dei finding verso canonico/Discovery **senza promozione automatica**;
- digest review-only delle sole variazioni commercialmente utili;
- **Project Execution investigation queue** per i canonici E4–E7 con open scope, urgency score e playbook di contractor hunt per singolo scope;
- workflow periodico predisposto con trigger giornaliero e selezione `--due`, senza commit automatici né modifiche automatiche al canonico.

La nuova tranche commerciale aggiunge player execution-oriented come Blu Costruzioni, EGM Project, Barone Costruzione, Gruppo Novello, La Molisana Trasporti, Pizzulo Costruzioni, SIMIC e F&C Wind Service. I riferimenti storici, la prossimità geografica o la presenza tecnica in sito restano **lead di rete**, non award: ad esempio non si deduce Blu sul repowering Carlentini corrente, Pizzulo su Andretta-Bisaccia o EGM come contractor esecutivo di Serra Giannina.

Gli adapter Abruzzo e Molise includono un fallback trasparente `source_channel_snapshot` quando il portale non espone righe progetto server-side: in quel caso il canale resta monitorabile ma non viene falsamente dichiarata acquisizione di dati progetto. Liguria e Marche lavorano sui registri pubblici regionali correnti.

Terna Econnextion resta intelligence aggregata di mercato e non genera progetti. Una VIA positiva MASE non viene interpretata come autorizzazione complessiva, procurement o costruzione. I finding company-direct restano network intelligence finché non esiste evidenza project-specific sul ruolo esecutivo.

Il workflow PR valida architettura e regressioni; la disponibilità live dei portali viene verificata solo da un'esecuzione effettiva degli adapter. Il workflow schedulato diventerà attivo solo se la v0.6 verrà approvata e il relativo file entrerà nel branch di default.

## Altri output repository

- `docs/data.json`
- `docs/index.html`
- `docs/branches.html`

Avvio locale legacy:
`.\aggiorna_radar.bat`

Fonti principali previste / utilizzate a seconda del radar:
1. MASE VIA
2. OpenCUP
3. ANAC / BDNCP
4. Regioni ed enti territoriali
5. developer / contractor / operatori diretti quando la fonte è primaria

<!-- MAINTENANCE-STANDARD:START -->
## Manutenzione repository

- Stato operativo: `CURRENT_STATE.md`
- Istruzioni per ChatGPT/Codex: `AGENTS.md`
- Storico modifiche: `CHANGELOG.md`
- Controllo pre-pubblicazione: `.\scripts\check_before_publish.ps1`

Comando consigliato prima del commit:

```powershell
.\scripts\check_before_publish.ps1
git status
git diff --check
```
<!-- MAINTENANCE-STANDARD:END -->
