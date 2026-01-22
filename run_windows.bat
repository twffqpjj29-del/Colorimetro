@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Trova Python (preferibilmente 3.12 tramite launcher 'py')
where py >nul 2>nul
if errorlevel 1 (
  echo ERRORE: Python launcher "py" non trovato.
  echo Installa Python 3.12 (da python.org) e abilita il launcher.
  pause
  exit /b 1
)

REM Crea venv se non esiste
if not exist ".venv\" (
  py -3.12 -m venv .venv
)

REM Attiva venv
call ".venv\Scripts\activate"

REM Aggiorna pip e installa dipendenze
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Avvio app
python "src\app.py"

pause
