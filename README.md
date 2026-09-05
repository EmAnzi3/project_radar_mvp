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

La v0.6 aggiunge un motore agent-style derivato da `pv_agent_mvp`: raw findings, storico variazioni, planner per cadenza ed evidence gate restano separati dal canonico. Gli adapter istituzionali eseguibili correnti sono **MASE VIA, Lazio VIA/PAUR, Toscana GeA, ATOS Toscana FER, Sardegna SIRA e Sicilia SI-VVI**. Ulteriori fonti regionali, company-watch e scheduling persistente sono ancora in sviluppo sul Draft PR #5. Il workflow PR valida architettura e regressioni; la disponibilità live dei portali viene verificata solo con l'esecuzione degli adapter.

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
