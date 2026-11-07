"""Análisis de comentarios: clasificar por tema, resumir y calcular tendencias.

UPC 1 · MODULOS.md §4 (backend/ia/analizar.py).
Funciona siempre: si no hay clave de IA o la IA falla, usa el modo de respaldo
(palabras clave para clasificar y un resumen descriptivo fijo por tema).
"""

from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json

# Valores cerrados (MODULOS.md §0)
TEMAS = [
    "descansos", "turnos", "carga_trabajo", "comunicacion", "liderazgo",
    "herramientas", "formacion", "reconocimiento", "seguridad", "ambiente",
    "conciliacion", "otros",
]
UMBRAL_MINIMO = 5        # mismo valor que backend/datos/metricas.py
TAMANO_LOTE = 50         # comentarios por llamada a la IA
MAX_MUESTRA_RESUMEN = 30
HILOS_IA = 4             # llamadas a la IA en paralelo

_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Cachés en memoria (duran lo que dura el servidor): el dashboard puede pedir el
# análisis muchas veces y así solo se llama a la IA la primera.
_CACHE_TEMA: dict[str, str] = {}
_CACHE_RESUMEN: dict[tuple, str] = {}

# ---------------------------------------------------------------------------
# Respaldo: palabras clave (raíces sin tildes, castellano y catalán)
# ---------------------------------------------------------------------------

PALABRAS_CLAVE: dict[str, list[str]] = {
    "descansos": ["descans", "pausa", "desconect", "desconnect", "recuper", "agotad",
                  "seure", "bano tranquil", "comer", "parar", "tomar algo", "10 min"],
    "turnos": ["turno", "\\btorn", "rotaci", "rotatiu", "cuadrante", "quadrant", "horarios cambian",
               "horari canvia", "calendario", "de noche", "\\bnit\\b"],
    "carga_trabajo": ["carga", "carrega", "abasto", "falta personal", "falta de gente", "menos gente",
                      "menys gent", "mas personal", "mas gente", "ritmo", "tareas", "volumen",
                      "picos", "limite", "desbordat", "mans", "refuerzo", "demasiado trabajo",
                      "mas faena", "capacidad", "no crece", "produccion sube"],
    "comunicacion": ["comunic", "informa", "avisa", "avisen", "avisar", "enteramos", "entere",
                     "rumor", "explicacion", "explicarme", "canal oficial", "wasa", "whatsapp",
                     "ens van dir", "no ens van", "nos dijo", "nadie nos", "oficial", "dijeron",
                     "de un dia para otro", "de un dia pa otro", "sin preguntar", "comunicat"],
    "liderazgo": ["jefe", "\\bcaps\\b", "mando", "responsable", "encargad", "lideraz", "lideratge",
                  "superior", "feedback", "decisiones", "escucha", "cercania"],
    "herramientas": ["herramient", "eines", "eina", "maquin", "software", "sistema se", "tablet",
                     "wifi", "portatil", "plataforma", "ordenador", "carretilla", "material",
                     "tecnolog", "bugs", "\\bapp\\b", "aplicacion", "actualitzar", "softw", "lentisim"],
    "formacion": ["formaci", "curso", "aprend", "carrera", "crecer", "creixer", "mentori",
                  "desenvolupament", "promocion", "oportunidad", "sin explicarnos", "linea nueva"],
    "reconocimiento": ["reconoc", "reconeix", "valora", "un gracias", "invisible", "celebr",
                       "esfuerzo", "nadie lo", "logros", "solo te dicen", "algo bien", "da igual lo"],
    "seguridad": ["segur", "peligr", "\\bepi", "senaliz", "extintor", "emergencia", "evacua",
                  "resbal", "cables", "ilumina", "prevenci", "ergonom", "botiquin", "riesgo",
                  "simulacro", "visibilidad", "accident", "sortides", "formacion en prevencion"],
    "ambiente": ["ambiente", "ambient", "companer", "companys", "grupito", "tension", "rollo",
                 "rotllo", "mal humor", "se ayuda", "como equipo"],
    "conciliacion": ["concilia", "hijos", "ninos", "nens", "famili", "flexib", "teletrabajo",
                     "vida social", "vida personal", "\\bcole\\b", "escola", "compagin", "familiar",
                     "veo a mis", "recoger a mi", "salir antes", "mi hij"],
    "otros": ["comedor", "menjador", "parking", "maquina de cafe", "cafe", "calefaccion",
              "transporte", "uniforme",
              "vestuario", "nada especial", "res a dir", "todo bien", "frio", "calor"],
}

