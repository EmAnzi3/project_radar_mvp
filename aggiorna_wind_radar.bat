@echo off
setlocal
cd /d "%~dp0"

echo.
echo === WIND RADAR - aggiornamento ===
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creo ambiente virtuale Python...
  py -m venv .venv
  if errorlevel 1 (
    echo ERRORE: Python non disponibile. Verifica che il comando "py" funzioni.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

if not exist "wind\input\projects.json" (
  echo ERRORE: manca wind\input\projects.json
  pause
  exit /b 1
)

echo Genero dashboard e file di export...
python "wind\scripts\build_wind_radar.py"
if errorlevel 1 (
  echo.
  echo ERRORE: generazione radar non riuscita.
  pause
  exit /b 1
)

echo.
echo OK - Wind Radar aggiornato.
echo Apro la dashboard...
start "" "%~dp0docs\wind\index.html"

echo.
git status
pause
