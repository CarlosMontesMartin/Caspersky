#!/usr/bin/env bash
# Arranca el backend con un solo comando. Ejecutar desde la raíz del repo.
set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python)
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi
source .venv/bin/activate

python -m pip install -q -r backend/api/requirements.txt
# --host 0.0.0.0: para poder abrir la encuesta desde el móvil en la misma wifi
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
