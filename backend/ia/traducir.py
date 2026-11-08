"""Traducción de encuestas entre castellano, catalán e inglés para quien responde.

Se traduce desde el idioma original de la encuesta (el de la pantalla de RRHH al generarla) a
los otros dos. Una llamada al modelo por idioma. Se conservan los ids y el número y orden de las
opciones, para que las respuestas se puedan guardar siempre con los valores del idioma original.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json

log = logging.getLogger(__name__)

TIMEOUT_TRADUCIR_SEG = 30
NOMBRE_IDIOMA = {"es": "castellano", "ca": "catalán", "en": "inglés"}
IDIOMAS_TRADUCCION = list(NOMBRE_IDIOMA)
_PROMPTS = Path(__file__).resolve().parent / "prompts"


def _pregunta(p: dict[str, Any]) -> dict[str, Any]:
    return {"id": p.get("id"), "texto": p.get("texto", ""), "opciones": list(p.get("opciones") or [])}


def _original(encuesta: dict[str, Any]) -> dict[str, Any]:
    return {
        "titulo": encuesta.get("titulo", ""),
        "intro": encuesta.get("intro", ""),
        "preguntas": [_pregunta(p) for p in encuesta.get("preguntas") or []],
        "preguntas_por_colectivo": {c: [_pregunta(p) for p in lista]
                                    for c, lista in (encuesta.get("preguntas_por_colectivo") or {}).items()},
    }


def _texto(valor: Any) -> str | None:
    return " ".join(valor.split()) if isinstance(valor, str) and valor.strip() else None


def _validar_lista(original: list[dict], traducida: Any) -> list[dict] | None:
    # Se emparejan por id: mismo conjunto de ids y mismo número de opciones en cada pregunta
    if not isinstance(traducida, list):
        return None
    por_id = {p.get("id"): p for p in traducida if isinstance(p, dict)}
    resultado = []
    for p in original:
        t = por_id.get(p["id"])
        texto = _texto(t.get("texto")) if t else None
        opciones = [_texto(o) for o in (t.get("opciones") or [])] if t else None
        if not texto or opciones is None or len(opciones) != len(p["opciones"]) or None in opciones:
            return None
        resultado.append({"id": p["id"], "texto": texto, "opciones": opciones})
    return resultado


def _validar(original: dict[str, Any], traducida: Any) -> dict[str, Any] | None:
    if not isinstance(traducida, dict):
        return None
    titulo, intro = _texto(traducida.get("titulo")), _texto(traducida.get("intro"))
    preguntas = _validar_lista(original["preguntas"], traducida.get("preguntas"))
    por_colectivo = {}
    propuestas = traducida.get("preguntas_por_colectivo") or {}
    for colectivo, lista in original["preguntas_por_colectivo"].items():
        validada = _validar_lista(lista, propuestas.get(colectivo) if isinstance(propuestas, dict) else None)
        if validada is None:
            return None
        por_colectivo[colectivo] = validada
    if not titulo or not intro or preguntas is None:
        return None
    return {"titulo": titulo, "intro": intro, "preguntas": preguntas,
            "preguntas_por_colectivo": por_colectivo}


def _traducir_idioma(original: dict[str, Any], idioma: str, colectivos: list[str],
                     origen: str = "es") -> dict[str, Any] | None:
    usuario = (f"Idioma de origen: {NOMBRE_IDIOMA[origen]} ({origen})\n"
               f"Idioma de destino: {NOMBRE_IDIOMA[idioma]} ({idioma})\n"
               f"Colectivos que responden: {', '.join(colectivos) or 'varios'}\n\n"
               f"Encuesta en {NOMBRE_IDIOMA[origen]} (JSON):\n" + json.dumps(original, ensure_ascii=False))
    inicio = time.monotonic()
    try:
        salida = llamar_llm_json((_PROMPTS / "traducir.md").read_text(encoding="utf-8"),
                                 usuario, TIMEOUT_TRADUCIR_SEG)
        traduccion = _validar(original, salida)
        if traduccion is None:
            log.warning("Traducción al %s descartada: no respeta ids u opciones (%.1f s)",
                        NOMBRE_IDIOMA[idioma], time.monotonic() - inicio)
        else:
            log.info("Traducción al %s lista en %.1f s", NOMBRE_IDIOMA[idioma], time.monotonic() - inicio)
        return traduccion
    except Exception as error:
        log.warning("Traducción al %s no disponible (%.1f s): %s", NOMBRE_IDIOMA[idioma],
                    time.monotonic() - inicio, error)
        return None


def traducir_encuesta(encuesta: dict[str, Any], idiomas_destino: list[str],
                      idioma_origen: str | None = None) -> dict[str, dict[str, Any]]:
    """Traduce título, intro y preguntas a cada idioma pedido: {"es": {...}, "en": {...}}.

    `idioma_origen` es el idioma original de la encuesta (si no se pasa, encuesta["idioma_original"]
    y, si no está, es). Nunca se traduce al propio idioma de origen. Mismos ids y mismo número y
    orden de opciones que el original. Un idioma que falla o no supera la validación no se incluye y
    queda en el log (la ruta marca estado_traduccion = "error" y la página lo muestra en el
    original). Sin modelo, {}.
    """
    origen = idioma_origen or encuesta.get("idioma_original") or "es"
    origen = origen if origen in NOMBRE_IDIOMA else "es"
    idiomas = [i for i in dict.fromkeys(idiomas_destino or []) if i in NOMBRE_IDIOMA and i != origen]
    if not idiomas or not hay_llm():
        return {}
    original = _original(encuesta)
    colectivos = encuesta.get("colectivos") or [encuesta.get("colectivo") or ""]
    with ThreadPoolExecutor(max_workers=len(idiomas)) as pool:
        resultados = dict(zip(idiomas, pool.map(
            lambda idioma: _traducir_idioma(original, idioma, colectivos, origen), idiomas)))
    return {idioma: traduccion for idioma, traduccion in resultados.items() if traduccion}
