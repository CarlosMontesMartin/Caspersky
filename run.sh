#!/usr/bin/env bash
# Linux y Mac. Toda la lógica está en run.py.
cd "$(dirname "$0")"
exec "$(command -v python3 || command -v python)" run.py
