"""Generación y validación de encuestas adaptadas al colectivo.

Implementación de UPC 1 para Antigravity / Damm Escucha Activa.
Funciona siempre en modo de respaldo si no hay clave LLM configurada o si esta falla.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from .llm import hay_llm, llamar_llm_json

# Valores cerrados según contratos/formatos.md
COLECTIVOS_VALIDOS = {"planta", "logistica", "comercial", "oficina", "manager"}
DIMENSIONES_VALIDAS = {
    "bienestar",
    "liderazgo",
    "desarrollo",
    "cultura",
    "entorno",
    "condiciones",
}
TIPOS_VALIDOS = {"escala_1_5", "opcion", "si_no", "texto"}

# Reglas por defecto si no existen en contenido/reglas_colectivos.md
REGLAS_POR_DEFECTO = {
    "planta": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano y directo, pensado para operarios de fábrica desde el móvil.",
    "logistica": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano, adaptado a personal de almacén en movimiento.",
    "comercial": "Máximo 5 preguntas. Frases claras y directas, enfocado a equipo en ruta y visitas comerciales.",
    "oficina": "Máximo 6 preguntas. Tono profesional, claro y respetuoso, enfocado a personal de sede y puestos administrativos.",
    "manager": "Máximo 6 preguntas. Tono profesional y constructivo, enfocado a liderazgo, recursos y coordinación de equipos.",
}

# Máximo de preguntas por colectivo (además del límite general de 3–6)
MAX_PREGUNTAS = {"planta": 4, "logistica": 4, "comercial": 5, "oficina": 6, "manager": 6}

# Raíces de palabra para temas prohibidos frecuentes. Se buscan como inicio de
# palabra, así "salari" bloquea salario, salarios, salarial…
SINONIMOS_PROHIBIDOS = {
    "salario": ["salari", "sueld", "nomina", "dinero", "retribu", "remunera",
                "paga", "pagan", "pagar", "cobr", "plus", "incentivo", "bonus"],
    "sueldo": ["salari", "sueld", "nomina", "retribu", "remunera", "cobr"],
    "dinero": ["dinero", "salari", "sueld", "paga", "cobr"],
}


def _normalizar_texto(texto: str) -> str:
    """Elimina tildes y convierte a minúsculas para comparaciones robustas."""
    texto_lower = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto_lower)
        if unicodedata.category(c) != "Mn"
    )


def _extraer_reglas_colectivo(reglas_texto: str, colectivo: str) -> str:
    """Extrae la sección '## <colectivo>' de un texto markdown de reglas."""
    if not reglas_texto:
        return ""
    patron = rf"^##\s+{re.escape(colectivo)}\b([\s\S]*?)(?=^##\s+|\Z)"
    match = re.search(patron, reglas_texto, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _cargar_prompt_sistema() -> str:
    """Carga el prompt de sistema desde prompts/generar.md."""
    prompt_path = Path(__file__).resolve().parent / "prompts" / "generar.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Eres un experto en clima laboral. Genera una microencuesta en JSON "
        "con titulo, intro y preguntas (id, texto, tipo, opciones, dimension)."
    )


# Respaldo: preguntas cortas (menos de 12 palabras) por tema detectado en la
# necesidad. Nunca se pega el objetivo literal de RRHH dentro de una pregunta.
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
    """Respaldo sin IA: 3 escala_1_5 + 1 texto sobre el tema de la necesidad.

    Detecta el tema por palabras clave en objetivo + contexto (turnos,
    herramienta, carga, comunicación, formación) y si no encuentra ninguno usa
    un pulso general. Mismas preguntas para todos los colectivos: son cortas y
    sirven tanto en planta como en oficina.
    """
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
    """Raíces normalizadas de los temas prohibidos (y sus sinónimos conocidos).

    Cada término se busca como INICIO de palabra: "salari" bloquea "salarial".
    Para palabras largas se usa la raíz sin la última letra (salario → salari).
    """
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
    """Comprueba si un texto contiene algún término prohibido como palabra completa."""
    if not terminos_prohibidos:
        return False
    texto_norm = _normalizar_texto(texto)
    for term in terminos_prohibidos:
        # Usar límite de palabra para no capturar subcadenas casuales
        patron = rf"\b{re.escape(term)}"
        if re.search(patron, texto_norm):
            return True
    return False


def validar_encuesta(encuesta: dict[str, Any], necesidad: dict[str, Any]) -> dict[str, Any]:
    """Corrige y asegura la coherencia de una encuesta según las reglas del MVP.

    - Fuerza colectivo = necesidad['colectivo']
    - Renumera preguntas como p1, p2...
    - Corrige tipos y dimensiones a valores cerrados
    - opciones = [] salvo en 'opcion' (si tiene <2 opciones pasa a escala_1_5)
    - condicion = None siempre (MVP)
    - Elimina preguntas con temas prohibidos (con sinónimos de salario)
    - Calcula tiempo_estimado_seg (15 s cortas, 30 s texto) y recorta si supera duracion_max_seg
    - Asegura entre 3 y 6 preguntas (completa con respaldo si quedan < 3)
    """
    colectivo = necesidad.get("colectivo", encuesta.get("colectivo", "planta"))
    if colectivo not in COLECTIVOS_VALIDOS:
        colectivo = "planta"

    objetivo = necesidad.get("objetivo", "clima laboral")
    duracion_max = int(necesidad.get("duracion_max_seg", 120))
    temas_prohibidos = necesidad.get("temas_prohibidos", [])
    terminos_prohibidos = _construir_terminos_prohibidos(temas_prohibidos)

    respaldo_textos = _plantilla_respaldo_colectivo(colectivo, objetivo,
                                                    necesidad.get("contexto", ""))
    titulo = encuesta.get("titulo")
    if (not titulo or not isinstance(titulo, str)
            or _texto_contiene_prohibido(titulo, terminos_prohibidos)):
        titulo = respaldo_textos["titulo"]

    intro = encuesta.get("intro")
    if (not intro or not isinstance(intro, str)
            or _texto_contiene_prohibido(intro, terminos_prohibidos)):
        intro = respaldo_textos["intro"]

    # Procesar y limpiar preguntas recibidas
    preguntas_raw = encuesta.get("preguntas", [])
    if not isinstance(preguntas_raw, list):
        preguntas_raw = []

    preguntas_limpias: list[dict[str, Any]] = []
    for p in preguntas_raw:
        if not isinstance(p, dict):
            continue

        texto = str(p.get("texto", "")).strip()
        if not texto:
            continue

        # Descartar si la pregunta o alguna de sus opciones toca un tema prohibido
        opciones_txt = " ".join(str(o) for o in p.get("opciones") or [])
        if _texto_contiene_prohibido(texto + " " + opciones_txt, terminos_prohibidos):
            continue

        tipo = p.get("tipo")
        if tipo not in TIPOS_VALIDOS:
            tipo = "escala_1_5"

        opciones_raw = p.get("opciones", [])
        if tipo == "opcion":
            if isinstance(opciones_raw, list) and len(opciones_raw) >= 2:
                opciones = [str(opt).strip() for opt in opciones_raw if str(opt).strip()]
                if len(opciones) < 2:
                    tipo = "escala_1_5"
                    opciones = []
            else:
                tipo = "escala_1_5"
                opciones = []
        else:
            opciones = []

        dim = p.get("dimension")
        if dim not in DIMENSIONES_VALIDAS:
            dim = "bienestar"

        preguntas_limpias.append({
            "texto": texto,
            "tipo": tipo,
            "opciones": opciones,
            "dimension": dim,
            "condicion": None,
        })

    # Regla: como mucho una pregunta de texto y siempre al final
    preguntas_no_texto = [p for p in preguntas_limpias if p["tipo"] != "texto"]
    preguntas_texto = [p for p in preguntas_limpias if p["tipo"] == "texto"]

    if preguntas_texto:
        # Conservar solo la última pregunta de texto y colocarla al final
        preguntas_filtradas = preguntas_no_texto + [preguntas_texto[-1]]
    else:
        preguntas_filtradas = preguntas_no_texto

    # Función auxiliar de cálculo de tiempo
    def _calcular_tiempo(pregs: list[dict[str, Any]]) -> int:
        return sum(30 if p["tipo"] == "texto" else 15 for p in pregs)

    # Si supera duracion_max_seg, recortar (primero la de texto, luego desde el final)
    while preguntas_filtradas and _calcular_tiempo(preguntas_filtradas) > duracion_max:
        # Si la última es texto, la quitamos primero
        if preguntas_filtradas[-1]["tipo"] == "texto":
            preguntas_filtradas.pop()
        else:
            preguntas_filtradas.pop()

    # Máximo de preguntas: 6 en general y menos según el colectivo
    # (manteniendo la de texto al final si la hay)
    maximo = min(6, MAX_PREGUNTAS.get(colectivo, 6))
    if len(preguntas_filtradas) > maximo:
        tiene_texto = preguntas_filtradas[-1]["tipo"] == "texto"
        if tiene_texto:
            preguntas_filtradas = preguntas_filtradas[:maximo - 1] + [preguntas_filtradas[-1]]
        else:
            preguntas_filtradas = preguntas_filtradas[:maximo]

    # Si quedan menos de 3 preguntas, completar con preguntas del respaldo
    if len(preguntas_filtradas) < 3:
        respaldo = respaldo_textos
        for p_resp in respaldo["preguntas"]:
            if len(preguntas_filtradas) >= 3:
                break
            # Verificar tema prohibido
            if _texto_contiene_prohibido(p_resp["texto"], terminos_prohibidos):
                continue
            # Evitar textos idénticos
            if any(p["texto"] == p_resp["texto"] for p in preguntas_filtradas):
                continue

            # Priorizar preguntas cortas (15 s) si el tiempo es ajustado
            tiempo_actual = _calcular_tiempo(preguntas_filtradas)
            coste = 30 if p_resp["tipo"] == "texto" else 15
            if tiempo_actual + coste <= duracion_max or len(preguntas_filtradas) < 3:
                # Si es de texto y ya hay una, no añadirla
                if p_resp["tipo"] == "texto" and any(p["tipo"] == "texto" for p in preguntas_filtradas):
                    continue
                preguntas_filtradas.append({
                    "texto": p_resp["texto"],
                    "tipo": p_resp["tipo"],
                    "opciones": list(p_resp.get("opciones", [])),
                    "dimension": p_resp["dimension"],
                    "condicion": None,
                })

        # Reordenar para que texto quede al final si lo hubiera
        no_txt = [p for p in preguntas_filtradas if p["tipo"] != "texto"]
        txt = [p for p in preguntas_filtradas if p["tipo"] == "texto"]
        preguntas_filtradas = no_txt + txt[:1]

    # Si tras completar aún superase duracion_max pero tiene > 3 preguntas, ajustar
    while len(preguntas_filtradas) > 3 and _calcular_tiempo(preguntas_filtradas) > duracion_max:
        if preguntas_filtradas[-1]["tipo"] == "texto":
            preguntas_filtradas.pop()
        else:
            preguntas_filtradas.pop()

    # Renumerar preguntas como p1, p2, p3...
    preguntas_finales: list[dict[str, Any]] = []
    for idx, p in enumerate(preguntas_filtradas, start=1):
        preguntas_finales.append({
            "id": f"p{idx}",
            "texto": p["texto"],
            "tipo": p["tipo"],
            "opciones": p["opciones"],
            "dimension": p["dimension"],
            "condicion": None,
        })

    tiempo_final = _calcular_tiempo(preguntas_finales)

    return {
        "titulo": titulo,
        "intro": intro,
        "colectivo": colectivo,
        "estado": "borrador",
        "periodo": datetime.now().strftime("%Y-%m"),
        "tiempo_estimado_seg": tiempo_final,
        "url": None,
        "qr": None,
        "preguntas": preguntas_finales,
    }


def generar_encuesta(necesidad: dict[str, Any], reglas: str = "") -> dict[str, Any]:
    """Genera una Encuesta (borrador) sin 'id' a partir de una Necesidad.

    Si hay clave LLM configurada, consulta al modelo de IA con prompts/generar.md.
    Si no hay clave o ante cualquier error, usa el modo de respaldo.
    Siempre valida el resultado final con validar_encuesta.
    """
    colectivo = necesidad.get("colectivo", "planta")
    if colectivo not in COLECTIVOS_VALIDOS:
        colectivo = "planta"

    # Extraer reglas específicas del colectivo o recurrir a las reglas por defecto
    reglas_colectivo = _extraer_reglas_colectivo(reglas, colectivo)
    if not reglas_colectivo:
        reglas_colectivo = REGLAS_POR_DEFECTO.get(
            colectivo, REGLAS_POR_DEFECTO["planta"]
        )

    encuesta_candidata: dict[str, Any] | None = None

    if hay_llm():
        try:
            prompt_sistema = _cargar_prompt_sistema()
            prompt_usuario = (
                f"Necesidad de RRHH:\n"
                f"- Colectivo: {colectivo}\n"
                f"- Objetivo: {necesidad.get('objetivo', '')}\n"
                f"- Contexto: {necesidad.get('contexto', '')}\n"
                f"- Duración máxima: {necesidad.get('duracion_max_seg', 120)} segundos\n"
                f"- Temas prohibidos: {', '.join(necesidad.get('temas_prohibidos', []))}\n\n"
                f"Reglas específicas para el colectivo '{colectivo}':\n"
                f"{reglas_colectivo}\n\n"
                f"Genera el JSON de la encuesta cumpliendo todas las indicaciones."
            )
            respuesta_json = llamar_llm_json(prompt_sistema, prompt_usuario)
            if isinstance(respuesta_json, dict) and "preguntas" in respuesta_json:
                encuesta_candidata = respuesta_json
        except Exception:
            # Ante CUALQUIER fallo de la IA se pasa transparentemente a respaldo
            encuesta_candidata = None

    if encuesta_candidata is None:
        encuesta_candidata = _plantilla_respaldo_colectivo(
            colectivo, necesidad.get("objetivo", ""), necesidad.get("contexto", "")
        )

    return validar_encuesta(encuesta_candidata, necesidad)