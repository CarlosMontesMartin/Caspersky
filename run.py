"""Arranca el proyecto con un solo comando, en Linux, Mac y Windows.

    Linux/Mac:  ./run.sh       Windows:  run.bat       (o en cualquiera: python run.py)

La primera vez crea el entorno virtual .venv e instala las dependencias.
"""
import os
import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
PYTHON_VENV = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQUISITOS = [RAIZ / "backend" / "api" / "requirements.txt",
              RAIZ / "backend" / "ia" / "requirements.txt"]  # el de IA solo si existe


def main() -> int:
    if not PYTHON_VENV.exists():
        print("Creando entorno virtual .venv (solo la primera vez)…")
        try:
            venv.create(VENV, with_pip=True)
        except Exception as error:
            print(f"No se pudo crear .venv: {error}")
            if os.name != "nt":
                print("En Ubuntu/Debian instala antes: sudo apt install python3-venv")
            return 1

    for requisitos in REQUISITOS:
        if requisitos.exists():
            subprocess.check_call([str(PYTHON_VENV), "-m", "pip", "install", "-q", "-r", str(requisitos)])

    # --host 0.0.0.0: para poder abrir la encuesta desde el móvil en la misma wifi
    comando = [str(PYTHON_VENV), "-m", "uvicorn", "backend.api.main:app",
               "--reload", "--host", "0.0.0.0", "--port", "8000"]
    print("Arrancando en http://localhost:8000  (documentación: /docs · Ctrl+C para parar)")
    try:
        return subprocess.call(comando, cwd=RAIZ)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
