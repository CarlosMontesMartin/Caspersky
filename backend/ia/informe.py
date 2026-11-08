"""Pregunta a tus datos y preguntas sugeridas, a partir de resultados agregados.

El modelo solo recibe datos agregados (nunca comentarios individuales) y las preguntas que
buscan identificar a alguien se rechazan antes de llamarlo, en castellano, catalán, inglés,
portugués o chino.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from . import segundo_plano
from .analizar import clasificacion_en_curso
from .llm import hay_llm, llamar_llm_json
from .recomendar import datos_agregados

log = logging.getLogger(__name__)

TIMEOUT_PREGUNTAR_SEG = 25
MAX_CARACTERES = 300
MAX_PALABRAS = 120
_PROMPTS = Path(__file__).resolve().parent / "prompts"
_CACHE: dict[tuple[str, str], dict[str, Any]] = {}

MAX_PALABRAS_SUGERENCIA = 14

AYUDA = {
    "es": ("Escribe una pregunta sobre los resultados, por ejemplo: ¿qué sector está peor y por qué? "
           "o ¿qué ha cambiado respecto al mes pasado?"),
    "ca": ("Escriu una pregunta sobre els resultats, per exemple: quin sector està pitjor i per què? "
           "o què ha canviat respecte al mes passat?"),
    "en": ("Ask a question about the results, for example: which area is doing worst and why? "
           "or what has changed since last month?"),
    "pt": ("Escreve uma pergunta sobre os resultados, por exemplo: que setor está pior e porquê? "
           "ou o que mudou em relação ao mês passado?"),
    "zh": "请就结果提一个问题，例如：哪个部门情况最差，为什么？或者与上个月相比有什么变化？",
}
RESPUESTA_PRIVACIDAD = {
    "es": ("Esta herramienta solo trabaja con resultados agregados: no puede identificar a nadie, "
           "decir qué ha respondido una persona ni servir para tomar decisiones sobre personas "
           "concretas. Puedes preguntar por colectivos, turnos o temas."),
    "ca": ("Aquesta eina només treballa amb resultats agregats: no pot identificar ningú, dir què ha "
           "respost una persona ni servir per prendre decisions sobre persones concretes. Pots "
           "preguntar per col·lectius, torns o temes."),
    "en": ("This tool only works with aggregated results: it cannot identify anyone, reveal what a "
           "person answered or support decisions about specific people. You can ask about groups, "
           "shifts or topics."),
    "pt": ("Esta ferramenta só trabalha com resultados agregados: não pode identificar ninguém, dizer o "
           "que uma pessoa respondeu nem servir para tomar decisões sobre pessoas concretas. Podes "
           "perguntar por grupos, turnos ou temas."),
    "zh": ("本工具只处理汇总结果：不能识别任何人，不能透露某个人的回答，也不能用于针对具体个人的决定。"
           "你可以按群体、班次或主题提问。"),
}
SIN_IA = {
    "es": "La IA no está disponible en este momento.",
    "ca": "La IA no està disponible en aquest moment.",
    "en": "AI is not available right now.",
    "pt": "A IA não está disponível neste momento.",
    "zh": "人工智能暂时不可用。",
}
RESUMEN_AUTOMATICO = {"es": "Resumen automático de los datos:", "ca": "Resum automàtic de les dades:",
                      "en": "Automatic summary of the data:", "pt": "Resumo automático dos dados:",
                      "zh": "数据自动摘要："}

# Peticiones que buscan identificar o actuar sobre personas concretas (castellano, catalán, inglés)
_IDENTIFICAR = re.compile(
    r"\bquien(es)?\b|\bnombres?\b(?! (del?|de la) (tema|sector|colectivo|turno|encuesta|pregunta))"
    r"|\bdni\b|\bnie\b|\bcorreos?\b|\be-?mails?\b|\btelefonos?\b"
    r"|que (ha|han) (dicho|escrito|respondido|contestado)|que dijo|quien dijo"
    r"|\bdespedi|\bdespido|\bsancion|\bcastig|\bidentifica|persona concreta|empleado concreto"
    r"|\bchivat|\bdelat"
    # Catalán
    r"|\bqui\b|\bnoms?\b(?! del? (tema|sector|col.lectiu|torn))|\bcorreu\b|\btelefon\b"
    r"|que (ha|han) dit|\bacomiad|\bsancion|\bcastiga"
    # Inglés
    r"|\bwho\b|\bwhose\b|\bnames?\b(?! of the (topic|area|group|shift|survey))|\bphone\b"
    r"|\bfire\b|\bdismiss|\bsack\b|\bpunish|\bsanction|\bidentify|what did \w+ (say|write)"
    r"|which (employee|person|worker)"
    # Portugués
    r"|\bquem\b|\bnomes?\b(?! do (tema|setor|grupo|turno))|\btelefone\b|que (disse|escreveu)"
    r"|\bdemitir|\bdespedir|\bpunir|\bidentificar")

# El chino no separa palabras con espacios: se buscan los caracteres directamente
_IDENTIFICAR_ZH = re.compile(r"谁|名字|姓名|身份|电话|邮箱|电子邮件|说了什么|写了什么|开除|解雇|辞退|处罚|惩罚|"
                             r"哪个员工|哪位员工|哪个人")

# Palabras frecuentes de cada idioma para adivinar el de la pregunta
_MARCAS_IDIOMA = {
    "es": set("que quien quienes cual cuales por el la los las del estan peor mejor turno noche hay y "
              "como respecto mes pasado se queja quejan dicho nombres despedir algun alguien "
              "es son tema temas".split()),
    "ca": set("qui quin quina quins quines per i els les dels amb pitjor millor torn nit hi ha queixat "
              "queixa algu noms dona m acomiadar respecte passat aquest aquesta col lectiu es son "
              "podem han dit".split()),
    "en": set("what which who whom why how the is are does did has have worst best shift night month "
              "complained complain people anyone someone names fire said say area topic since last "
              "can we".split()),
    "pt": set("quem qual quais pior melhor noite nao sao voce mudou setor dos das em uma um isso houve "
              "porque funcionarios turno mes passado ha quanto esta queixou queixa queixaram alguem "
              "demitir ninguem tambem voces".split()),
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def detectar_idioma(texto: str) -> str:
    """Idioma probable de la pregunta: es, ca, en, pt o zh (caracteres chinos o palabras frecuentes)."""
    if re.search(r"[\u4e00-\u9fff]", texto or ""):
        return "zh"
    palabras = re.findall(r"[a-z]+", _normalizar(texto))
    puntos = {idioma: sum(p in marcas for p in palabras) for idioma, marcas in _MARCAS_IDIOMA.items()}
    # Las palabras compartidas entre castellano y catalán (es, son, ha...) no deciden por sí solas
    mejor = max(puntos, key=lambda i: (puntos[i], i == "es"))
    return mejor if puntos[mejor] > 0 else "es"


def busca_identificar(pregunta: str) -> bool:
    """Indica si la pregunta busca identificar o actuar sobre una persona concreta."""
    return bool(_IDENTIFICAR.search(_normalizar(pregunta)) or _IDENTIFICAR_ZH.search(pregunta or ""))


def _respuesta(texto: str, cifras: list[str], confianza: str, origen: str) -> dict[str, Any]:
    return {"respuesta": texto, "cifras": cifras, "confianza": confianza, "origen": origen}


def _pct(valor: Any) -> str:
    return f"{float(valor) * 100:.0f} %" if isinstance(valor, (int, float)) else "—"


def _respuesta_reglas(analisis: dict[str, Any], recomendaciones: dict[str, Any] | None,
                      idioma: str) -> dict[str, Any]:
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
    texto = f"{SIN_IA[idioma]} {RESUMEN_AUTOMATICO[idioma]} {lectura}".strip()
    return _respuesta(texto, cifras[:6], "baja", "reglas")


def preguntar(pregunta: str, analisis: dict[str, Any],
              recomendaciones: dict[str, Any] | None = None) -> dict[str, Any]:
    """Responde una pregunta en lenguaje natural citando cifras de los resultados agregados.

    Rechaza sin llamar al modelo las preguntas que buscan identificar a alguien. Límite de 25 s;
    sin modelo o si falla, devuelve un resumen de los datos sin interpretar la pregunta.
    """
    pregunta = " ".join(str(pregunta or "").split())[:MAX_CARACTERES]
    analisis = analisis or {}
    idioma = detectar_idioma(pregunta)
    if not pregunta:
        return _respuesta(AYUDA["es"], [], "alta", "reglas")
    if busca_identificar(pregunta):
        return _respuesta(RESPUESTA_PRIVACIDAD[idioma], [], "alta", "reglas")
    if not hay_llm():
        return _respuesta_reglas(analisis, recomendaciones, idioma)

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
        return _respuesta_reglas(analisis, recomendaciones, idioma)
    _CACHE[clave] = resultado
    return resultado


def _sugerir_con_ia(datos: dict[str, Any]) -> list[str] | None:
    salida = llamar_llm_json((_PROMPTS / "sugerir.md").read_text(encoding="utf-8"),
                             json.dumps(datos, ensure_ascii=False), segundo_plano.TIMEOUT_SEG)
    propuestas = salida.get("preguntas") if isinstance(salida, dict) else salida
    preguntas = []
    for texto in propuestas if isinstance(propuestas, list) else []:
        texto = " ".join(str(texto).split()).strip(" \"'")
        if not texto or len(texto.split()) > MAX_PALABRAS_SUGERENCIA or busca_identificar(texto):
            continue
        if not texto.endswith("?"):
            texto += "?"
        if not texto.startswith("¿"):
            texto = "¿" + texto
        preguntas.append(texto)
    return preguntas[:3] if len(preguntas) >= 3 else None


def sugerir_preguntas(analisis: dict[str, Any]) -> dict[str, Any]:
    """Tres preguntas que RRHH debería hacerse con estos resultados, propuestas por el modelo.

    Se calculan en segundo plano con caché por los datos. Sin modelo, o si falla, no hay
    sugerencias: nunca se devuelve una lista fija.
    """
    analisis = analisis or {}
    if not hay_llm() or not analisis.get("n_respuestas"):
        return {"preguntas": [], "origen": "ninguno"}
    if clasificacion_en_curso():
        return {"preguntas": [], "origen": "pendiente"}
    datos = datos_agregados(analisis)
    clave = ("sugerir", json.dumps(datos, ensure_ascii=False, sort_keys=True))
    estado, preguntas = segundo_plano.consultar(clave, lambda: _sugerir_con_ia(datos))
    if estado == "pendiente":
        return {"preguntas": [], "origen": "pendiente"}
    return {"preguntas": preguntas, "origen": "ia"} if preguntas else {"preguntas": [], "origen": "ninguno"}
