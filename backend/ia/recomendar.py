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
from . import textos_respaldo as textos

COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
DURACION_SEGUIMIENTO = 60
TEMAS_PROHIBIDOS_SEGUIMIENTO = ["salario"]
_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Los textos (es, ca, en) están en textos_respaldo.py
ACCION_POR_TEMA = textos.ACCION_POR_TEMA["es"]


def _pct(valor: float | None, idioma: str = "es") -> str:
    return textos.pct(valor, idioma)


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


def _accion_tema(tema: dict[str, Any], idioma: str = "es") -> dict[str, str]:
    clave = tema["tema"]
    nombre = textos.nombre("tema", clave, idioma)
    pct = tema.get("pct")
    cifra = (textos.frase("cifra", idioma, n=tema.get("n", 0), pct=_pct(pct, idioma))
             + (textos.frase("cifra_antes", idioma, pct=_pct(tema.get("pct_anterior"), idioma))
                if tema.get("pct_anterior") is not None else ""))
    objetivo = (textos.frase("por_debajo", idioma, pct=_pct(pct, idioma)) if pct
                else textos.frase("en_descenso", idioma))
    tendencia = textos.TEXTO_TENDENCIA[idioma].get(tema.get("tendencia"), "")
    return {
        "titulo": textos.ACCION_POR_TEMA[idioma][clave][0],
        "motivo": textos.frase("motivo_tema", idioma, tema=nombre, tendencia=tendencia, cifra=cifra),
        "tema": clave,
        "responsable": textos.RESPONSABLE[idioma][clave],
        "plazo": textos.plazo(clave, idioma),
        "indicador": textos.frase("indicador_tema", idioma, tema=nombre, objetivo=objetivo),
    }


def _accion_participacion(seg: dict[str, Any], tema_principal: str,
                          idioma: str = "es") -> dict[str, str]:
    quien = textos.quien(seg.get("colectivo", ""), seg.get("turno"), idioma)
    return {
        "titulo": textos.frase("titulo_participacion", idioma, quien=quien),
        "motivo": textos.frase("motivo_participacion", idioma, quien=quien,
                               pct=_pct(float(seg.get("tasa", 0)), idioma),
                               r=seg.get("respuestas", 0), p=seg.get("personas", 0)),
        "tema": tema_principal,
        "responsable": textos.RESPONSABLE[idioma]["participacion"],
        "plazo": textos.plazo("participacion", idioma),
        "indicador": textos.frase("indicador_participacion", idioma, quien=quien),
    }


def _seguimiento(tema: str | None, colectivo: str, analisis: dict[str, Any],
                 idioma: str = "es") -> dict[str, Any]:
    periodo = analisis.get("periodo_actual")
    if tema:
        acciones = textos.ACCION_POR_TEMA[idioma]
        objetivo = acciones.get(tema, acciones["otros"])[1]
        contexto = textos.frase("contexto_seguimiento", idioma,
                                periodo=textos.frase("periodo", idioma, periodo=periodo) if periodo else "",
                                tema=textos.nombre("tema", tema, idioma))
    else:
        objetivo = textos.frase("objetivo_sin_temas", idioma)
        contexto = textos.frase("contexto_sin_temas", idioma)
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


def _texto_alerta(alerta: dict[str, Any], analisis: dict[str, Any], idioma: str) -> str:
    """Las alertas llegan redactadas en analisis["idioma"]; si es otro, se rehace con sus datos."""
    if analisis.get("idioma", "es") == idioma:
        return str(alerta.get("mensaje", "")).rstrip(".") + "."
    if alerta.get("tipo") == "representatividad":
        fila = next((f for f in analisis.get("participacion") or []
                     if f.get("colectivo") == alerta.get("colectivo")
                     and f.get("turno") == alerta.get("turno")), None)
        if fila:
            frase = textos.frase("motivo_participacion", idioma,
                                 quien=textos.quien(fila.get("colectivo", ""), fila.get("turno"), idioma),
                                 pct=_pct(float(fila.get("tasa", 0)), idioma),
                                 r=fila.get("respuestas", 0), p=fila.get("personas", 0))
            return frase.split(":")[0] + "."
    return ""


