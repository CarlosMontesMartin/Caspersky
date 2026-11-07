"""Pregunta a tus datos: respuestas en lenguaje natural a partir de resultados agregados.

El modelo solo recibe datos agregados (nunca comentarios individuales) y las preguntas que
buscan identificar a alguien se rechazan antes de llamarlo.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json
from .recomendar import datos_agregados

log = logging.getLogger(__name__)

TIMEOUT_PREGUNTAR_SEG = 25
MAX_CARACTERES = 300
MAX_PALABRAS = 120
_PROMPTS = Path(__file__).resolve().parent / "prompts"
_CACHE: dict[tuple[str, str], dict[str, Any]] = {}

AYUDA = ("Escribe una pregunta sobre los resultados, por ejemplo: ¿qué sector está peor y por qué? "
         "o ¿qué ha cambiado respecto al mes pasado?")
RESPUESTA_PRIVACIDAD = ("Esta herramienta solo trabaja con resultados agregados: no puede identificar "
                        "a nadie, decir qué ha respondido una persona ni servir para tomar decisiones "
                        "sobre personas concretas. Puedes preguntar por colectivos, turnos o temas.")

# Peticiones que buscan identificar o actuar sobre personas concretas
_IDENTIFICAR = re.compile(
    r"\bquien(es)?\b|\bnombres?\b(?! (del?|de la) (tema|sector|colectivo|turno|encuesta|pregunta))|\bdni\b|\bnie\b|\bcorreos?\b|\be-?mails?\b|\btelefonos?\b"
    r"|que (ha|han) (dicho|escrito|respondido|contestado)|que dijo|quien dijo"
    r"|\bdespedi|\bdespido|\bsancion|\bcastig|\bidentifica|persona concreta|empleado concreto"
    r"|\bchivat|\bdelat")


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def busca_identificar(pregunta: str) -> bool:
    """Indica si la pregunta busca identificar o actuar sobre una persona concreta."""
    return bool(_IDENTIFICAR.search(_normalizar(pregunta)))


def _respuesta(texto: str, cifras: list[str], confianza: str, origen: str) -> dict[str, Any]:
    return {"respuesta": texto, "cifras": cifras, "confianza": confianza, "origen": origen}


def _pct(valor: Any) -> str:
    return f"{float(valor) * 100:.0f} %" if isinstance(valor, (int, float)) else "—"


def _respuesta_reglas(analisis: dict[str, Any], recomendaciones: dict[str, Any] | None,
                      motivo: str) -> dict[str, Any]:
    # Sin modelo no se interpreta la pregunta: se resumen los datos clave, sin inventar nada
    cifras = []
    if analisis.get("n_respuestas"):
        cifras.append(f"{analisis['n_respuestas']} respuestas en {analisis.get('periodo_actual', '')}")
    for fila in analisis.get("participacion") or []:
        if fila.get("representativo") is False:
            cifras.append(f"{fila.get('colectivo')} {fila.get('turno')}: {_pct(fila.get('tasa'))} "
                          f"de participación (no representativo)")
    for tema in (analisis.get("temas") or [])[:3]:
        cifras.append(f"{tema.get('tema')}: {tema.get('n')} comentarios ({tema.get('tendencia')})")
    lectura = (recomendaciones or {}).get("lectura") or ""
    texto = f"{motivo} Resumen automático de los datos: {lectura}".strip()
    return _respuesta(texto, cifras[:6], "baja", "reglas")


def preguntar(pregunta: str, analisis: dict[str, Any],
              recomendaciones: dict[str, Any] | None = None) -> dict[str, Any]:
    """Responde una pregunta en lenguaje natural citando cifras de los resultados agregados.

    Rechaza sin llamar al modelo las preguntas que buscan identificar a alguien. Límite de 25 s;
    sin modelo o si falla, devuelve un resumen de los datos sin interpretar la pregunta.
    """
    pregunta = " ".join(str(pregunta or "").split())[:MAX_CARACTERES]
    analisis = analisis or {}
    if not pregunta:
        return _respuesta(AYUDA, [], "alta", "reglas")
    if busca_identificar(pregunta):
        return _respuesta(RESPUESTA_PRIVACIDAD, [], "alta", "reglas")
    if not hay_llm():
        return _respuesta_reglas(analisis, recomendaciones,
                                 "La IA no está disponible en este momento.")

    datos = datos_agregados(analisis)
    datos["resumenes_temas"] = {t.get("tema"): t.get("resumen")
                                for t in analisis.get("temas") or [] if t.get("resumen")}
    datos["acciones_propuestas"] = [a.get("titulo") for a in (recomendaciones or {}).get("acciones") or []]
    clave = (_normalizar(pregunta), json.dumps(datos, ensure_ascii=False, sort_keys=True))
    if clave in _CACHE:
        return _CACHE[clave]

    try:
        usuario = (f"Pregunta de RRHH: {pregunta}\n\nDatos agregados (JSON):\n"
                   + json.dumps(datos, ensure_ascii=False))
        salida = llamar_llm_json((_PROMPTS / "preguntar.md").read_text(encoding="utf-8"),
                                 usuario, TIMEOUT_PREGUNTAR_SEG)
        texto = str(salida.get("respuesta", "")).strip() if isinstance(salida, dict) else ""
        if not texto:
            raise ValueError("respuesta vacía")
        palabras = texto.split()
        if len(palabras) > MAX_PALABRAS:
            texto = " ".join(palabras[:MAX_PALABRAS]).rstrip(",;:") + "…"
        cifras = [str(c).strip() for c in salida.get("cifras") or [] if str(c).strip()][:6]
        confianza = salida.get("confianza") if salida.get("confianza") in ("alta", "media", "baja") \
            else "media"
        resultado = _respuesta(texto, cifras, confianza, "ia")
    except Exception as error:
        log.warning("Pregunta a tus datos sin modelo: %s", error)
        return _respuesta_reglas(analisis, recomendaciones,
                                 "La IA no ha respondido a tiempo.")
    _CACHE[clave] = resultado
    return resultado
