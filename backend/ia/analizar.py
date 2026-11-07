"""Clasificación temática, generación de resúmenes y cálculo de tendencias de comentarios.

Si no hay clave de modelo disponible o la llamada falla, recurre a reglas por palabras clave.
"""

from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json

TEMAS = [
    "descansos", "turnos", "carga_trabajo", "comunicacion", "liderazgo",
    "herramientas", "formacion", "reconocimiento", "seguridad", "ambiente",
    "conciliacion", "otros",
]
UMBRAL_MINIMO = 5
TAMANO_LOTE = 50
MAX_MUESTRA_RESUMEN = 30
HILOS_IA = 4

_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Evita llamadas repetidas durante la sesión del servidor
_CACHE_TEMA: dict[str, str] = {}
_CACHE_RESUMEN: dict[tuple, str] = {}

# Raíces sin tildes, en castellano y catalán

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


# Turnos suele ser el contexto, no el tema: si aparece otro tema, prevalece
TEMAS_CONTEXTO = {"turnos"}


def clasificar_por_palabras(texto: str) -> str:
    """Clasifica un comentario asignándole un tema mediante reglas de palabras clave.

    Prioriza la primera coincidencia en el texto y la palabra clave más larga.
    """
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


def _leer_prompt(nombre: str) -> str:
    ruta = _PROMPTS / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _clasificar_lote_ia(lote: list[str]) -> list[str]:
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
    """Clasifica una lista de comentarios asignando a cada uno un tema de la lista cerrada.

    Procesa en lotes con el modelo de lenguaje y recurre a palabras clave si no hay servicio.
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
    """Genera un resumen breve y anónimo sobre los comentarios agrupados en un tema.

    Utiliza una muestra de comentarios y omite citas literales para preservar el anonimato.
    """
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
            # Descarta el resumen si contiene citas textuales para proteger el anonimato
            if texto and '"' not in texto and "«" not in texto and not _copia_literal(texto, muestra):
                resumen = texto
        except Exception:
            pass
    _CACHE_RESUMEN[clave] = resumen
    return resumen


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

    Sube o baja con una variación relativa del 30 %; nuevo si antes no aparecía y ahora
    tiene al menos 5 comentarios.
    """
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
    """Analiza los comentarios del periodo actual y calcula su evolución respecto al anterior.

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
