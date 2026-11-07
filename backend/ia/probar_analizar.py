"""Pruebas de integración para análisis temático y recomendaciones sobre datos sintéticos."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from backend.ia.analizar import TEMAS, analizar_comentarios, clasificar_comentarios
from backend.ia.llm import hay_llm
from backend.ia.recomendar import recomendar

RAIZ = Path(__file__).resolve().parents[2]


def _cargar(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    """Ejecuta la validación de análisis temático, cálculo de tendencias y recomendaciones."""
    respuestas = _cargar(RAIZ / "datos_sinteticos" / "respuestas.json")
    encuesta = _cargar(RAIZ / "datos_sinteticos" / "enc_000.json")
    plantilla_ruta = RAIZ / "contenido" / "plantilla.json"
    plantilla = _cargar(plantilla_ruta) if plantilla_ruta.exists() else []

    periodos = sorted({r["periodo"] for r in respuestas})
    actual = [r for r in respuestas if r["periodo"] == periodos[-1]]
    anterior = [r for r in respuestas if len(periodos) > 1 and r["periodo"] == periodos[-2]]
    print(f"Modo: {'IA real' if hay_llm() else 'respaldo (sin clave)'}")
    print(f"Respuestas: {len(actual)} en {periodos[-1]} · {len(anterior)} en "
          f"{periodos[-2] if len(periodos) > 1 else '-'}")

    con_texto = [r for r in respuestas if r.get("comentario")]
    predichos = clasificar_comentarios([r["comentario"] for r in con_texto])
    aciertos = sum(p == r["tema_real"] for p, r in zip(predichos, con_texto))
    print(f"\nPrecisión de la clasificación: {aciertos / len(con_texto):.0%} "
          f"({aciertos}/{len(con_texto)})")
    fallos = Counter((r["tema_real"], p) for p, r in zip(predichos, con_texto) if p != r["tema_real"])
    if fallos:
        print("  Confusiones más frecuentes (real → predicho):",
              ", ".join(f"{a}→{b} ×{n}" for (a, b), n in fallos.most_common(4)))

    temas = analizar_comentarios(actual, anterior)
    print("\nTemas (n ≥ 5):")
    for t in temas:
        flecha = "↑" if t["tendencia"] in ("nuevo", "sube") else "↓" if t["tendencia"] == "baja" else "·"
        print(f"  {flecha} {t['tema']:<15}{t['n']:>4}  {t['tendencia']:<8} {t['resumen']}")

    participacion = []
    for fila in plantilla:
        n = sum(1 for r in actual if r["colectivo"] == fila["colectivo"] and r["turno"] == fila["turno"])
        tasa = n / fila["personas"] if fila["personas"] else 0.0
        participacion.append({**fila, "respuestas": n, "tasa": round(tasa, 3),
                              "representativo": n >= 5 and tasa >= 0.20})
    analisis = {"encuesta_id": encuesta["id"], "n_respuestas": len(actual),
                "periodo_actual": periodos[-1],
                "periodo_anterior": periodos[-2] if len(periodos) > 1 else None,
                "participacion": participacion, "medias": [], "temas": temas,
                "alertas": [], "limites": []}
    rec = recomendar(analisis, encuesta)
    print("\nRecomendaciones (propuestas):")
    for a in rec["acciones"]:
        print(f"  - {a['titulo']}  [{a['tema']}]\n      {a['motivo']}")
    print("Encuesta de seguimiento:", json.dumps(rec["seguimiento"], ensure_ascii=False))

    errores = []
    if any(t["tema"] not in TEMAS or t["n"] < 5 for t in temas):
        errores.append("tema fuera de la lista o con n < 5")
    if any(t["tendencia"] not in ("nuevo", "sube", "estable", "baja") for t in temas):
        errores.append("tendencia no válida")
    if not 1 <= len(rec["acciones"]) <= 3:
        errores.append("número de acciones fuera de 1–3")
    seg = rec["seguimiento"]
    if set(seg) != {"objetivo", "colectivo", "contexto", "duracion_max_seg", "temas_prohibidos"}:
        errores.append("el seguimiento no tiene el formato Necesidad")
    if seg.get("duracion_max_seg") != 60:
        errores.append("duracion_max_seg del seguimiento distinta de 60")
    print("\n" + ("TODAS LAS COMPROBACIONES OK" if not errores else "ERRORES: " + "; ".join(errores)))
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
