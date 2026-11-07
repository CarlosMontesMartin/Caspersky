"""Recomendaciones de acción, lectura ejecutiva y encuesta de seguimiento.

Responde al momento con la versión por reglas y pide al modelo, en segundo plano, una versión
redactada a partir de datos agregados. Si el modelo falla, se queda la versión por reglas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import segundo_plano
from .analizar import TEMAS, clasificacion_en_curso
from .llm import hay_llm, llamar_llm_json

COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
NOMBRE_COLECTIVO = {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                    "oficina": "oficina", "manager": "managers"}
NOMBRE_TURNO = {"manana": "de mañana", "tarde": "de tarde", "noche": "de noche"}
DURACION_SEGUIMIENTO = 60
TEMAS_PROHIBIDOS_SEGUIMIENTO = ["salario"]
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


# Quién lo lleva y en cuánto tiempo, por tema
RESPONSABLE_PLAZO: dict[str, tuple[str, str]] = {
    "descansos": ("Jefes de turno y RRHH", "2 semanas"),
    "turnos": ("Dirección de planta y RRHH", "1 mes"),
    "carga_trabajo": ("Responsables de área", "1 mes"),
    "comunicacion": ("RRHH y Comunicación interna", "1 semana"),
    "liderazgo": ("Responsables de equipo", "1 mes"),
    "herramientas": ("Mantenimiento e IT", "1 mes"),
    "formacion": ("RRHH (Desarrollo)", "2 meses"),
    "reconocimiento": ("Responsables de equipo", "1 mes"),
    "seguridad": ("Prevención de riesgos", "1 semana"),
    "ambiente": ("Responsables de equipo y RRHH", "1 mes"),
    "conciliacion": ("RRHH", "2 meses"),
    "otros": ("Servicios generales", "1 mes"),
}


def _pct(valor: float | None) -> str:
    return "—" if valor is None else f"{valor * 100:.0f} %"


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
    responsable, plazo = RESPONSABLE_PLAZO[nombre]
    pct = tema.get("pct")
    cifra = (f"{tema.get('n', 0)} comentarios, {_pct(pct)} del total"
             + (f"; antes {_pct(tema.get('pct_anterior'))}" if tema.get("pct_anterior") is not None
                else ""))
    objetivo = f"por debajo del {_pct(pct)}" if pct else "en descenso"
    return {
        "titulo": ACCION_POR_TEMA[nombre][0],
        "motivo": (f"El tema {NOMBRE_TEMA[nombre]} {TEXTO_TENDENCIA.get(tema.get('tendencia'), '')} "
                   f"({cifra}). Propuesta para valorar por RRHH."),
        "tema": nombre,
        "responsable": responsable,
        "plazo": plazo,
        "indicador": f"Peso de {NOMBRE_TEMA[nombre]} en los comentarios {objetivo} en el seguimiento",
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
        "responsable": "RRHH y jefes de turno",
        "plazo": "2 semanas",
        "indicador": f"Participación de {quien} de al menos el 20 %",
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
        "colectivos": [colectivo],
        "colectivo": colectivo,
        "contexto": contexto,
        "duracion_max_seg": DURACION_SEGUIMIENTO,
        "temas_prohibidos": list(TEMAS_PROHIBIDOS_SEGUIMIENTO),
    }


def _participacion_global(analisis: dict[str, Any]) -> float | None:
    if analisis.get("participacion_global") is not None:
        return analisis["participacion_global"]
    filas = analisis.get("participacion") or []
    personas = sum(f.get("personas", 0) for f in filas)
    return sum(f.get("respuestas", 0) for f in filas) / personas if personas else None


def _lectura_reglas(analisis: dict[str, Any], temas: list[dict[str, Any]]) -> str:
    frases = []
    n = analisis.get("n_respuestas")
    if n:
        global_ = _participacion_global(analisis)
        frases.append(f"Han respondido {n} personas"
                      + (f", un {_pct(global_)} de la plantilla consultada." if global_ else "."))
    alertas = analisis.get("alertas") or []
    if alertas:
        frases.append(str(alertas[0].get("mensaje", "")).rstrip(".") + ".")
    destacados = [t for t in temas if t.get("tendencia") in ("nuevo", "sube")][:2]
    if destacados:
        partes = [f"{NOMBRE_TEMA[t['tema']]} ({_pct(t.get('pct'))} de los comentarios"
                  + (", tema nuevo)" if t.get("tendencia") == "nuevo" else
                     f", antes {_pct(t.get('pct_anterior'))})") for t in destacados]
        frases.append("Ganan peso " + " y ".join(partes) + ".")
    return " ".join(frases) or "Todavía no hay datos suficientes para una lectura de resultados."


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
                     "tema": "otros", "responsable": "RRHH", "plazo": "2 semanas",
                     "indicador": "Al menos 5 respuestas por segmento"}]
    return {
        "origen": "reglas",
        "lectura": _lectura_reglas(analisis, temas),
        "acciones": acciones[:3],
        "seguimiento": _seguimiento(tema_principal, _colectivo_seguimiento(analisis, encuesta),
                                    analisis),
    }


def datos_agregados(analisis: dict[str, Any]) -> dict[str, Any]:
    """Resumen del análisis sin ningún comentario individual: lo único que ve el modelo."""
    textos = {p.get("id"): p.get("texto") for p in analisis.get("preguntas") or []}

    def medias(clave: str) -> list[dict[str, Any]]:
        return [{"pregunta": textos.get(m.get("pregunta"), m.get("pregunta")),
                 "colectivo": m.get("colectivo"), "media": m.get("media"), "n": m.get("n")}
                for m in analisis.get(clave) or []]

    return {
        "periodo_actual": analisis.get("periodo_actual"),
        "periodo_anterior": analisis.get("periodo_anterior"),
        "n_respuestas": analisis.get("n_respuestas"),
        "n_anterior": analisis.get("n_anterior"),
        "colectivos": analisis.get("colectivos"),
        "participacion_global": _participacion_global(analisis),
        "participacion": [{k: f.get(k) for k in ("colectivo", "turno", "respuestas", "personas",
                                                 "tasa", "representativo")}
                          for f in analisis.get("participacion") or []],
        "medias": medias("medias"),
        "medias_anterior": medias("medias_anterior"),
        "temas": [{k: t.get(k) for k in ("tema", "n", "pct", "pct_anterior", "tendencia")}
                  for t in analisis.get("temas") or []],
        "alertas": [a.get("mensaje") for a in analisis.get("alertas") or []],
        "limites": analisis.get("limites") or [],
    }


def _texto_valido(valor: Any, minimo: int, maximo: int) -> bool:
    return isinstance(valor, str) and minimo <= len(valor.strip()) <= maximo


def _validar_modelo(respuesta: Any, base: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(respuesta, dict) or not _texto_valido(respuesta.get("lectura"), 40, 800):
        return None
    acciones = []
    for a in respuesta.get("acciones") or []:
        if not isinstance(a, dict):
            continue
        tema = str(a.get("tema", "")).strip().lower()
        if (tema in TEMAS and _texto_valido(a.get("titulo"), 5, 120)
                and _texto_valido(a.get("motivo"), 10, 400) and re.search(r"\d", a["motivo"])
                and _texto_valido(a.get("responsable"), 2, 80)
                and _texto_valido(a.get("plazo"), 2, 40)
                and _texto_valido(a.get("indicador"), 5, 200)):
            acciones.append({"titulo": a["titulo"].strip(), "motivo": a["motivo"].strip(),
                             "tema": tema, "responsable": a["responsable"].strip(),
                             "plazo": a["plazo"].strip(), "indicador": a["indicador"].strip()})
    if not 2 <= len(acciones) <= 3:
        return None

    seguimiento = dict(base["seguimiento"])
    propuesta = respuesta.get("seguimiento")
    if isinstance(propuesta, dict):
        colectivos = [c for c in COLECTIVOS if c in (propuesta.get("colectivos") or [])]
        if _texto_valido(propuesta.get("objetivo"), 10, 200) and colectivos:
            seguimiento.update(
                objetivo=propuesta["objetivo"].strip(), colectivos=colectivos,
                colectivo=colectivos[0] if len(colectivos) == 1 else "varios",
                contexto=(propuesta.get("contexto") or seguimiento["contexto"]).strip()[:300])
    return {"origen": "ia", "lectura": respuesta["lectura"].strip(), "acciones": acciones,
            "seguimiento": seguimiento}


def _recomendar_con_ia(datos: dict[str, Any], base: dict[str, Any]) -> dict[str, Any] | None:
    prompt = (_PROMPTS / "recomendar_completo.md").read_text(encoding="utf-8")
    respuesta = llamar_llm_json(prompt, json.dumps(datos, ensure_ascii=False),
                                segundo_plano.TIMEOUT_SEG)
    return _validar_modelo(respuesta, base)


def recomendar(analisis: dict[str, Any], encuesta: dict[str, Any]) -> dict[str, Any]:
    """Devuelve lectura ejecutiva, 2-3 acciones con responsable, plazo e indicador y seguimiento.

    Al momento, la versión por reglas (origen reglas). Con modelo, lanza en segundo plano la
    versión del modelo y la devuelve (origen ia) en cuanto está lista y es válida.
    """
    analisis = analisis or {}
    base = _recomendar_respaldo(analisis, encuesta or {})
    # Mientras se clasifican los comentarios los temas cambian: se espera a que terminen
    if not hay_llm() or not analisis.get("temas") or clasificacion_en_curso():
        return base
    datos = datos_agregados(analisis)
    clave = ("recomendar", json.dumps(datos, ensure_ascii=False, sort_keys=True))
    return segundo_plano.obtener(clave, lambda: _recomendar_con_ia(datos, base)) or base
