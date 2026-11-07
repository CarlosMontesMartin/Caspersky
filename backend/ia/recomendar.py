"""Generación de propuestas de acción y definición de encuestas de seguimiento.

Si no hay clave de modelo disponible o la llamada falla, recurre a reglas fijas por tema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json

COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
NOMBRE_COLECTIVO = {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                    "oficina": "oficina", "manager": "managers"}
NOMBRE_TURNO = {"manana": "de mañana", "tarde": "de tarde", "noche": "de noche"}
DURACION_SEGUIMIENTO = 60
_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Acciones fijas por tema orientadas a procesos y organización
ACCION_POR_TEMA: dict[str, tuple[str, str]] = {
    "descansos": ("Revisar con los equipos la duración y el momento de las pausas",
                  "Saber qué cambios en las pausas ayudarían a descansar mejor"),
    "turnos": ("Abrir un espacio para recoger propuestas sobre el sistema de turnos",
               "Entender qué dificultades concretas genera el nuevo sistema de turnos"),
    "carga_trabajo": ("Analizar los picos de trabajo y reforzar los momentos críticos",
                      "Detectar en qué momentos la carga de trabajo es más difícil de asumir"),
    "comunicacion": ("Comunicar los cambios por un canal oficial y con antelación",
                     "Saber por qué canal y con cuánta antelación quieren recibir los cambios"),
    "liderazgo": ("Reforzar las reuniones breves de equipo con los responsables",
                  "Conocer qué esperan los equipos de sus responsables en el día a día"),
    "herramientas": ("Priorizar la reparación y renovación de las herramientas más citadas",
                     "Identificar qué herramientas o equipos dificultan más el trabajo"),
    "formacion": ("Publicar una oferta de formación ligada a los nuevos procesos",
                  "Saber qué formación necesitan los equipos para su día a día"),
    "reconocimiento": ("Incorporar el reconocimiento en las reuniones de equipo",
                       "Entender cómo les gustaría que se reconociera su trabajo"),
    "seguridad": ("Revisar con prevención los puntos de riesgo señalados",
                  "Identificar las situaciones de riesgo que más preocupan"),
    "ambiente": ("Impulsar actividades que refuercen la colaboración entre equipos",
                 "Conocer qué mejoraría la relación entre compañeros"),
    "conciliacion": ("Estudiar medidas de flexibilidad compatibles con cada puesto",
                     "Saber qué medidas de flexibilidad serían más útiles"),
    "otros": ("Revisar las incidencias de instalaciones y servicios señaladas",
              "Detectar qué servicios o instalaciones conviene mejorar primero"),
}
NOMBRE_TEMA = {
    "descansos": "descansos", "turnos": "turnos", "carga_trabajo": "carga de trabajo",
    "comunicacion": "comunicación", "liderazgo": "liderazgo", "herramientas": "herramientas",
    "formacion": "formación", "reconocimiento": "reconocimiento", "seguridad": "seguridad",
    "ambiente": "ambiente", "conciliacion": "conciliación", "otros": "otros temas",
}
TEXTO_TENDENCIA = {"nuevo": "aparece como tema nuevo", "sube": "gana peso respecto al periodo anterior",
                   "estable": "se mantiene estable", "baja": "pierde peso"}


def _temas_prioritarios(analisis: dict[str, Any]) -> list[dict[str, Any]]:
    temas = [t for t in analisis.get("temas") or [] if t.get("tema") in ACCION_POR_TEMA]
    prioridad = {"nuevo": 0, "sube": 1, "estable": 2, "baja": 3}
    temas.sort(key=lambda t: (prioridad.get(t.get("tendencia"), 1), t.get("tema") == "otros",
                              -int(t.get("n", 0))))
    return temas


def _segmento_menos_representado(analisis: dict[str, Any]) -> dict[str, Any] | None:
    filas = [p for p in analisis.get("participacion") or [] if p.get("representativo") is False]
    return min(filas, key=lambda p: p.get("tasa", 1.0)) if filas else None


def _colectivo_seguimiento(analisis: dict[str, Any], encuesta: dict[str, Any]) -> str:
    colectivo = (encuesta or {}).get("colectivo")
    if colectivo in COLECTIVOS:
        return colectivo
    seg = _segmento_menos_representado(analisis)
    return seg["colectivo"] if seg and seg.get("colectivo") in COLECTIVOS else "planta"


def _accion_tema(tema: dict[str, Any]) -> dict[str, str]:
    nombre = tema["tema"]
    return {
        "titulo": ACCION_POR_TEMA[nombre][0],
        "motivo": (f"El tema {NOMBRE_TEMA[nombre]} {TEXTO_TENDENCIA.get(tema.get('tendencia'), '')} "
                   f"({tema.get('n', 0)} comentarios en este periodo). Propuesta para valorar por RRHH."),
        "tema": nombre,
    }


def _accion_participacion(seg: dict[str, Any], tema_principal: str) -> dict[str, str]:
    grupo = NOMBRE_COLECTIVO.get(seg.get("colectivo"), seg.get("colectivo", ""))
    turno = NOMBRE_TURNO.get(seg.get("turno"), "")
    quien = f"{grupo} {turno}".strip()
    return {
        "titulo": f"Reforzar la participación de {quien} con QR y quiosco en el centro",
        "motivo": (f"Solo ha respondido un {round(float(seg.get('tasa', 0)) * 100)} % de {quien} "
                   f"({seg.get('respuestas', 0)} de {seg.get('personas', 0)}): sus resultados pueden "
                   f"no estar representados. Propuesta para valorar por RRHH."),
        "tema": tema_principal,
    }


def _seguimiento(tema: str | None, colectivo: str, analisis: dict[str, Any]) -> dict[str, Any]:
    periodo = analisis.get("periodo_actual")
    if tema:
        objetivo = ACCION_POR_TEMA.get(tema, ACCION_POR_TEMA["otros"])[1]
        contexto = (f"Seguimiento del análisis{' de ' + periodo if periodo else ''}: "
                    f"el tema {NOMBRE_TEMA.get(tema, tema)} destaca en los comentarios.")
    else:
        objetivo = "Conocer cómo se sienten las personas en su día a día"
        contexto = "Seguimiento: todavía hay pocos comentarios para identificar temas."
    return {
        "objetivo": objetivo,
        "colectivo": colectivo,
        "contexto": contexto,
        "duracion_max_seg": DURACION_SEGUIMIENTO,
        "temas_prohibidos": [],
    }


def _recomendar_respaldo(analisis: dict[str, Any], encuesta: dict[str, Any]) -> dict[str, Any]:
    temas = _temas_prioritarios(analisis)
    tema_principal = temas[0]["tema"] if temas else None
    acciones = [_accion_tema(t) for t in temas[:2]]
    seg = _segmento_menos_representado(analisis)
    if seg:
        acciones.append(_accion_participacion(seg, tema_principal or "otros"))
    elif len(temas) > 2:
        acciones.append(_accion_tema(temas[2]))
    if not acciones:
        acciones = [{"titulo": "Recoger más respuestas antes de decidir",
                     "motivo": "Todavía no hay datos suficientes para proponer acciones.",
                     "tema": "otros"}]
    return {"acciones": acciones[:3],
            "seguimiento": _seguimiento(tema_principal, _colectivo_seguimiento(analisis, encuesta),
                                        analisis)}


def recomendar(analisis: dict[str, Any], encuesta: dict[str, Any]) -> dict[str, Any]:
    """Genera recomendaciones de acción y una propuesta de encuesta de seguimiento.

    Prioriza segmentos con baja representación y temas nuevos o en aumento.
    """
    analisis = analisis or {}
    base = _recomendar_respaldo(analisis, encuesta or {})
    if not hay_llm() or not analisis.get("temas"):
        return base
    try:
        resumen_datos = {
            "temas": [{k: t.get(k) for k in ("tema", "n", "tendencia", "resumen")}
                      for t in _temas_prioritarios(analisis)[:5]],
            "alertas": analisis.get("alertas") or [],
            "limites": analisis.get("limites") or [],
            "acciones_base": base["acciones"],
        }
        import json
        prompt = (_PROMPTS / "recomendar.md").read_text(encoding="utf-8")
        datos = llamar_llm_json(prompt, json.dumps(resumen_datos, ensure_ascii=False))
        nuevas = datos.get("acciones") if isinstance(datos, dict) else None
        if not isinstance(nuevas, list) or len(nuevas) != len(base["acciones"]):
            return base
        acciones = []
        for propuesta, original in zip(nuevas, base["acciones"]):
            titulo = str(propuesta.get("titulo", "")).strip()
            motivo = str(propuesta.get("motivo", "")).strip()
            acciones.append({
                "titulo": titulo if 5 <= len(titulo) <= 120 else original["titulo"],
                "motivo": motivo if 10 <= len(motivo) <= 300 else original["motivo"],
                "tema": original["tema"],  # La asignación temática procede de las reglas de negocio
            })
        return {"acciones": acciones, "seguimiento": base["seguimiento"]}
    except Exception:
        return base
