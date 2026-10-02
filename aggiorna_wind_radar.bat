@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Alayan Wind Radar - aggiornamento locale

echo.
echo ============================================================
echo   ALAYAN WIND PROJECT ^& CONTRACTOR RADAR
echo   Aggiornamento intelligence + apertura dashboard
echo ============================================================
echo.

set "MODE=%~1"
set "UPDATE_ARGS="
if /I "%MODE%"=="offline" set "UPDATE_ARGS=--offline"
if /I "%MODE%"=="all" set "UPDATE_ARGS=--all"

if not "%MODE%"=="" if /I not "%MODE%"=="offline" if /I not "%MODE%"=="all" (
  echo ERRORE: modalita non riconosciuta "%MODE%".
  echo Usa: aggiorna_wind_radar.bat ^| offline ^| all
  goto :fail
)

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Creo ambiente virtuale Python...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>nul
    if errorlevel 1 (
      echo ERRORE: Python non trovato. Installa Python 3 e riprova.
      goto :fail
    )
    python -m venv .venv
  )
  if errorlevel 1 goto :fail
)

set "PY=%CD%\.venv\Scripts\python.exe"

echo [SETUP] Verifico dipendenze...
"%PY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo ERRORE: installazione dipendenze non riuscita.
  goto :fail
)

echo.
if /I "%MODE%"=="offline" (
  echo [1/3] Modalita OFFLINE: aggiorno stato locale senza interrogare fonti esterne...
) else if /I "%MODE%"=="all" (
  echo [1/3] Modalita ALL: interrogo tutte le fonti e tutti i player monitorati...
) else (
  echo [1/3] Scansione giornaliera: interrogo TUTTE le fonti progetto istituzionali...
  echo       I player commerciali vengono controllati secondo cadenza.
)

"%PY%" scripts\update_wind_radar_local.py %UPDATE_ARGS%
if errorlevel 1 (
  echo.
  echo ATTENZIONE: il refresh intelligence ha restituito un errore.
  echo Il canonico non e stato modificato. Procedo comunque con le verifiche locali.
)

echo.
echo [2/3] Verifico coerenza del Wind Radar...
for %%S in (
  scripts\check_wind_daily_discovery.py
  scripts\check_wind_v05.py
  scripts\check_wind_v05_enrichment.py
  scripts\check_wind_v06_agents.py
  scripts\check_wind_v06_commercial.py
  scripts\check_wind_v06_commercial_c.py
  scripts\check_wind_v06_commercial_d.py
  scripts\check_wind_v06_institutional.py
  scripts\check_wind_v06_map.py
  scripts\check_wind_v06_mase_normalization.py
  scripts\check_wind_v06_network.py
) do (
  "%PY%" "%%S"
  if errorlevel 1 (
    echo.
    echo ERRORE: validazione fallita su %%S
    goto :fail
  )
)

where node >nul 2>nul
if not errorlevel 1 (
  node --check docs\wind\assets\app.js >nul
  if errorlevel 1 goto :fail
  node --check docs\wind\assets\local-run.js >nul
  if errorlevel 1 goto :fail
)

echo.
echo [3/3] Apro report giornaliero e dashboard...
set "RADAR_URL=http://127.0.0.1:8766/docs/wind/"
set "DAILY_REPORT=%CD%\reports\wind-agent\daily-discovery-latest.html"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%RADAR_URL%'; if($r.Content -match 'Wind Project') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul

if errorlevel 1 (
  start "Wind Radar Local Server" /min "%PY%" -m http.server 8766 --bind 127.0.0.1 --directory "%CD%"
  timeout /t 2 /nobreak >nul
)

if exist "%DAILY_REPORT%" (
  start "" "%DAILY_REPORT%"
) else (
  echo ATTENZIONE: report giornaliero non trovato: %DAILY_REPORT%
)
start "" "%RADAR_URL%"

echo.
echo ============================================================
echo   WIND RADAR GIORNALIERO COMPLETATO
echo ============================================================
echo Report nuovi progetti: %DAILY_REPORT%
echo Dashboard: %RADAR_URL%
echo.
echo Modalita disponibili:
echo   doppio click              = scansione giornaliera di TUTTE le fonti progetto
echo   aggiorna_wind_radar.bat all      = come sopra + forza tutti i player commerciali
echo   aggiorna_wind_radar.bat offline  = valida e apre senza rete
echo.
echo NOTA: il report distingue:
echo       - nuovi progetti candidati
echo       - aggiornamenti dei 51 progetti gia noti
echo       - aggiornamenti della coda Discovery
echo       - identita da verificare / errori fonte
echo.
echo Nessun nuovo progetto viene aggiunto automaticamente al canonico:
echo la promozione resta soggetta al gate di verifica.
echo.
git status --short
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo   WIND RADAR NON AGGIORNATO
echo ============================================================
echo Controlla il messaggio di errore sopra. Nessun dato canonico viene
echo modificato automaticamente da questo BAT.
echo.
pause
exit /b 1
