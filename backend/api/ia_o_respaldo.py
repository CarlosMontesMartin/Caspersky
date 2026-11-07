"""Puente con backend/ia/ (UPC 1).

Si backend/ia/ todavía no existe o una función falla, se usa un respaldo
para que el ciclo completo funcione igual. Cuando UPC 1 suba su código con
las firmas de modulos.md, se usa automáticamente.
"""
import copy
import json
from pathlib import Path

EJEMPLOS = Path(__file__).resolve().parents[2] / "contratos" / "ejemplos"


def _ejemplo(nombre: str) -> dict:
    return json.loads((EJEMPLOS / f"{nombre}.json").read_text(encoding="utf-8"))


def hay_llm() -> bool:
    try:
        from backend.ia.llm import hay_llm as real
        return bool(real())
    except Exception:
        return False


def generar_encuesta(necesidad: dict, reglas: str) -> dict:
    try:
        from backend.ia.generar import generar_encuesta as real
        return real(necesidad, reglas)
    except Exception as error:
        print(f"[ia] generar_encuesta usa respaldo: {error!r}")
    encuesta = _ejemplo("encuesta")
    encuesta["colectivo"] = necesidad["colectivo"]
    for pregunta in encuesta["preguntas"]:
        pregunta["condicion"] = None
    return encuesta


def analizar_comentarios(actual: list, anterior: list) -> list:
    try:
        from backend.ia.analizar import analizar_comentarios as real
        return real(actual, anterior)
    except Exception as error:
        print(f"[ia] analizar_comentarios usa respaldo: {error!r}")
    return []


def recomendar(analisis: dict, encuesta: dict) -> dict:
    try:
        from backend.ia.recomendar import recomendar as real
        return real(analisis, encuesta)
    except Exception as error:
        print(f"[ia] recomendar usa respaldo: {error!r}")
    recomendaciones = copy.deepcopy(_ejemplo("recomendaciones"))
    colectivo = encuesta.get("colectivo")
    recomendaciones["seguimiento"]["colectivo"] = colectivo if colectivo != "todos" else "planta"
    return recomendaciones
