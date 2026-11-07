"""Precisión de la clasificación de comentarios frente al tema real de los datos sintéticos.

Uso: python3 -m backend.ia.evaluar [ruta de respuestas.json]
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from . import segundo_plano
from .analizar import (TEMAS, clasificacion_en_curso, clasificar_comentarios,
                       clasificar_por_palabras, estado_clasificacion)
from .llm import hay_llm

RAIZ = Path(__file__).resolve().parents[2]


def _precision(predichos: list[str], reales: list[str]) -> dict[str, Any]:
    por_tema = {}
    for tema in TEMAS:
        indices = [i for i, r in enumerate(reales) if r == tema]
        if indices:
            por_tema[tema] = round(sum(predichos[i] == tema for i in indices) / len(indices), 3)
    aciertos = sum(p == r for p, r in zip(predichos, reales))
    return {"precision": round(aciertos / len(reales), 3) if reales else 0.0,
            "n": len(reales), "por_tema": por_tema}


def precision_clasificacion(respuestas: list[dict[str, Any]]) -> dict[str, Any]:
    """Compara la clasificación de cada comentario con su tema_real.

    Con modelo, espera a que termine la clasificación en segundo plano antes de medir.
    """
    con_tema = [r for r in respuestas if r.get("comentario") and r.get("tema_real") in TEMAS]
    textos = [r["comentario"] for r in con_tema]
    reales = [r["tema_real"] for r in con_tema]
    predichos = clasificar_comentarios(textos)
    if hay_llm():
        limite = time.monotonic() + 600
        while clasificacion_en_curso() and time.monotonic() < limite:
            segundo_plano.esperar(timeout=30)
        predichos = clasificar_comentarios(textos)
    return _precision(predichos, reales)


def main() -> int:
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "datos_sinteticos" / "respuestas.json"
    respuestas = json.loads(ruta.read_text(encoding="utf-8"))
    con_tema = [r for r in respuestas if r.get("comentario") and r.get("tema_real") in TEMAS]

    reglas = _precision([clasificar_por_palabras(r["comentario"]) for r in con_tema],
                        [r["tema_real"] for r in con_tema])
    print(f"Comentarios evaluados: {reglas['n']}")
    print(f"Palabras clave:   {reglas['precision']:.1%}")
    if not hay_llm():
        print("Modelo:           sin clave de IA (solo palabras clave)")
        return 0

    inicio = time.monotonic()
    modelo = precision_clasificacion(respuestas)
    estado = estado_clasificacion([r["comentario"] for r in con_tema])
    print(f"Modelo + respaldo: {modelo['precision']:.1%}  "
          f"({estado['por_ia']} de {estado['total']} comentarios distintos clasificados por el "
          f"modelo, {time.monotonic() - inicio:.0f} s)")
    fallos = Counter((r["tema_real"], p) for r, p in
                     zip(con_tema, clasificar_comentarios([r["comentario"] for r in con_tema]))
                     if p != r["tema_real"])
    if fallos:
        print("Confusiones más frecuentes (real → asignado):",
              ", ".join(f"{a}→{b} ×{n}" for (a, b), n in fallos.most_common(5)))
    peores = sorted(modelo["por_tema"].items(), key=lambda kv: kv[1])[:3]
    print("Temas con menor precisión:", ", ".join(f"{t} {p:.0%}" for t, p in peores))
    return 0


if __name__ == "__main__":
    sys.exit(main())
