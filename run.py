"""Arranca el proyecto con un solo comando, en Linux, Mac y Windows.

    Linux/Mac:  ./run.sh       Windows:  run.bat       (o en cualquiera: python run.py)
    Desarrollo (se reinicia solo al cambiar el código):  ./run.sh --dev   ·   run.bat --dev

La primera vez crea el entorno virtual .venv e instala las dependencias.
Siempre se abre la app en http://localhost:8000 (nunca con Live Server).
"""
import os
import socket
import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
PYTHON_VENV = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQUISITOS = [RAIZ / "backend" / "api" / "requirements.txt",
              RAIZ / "backend" / "ia" / "requirements.txt"]  # el de IA solo si existe


def ip_local() -> str | None:
    """IP del portátil en la red (para el QR desde el móvil). No envía nada por la red."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def main() -> int:
    dev = "--dev" in sys.argv[1:]
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
    comando = [str(PYTHON_VENV), "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
    if dev:
        comando.append("--reload")
    ip = ip_local()
    print("\n  Abre http://localhost:8000   (nunca con Live Server · documentación: /docs)")
    print("  Modo desarrollo: se reinicia solo al cambiar el código." if dev else
          "  Después de cada git pull, para con Ctrl+C y vuelve a arrancar (o usa --dev).")
    if ip:
        print(f"  Para el QR desde el móvil (misma wifi): BASE_URL=http://{ip}:8000 en el .env")
    print("  Ctrl+C para parar\n")
    try:
        return subprocess.call(comando, cwd=RAIZ)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
