"""Borrador de un compromiso "Dijisteis → Hemos hecho" a partir de una acción recomendada.

La IA redacta el borrador y RRHH lo firma. El modelo solo ve cifras agregadas (sin ningún
comentario): el "Dijisteis" lleva la cifra del tema y el "Hemos hecho" es un borrador con [fecha]
para que RRHH lo complete. Sin modelo, o si su texto no pasa la validación, plantillas en es/ca/en.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .analizar import _copia_literal
from .llm import hay_llm, llamar_llm_json
from .recomendar import datos_agregados
from . import cache_disco
from . import textos_respaldo as textos

log = logging.getLogger(__name__)
_PROMPTS = Path(__file__).resolve().parent / "prompts"
TIMEOUT_COMPROMISO_SEG = 20
MAX_PALABRAS = 30          # el prompt pide 25; se deja algo de margen antes de descartar
_COMILLAS = re.compile(r"[\"“”«»„]")
_CACHE: dict[tuple, dict[str, str]] = {}


def _cifras_de_colectivos(analisis: dict[str, Any], colectivos: list[str]) -> list[str] | None:
    """Los temas se cuentan sobre todos los comentarios de la encuesta: solo se puede decir
    "de planta" si la encuesta es solo de esos colectivos. Si no, None (cifra de toda la encuesta)."""
    de_la_encuesta = [c for c in analisis.get("colectivos") or [] if c]
    if colectivos and de_la_encuesta and set(de_la_encuesta) <= set(colectivos):
        return de_la_encuesta
    return None


def _datos_modelo(tema: dict[str, Any], analisis: dict[str, Any], accion: dict[str, Any],
                  colectivos: list[str], grupo: list[str] | None, idioma: str) -> dict[str, Any]:
    agregados = datos_agregados(analisis)
    # Nada de grupos con menos de 5: las medias pequeñas ya no llegan, pero por si acaso
    agregados["medias"] = [m for m in agregados.get("medias") or [] if (m.get("n") or 0) >= 5]
    agregados["medias_anterior"] = [m for m in agregados.get("medias_anterior") or []
                                    if (m.get("n") or 0) >= 5]
    return {
        "tema": {"codigo": tema.get("tema"), "nombre": textos.nombre("tema", tema.get("tema", ""), idioma),
                 "descripcion": textos.DESCRIPCION_TEMA[idioma].get(tema.get("tema"), ""),
                 "n": tema.get("n"), "pct": tema.get("pct"), "pct_anterior": tema.get("pct_anterior"),
                 "tendencia": tema.get("tendencia"),
                 "periodo": textos.periodo_legible(analisis.get("periodo_actual"), idioma)},
        "cifras_de": ([textos.nombre("colectivo", c, idioma) for c in grupo] if grupo
                      else "toda la encuesta (no las atribuyas a un colectivo)"),
        "colectivos_del_compromiso": [textos.nombre("colectivo", c, idioma) for c in colectivos],
        "accion": {k: accion.get(k) for k in ("titulo", "responsable", "plazo")},
        "datos_agregados": agregados,
    }


def _valido(texto: Any, con_cifra: bool) -> bool:
    if not isinstance(texto, str) or not texto.strip():
        return False
    texto = texto.strip()
    if _COMILLAS.search(texto) or len(texto.split()) > MAX_PALABRAS:
        return False
    return not con_cifra or bool(re.search(r"\d", texto))


def _validar(respuesta: Any, comentarios: list[str]) -> dict[str, str] | None:
    if not isinstance(respuesta, dict):
        return None
    dijisteis, hicimos = respuesta.get("dijisteis"), respuesta.get("hicimos")
    if not (_valido(dijisteis, con_cifra=True) and _valido(hicimos, con_cifra=False)):
        return None
    if comentarios and any(_copia_literal(t, comentarios) for t in (dijisteis, hicimos)):
        return None
    return {"dijisteis": dijisteis.strip(), "hicimos": hicimos.strip()}


def redactar_compromiso(tema: str | dict[str, Any], analisis: dict[str, Any], accion: dict[str, Any],
                        colectivos: list[str] | None = None, idioma: str = "es",
                        comentarios: list[str] | None = None) -> dict[str, str]:
    """{"dijisteis", "hicimos", "origen"}: borrador del compromiso en `idioma` (es, ca o en).

    tema: código del tema ("descansos") o su fila de analisis["temas"].
    accion: la acción recomendada (titulo, responsable, plazo…).
    colectivos: a quién va dirigido el compromiso (por defecto, los de la encuesta).
    comentarios (opcional): textos del tema, solo para comprobar que no se copia ninguno; el
    modelo no los ve nunca. origen: "ia" o "reglas".
    """
    idioma = textos.idioma_valido(idioma)
    analisis = analisis or {}
    accion = accion or {}
    codigo = tema.get("tema") if isinstance(tema, dict) else (tema or accion.get("tema") or "otros")
    fila = next((t for t in analisis.get("temas") or [] if t.get("tema") == codigo), None)
    fila = fila or (tema if isinstance(tema, dict) else {"tema": codigo})
    colectivos = [c for c in (colectivos or analisis.get("colectivos") or []) if c]
    grupo = _cifras_de_colectivos(analisis, colectivos)
    respaldo = {**textos.compromiso_respaldo(fila, grupo, analisis.get("periodo_actual"), idioma),
                "origen": "reglas"}
    if not hay_llm() or not fila.get("n"):
        return respaldo

    datos = _datos_modelo(fila, analisis, accion, colectivos, grupo, idioma)
    clave = (idioma, json.dumps(datos, ensure_ascii=False, sort_keys=True))
    if clave not in _CACHE and cache_disco.leer("compromiso", clave):
        _CACHE[clave] = cache_disco.leer("compromiso", clave)
    if clave in _CACHE:
        return {**_CACHE[clave], "origen": "ia"}
    prompt = ((_PROMPTS / "compromiso.md").read_text(encoding="utf-8")
              + f"\n\nEscribe los dos textos en {textos.NOMBRE_IDIOMA[idioma]}.")
    try:
        salida = llamar_llm_json(prompt, json.dumps(datos, ensure_ascii=False), TIMEOUT_COMPROMISO_SEG)
    except Exception as error:  # noqa: BLE001
        log.warning("Compromiso por plantilla: el modelo no respondió (%s)", error)
        return respaldo
    resultado = _validar(salida, comentarios or [])
    if resultado is None:
        log.warning("Compromiso por plantilla: el texto del modelo no pasa la validación")
        return respaldo
    _CACHE[clave] = resultado
    cache_disco.guardar("compromiso", clave, resultado)
    return {**resultado, "origen": "ia"}
