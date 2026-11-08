"""Generación y validación de encuestas adaptadas a uno o varios colectivos.

Con varios colectivos la encuesta tiene un núcleo común (c1..c3) y preguntas propias de cada
sector. Si no hay clave de modelo o la llamada falla, recurre a plantillas de respaldo.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import reglas

from .llm import hay_llm, llamar_llm_json

ORDEN_COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
COLECTIVOS_VALIDOS = set(ORDEN_COLECTIVOS)
DIMENSIONES_VALIDAS = {
    "bienestar",
    "liderazgo",
    "desarrollo",
    "cultura",
    "entorno",
    "condiciones",
}
TIPOS_VALIDOS = {"escala_1_5", "opcion", "si_no", "texto"}

REGLAS_POR_DEFECTO = {
    "planta": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano y directo, pensado para operarios de fábrica desde el móvil.",
    "logistica": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano, adaptado a personal de almacén en movimiento.",
    "comercial": "Máximo 5 preguntas. Frases claras y directas, enfocado a equipo en ruta y visitas comerciales.",
    "oficina": "Máximo 6 preguntas. Tono profesional, claro y respetuoso, enfocado a personal de sede y puestos administrativos.",
    "manager": "Máximo 6 preguntas. Tono profesional y constructivo, enfocado a liderazgo, recursos y coordinación de equipos.",
}

# RRHH está esperando delante de la pantalla: pasado este tiempo se usa la plantilla de respaldo
TIMEOUT_GENERAR_SEG = 20
TIMEOUT_GENERAR_SECTORES_SEG = 30

# Tiempo máximo por colectivo (contenido/reglas_colectivos.md, sección 3)
TIEMPO_MAX_COLECTIVO = {"planta": 90, "logistica": 60, "comercial": 120, "oficina": 180,
                        "manager": 120}

log = logging.getLogger(__name__)

MAX_PREGUNTAS = {"planta": 4, "logistica": 4, "comercial": 5, "oficina": 6, "manager": 5}

# Respaldo multisector: dos preguntas propias por colectivo, con el vocabulario de cada uno
PREGUNTAS_SECTOR: dict[str, list[tuple[str, str, str]]] = {
    "planta": [("¿Te da tiempo a hacer la pausa completa en tu turno?", "si_no", "bienestar"),
               ("¿Recibes el cuadrante con antelación suficiente?", "escala_1_5", "condiciones")],
    "logistica": [("¿El relevo te da tiempo a pasar la información?", "si_no", "condiciones"),
                  ("¿Cómo valoras la coordinación en el muelle?", "escala_1_5", "entorno")],
    "comercial": [("¿Tienes el apoyo que necesitas para tus visitas?", "escala_1_5", "liderazgo"),
                  ("¿Puedes desconectar al acabar la jornada en ruta?", "si_no", "bienestar")],
    "oficina": [("¿Las reuniones te dejan tiempo para tu trabajo?", "escala_1_5", "condiciones"),
                ("¿Las herramientas digitales te facilitan el día a día?", "escala_1_5", "entorno")],
    "manager": [("¿Tienes la información necesaria para decidir con tu equipo?", "escala_1_5",
                 "liderazgo"),
                ("¿Recibes apoyo de People para gestionar los cambios?", "escala_1_5", "cultura")],
}

# Raíces de palabras bloqueadas por reglas de negocio
SINONIMOS_PROHIBIDOS = {
    "salario": ["salari", "sueld", "nomina", "dinero", "retribu", "remunera",
                "paga", "pagan", "pagar", "cobr", "plus", "incentivo", "bonus"],
    "sueldo": ["salari", "sueld", "nomina", "retribu", "remunera", "cobr"],
    "dinero": ["dinero", "salari", "sueld", "paga", "cobr"],
}


def _normalizar_texto(texto: str) -> str:
    texto_lower = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto_lower)
        if unicodedata.category(c) != "Mn"
    )


def _extraer_reglas_colectivo(reglas_texto: str, colectivo: str) -> str:
    # Admite "## planta" y "### 3.1 `planta` — Producción", como en contenido/reglas_colectivos.md
    if not reglas_texto:
        return ""
    patron = (rf"^(#{{2,4}})\s+(?:[\d.]+\s+)?`?{re.escape(colectivo)}`?\b.*$"
              rf"([\s\S]*?)(?=^#{{2,4}}\s|\Z)")
    match = re.search(patron, reglas_texto, re.MULTILINE | re.IGNORECASE)
    return match.group(2).strip() if match else ""


def colectivos_de(datos: dict[str, Any]) -> list[str]:
    """Devuelve los colectivos de una necesidad o encuesta, en orden fijo (formato nuevo o antiguo)."""
    lista = datos.get("colectivos")
    if isinstance(lista, list) and lista:
        validos = [c for c in ORDEN_COLECTIVOS if c in lista]
        if validos:
            return validos
    colectivo = datos.get("colectivo")
    if colectivo == "todos":
        return list(ORDEN_COLECTIVOS)
    return [colectivo] if colectivo in COLECTIVOS_VALIDOS else ["planta"]


def etiqueta_colectivo(colectivos: list[str]) -> str:
    """Valor del campo antiguo colectivo: el único, todos o varios."""
    if len(colectivos) == 1:
        return colectivos[0]
    return "todos" if set(colectivos) == COLECTIVOS_VALIDOS else "varios"


def preguntas_de(encuesta: dict[str, Any], colectivo: str) -> list[dict[str, Any]]:
    """Preguntas que ve un colectivo: el núcleo común más las propias de su sector."""
    return (encuesta.get("preguntas") or []) + (
        encuesta.get("preguntas_por_colectivo") or {}).get(colectivo, [])


def _cargar_prompt_sistema() -> str:
    prompt_path = Path(__file__).resolve().parent / "prompts" / "generar.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Eres un experto en clima laboral. Genera una microencuesta en JSON "
        "con titulo, intro y preguntas (id, texto, tipo, opciones, dimension)."
    )


# Preguntas predefinidas para el modo de respaldo
_TEMAS_RESPALDO: list[dict[str, Any]] = [
    {
        "claves": ["turno", "horario", "cuadrante", "rotacion", "jornada"],
        "titulo": "Tu opinión sobre los nuevos turnos",
        "sobre": "el cambio de turnos",
        "preguntas": [
            ("¿Cómo valoras el nuevo sistema de turnos?", "condiciones"),
            ("¿Te explicaron bien cómo funciona el cambio?", "liderazgo"),
            ("¿Puedes descansar bien con los turnos actuales?", "bienestar"),
            ("¿Qué cambiarías o reforzarías de los turnos?", "condiciones"),
        ],
    },
    {
        "claves": ["herramienta", "software", "aplicacion", "app", "sistema nuevo",
                   "programa", "maquina", "tablet", "plataforma", "digital"],
        "titulo": "Tu opinión sobre la nueva herramienta",
        "sobre": "la nueva herramienta",
        "preguntas": [
            ("¿Cómo valoras la nueva herramienta?", "condiciones"),
            ("¿Has recibido formación suficiente para usarla?", "desarrollo"),
            ("¿Te ayuda a hacer mejor tu trabajo?", "entorno"),
            ("¿Qué mejorarías de la herramienta?", "condiciones"),
        ],
    },
    {
        "claves": ["carga", "ritmo", "volumen", "pico", "estres", "presion"],
        "titulo": "Tu opinión sobre la carga de trabajo",
        "sobre": "la carga de trabajo",
        "preguntas": [
            ("¿Cómo valoras tu carga de trabajo actual?", "condiciones"),
            ("¿Puedes hacer pausas cuando lo necesitas?", "bienestar"),
            ("¿Tienes apoyo cuando hay picos de trabajo?", "liderazgo"),
            ("¿Qué ayudaría a repartir mejor el trabajo?", "condiciones"),
        ],
    },
    {
        "claves": ["comunica", "informa", "aviso", "transparen"],
        "titulo": "Tu opinión sobre la comunicación",
        "sobre": "cómo te llega la información",
        "preguntas": [
            ("¿Te llega a tiempo la información importante?", "cultura"),
            ("¿Entiendes por qué se toman las decisiones?", "liderazgo"),
            ("¿Sabes a quién acudir si tienes dudas?", "liderazgo"),
            ("¿Cómo te gustaría recibir la información?", "cultura"),
        ],
    },
    {
        "claves": ["formacion", "curso", "aprend", "desarrollo", "carrera", "crecer"],
        "titulo": "Tu opinión sobre formación y desarrollo",
        "sobre": "tu formación y desarrollo",
        "preguntas": [
            ("¿Tienes oportunidades para aprender cosas nuevas?", "desarrollo"),
            ("¿La formación te sirve en tu día a día?", "desarrollo"),
            ("¿Sabes cómo puedes crecer en la empresa?", "desarrollo"),
            ("¿Qué te gustaría aprender?", "desarrollo"),
        ],
    },
]
_RESPALDO_GENERAL: dict[str, Any] = {
    "titulo": "¿Cómo estás?",
    "sobre": "tu día a día en el trabajo",
    "preguntas": [
        ("¿Cómo te sientes en tu trabajo últimamente?", "bienestar"),
        ("¿Te sientes escuchado/a por tu responsable?", "liderazgo"),
        ("¿Tienes lo necesario para hacer bien tu trabajo?", "condiciones"),
        ("¿Qué cambiarías para estar mejor?", "condiciones"),
    ],
}


def _plantilla_respaldo_colectivo(colectivo: str, objetivo: str,
                                  contexto: str = "") -> dict[str, Any]:
    texto = _normalizar_texto(f"{objetivo} {contexto}")
    elegido = next((t for t in _TEMAS_RESPALDO
                    if any(clave in texto for clave in t["claves"])), _RESPALDO_GENERAL)
    *escalas, abierta = elegido["preguntas"]
    preguntas = [
        {"id": f"p{i}", "texto": txt, "tipo": "escala_1_5", "opciones": [],
         "dimension": dim, "condicion": None}
        for i, (txt, dim) in enumerate(escalas, start=1)
    ]
    preguntas.append({"id": "p4", "texto": abierta[0], "tipo": "texto", "opciones": [],
                      "dimension": abierta[1], "condicion": None})
    return {
        "titulo": elegido["titulo"],
        "intro": (f"Queremos saber qué opinas sobre {elegido['sobre']} para mejorarlo. "
                  "Es anónima: solo se ven resultados agregados."),
        "preguntas": preguntas,
    }


def _construir_terminos_prohibidos(temas_prohibidos: list[str]) -> set[str]:
    terminos = set()
    for tema in temas_prohibidos or []:
        norm = _normalizar_texto(str(tema).strip())
        if not norm:
            continue
        terminos.add(norm[:-1] if len(norm) >= 6 and " " not in norm else norm)
        for clave, raices in SINONIMOS_PROHIBIDOS.items():
            if clave in norm:
                terminos.update(raices)
    return terminos


def _texto_contiene_prohibido(texto: str, terminos_prohibidos: set[str]) -> bool:
    if not terminos_prohibidos:
        return False
    texto_norm = _normalizar_texto(texto)
    for term in terminos_prohibidos:
        # Límite de palabra para evitar falsos positivos
        patron = rf"\b{re.escape(term)}"
        if re.search(patron, texto_norm):
            return True
    return False


def _limpiar_pregunta(p: Any, terminos_prohibidos: set[str]) -> dict[str, Any] | None:
    if not isinstance(p, dict):
        return None
    texto = str(p.get("texto", "")).strip()
    if not texto:
        return None
    opciones_txt = " ".join(str(o) for o in p.get("opciones") or [])
    if _texto_contiene_prohibido(texto + " " + opciones_txt, terminos_prohibidos):
        return None
    tipo = p.get("tipo") if p.get("tipo") in TIPOS_VALIDOS else "escala_1_5"
    opciones: list[str] = []
    if tipo == "opcion":
        opciones = [str(o).strip() for o in p.get("opciones") or [] if str(o).strip()]
        if len(opciones) < 2:
            tipo, opciones = "escala_1_5", []
    dimension = p.get("dimension") if p.get("dimension") in DIMENSIONES_VALIDAS else "bienestar"
    return {"texto": texto, "tipo": tipo, "opciones": opciones, "dimension": dimension,
            "condicion": None}


def _tiempo(preguntas: list[dict[str, Any]]) -> int:
    return reglas.segundos(preguntas)


def _numerar(preguntas: list[dict[str, Any]], prefijo: str) -> list[dict[str, Any]]:
    return [{"id": f"{prefijo}{i}", **{k: p[k] for k in ("texto", "tipo", "opciones",
                                                         "dimension", "condicion")}}
            for i, p in enumerate(preguntas, start=1)]


def _limite_tiempo(colectivo: str, duracion_max: int, n_sectores: int = 1) -> int:
    # El tope del colectivo nunca baja de la duración mínima, para que siempre quepan 3 preguntas
    tope = max(TIEMPO_MAX_COLECTIVO.get(colectivo, duracion_max), reglas.duracion_minima(n_sectores))
    return min(duracion_max, tope)


def _orden_recorte(preguntas: list[dict[str, Any]]) -> list[int]:
    """Índices en el orden en que se pueden quitar: si_no u opción, escalas sobrantes y texto.

    La última escala_1_5 no aparece nunca: no se puede quitar.
    """
    escalas = [i for i, p in enumerate(preguntas) if p["tipo"] == "escala_1_5"]
    otras = [i for i, p in enumerate(preguntas) if p["tipo"] in ("si_no", "opcion")]
    textos = [i for i, p in enumerate(preguntas) if p["tipo"] == "texto"]
    return otras[::-1] + escalas[1:][::-1] + textos


def _con_escala(preguntas: list[dict[str, Any]], escala: dict[str, Any]) -> list[dict[str, Any]]:
    # Al menos una escala_1_5, al principio si hay que añadirla; como mucho un texto, al final
    abiertas = [p for p in preguntas if p["tipo"] == "texto"][-1:]
    cerradas = [p for p in preguntas if p["tipo"] != "texto"]
    if not any(p["tipo"] == "escala_1_5" for p in cerradas):
        cerradas.insert(0, dict(escala))
    return cerradas + abiertas


def _textos_generales(encuesta: dict[str, Any], respaldo: dict[str, Any],
                      terminos: set[str]) -> tuple[str, str]:
    titulo, intro = encuesta.get("titulo"), encuesta.get("intro")
    if not isinstance(titulo, str) or not titulo.strip() or _texto_contiene_prohibido(titulo, terminos):
        titulo = respaldo["titulo"]
    if not isinstance(intro, str) or not intro.strip() or _texto_contiene_prohibido(intro, terminos):
        intro = respaldo["intro"]
    return titulo.strip(), intro.strip()


def comprobar_duracion(necesidad: dict[str, Any]) -> None:
    """Lanza ValueError si la duración no llega al mínimo de reglas.py para sus sectores."""
    n = len(colectivos_de(necesidad))
    duracion = int(necesidad.get("duracion_max_seg", 120))
    if duracion < reglas.duracion_minima(n):
        raise ValueError(f"La duración máxima debe ser de al menos {reglas.duracion_minima(n)} s "
                         f"con {n} {'sector' if n == 1 else 'sectores'}")


def validar_encuesta(encuesta: dict[str, Any], necesidad: dict[str, Any]) -> dict[str, Any]:
    """Ajusta una encuesta a las reglas del contrato: tipos, tiempos, temas prohibidos e ids.

    Con un colectivo todo va en preguntas (p1...). Con varios, núcleo común (c1...) y preguntas
    propias de cada sector (planta_p1...), con 3 a 6 preguntas y el tiempo de cada colectivo.
    """
    colectivos = colectivos_de(necesidad)
    comprobar_duracion(necesidad)
    if len(colectivos) == 1:
        resultado = _validar_un_colectivo(encuesta, necesidad, colectivos[0])
    else:
        resultado = _validar_sectores(encuesta, necesidad, colectivos)
    resultado["origen"] = encuesta.get("origen", "respaldo")
    return resultado


def _validar_un_colectivo(encuesta: dict[str, Any], necesidad: dict[str, Any],
                          colectivo: str) -> dict[str, Any]:
    objetivo = necesidad.get("objetivo", "clima laboral")
    limite = _limite_tiempo(colectivo, int(necesidad.get("duracion_max_seg", 120)))
    terminos = _construir_terminos_prohibidos(necesidad.get("temas_prohibidos", []))
    respaldo = _plantilla_respaldo_colectivo(colectivo, objetivo, necesidad.get("contexto", ""))
    titulo, intro = _textos_generales(encuesta, respaldo, terminos)
    de_respaldo = [_limpiar_pregunta(p, set()) for p in respaldo["preguntas"]]
    escala = next(p for p in de_respaldo if p["tipo"] == "escala_1_5")

    preguntas = _con_escala([q for q in (_limpiar_pregunta(p, terminos)
                                         for p in encuesta.get("preguntas") or []) if q], escala)
    maximo = min(reglas.TOTAL_MAX, MAX_PREGUNTAS.get(colectivo, reglas.TOTAL_MAX))
    # Recorte por número y por tiempo sin quitar nunca la última escala
    while len(preguntas) > maximo or _tiempo(preguntas) > limite:
        orden = _orden_recorte(preguntas)
        if not orden:
            break
        preguntas.pop(orden[0])
    # Completar hasta el mínimo con preguntas cerradas del respaldo, si caben
    for p in de_respaldo:
        if len(preguntas) >= reglas.TOTAL_MIN:
            break
        if (p["tipo"] != "texto" and not _texto_contiene_prohibido(p["texto"], terminos)
                and all(_normalizar_texto(p["texto"]) != _normalizar_texto(q["texto"]) for q in preguntas)):
            preguntas.insert(len([q for q in preguntas if q["tipo"] != "texto"]), dict(p))
            while _tiempo(preguntas) > limite and _orden_recorte(preguntas):
                indice = _orden_recorte(preguntas)[-1] if preguntas[-1]["tipo"] == "texto" \
                    else _orden_recorte(preguntas)[0]
                preguntas.pop(indice)
    if len(preguntas) < reglas.TOTAL_MIN or _tiempo(preguntas) > limite:
        raise ValueError(f"Con {necesidad.get('duracion_max_seg')} s no caben {reglas.TOTAL_MIN} "
                         f"preguntas para {colectivo}: aumenta la duración máxima")

    preguntas = _numerar(preguntas, "p")
    tiempo = _tiempo(preguntas)
    return {
        "titulo": titulo, "intro": intro,
        "colectivo": colectivo, "colectivos": [colectivo],
        "estado": "borrador", "periodo": datetime.now().strftime("%Y-%m"),
        "tiempo_estimado_seg": tiempo, "tiempo_por_colectivo": {colectivo: tiempo},
        "url": None, "qr": None,
        "preguntas": preguntas, "preguntas_por_colectivo": {},
    }


def _respaldo_sectores(necesidad: dict[str, Any], colectivos: list[str]) -> dict[str, Any]:
    base = _plantilla_respaldo_colectivo(colectivos[0], necesidad.get("objetivo", ""),
                                         necesidad.get("contexto", ""))
    primera = next(p for p in base["preguntas"] if p["tipo"] == "escala_1_5")
    return {
        "titulo": base["titulo"],
        "intro": base["intro"],
        "preguntas": [dict(primera),
                      {"texto": "¿Qué cambiarías?", "tipo": "texto", "opciones": [],
                       "dimension": "condiciones", "condicion": None}],
        "preguntas_por_colectivo": {
            c: [{"texto": t, "tipo": tipo, "opciones": [], "dimension": d, "condicion": None}
                for t, tipo, d in PREGUNTAS_SECTOR[c]]
            for c in colectivos
        },
    }


def _propias_candidatas(propuestas: Any, respaldo: list[dict[str, Any]], nucleo: list[dict],
                        terminos: set[str]) -> list[dict[str, Any]]:
    """Preguntas propias válidas de un sector: primero las del modelo, después las del respaldo."""
    textos_nucleo = {_normalizar_texto(p["texto"]) for p in nucleo}
    elegidas: list[dict[str, Any]] = []
    for p in (propuestas if isinstance(propuestas, list) else []) + respaldo:
        q = _limpiar_pregunta(p, terminos)
        # Las propias nunca son de texto ni repiten el núcleo ni otra propia
        if (q and q["tipo"] != "texto" and _normalizar_texto(q["texto"]) not in textos_nucleo
                and all(_normalizar_texto(q["texto"]) != _normalizar_texto(x["texto"]) for x in elegidas)):
            elegidas.append(q)
    return elegidas


def _cuantas_propias(nucleo: list[dict], candidatas: list[dict], limite: int, colectivo: str) -> int:
    """Cuántas propias caben (0 si no se puede cumplir el mínimo con este núcleo)."""
    maximo_total = min(reglas.TOTAL_MAX, MAX_PREGUNTAS.get(colectivo, reglas.TOTAL_MAX))
    tope = min(reglas.PROPIAS_MAX, maximo_total - len(nucleo), len(candidatas))
    minimo = max(reglas.PROPIAS_MIN, reglas.TOTAL_MIN - len(nucleo))
    for k in range(tope, minimo - 1, -1):
        if _tiempo(nucleo + candidatas[:k]) <= limite:
            return k
    return 0


def _validar_sectores(encuesta: dict[str, Any], necesidad: dict[str, Any],
                      colectivos: list[str]) -> dict[str, Any]:
    duracion = int(necesidad.get("duracion_max_seg", 120))
    terminos = _construir_terminos_prohibidos(necesidad.get("temas_prohibidos", []))
    respaldo = _respaldo_sectores(necesidad, colectivos)
    titulo, intro = _textos_generales(encuesta, respaldo, terminos)
    limites = {c: _limite_tiempo(c, duracion, len(colectivos)) for c in colectivos}
    escala = _limpiar_pregunta(respaldo["preguntas"][0], set())

    # Núcleo: 1-3 preguntas, siempre con una escala_1_5, como mucho un texto y al final
    nucleo = _con_escala([q for q in (_limpiar_pregunta(p, terminos)
                                      for p in encuesta.get("preguntas") or []) if q], escala)
    while len(nucleo) > reglas.NUCLEO_MAX:
        nucleo.pop(_orden_recorte(nucleo)[0])

    propuestas = encuesta.get("preguntas_por_colectivo")
    propuestas = propuestas if isinstance(propuestas, dict) else {}
    while True:
        candidatas = {c: _propias_candidatas(propuestas.get(c), respaldo["preguntas_por_colectivo"][c],
                                             nucleo, terminos) for c in colectivos}
        cuantas = {c: _cuantas_propias(nucleo, candidatas[c], limites[c], c) for c in colectivos}
        if all(cuantas.values()):
            break
        # Algún sector no cabe: se reduce el núcleo (nunca la última escala)
        orden = _orden_recorte(nucleo)
        if not orden:
            sector = next(c for c in colectivos if not cuantas[c])
            raise ValueError(f"Con {duracion} s no caben {reglas.TOTAL_MIN} preguntas para {sector}: "
                             "aumenta la duración máxima")
        nucleo.pop(orden[0])

    por_colectivo = {c: _numerar(candidatas[c][:cuantas[c]], f"{c}_p") for c in colectivos}
    tiempos = {c: _tiempo(nucleo + por_colectivo[c]) for c in colectivos}
    return {
        "titulo": titulo, "intro": intro,
        "colectivo": etiqueta_colectivo(colectivos), "colectivos": colectivos,
        "estado": "borrador", "periodo": datetime.now().strftime("%Y-%m"),
        "tiempo_estimado_seg": max(tiempos.values()), "tiempo_por_colectivo": tiempos,
        "url": None, "qr": None,
        "preguntas": _numerar(nucleo, "c"), "preguntas_por_colectivo": por_colectivo,
    }


def _leer_prompt(nombre: str) -> str:
    ruta = Path(__file__).resolve().parent / "prompts" / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _texto_necesidad(necesidad: dict[str, Any], colectivos: list[str]) -> str:
    return (
        f"Necesidad de RRHH:\n"
        f"- Colectivos: {', '.join(colectivos)}\n"
        f"- Objetivo: {necesidad.get('objetivo', '')}\n"
        f"- Contexto: {necesidad.get('contexto', '')}\n"
        f"- Duración máxima: {necesidad.get('duracion_max_seg', 120)} segundos\n"
        f"- Temas prohibidos: {', '.join(necesidad.get('temas_prohibidos', [])) or 'ninguno'}\n"
    )


def generar_encuesta(necesidad: dict[str, Any], reglas: str = "") -> dict[str, Any]:
    """Genera una encuesta en borrador para uno o varios colectivos.

    Una sola llamada al modelo (20 s con un colectivo, 30 s con varios); si no hay modelo o
    falla, plantillas de respaldo. Devuelve siempre origen, colectivos y colectivo. Lanza
    ValueError si la duración no permite una encuesta válida (la ruta responde 422).
    """
    colectivos = colectivos_de(necesidad)
    necesidad = {**necesidad, "colectivos": colectivos}
    comprobar_duracion(necesidad)  # Antes de llamar al modelo: un error claro y sin esperas
    candidata: dict[str, Any] | None = None

    if hay_llm():
        inicio = time.monotonic()
        try:
            if len(colectivos) == 1:
                c = colectivos[0]
                reglas_c = _extraer_reglas_colectivo(reglas, c) or REGLAS_POR_DEFECTO[c]
                usuario = (_texto_necesidad(necesidad, colectivos)
                           + f"- Tiempo máximo del colectivo: {TIEMPO_MAX_COLECTIVO[c]} s\n\n"
                           + f"Reglas específicas para el colectivo '{c}':\n{reglas_c}\n\n"
                           + "Genera el JSON de la encuesta cumpliendo todas las indicaciones.")
                respuesta = llamar_llm_json(_cargar_prompt_sistema(), usuario, TIMEOUT_GENERAR_SEG)
            else:
                bloques = [f"### {c} (tiempo máximo {TIEMPO_MAX_COLECTIVO[c]} s)\n"
                           f"{_extraer_reglas_colectivo(reglas, c) or REGLAS_POR_DEFECTO[c]}"
                           for c in colectivos]
                varios = _extraer_reglas_colectivo(reglas, "varios")
                usuario = (_texto_necesidad(necesidad, colectivos)
                           + (f"\nReglas del núcleo común:\n{varios}\n" if varios else "")
                           + "\nReglas de cada colectivo:\n\n" + "\n\n".join(bloques)
                           + "\n\nGenera el JSON con el núcleo común y las preguntas de cada "
                             f"colectivo ({', '.join(colectivos)}).")
                respuesta = llamar_llm_json(_leer_prompt("generar_sectores.md"), usuario,
                                            TIMEOUT_GENERAR_SECTORES_SEG)
            if isinstance(respuesta, dict) and respuesta.get("preguntas"):
                candidata = {**respuesta, "origen": "ia"}
                log.info("Encuesta generada por el modelo en %.1f s", time.monotonic() - inicio)
        except Exception as error:
            log.warning("Encuesta generada con la plantilla de respaldo: %s", error)

    if candidata is None:
        if len(colectivos) == 1:
            candidata = _plantilla_respaldo_colectivo(
                colectivos[0], necesidad.get("objetivo", ""), necesidad.get("contexto", ""))
        else:
            candidata = _respaldo_sectores(necesidad, colectivos)
        candidata["origen"] = "respaldo"

    return validar_encuesta(candidata, necesidad)
