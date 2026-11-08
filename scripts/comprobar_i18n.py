"""Comprueba que todas las claves t()/tr()/data-i18n del frontend existen en los JSON de idioma.

Uso (desde la raíz del repo):  python scripts/comprobar_i18n.py   → sale con 1 si falta algo.
Solo lee JSON y código fuente: no ejecuta nada del proyecto. (v6, anexo A · UAB 2)
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "frontend"
LLAMADA = re.compile(r"""\b(?:t|tr)\(\s*['"]([a-z0-9_]+\.[a-z0-9_.]+)['"]""")
ATRIBUTO = re.compile(r"""data-i18n(?:-[a-z]+)?=["']([a-z0-9_]+\.[a-z0-9_.]+)["']""")


def claves(nombre):
    return set(json.loads((RAIZ / "i18n" / f"{nombre}.json").read_text(encoding="utf-8")))


def usos():
    rrhh, responder = set(), set()
    for f in [*RAIZ.glob("*.html"), *(RAIZ / "js").glob("*.js")]:
        if f.name == "i18n.js":
            continue  # solo tiene ejemplos en comentarios
        texto = f.read_text(encoding="utf-8")
        encontradas = {m.group(1) for p in (LLAMADA, ATRIBUTO) for m in p.finditer(texto)}
        (responder if f.name == "responder.html" else rrhh).update(encontradas)
    return rrhh, responder


def main():
    rrhh, responder = usos()
    fallos = 0
    for archivo, usadas in [("rrhh_ca", rrhh), ("rrhh_en", rrhh), ("es", responder), ("ca", responder), ("en", responder)]:
        faltan = sorted(usadas - claves(archivo))
        for k in faltan:
            print(f"FALTA  {archivo}.json  {k}")
        fallos += len(faltan)
    if claves("rrhh_ca") != claves("rrhh_en"):
        print("rrhh_ca y rrhh_en no tienen las mismas claves")
        fallos += 1
    if not (claves("es") == claves("ca") == claves("en")):
        print("es, ca y en no tienen las mismas claves")
        fallos += 1
    print("OK" if not fallos else f"{fallos} problemas")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
