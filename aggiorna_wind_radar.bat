@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================
echo  ALAYAN WIND RADAR - BUILD / VALIDATE / PREVIEW
echo ============================================================
echo.

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [1/6] Creo ambiente Python isolato...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>nul
    if errorlevel 1 goto :no_python
    python -m venv .venv
  )
  if errorlevel 1 goto :failure
)

if not exist "%PY%" goto :no_python

echo [2/6] Verifico sintassi Python...
"%PY%" -m py_compile "wind\scripts\build_wind_radar.py"
if errorlevel 1 goto :failure

echo [3/6] Leggo e valido il seed canonico...
if not exist "wind\input\projects.json" (
  echo [FAILURE] Manca wind\input\projects.json
  goto :failure
)

echo [4/6] Genero master, relazioni, JSON, CSV e web output...
"%PY%" "wind\scripts\build_wind_radar.py"
if errorlevel 1 goto :failure

echo [5/6] Eseguo i controlli sugli output...
"%PY%" "wind\scripts\build_wind_radar.py" --check-only
if errorlevel 1 goto :failure

echo [6/6] Controllo JavaScript se Node.js e disponibile...
where node >nul 2>nul
if errorlevel 1 (
  echo [INFO] Node.js non trovato: controllo JS opzionale saltato.
) else (
  node --check "docs\wind\assets\app.js"
  if errorlevel 1 goto :failure
  node --check "docs\wind\assets\review-fixes.js"
  if errorlevel 1 goto :failure
  node --check "docs\wind\assets\contractor-direct-fix.js"
  if errorlevel 1 goto :failure
)

echo.
echo [SUCCESS] Wind Radar aggiornato e validato.
echo [SUCCESS] Dashboard Pages: docs\wind\index.html
echo [SUCCESS] Preview standalone: docs\wind\preview.html
echo.

if /I not "%WIND_NO_OPEN%"=="1" start "" "%CD%\docs\wind\preview.html"
if /I not "%WIND_NO_PAUSE%"=="1" pause
exit /b 0

:no_python
echo.
echo [FAILURE] Python non disponibile. Installa Python 3 e assicurati che py o python sia nel PATH.
goto :end_failure

:failure
echo.
echo [FAILURE] Aggiornamento Wind Radar interrotto. Correggere l'errore indicato sopra.

:end_failure
if /I not "%WIND_NO_PAUSE%"=="1" pause
exit /b 1
