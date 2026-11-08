"""Clasificación temática, generación de resúmenes y cálculo de tendencias de comentarios.

Las palabras clave clasifican al instante. Con modelo, todos los comentarios se clasifican
además en segundo plano y, en cuanto hay resultado, sustituye al de las palabras clave.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any

from . import segundo_plano, textos_respaldo
from .llm import hay_llm, llamar_llm_json

log = logging.getLogger(__name__)

TEMAS = [
    "descansos", "turnos", "carga_trabajo", "comunicacion", "liderazgo",
    "herramientas", "formacion", "reconocimiento", "seguridad", "ambiente",
    "conciliacion", "otros",
]
UMBRAL_MINIMO = 5
TAMANO_LOTE = 25  # Lotes pequeños para que cada llamada quede lejos del timeout de 30 s
MAX_MUESTRA_RESUMEN = 30

_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Evita llamadas repetidas durante la sesión del servidor
_CACHE_IA: dict[str, str] = {}      # Texto -> tema asignado por el modelo
_EN_CURSO: set[str] = set()         # Textos en un lote que aún no ha terminado
_FALLIDOS: dict[str, float] = {}    # Texto -> momento del fallo, para no reintentar en bucle
_BLOQUEO = threading.Lock()
REINTENTO_FALLIDOS_SEG = 120

# Raíces sin tildes, en castellano y catalán. Las que empiezan por \\b son expresiones regulares.
PALABRAS_CLAVE: dict[str, list[str]] = {
    "descansos": ["descans", "pausa", "desconect", "desconnect", "recuper", "agotad",
                  "seure", "bano tranquil", "comer", "parar", "tomar algo", "10 min", "esgotat"],
    "turnos": ["turno", "\\btorn", "rotaci", "rotatiu", "cuadrante", "quadrant", "horarios cambian",
               "horari canvia", "calendario", "de noche", "\\bnit\\b"],
    "carga_trabajo": ["carga", "carrega", "abasto", "falta personal", "falta de gente", "menos gente",
                      "menys gent", "mas personal", "mas gente", "ritmo", "tareas", "volumen",
                      "picos", "limite", "desbordat", "mans", "refuerzo", "demasiado trabajo",
                      "mas faena", "capacidad", "no crece", "produccion sube", "ritme", "\\bsom pocs",
                      "no arribem", "massa feina", "poca gent"],
    "comunicacion": ["comunic", "informa", "avisa", "avisen", "avisar", "enteramos", "entere",
                     "rumor", "explicacion", "explicarme", "canal oficial", "wasa", "whatsapp",
                     "ens van dir", "no ens van", "nos dijo", "nadie nos", "oficial", "dijeron",
                     "de un dia para otro", "de un dia pa otro", "sin preguntar", "comunicat",
                     "assabent"],
    "liderazgo": ["jefe", "\\bcaps\\b", "mando", "responsable", "encargad", "encarreg", "lideraz",
                  "lideratge", "superior", "feedback", "decisiones", "escucha", "escolta", "cercania"],
    "herramientas": ["herramient", "\\beines\\b", "\\beina\\b", "maquin", "software", "sistema se", "tablet",
                     "wifi", "portatil", "plataforma", "ordenador", "carretilla", "material",
                     "tecnolog", "bugs", "\\bapp\\b", "aplicacion", "actualitzar", "softw", "lentisim",
                     "programa nou", "s'espatlla"],
    "formacion": ["formaci", "curso", "\\bcurs\\b", "aprend", "carrera", "crecer", "creixer", "mentori",
                  "desenvolupament", "promocion", "oportunidad", "sin explicarnos", "linea nueva"],
    "reconocimiento": ["reconoc", "reconeix", "valora", "un gracias", "\\bgracies", "invisible", "celebr",
                       "esfuerzo", "nadie lo", "logros", "solo te dicen", "algo bien", "da igual lo"],
    "seguridad": ["segur", "peligr", "\\bepi", "senaliz", "extintor", "emergencia", "evacua",
                  "resbal", "rellisca", "cables", "ilumina", "prevenci", "ergonom", "botiquin", "riesgo",
                  "simulacro", "visibilidad", "accident", "sortides", "formacion en prevencion"],
    "ambiente": ["ambiente", "ambient", "companer", "companys", "grupito", "tension", "rollo",
                 "rotllo", "mal humor", "se ayuda", "como equipo"],
    "conciliacion": ["concilia", "hijos", "ninos", "nens", "famili", "flexib", "teletrabajo",
                     "vida social", "vida personal", "\\bcole\\b", "escola", "compagin", "familiar",
                     "veo a mis", "recoger a mi", "salir antes", "mi hij"],
    "otros": ["comedor", "menjador", "parking", "aparcament", "maquina de cafe", "cafe", "calefaccion",
              "transporte", "uniforme",
              "vestuario", "nada especial", "res a dir", "todo bien", "tot be", "frio", "calor"],
}

# Inglés (v5): mismas reglas; las palabras cortas, con límite de palabra para no confundirse
PALABRAS_CLAVE_EN: dict[str, list[str]] = {
    "descansos": ["\\brest\\b", "\\bresting", "\\bbreaks?\\b", "tired", "exhaust", "worn out",
                  "\\blunch", "switch off", "sit down", "recover"],
    "turnos": ["\\bshifts?\\b", "\\brota\\b", "\\brotas\\b", "schedul", "night shift", "roster"],
    "carga_trabajo": ["workload", "understaff", "short-staffed", "short staffed", "\\bstaff\\b",
                      "too much work", "\\bpace\\b", "overload", "overwhelm", "more people",
                      "so few people", "extra hands", "\\bpeaks?\\b"],
    "comunicacion": ["\\btold\\b", "\\btell us", "\\binform", "communicat", "\\bnotice\\b",
                     "\\brumou?rs?\\b", "found out", "find out", "\\bannounce", "nobody explain"],
    "liderazgo": ["\\bboss", "\\bmanager", "supervisor", "\\blisten", "\\bleader", "team lead",
                  "management"],
    "herramientas": ["\\btools?\\b", "machine", "equipment", "forklift", "laptop", "computer",
                     "\\bscanner", "\\bsystem", "\\bbreaks? down", "crash"],
    "formacion": ["training", "\\bcourses?\\b", "career", "promotion", "\\blearn", "\\bgrow\\b",
                  "\\bskills?\\b"],
    "reconocimiento": ["recogni", "\\bthank", "valued", "appreciat", "unnoticed", "nobody notices",
                       "\\bcredit\\b", "\\bpraise"],
    "seguridad": ["safety", "\\bsafe\\b", "danger", "\\bppe\\b", "hazard", "injur", "\\brisks?\\b",
                  "helmet", "slipp"],
    "ambiente": ["\\bteam\\b", "colleague", "atmosphere", "coworker", "co-worker", "workmate",
                 "\\bmood\\b", "each other"],
    "conciliacion": ["family", "\\bkids?\\b", "children", "work-life", "work life", "from home",
                     "remote", "childcare", "\\bschool"],
    "otros": ["canteen", "\\bcoffee", "heating", "\\bcold\\b", "\\bhot\\b", "locker",
              "nothing special", "all good", "all fine"],
}
for _tema, _claves in PALABRAS_CLAVE_EN.items():
    PALABRAS_CLAVE[_tema] = PALABRAS_CLAVE[_tema] + _claves

_PATRONES = {
    tema: [re.compile(p if p.startswith("\\b") else re.escape(p)) for p in claves]
    for tema, claves in PALABRAS_CLAVE.items()
}

# Descripción de cada tema en es, ca y en (textos_respaldo.py)
DESCRIPCION_TEMA = textos_respaldo.DESCRIPCION_TEMA["es"]


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


# Turnos suele ser el contexto, no el tema: si aparece otro tema, prevalece
TEMAS_CONTEXTO = {"turnos"}


def clasificar_por_palabras(texto: str) -> str:
    """Clasifica un comentario mediante palabras clave; sin coincidencias devuelve otros."""
    return _tema_por_palabras(texto) or "otros"


def _tema_por_palabras(texto: str) -> str | None:
    # Prioriza la primera coincidencia en el texto y, en la misma posición, la más larga
    t = _normalizar(texto)
    mejor, mejor_clave = None, None
    for tema, patrones in _PATRONES.items():
        coincidencias = [(m.start(), -(m.end() - m.start())) for p in patrones for m in p.finditer(t)]
        if not coincidencias:
            continue
        clave = (tema in TEMAS_CONTEXTO, *min(coincidencias), -len(coincidencias))
        if mejor_clave is None or clave < mejor_clave:
            mejor, mejor_clave = tema, clave
    return mejor


def _leer_prompt(nombre: str) -> str:
    ruta = _PROMPTS / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


_ALIAS_TEMA = {"carga": "carga_trabajo", "carga_de_trabajo": "carga_trabajo",
               "comunicaciones": "comunicacion", "formaciones": "formacion",
               "herramienta": "herramientas", "turno": "turnos", "descanso": "descansos",
               "otro": "otros"}


def _normalizar_tema(valor) -> str | None:
    if isinstance(valor, dict):
        valor = valor.get("tema") or valor.get("categoria") or valor.get("topic")
    if not isinstance(valor, str):
        return None
    clave = re.sub(r"[\s\-]+", "_", _normalizar(valor).strip(" .\"'"))
    clave = _ALIAS_TEMA.get(clave, clave)
    return clave if clave in TEMAS else None


def _extraer_temas(datos, n: int) -> list[str | None]:
    # Los modelos no siempre respetan el formato: se aceptan lista, {"temas": [...]}
    # o un diccionario numerado {"1": "tema", ...}
    if isinstance(datos, dict):
        for clave in ("temas", "categorias", "resultados", "clasificacion"):
            if clave in datos:
                datos = datos[clave]
                break
    if isinstance(datos, dict):
        try:
            datos = [v for _, v in sorted(datos.items(), key=lambda kv: int(kv[0]))]
        except (TypeError, ValueError):
            datos = list(datos.values())
    if not isinstance(datos, list) or len(datos) != n:
        recibidos = len(datos) if isinstance(datos, list) else type(datos).__name__
        raise ValueError(f"se esperaban {n} temas y llegaron {recibidos}")
    return [_normalizar_tema(v) for v in datos]


def _usuario_clasificar(lote: list[str]) -> str:
    return (f"Temas permitidos: {', '.join(TEMAS)}\n\n"
            f"Clasifica estos {len(lote)} comentarios. Devuelve exactamente {len(lote)} temas "
            f"en el mismo orden, con el formato {{\"temas\": [...]}}.\n\n"
            + "\n".join(f"{i}. {txt}" for i, txt in enumerate(lote, start=1)))


def _clasificar_lote_ia(lote: list[str]) -> dict[str, str]:
    # Devuelve solo lo que el modelo ha clasificado con un tema válido
    try:
        datos = llamar_llm_json(_leer_prompt("clasificar.md"), _usuario_clasificar(lote),
                                segundo_plano.TIMEOUT_SEG)
        resultado = {txt: tema for txt, tema in zip(lote, _extraer_temas(datos, len(lote))) if tema}
    except Exception as error:
        log.warning("Lote de %d comentarios sin clasificar por el modelo: %s", len(lote), error)
        resultado = {}
    with _BLOQUEO:
        _CACHE_IA.update(resultado)
        ahora = time.monotonic()
        for txt in lote:
            _EN_CURSO.discard(txt)
            if txt not in resultado:
                _FALLIDOS[txt] = ahora
    return resultado


def clasificar_comentarios(textos: list[str]) -> list[str]:
    """Asigna a cada comentario un tema de la lista cerrada, en el mismo orden.

    Responde al momento: usa el tema del modelo si ya está y, si no, el de las palabras clave.
    Con modelo, lanza en segundo plano lotes de 25 con los comentarios que aún no tiene.
    """
    if hay_llm():
        ahora = time.monotonic()
        with _BLOQUEO:
            nuevos = sorted({t for t in textos if t and t not in _CACHE_IA and t not in _EN_CURSO
                             and ahora - _FALLIDOS.get(t, -1e9) > REINTENTO_FALLIDOS_SEG})
            _EN_CURSO.update(nuevos)
        for i in range(0, len(nuevos), TAMANO_LOTE):
            lote = nuevos[i:i + TAMANO_LOTE]
            segundo_plano.obtener(("clasificar", hash(tuple(lote))),
                                  lambda lote=lote: _clasificar_lote_ia(lote))
    return [_CACHE_IA.get(t) or clasificar_por_palabras(t) for t in textos]


def estado_clasificacion(textos: list[str]) -> dict[str, int]:
    """Cuántos comentarios distintos hay y cuántos tienen ya el tema asignado por el modelo."""
    unicos = {t for t in textos if t}
    return {"total": len(unicos), "por_ia": sum(1 for t in unicos if t in _CACHE_IA)}


def clasificacion_en_curso() -> bool:
    """Indica si quedan lotes de comentarios pendientes de clasificar por el modelo."""
    with _BLOQUEO:
        return bool(_EN_CURSO)


def _resumen_respaldo(tema: str, n: int, idioma: str = "es") -> str:
    return textos_respaldo.resumen_respaldo(tema, n, idioma)


def resumir_tema(tema: str, textos: list[str], idioma: str = "es") -> str:
    """Devuelve un resumen breve y anónimo de los comentarios de un tema, escrito en `idioma`."""
    return resumir_tema_con_origen(tema, textos, idioma)[0]


def resumir_tema_con_origen(tema: str, textos: list[str], idioma: str = "es") -> tuple[str, str]:
    """Devuelve (resumen, origen): origen ia, pendiente (el modelo trabaja) o reglas (sin modelo).

    El resumen se escribe en `idioma` (es, ca o en) aunque los comentarios estén en otro.
    Mientras el resumen está pendiente se devuelve el texto de respaldo, que la pantalla no muestra.
    """
    idioma = textos_respaldo.idioma_valido(idioma)
    if not textos:
        return "", "reglas"
    respaldo = _resumen_respaldo(tema, len(textos), idioma)
    if not hay_llm():
        return respaldo, "reglas"
    # Mientras la clasificación avanza los grupos cambian; se resume al terminar
    if clasificacion_en_curso():
        return respaldo, "pendiente"
    clave = ("resumen", idioma, tema, len(textos), hash(tuple(sorted(textos))))
    estado, valor = segundo_plano.consultar(clave, lambda: _resumir_con_ia(tema, textos, idioma))
    if estado == "pendiente":
        return respaldo, "pendiente"
    return (valor, "ia") if valor else (respaldo, "reglas")


def _resumir_con_ia(tema: str, textos: list[str], idioma: str = "es") -> str | None:
    prompt = _leer_prompt("resumir.md") + textos_respaldo.instruccion_idioma(idioma)
    muestra = textos[:MAX_MUESTRA_RESUMEN]
    usuario = (
        f"Tema: {tema} ({DESCRIPCION_TEMA.get(tema, '')})\n"
        f"Número total de comentarios del tema: {len(textos)}\n"
        f"Muestra de {len(muestra)} comentarios:\n"
        + "\n".join(f"- {t}" for t in muestra)
    )
    for intento in range(2):
        datos = llamar_llm_json(prompt, usuario, segundo_plano.TIMEOUT_SEG)
        texto = _recortar(str(datos.get("resumen", "") if isinstance(datos, dict) else "").strip())
        if not texto:
            log.warning("Resumen de '%s' vacío; se mantiene el de respaldo", tema)
            return None
        # Por anonimato se descarta cualquier resumen con citas o frases copiadas
        if '"' not in texto and "«" not in texto and not _copia_literal(texto, muestra):
            return texto
        usuario += ("\n\nTu resumen anterior repetía frases literales de los comentarios. "
                    "Reescríbelo con palabras distintas, sin copiar ninguna frase.")
    log.warning("Resumen de '%s' descartado por contener una cita literal", tema)
    return None


def _recortar(texto: str, max_frases: int = 2, max_palabras: int = 45) -> str:
    frases = re.split(r"(?<=[.!?])\s+", texto)
    corto = " ".join(frases[:max_frases])
    palabras = corto.split()
    return corto if len(palabras) <= max_palabras else " ".join(palabras[:max_palabras]).rstrip(",;:") + "…"


def _copia_literal(resumen: str, textos: list[str], palabras: int = 6) -> bool:
    r = _normalizar(resumen)
    for t in textos:
        w = _normalizar(t).split()
        for i in range(len(w) - palabras + 1):
            if " ".join(w[i:i + palabras]) in r:
                return True
    return False


def calcular_tendencia(n_actual: int, total_actual: int,
                       n_anterior: int, total_anterior: int) -> str:
    """Devuelve nuevo, sube, baja o estable comparando el peso del tema entre periodos.

    Sube o baja con una variación relativa del 30 %; nuevo si antes tenía menos de 2
    comentarios y ahora tiene al menos 5.
    """
    if total_anterior <= 0:
        return "estable"
    # Menos de 2 en el periodo anterior: un comentario mal clasificado no anula un tema nuevo
    if n_anterior < 2 and n_actual >= UMBRAL_MINIMO:
        return "nuevo"
    if n_anterior == 0:
        return "estable"
    pct_actual = n_actual / total_actual if total_actual else 0.0
    pct_anterior = n_anterior / total_anterior
    cambio = (pct_actual - pct_anterior) / pct_anterior
    if cambio >= 0.30:
        return "sube"
    if cambio <= -0.30:
        return "baja"
    return "estable"


def _textos(respuestas: list[dict[str, Any]]) -> list[str]:
    return [str(r.get("comentario") or "").strip() for r in respuestas
            if str(r.get("comentario") or "").strip()]


def analizar_comentarios(respuestas_actual: list[dict[str, Any]],
                         respuestas_anterior: list[dict[str, Any]],
                         idioma: str = "es") -> list[dict[str, Any]]:
    """Analiza los comentarios del periodo actual y calcula su evolución respecto al anterior.

    Los resúmenes salen en `idioma` (es, ca o en); la clasificación no depende del idioma.

    Omite temas con menos de 5 comentarios y ordena primero por tendencias activas.
    """
    actuales = _textos(respuestas_actual or [])
    anteriores = _textos(respuestas_anterior or [])
    if not actuales:
        return []

    temas_todos = clasificar_comentarios(actuales + anteriores)
    temas_act, temas_ant = temas_todos[:len(actuales)], temas_todos[len(actuales):]

    por_tema: dict[str, list[str]] = {}
    for texto, tema in zip(actuales, temas_act):
        por_tema.setdefault(tema, []).append(texto)
    cuenta_ant: dict[str, int] = {}
    for tema in temas_ant:
        cuenta_ant[tema] = cuenta_ant.get(tema, 0) + 1

    visibles = {t: txt for t, txt in por_tema.items() if len(txt) >= UMBRAL_MINIMO}
    resumenes = {tema: resumir_tema_con_origen(tema, txt, idioma) for tema, txt in visibles.items()}

    resultado = [
        {
            "tema": tema,
            "n": len(txt),
            "resumen": resumenes[tema][0],
            "resumen_origen": resumenes[tema][1],
            "tendencia": calcular_tendencia(len(txt), len(actuales),
                                            cuenta_ant.get(tema, 0), len(anteriores)),
            "n_anterior": cuenta_ant.get(tema, 0),
            "pct": round(len(txt) / len(actuales), 3),
            "pct_anterior": (round(cuenta_ant.get(tema, 0) / len(anteriores), 3)
                             if anteriores else None),
        }
        for tema, txt in visibles.items()
    ]
    prioridad = {"nuevo": 0, "sube": 0, "estable": 1, "baja": 1}
    resultado.sort(key=lambda t: (prioridad[t["tendencia"]], -t["n"], t["tema"]))
    return resultado
