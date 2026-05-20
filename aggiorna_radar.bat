@echo off
setlocal

cd /d "%~dp0"

echo =====================================
echo Project Radar MVP - aggiornamento
echo =====================================

set "PYTHON_CMD="

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo ERRORE: Python non trovato.
    echo.
    echo Verifica con:
    echo python --version
    echo oppure installa Python da python.org
    echo.
    pause
    exit /b 1
)

echo Python rilevato: %PYTHON_CMD%

if not exist ".venv\Scripts\python.exe" (
    echo Creo ambiente virtuale...
    %PYTHON_CMD% -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo ERRORE: ambiente virtuale non creato.
    echo Prova manualmente:
    echo python -m venv .venv
    pause
    exit /b 1
)

echo Installo/aggiorno dipendenze...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Avvio generazione radar...
".venv\Scripts\python.exe" scripts\run_once.py

echo.
echo Fine.
pause
