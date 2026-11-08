"""Pregunta a tus datos y preguntas sugeridas, a partir de resultados agregados.

El modelo solo recibe datos agregados (nunca comentarios individuales) y las preguntas que
buscan identificar a alguien se rechazan antes de llamarlo. Se responde en castellano, catalán
o inglés: el de la pregunta y, si no se puede saber, el de la pantalla de RRHH.
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
from . import cache_disco
from . import textos_respaldo as textos

log = logging.getLogger(__name__)

TIMEOUT_PREGUNTAR_SEG = 25
MAX_CARACTERES = 300
MAX_PALABRAS = 120
_PROMPTS = Path(__file__).resolve().parent / "prompts"
_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}

MAX_PALABRAS_SUGERENCIA = 14

AYUDA = {
    "es": ("Escribe una pregunta sobre los resultados, por ejemplo: ¿qué sector está peor y por qué? "
           "o ¿qué ha cambiado respecto al mes pasado?"),
    "ca": ("Escriu una pregunta sobre els resultats, per exemple: quin sector està pitjor i per què? "
           "o què ha canviat respecte al mes passat?"),
    "en": ("Ask a question about the results, for example: which area is doing worst and why? "
           "or what has changed since last month?"),
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
}
SIN_IA = {
    "es": "La IA no está disponible en este momento.",
    "ca": "La IA no està disponible en aquest moment.",
    "en": "AI is not available right now.",
}
RESUMEN_AUTOMATICO = {"es": "Resumen automático de los datos:", "ca": "Resum automàtic de les dades:",
                      "en": "Automatic summary of the data:"}

# Peticiones que buscan identificar o actuar sobre personas concretas. Se responde en es, ca o en,
# pero se bloquean también en portugués y chino por si alguien pregunta en esos idiomas.
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
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def detectar_idioma(texto: str, por_defecto: str | None = "es") -> str | None:
    """Idioma probable de la pregunta (es, ca o en) por sus palabras frecuentes; si no hay pistas,
    `por_defecto`."""
    palabras = re.findall(r"[a-z]+", _normalizar(texto))
    puntos = {idioma: sum(p in marcas for p in palabras) for idioma, marcas in _MARCAS_IDIOMA.items()}
    # Las palabras compartidas entre castellano y catalán (es, son, ha...) no deciden por sí solas
    mejor = max(puntos, key=lambda i: (puntos[i], i == "es"))
    return mejor if puntos[mejor] > 0 else por_defecto


def busca_identificar(pregunta: str) -> bool:
    """Indica si la pregunta busca identificar o actuar sobre una persona concreta."""
    return bool(_IDENTIFICAR.search(_normalizar(pregunta)) or _IDENTIFICAR_ZH.search(pregunta or ""))


def _respuesta(texto: str, cifras: list[str], confianza: str, origen: str) -> dict[str, Any]:
    return {"respuesta": texto, "cifras": cifras, "confianza": confianza, "origen": origen}


def _pct(valor: Any, idioma: str = "es") -> str:
    return textos.pct(float(valor), idioma) if isinstance(valor, (int, float)) else "—"


_CIFRAS = {
    "es": {"respuestas": "{n} respuestas en {periodo}",
           "no_repr": "{quien}: {pct} de participación (no representativo)",
           "tema": "{tema}: {n} comentarios ({tendencia})",
           "tendencia": {"nuevo": "nuevo", "sube": "sube", "estable": "estable", "baja": "baja"}},
    "ca": {"respuestas": "{n} respostes a {periodo}",
           "no_repr": "{quien}: {pct} de participació (no representatiu)",
           "tema": "{tema}: {n} comentaris ({tendencia})",
           "tendencia": {"nuevo": "nou", "sube": "puja", "estable": "estable", "baja": "baixa"}},
    "en": {"respuestas": "{n} responses in {periodo}",
           "no_repr": "{quien}: {pct} participation (not representative)",
           "tema": "{tema}: {n} comments ({tendencia})",
           "tendencia": {"nuevo": "new", "sube": "rising", "estable": "stable", "baja": "falling"}},
}


def _respuesta_reglas(analisis: dict[str, Any], recomendaciones: dict[str, Any] | None,
                      idioma: str) -> dict[str, Any]:
    # Sin modelo no se interpreta la pregunta: se resumen los datos clave, sin inventar nada
    f = _CIFRAS[idioma]
    cifras = []
    if analisis.get("n_respuestas"):
        cifras.append(f["respuestas"].format(n=analisis["n_respuestas"],
                                             periodo=analisis.get("periodo_actual", "")))
    for fila in analisis.get("participacion") or []:
        if fila.get("representativo") is False:
            quien = textos.quien(fila.get("colectivo", ""), fila.get("turno"), idioma)
            cifras.append(f["no_repr"].format(quien=quien[:1].upper() + quien[1:],
                                              pct=_pct(fila.get("tasa"), idioma)))
    for tema in (analisis.get("temas") or [])[:3]:
        nombre = textos.nombre("tema", tema.get("tema", ""), idioma)
        cifras.append(f["tema"].format(tema=nombre[:1].upper() + nombre[1:], n=tema.get("n"),
                                       tendencia=f["tendencia"].get(tema.get("tendencia"), "")))
    # La lectura solo se reutiliza si está en el mismo idioma
    recs = recomendaciones or {}
    lectura = (recs.get("lectura") or "") if recs.get("idioma", "es") == idioma else ""
    texto = f"{SIN_IA[idioma]} {RESUMEN_AUTOMATICO[idioma]} {lectura}".strip()
    return _respuesta(texto, cifras[:6], "baja", "reglas")


def preguntar(pregunta: str, analisis: dict[str, Any],
              recomendaciones: dict[str, Any] | None = None, idioma: str = "es") -> dict[str, Any]:
    """Responde una pregunta en lenguaje natural citando cifras de los resultados agregados.

    Responde en el idioma de la pregunta; si no se puede detectar, en `idioma` (el de la pantalla).

    Rechaza sin llamar al modelo las preguntas que buscan identificar a alguien. Límite de 25 s;
    sin modelo o si falla, devuelve un resumen de los datos sin interpretar la pregunta.
    """
    pregunta = " ".join(str(pregunta or "").split())[:MAX_CARACTERES]
    analisis = analisis or {}
    pantalla = textos.idioma_valido(idioma)
    idioma = detectar_idioma(pregunta, por_defecto=pantalla)
    if not pregunta:
        return _respuesta(AYUDA[pantalla], [], "alta", "reglas")
    if busca_identificar(pregunta):
        return _respuesta(RESPUESTA_PRIVACIDAD[idioma], [], "alta", "reglas")
    if not hay_llm():
        return _respuesta_reglas(analisis, recomendaciones, idioma)

    datos = datos_agregados(analisis)
    datos["resumenes_temas"] = {t.get("tema"): t.get("resumen")
                                for t in analisis.get("temas") or [] if t.get("resumen")}
    datos["acciones_propuestas"] = [a.get("titulo") for a in (recomendaciones or {}).get("acciones") or []]
    clave = (idioma, _normalizar(pregunta), json.dumps(datos, ensure_ascii=False, sort_keys=True))
    if clave in _CACHE:
        return _CACHE[clave]
    guardada = cache_disco.leer("preguntar", clave)
    if guardada:
        _CACHE[clave] = guardada
        return guardada

    try:
        usuario = (f"Pregunta de RRHH: {pregunta}\n\nDatos agregados (JSON):\n"
                   + json.dumps(datos, ensure_ascii=False))
        prompt = (_PROMPTS / "preguntar.md").read_text(encoding="utf-8") + textos.instruccion_idioma(idioma)
        salida = llamar_llm_json(prompt, usuario, TIMEOUT_PREGUNTAR_SEG)
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
    if resultado.get("origen") == "ia":
        cache_disco.guardar("preguntar", clave, resultado)
    return resultado


def _sugerir_con_ia(datos: dict[str, Any], idioma: str = "es") -> list[str] | None:
    prompt = (_PROMPTS / "sugerir.md").read_text(encoding="utf-8") + textos.instruccion_idioma(idioma)
    salida = llamar_llm_json(prompt, json.dumps(datos, ensure_ascii=False), segundo_plano.TIMEOUT_SEG)
    propuestas = salida.get("preguntas") if isinstance(salida, dict) else salida
    preguntas = []
    for texto in propuestas if isinstance(propuestas, list) else []:
        texto = " ".join(str(texto).split()).strip(" \"'")
        if not texto or len(texto.split()) > MAX_PALABRAS_SUGERENCIA or busca_identificar(texto):
            continue
        if not texto.endswith("?"):
            texto += "?"
        if idioma == "es" and not texto.startswith("¿"):
            texto = "¿" + texto
        elif idioma != "es":
            texto = texto.lstrip("¿")
        preguntas.append(texto)
    return preguntas[:3] if len(preguntas) >= 3 else None


def sugerir_preguntas(analisis: dict[str, Any], idioma: str = "es") -> dict[str, Any]:
    """Tres preguntas que RRHH debería hacerse con estos resultados, propuestas por el modelo
    y escritas en `idioma` (es, ca o en).

    Se calculan en segundo plano con caché por los datos. Sin modelo, o si falla, no hay
    sugerencias: nunca se devuelve una lista fija.
    """
    analisis = analisis or {}
    idioma = textos.idioma_valido(idioma)
    if not hay_llm() or not analisis.get("n_respuestas"):
        return {"preguntas": [], "origen": "ninguno"}
    if clasificacion_en_curso():
        return {"preguntas": [], "origen": "pendiente"}
    datos = datos_agregados(analisis)
    clave = ("sugerir", idioma, json.dumps(datos, ensure_ascii=False, sort_keys=True))
    estado, preguntas = segundo_plano.consultar(clave, lambda: _sugerir_con_ia(datos, idioma),
                                                prioritario=True)
    if estado == "pendiente":
        return {"preguntas": [], "origen": "pendiente"}
    return {"preguntas": preguntas, "origen": "ia"} if preguntas else {"preguntas": [], "origen": "ninguno"}
