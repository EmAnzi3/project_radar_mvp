@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Wind Project & Contractor Radar

echo.
echo ============================================================
echo   WIND PROJECT ^& CONTRACTOR RADAR - Alayan
echo ============================================================
echo.

if not exist "docs\wind\index.html" (
  echo [ERRORE] Dashboard non trovata: docs\wind\index.html
  pause
  exit /b 1
)

if not exist "docs\wind\data\projects.json" (
  echo [ERRORE] Manifest dati non trovato: docs\wind\data\projects.json
  pause
  exit /b 1
)

set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)

if not defined PY (
  echo [ERRORE] Python 3 non trovato.
  echo Installa Python oppure aggiungilo al PATH.
  pause
  exit /b 1
)

echo [1/3] Verifica dataset e contractor coverage...
%PY% "scripts\check_wind_v07_execution_coverage.py"
if errorlevel 1 (
  echo.
  echo [ERRORE] Il controllo Wind Radar v0.7 e' fallito.
  echo La dashboard non viene aperta per evitare di mostrare dati incoerenti.
  pause
  exit /b 1
)

set "PORT=8765"
set "URL=http://127.0.0.1:%PORT%/wind/"

echo [2/3] Verifica server locale...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -TimeoutSec 1; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
  echo Avvio server locale sulla porta %PORT%...
  start "Wind Radar Server" /min cmd /c "%PY% -m http.server %PORT% --directory docs"
  timeout /t 2 /nobreak >nul
) else (
  echo Server locale gia' attivo.
)

echo [3/3] Apro il radar...
start "" "%URL%"

echo.
echo OK - Wind Radar aperto:
echo %URL%
echo.
echo Il server resta attivo in una finestra minimizzata.
echo Per chiuderlo, chiudi la finestra "Wind Radar Server".
echo.
endlocal
