#!/bin/bash
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Errore: python3 non trovato. Installa Python 3.12 e riprova."
  exit 1
fi

if [ ! -f "requirements.txt" ]; then
  echo "Errore: requirements.txt non trovato nella cartella:"
  pwd
  echo "Assicurati che requirements.txt sia nella root del progetto (accanto a run_mac.command)."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python src/app.py
