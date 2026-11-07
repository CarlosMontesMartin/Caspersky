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
python -m uvicorn backend.api.main:app --reload --port 8000