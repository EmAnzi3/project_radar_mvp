# project_radar_mvp

MVP per radar commerciale progetti.

Obiettivo:
- raccogliere progetti da fonti pubbliche;
- normalizzare dati essenziali;
- calcolare uno score commerciale;
- generare JSON, CSV e dashboard HTML.

Output iniziali:
- docs/data.json
- docs/index.html

Avvio locale:
.\aggiorna_radar.bat

Fonti previste:
1. MASE VIA
2. OpenCUP
3. ANAC / BDNCP
4. Regioni
5. Albi pretori selezionati

Stato:
Versione iniziale con record demo e struttura dati base.

<!-- MAINTENANCE-STANDARD:START -->
## Manutenzione repository

- Stato operativo: `CURRENT_STATE.md`
- Istruzioni per ChatGPT/Codex: `AGENTS.md`
- Storico modifiche: `CHANGELOG.md`
- Controllo pre-pubblicazione: `.\scripts\check_before_publish.ps1`

Comando consigliato prima del commit:

`powershell
.\scripts\check_before_publish.ps1
git status
git diff --check
`
<!-- MAINTENANCE-STANDARD:END -->
