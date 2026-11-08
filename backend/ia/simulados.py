"""Comentarios simulados coherentes con cada encuesta, para que el modo demo parezca real.

Solo se aceptan frases que no contengan datos personales y que las palabras clave clasifiquen
en su tema: así la historia del demo es la misma con modelo o sin él.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .analizar import TEMAS, clasificar_por_palabras
from .llm import hay_llm, llamar_llm_json

log = logging.getLogger(__name__)

TIMEOUT_SIMULADOS_SEG = 25
FRASES_POR_TEMA = 4
_PROMPTS = Path(__file__).resolve().parent / "prompts"
_CACHE: dict[str, dict[str, list[str]]] = {}


def _anonimizar():
    try:
        from backend.datos.anonimizar import anonimizar
        return anonimizar
    except ImportError:
        return None


def _contexto(encuesta: dict[str, Any]) -> str:
    preguntas = list(encuesta.get("preguntas") or [])
    for lista in (encuesta.get("preguntas_por_colectivo") or {}).values():
        preguntas += lista
    colectivos = encuesta.get("colectivos") or [encuesta.get("colectivo")]
    return (f"Título: {encuesta.get('titulo', '')}\n"
            f"Sectores: {', '.join(c for c in colectivos if c)}\n"
            "Preguntas:\n" + "\n".join(f"- {p.get('texto', '')}" for p in preguntas))


def banco_contextual(encuesta: dict[str, Any], temas: list[str],
                     idioma: str = "es") -> dict[str, list[str]]:
    """Devuelve {tema: [frases]} escritas para esta encuesta, o {} sin modelo o si falla.

    `idioma` se acepta por uniformidad pero se ignora: los comentarios simulados imitan a la
    plantilla y se escriben siempre en castellano (con algo de catalán), sea cual sea la pantalla.

    Una llamada por encuesta (con caché por id). Solo quedan las frases sin datos personales
    que las palabras clave clasifican en su mismo tema.
    """
    temas = [t for t in dict.fromkeys(temas or []) if t in TEMAS]
    clave = str(encuesta.get("id") or encuesta.get("titulo") or "")
    if not temas or not hay_llm():
        return {}
    if clave in _CACHE:
        return {t: f for t, f in _CACHE[clave].items() if t in temas}

    anonimizar = _anonimizar()
    banco: dict[str, list[str]] = {}
    try:
        usuario = (_contexto(encuesta) + f"\n\nTemas: {', '.join(temas)}\n"
                   f"Escribe {FRASES_POR_TEMA} comentarios por tema.")
        datos = llamar_llm_json((_PROMPTS / "comentarios_simulados.md").read_text(encoding="utf-8"),
                                usuario, TIMEOUT_SIMULADOS_SEG)
        propuesto = datos.get("comentarios", datos) if isinstance(datos, dict) else {}
        for tema in temas:
            frases = propuesto.get(tema) if isinstance(propuesto, dict) else None
            validas = []
            for frase in frases if isinstance(frases, list) else []:
                frase = " ".join(str(frase).split()).strip(" \"'")
                if (5 <= len(frase) <= 200
                        and (anonimizar is None or anonimizar(frase) == frase)
                        and clasificar_por_palabras(frase) == tema):
                    validas.append(frase)
            if validas:
                banco[tema] = validas
        log.info("Banco contextual: %d frases válidas para %d temas",
                 sum(len(f) for f in banco.values()), len(banco))
    except Exception as error:
        log.warning("Banco contextual no disponible, se usan las frases de siempre: %s", error)
    # También se guarda un fallo, para no esperar 25 s en cada simulación
    _CACHE[clave] = banco
    return banco