def _lectura_reglas(analisis: dict[str, Any], temas: list[dict[str, Any]],
                    idioma: str = "es") -> str:
    frases = []
    n = analisis.get("n_respuestas")
    if n:
        global_ = _participacion_global(analisis)
        frases.append(textos.frase("lectura_respuestas", idioma, n=n)
                      + (textos.frase("lectura_global", idioma, pct=_pct(global_, idioma))
                         if global_ else "."))
    for alerta in (analisis.get("alertas") or [])[:1]:
        texto = _texto_alerta(alerta, analisis, idioma)
        if texto.strip("."):
            frases.append(texto)
    destacados = [t for t in temas if t.get("tendencia") in ("nuevo", "sube")][:2]
    if destacados:
        partes = []
        for t in destacados:
            extra = (textos.frase("lectura_nuevo", idioma) if t.get("tendencia") == "nuevo"
                     else textos.frase("lectura_antes", idioma, pct=_pct(t.get("pct_anterior"), idioma)))
            partes.append(textos.frase("lectura_tema", idioma, tema=textos.nombre("tema", t["tema"], idioma),
                                       pct=_pct(t.get("pct"), idioma), extra=extra))
        frases.append(textos.frase("lectura_destacados", idioma,
                                   temas=textos.frase("y", idioma).join(partes)))
    return " ".join(frases) or textos.frase("sin_datos", idioma)


def _recomendar_respaldo(analisis: dict[str, Any], encuesta: dict[str, Any],
                         idioma: str = "es") -> dict[str, Any]:
    temas = _temas_prioritarios(analisis)
    tema_principal = temas[0]["tema"] if temas else None
    acciones = [_accion_tema(t, idioma) for t in temas[:2]]
    seg = _segmento_menos_representado(analisis)
    if seg:
        acciones.append(_accion_participacion(seg, tema_principal or "otros", idioma))
    elif len(temas) > 2:
        acciones.append(_accion_tema(temas[2], idioma))
    if not acciones:
        acciones = [{"titulo": textos.frase("titulo_mas_respuestas", idioma),
                     "motivo": textos.frase("motivo_mas_respuestas", idioma),
                     "tema": "otros", "responsable": textos.RESPONSABLE[idioma]["conciliacion"],
                     "plazo": textos.plazo("participacion", idioma),
                     "indicador": textos.frase("indicador_mas_respuestas", idioma)}]
    return {
        "origen": "reglas",
        "idioma": idioma,
        "lectura": _lectura_reglas(analisis, temas, idioma),
        "acciones": acciones[:3],
        "seguimiento": _seguimiento(tema_principal, _colectivo_seguimiento(analisis, encuesta),
                                    analisis, idioma),
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
    return {"origen": "ia", "idioma": base.get("idioma", "es"), "lectura": respuesta["lectura"].strip(),
            "acciones": acciones, "seguimiento": seguimiento}


def _recomendar_con_ia(datos: dict[str, Any], base: dict[str, Any], idioma: str) -> dict[str, Any] | None:
    prompt = ((_PROMPTS / "recomendar_completo.md").read_text(encoding="utf-8")
              + textos.instruccion_idioma(idioma))
    respuesta = llamar_llm_json(prompt, json.dumps(datos, ensure_ascii=False),
                                segundo_plano.TIMEOUT_SEG)
    return _validar_modelo(respuesta, base)


def recomendar(analisis: dict[str, Any], encuesta: dict[str, Any], idioma: str = "es") -> dict[str, Any]:
    """Devuelve lectura ejecutiva, 2-3 acciones con responsable, plazo e indicador y seguimiento.

    Todo redactado en `idioma` (es, ca o en): el de la pantalla de RRHH.
    origen ia (del modelo), pendiente (el modelo trabaja; se devuelve la versión por reglas, que
    la pantalla no muestra) o reglas (no hay modelo o ha fallado).
    """
    idioma = textos.idioma_valido(idioma)
    analisis = analisis or {}
    base = _recomendar_respaldo(analisis, encuesta or {}, idioma)
    if not hay_llm() or not (analisis.get("n_respuestas") or analisis.get("temas")):
        return base
    # Mientras se clasifican los comentarios los temas cambian: se espera a que terminen
    if clasificacion_en_curso():
        return {**base, "origen": "pendiente"}
    datos = datos_agregados(analisis)
    clave = ("recomendar", idioma, json.dumps(datos, ensure_ascii=False, sort_keys=True))
    estado, valor = segundo_plano.consultar(clave, lambda: _recomendar_con_ia(datos, base, idioma))
    if estado == "pendiente":
        return {**base, "origen": "pendiente"}
    return valor or base