_PATRONES = {
    tema: [re.compile(p if p.startswith("\\b") else re.escape(p)) for p in claves]
    for tema, claves in PALABRAS_CLAVE.items()
}

# Para el resumen de respaldo: de qué suele hablar cada tema (texto neutro).
DESCRIPCION_TEMA = {
    "descansos": "las pausas y el tiempo para descansar o desconectar",
    "turnos": "la organización de los turnos y los cambios de horario",
    "carga_trabajo": "el volumen de trabajo y la falta de personal",
    "comunicacion": "cómo y cuándo llega la información sobre los cambios",
    "liderazgo": "la relación con los responsables y la toma de decisiones",
    "herramientas": "el estado de las herramientas, los equipos y el software",
    "formacion": "las oportunidades de formación y de crecimiento",
    "reconocimiento": "el reconocimiento del esfuerzo y del trabajo bien hecho",
    "seguridad": "la seguridad y la prevención de riesgos",
    "ambiente": "el ambiente y la relación entre compañeros",
    "conciliacion": "la conciliación con la vida personal y familiar",
    "otros": "cuestiones variadas (instalaciones, servicios y otros)",
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


# "turnos" suele ser el CONTEXTO del comentario, no su tema ("con los nuevos turnos
# no veo a mis hijos" habla de conciliación). Si aparece otro tema, gana el otro.
TEMAS_CONTEXTO = {"turnos"}


def clasificar_por_palabras(texto: str) -> str:
    """Respaldo sin IA. Gana el tema cuya palabra clave aparece ANTES en el texto
    (en un comentario que mezcla temas, el principal suele ir primero), salvo
    "turnos", que solo gana si no hay otro tema. En la misma posición gana la
    coincidencia más larga ("maquina de cafe" frente a "maquin"). Sin coincidencias → otros."""
    t = _normalizar(texto)
    mejor, mejor_clave = "otros", None
    for tema, patrones in _PATRONES.items():
        coincidencias = [(m.start(), -(m.end() - m.start())) for p in patrones for m in p.finditer(t)]
        if not coincidencias:
            continue
        clave = (tema in TEMAS_CONTEXTO, *min(coincidencias), -len(coincidencias))
        if mejor_clave is None or clave < mejor_clave:
            mejor, mejor_clave = tema, clave
    return mejor

# ---------------------------------------------------------------------------
# Funciones del módulo
# ---------------------------------------------------------------------------


def _leer_prompt(nombre: str) -> str:
    ruta = _PROMPTS / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _clasificar_lote_ia(lote: list[str]) -> list[str]:
    """Una llamada a la IA para un lote. Si algo falla, respaldo para ese lote."""
    try:
        usuario = (
            f"Temas permitidos: {', '.join(TEMAS)}\n\n"
            f"Clasifica estos {len(lote)} comentarios. Devuelve exactamente {len(lote)} temas, "
            f"en el mismo orden.\n\n"
            + json.dumps({str(i + 1): txt for i, txt in enumerate(lote)}, ensure_ascii=False)
        )
        datos = llamar_llm_json(_leer_prompt("clasificar.md"), usuario)
        temas = datos.get("temas") if isinstance(datos, dict) else datos
        if not isinstance(temas, list) or len(temas) != len(lote):
            raise ValueError("número de temas distinto al de comentarios")
        return [t if t in TEMAS else clasificar_por_palabras(txt)
                for t, txt in zip(temas, lote)]
    except Exception:
        return [clasificar_por_palabras(txt) for txt in lote]


def clasificar_comentarios(textos: list[str]) -> list[str]:
    """Un tema de la lista cerrada por texto, en el mismo orden.

    Con IA: lotes de 50 en paralelo, con caché por texto. Sin IA: palabras clave.
    """
    if not hay_llm():
        return [clasificar_por_palabras(t) for t in textos]

    pendientes = list(dict.fromkeys(t for t in textos if t not in _CACHE_TEMA))
    lotes = [pendientes[i:i + TAMANO_LOTE] for i in range(0, len(pendientes), TAMANO_LOTE)]
    if lotes:
        with ThreadPoolExecutor(max_workers=HILOS_IA) as pool:
            for lote, temas in zip(lotes, pool.map(_clasificar_lote_ia, lotes)):
                _CACHE_TEMA.update(zip(lote, temas))
    return [_CACHE_TEMA.get(t) or clasificar_por_palabras(t) for t in textos]


def _resumen_respaldo(tema: str, n: int) -> str:
    return f"{n} comentarios sobre {DESCRIPCION_TEMA.get(tema, tema)}."


def resumir_tema(tema: str, textos: list[str]) -> str:
    """1–2 frases sobre lo que dicen los comentarios de un tema, sin citas literales
    ni nada que identifique. Usa una muestra de hasta 30 comentarios. Con caché."""
    if not textos:
        return ""
    clave = (tema, len(textos), hash(tuple(sorted(textos))))
    if clave in _CACHE_RESUMEN:
        return _CACHE_RESUMEN[clave]

    resumen = _resumen_respaldo(tema, len(textos))
    if hay_llm():
        try:
            muestra = textos[:MAX_MUESTRA_RESUMEN]
            usuario = (
                f"Tema: {tema} ({DESCRIPCION_TEMA.get(tema, '')})\n"
                f"Número total de comentarios del tema: {len(textos)}\n"
                f"Muestra de {len(muestra)} comentarios:\n"
                + "\n".join(f"- {t}" for t in muestra)
            )
            datos = llamar_llm_json(_leer_prompt("resumir.md"), usuario)
            texto = datos.get("resumen", "") if isinstance(datos, dict) else ""
            texto = str(texto).strip()
            # Sin citas literales: si aparece un fragmento largo de un comentario, se descarta
            if texto and '"' not in texto and "«" not in texto and not _copia_literal(texto, muestra):
                resumen = texto
        except Exception:
            pass
    _CACHE_RESUMEN[clave] = resumen
    return resumen


def _copia_literal(resumen: str, textos: list[str], palabras: int = 6) -> bool:
    """True si el resumen copia 6 o más palabras seguidas de algún comentario."""
    r = _normalizar(resumen)
    for t in textos:
        w = _normalizar(t).split()
        for i in range(len(w) - palabras + 1):
            if " ".join(w[i:i + palabras]) in r:
                return True
    return False


def calcular_tendencia(n_actual: int, total_actual: int,
                       n_anterior: int, total_anterior: int) -> str:
    """nuevo si antes 0 y ahora ≥ 5; sube/baja si el porcentaje cambia ±30 % o más;
    si no, estable. Sin periodo anterior → estable."""
    if total_anterior <= 0:
        return "estable"
    if n_anterior == 0:
        return "nuevo" if n_actual >= UMBRAL_MINIMO else "estable"
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
                         respuestas_anterior: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lista de Tema {tema, n, resumen, tendencia} del periodo actual.

    Clasifica los comentarios no vacíos de ambos periodos, cuenta por tema, resume
    y calcula la tendencia. Omite los temas con n < 5. Orden: primero nuevo y sube,
    después por n de mayor a menor.
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
    with ThreadPoolExecutor(max_workers=HILOS_IA) as pool:
        resumenes = dict(zip(visibles, pool.map(lambda t: resumir_tema(t, visibles[t]), visibles)))

    resultado = [
        {
            "tema": tema,
            "n": len(txt),
            "resumen": resumenes[tema],
            "tendencia": calcular_tendencia(len(txt), len(actuales),
                                            cuenta_ant.get(tema, 0), len(anteriores)),
        }
        for tema, txt in visibles.items()
    ]
    prioridad = {"nuevo": 0, "sube": 0, "estable": 1, "baja": 1}
    resultado.sort(key=lambda t: (prioridad[t["tendencia"]], -t["n"], t["tema"]))
    return resultado
