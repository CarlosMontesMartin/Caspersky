"""Puente con backend/ia/ (UPC 1) · UPC 2.

Cada función llama a la de UPC 1 con la firma de v2.md / modulos.md. Si el
módulo no está o falla, se usa un respaldo sencillo para que el ciclo
funcione igual. En el repo completo se usa siempre la de UPC 1, que ya trae
su propio modo sin IA: estos respaldos son solo la última red.
"""
import inspect
import re

from backend import textos
from backend.api.validacion import ORDEN_COLECTIVOS, colectivos_de, etiqueta_colectivo


def _aviso(funcion: str, error: Exception) -> None:
    print(f"[ia] {funcion} usa respaldo: {error!r}")


def _con_idioma(funcion, *args, idioma: str = "es"):
    """Llama a una función de UPC 1 pasándole idioma= solo si ya lo acepta (v4.md P0-2 de UPC 1)."""
    try:
        acepta = "idioma" in inspect.signature(funcion).parameters
    except (TypeError, ValueError):
        acepta = False
    return funcion(*args, idioma=idioma) if acepta else funcion(*args)


# ---------- estado ----------

def hay_llm() -> bool:
    try:
        from backend.ia.llm import hay_llm as real
        return bool(real())
    except Exception:
        return False


def pendientes() -> int:
    try:
        from backend.ia.segundo_plano import pendientes as real
        return int(real())
    except Exception:
        return 0


# ---------- generar ----------

PREGUNTAS_SECTOR = {  # respaldo mínimo si backend/ia no está
    "planta": [("¿Te da tiempo a hacer la pausa completa en tu turno?", "si_no", "bienestar"),
               ("¿Cómo valoras la organización de tu línea?", "escala_1_5", "condiciones")],
    "logistica": [("¿Te llega a tiempo el cuadrante de rutas?", "escala_1_5", "condiciones"),
                  ("¿Te avisan con tiempo de los cambios en el muelle?", "si_no", "liderazgo")],
    "comercial": [("¿Tus objetivos de visitas son realistas?", "escala_1_5", "condiciones"),
                  ("¿Tienes el apoyo que necesitas de la oficina?", "si_no", "liderazgo")],
    "oficina": [("¿Las reuniones te dejan tiempo para tu trabajo?", "escala_1_5", "condiciones"),
                ("¿Las herramientas que usas funcionan bien?", "si_no", "entorno")],
    "manager": [("¿Tienes margen para tomar decisiones con tu equipo?", "escala_1_5", "liderazgo"),
                ("¿Recibes la información a tiempo para tu equipo?", "si_no", "liderazgo")],
}


def _pregunta(pid, texto, tipo, dimension):
    return {"id": pid, "texto": texto, "tipo": tipo, "opciones": [], "dimension": dimension, "condicion": None}


def _generar_respaldo(necesidad: dict) -> dict:
    colectivos = colectivos_de(necesidad)
    objetivo = necesidad.get("objetivo", "").strip().rstrip(".")
    valoracion = f"Del 1 al 5, ¿cómo valoras lo siguiente: {objetivo[:1].lower() + objetivo[1:]}?"
    base = {"origen": "respaldo", "idioma_original": "es", "titulo": "Tu opinión cuenta", "periodo": None, "url": None, "qr": None,
            "intro": "Menos de 2 minutos. Es anónima: solo vemos resultados de grupos de 5 personas o más.",
            "colectivos": colectivos, "colectivo": etiqueta_colectivo(colectivos)}
    if len(colectivos) == 1:
        preguntas = [_pregunta("p1", valoracion, "escala_1_5", "condiciones"),
                     _pregunta("p2", "¿Te han explicado bien los cambios que te afectan?", "escala_1_5", "liderazgo"),
                     _pregunta("p3", "¿Qué cambiarías?", "texto", "condiciones")]
        tiempo = 60
        return dict(base, preguntas=preguntas, preguntas_por_colectivo={},
                    tiempo_estimado_seg=tiempo, tiempo_por_colectivo={colectivos[0]: tiempo})
    nucleo = [_pregunta("c1", valoracion, "escala_1_5", "condiciones"),
              _pregunta("c2", "¿Qué cambiarías?", "texto", "condiciones")]
    por_colectivo = {c: [_pregunta(f"{c}_p{i}", *datos) for i, datos in enumerate(PREGUNTAS_SECTOR[c], 1)]
                     for c in colectivos}
    tiempos = {c: 15 + 30 + 15 * len(por_colectivo[c]) for c in colectivos}
    return dict(base, preguntas=nucleo, preguntas_por_colectivo=por_colectivo,
                tiempo_por_colectivo=tiempos, tiempo_estimado_seg=max(tiempos.values()))


def generar_encuesta(necesidad: dict, reglas: str, idioma: str = "es") -> dict:
    """Encuesta escrita en `idioma` (v5 §1). Un ValueError de UPC 1 (necesidad imposible, p. ej.
    duración demasiado corta) se deja pasar: la ruta lo convierte en 422."""
    try:
        from backend.ia.generar import generar_encuesta as real
    except Exception as error:
        _aviso("generar_encuesta", error)
        return _generar_respaldo(necesidad)
    try:
        return _con_idioma(real, necesidad, reglas, idioma=idioma)
    except ValueError:
        raise
    except Exception as error:
        _aviso("generar_encuesta", error)
    return _generar_respaldo(necesidad)


# ---------- analizar ----------

def analizar_comentarios(actual: list, anterior: list, idioma: str = "es") -> list:
    try:
        from backend.ia.analizar import analizar_comentarios as real
        return _con_idioma(real, actual, anterior, idioma=idioma)
    except Exception as error:
        _aviso("analizar_comentarios", error)
    return []


def clasificar_comentarios(textos: list) -> list:
    try:
        from backend.ia.analizar import clasificar_comentarios as real
        return real(textos)
    except Exception as error:
        _aviso("clasificar_comentarios", error)
    return ["otros"] * len(textos)


def estado_clasificacion(textos: list) -> dict:
    try:
        from backend.ia.analizar import estado_clasificacion as real
        return real(textos)
    except Exception as error:
        _aviso("estado_clasificacion", error)
    return {"total": len(set(textos)), "por_ia": 0}


# ---------- recomendar ----------

ACCION_POR_TEMA = {  # respaldo: (título, responsable, plazo, indicador)
    "descansos": ("Revisar la duración y el reparto de las pausas", "RRHH y jefes de turno", "2 semanas",
                  "Menos comentarios sobre descansos en el seguimiento"),
    "turnos": ("Publicar los cuadrantes con más antelación", "Jefes de turno", "2 semanas",
               "Mejora de la valoración de condiciones en el seguimiento"),
    "comunicacion": ("Explicar los cambios en una sesión breve al inicio de cada turno", "Mandos intermedios",
                     "1 semana", "Media ≥ 3,5 en «me han explicado bien el cambio»"),
}
ACCION_GENERICA = ("Analizar con el equipo las causas de «{tema}»", "RRHH", "1 mes",
                   "Menos comentarios sobre este tema en el seguimiento")


def _recomendar_respaldo(analisis: dict, encuesta: dict) -> dict:
    temas = sorted(analisis.get("temas", []), key=lambda t: (t.get("tendencia") not in ("nuevo", "sube"), -t["n"]))
    acciones = []
    for t in temas[:2]:
        titulo, responsable, plazo, indicador = ACCION_POR_TEMA.get(t["tema"], ACCION_GENERICA)
        acciones.append({"titulo": titulo.format(tema=t["tema"]), "tema": t["tema"], "responsable": responsable,
                         "plazo": plazo, "indicador": indicador,
                         "motivo": f"{t['n']} comentarios sobre {t['tema']} (tendencia: {t.get('tendencia', '—')})."})
    no_repr = [a for a in analisis.get("alertas", []) if a.get("tipo") == "representatividad"]
    if no_repr and len(acciones) < 3:
        acciones.append({"titulo": "Reforzar la participación con QR y quiosco en los segmentos que menos responden",
                         "motivo": no_repr[0]["mensaje"], "tema": "otros", "responsable": "RRHH",
                         "plazo": "Antes del próximo pulso", "indicador": "Participación ≥ 20 % en todos los segmentos"})
    if not acciones:
        acciones.append({"titulo": "Compartir los resultados con los equipos y recoger propuestas",
                         "motivo": f"{analisis.get('n_respuestas', 0)} respuestas en el periodo.", "tema": "otros",
                         "responsable": "RRHH", "plazo": "2 semanas", "indicador": "Participación en el seguimiento"})
    colectivos = colectivos_de(encuesta) or list(ORDEN_COLECTIVOS)
    tema = temas[0]["tema"] if temas else "el clima"
    return {"origen": "reglas", "lectura": lectura_respaldo(analisis), "acciones": acciones,
            "seguimiento": {"objetivo": f"Comprobar si mejora {tema} tras las acciones propuestas",
                            "colectivos": colectivos, "contexto": "Encuesta de seguimiento un mes después",
                            "duracion_max_seg": 60, "temas_prohibidos": ["salario"]}}


LECTURA = {
    "es": {"respuestas": "{n} respuestas en el periodo {periodo}", "global": ", con una participación global del {pct} %",
           "peor": "La valoración más baja es la de {sector}: {media} sobre 5{cambio}.",
           "cambio": " ({var} respecto al periodo anterior)",
           "no_repr": "Hay {n} segmentos poco representados: sus datos deben leerse con cautela."},
    "ca": {"respuestas": "{n} respostes al període {periodo}", "global": ", amb una participació global del {pct} %",
           "peor": "La valoració més baixa és la de {sector}: {media} sobre 5{cambio}.",
           "cambio": " ({var} respecte al període anterior)",
           "no_repr": "Hi ha {n} segments poc representats: les seves dades s'han de llegir amb cautela."},
    "en": {"respuestas": "{n} responses in period {periodo}", "global": ", with an overall participation of {pct}%",
           "peor": "The lowest rating is in {sector}: {media} out of 5{cambio}.",
           "cambio": " ({var} vs. the previous period)",
           "no_repr": "{n} segments are under-represented: read their data with caution."},
}


def lectura_respaldo(analisis: dict, idioma: str = "es") -> str:
    """2–3 frases con cifras, sin IA, en `idioma`."""
    L = LECTURA[textos.idioma_valido(idioma)]
    frases = [L["respuestas"].format(n=analisis.get("n_respuestas", 0), periodo=analisis.get("periodo_actual") or "—")
              + (L["global"].format(pct=round(analisis.get("participacion_global", 0) * 100))
                 if analisis.get("participacion_global") else "") + "."]
    zonas = [z for z in analisis.get("zonas", []) if z.get("media") is not None]
    if zonas:
        peor = min(zonas, key=lambda z: z["media"])
        cambio = (L["cambio"].format(var=("+" if peor["variacion"] > 0 else "") + textos.numero(peor["variacion"], idioma))
                  if peor.get("variacion") is not None else "")
        frases.append(L["peor"].format(sector=textos.nombre("colectivo", peor["colectivo"], idioma).lower(),
                                       media=textos.numero(peor["media"], idioma), cambio=cambio))
    no_repr = [a for a in analisis.get("alertas", []) if a.get("tipo") == "representatividad"]
    if no_repr:
        frases.append(L["no_repr"].format(n=len(no_repr)))
    return " ".join(frases)


def recomendar(analisis: dict, encuesta: dict, idioma: str = "es") -> dict:
    try:
        from backend.ia.recomendar import recomendar as real
        resultado = _con_idioma(real, analisis, encuesta, idioma=idioma)
    except Exception as error:
        _aviso("recomendar", error)
        resultado = _recomendar_respaldo(analisis, encuesta)
    resultado.setdefault("origen", "reglas")
    if not resultado.get("lectura"):
        resultado["lectura"] = lectura_respaldo(analisis, idioma)
    return resultado


# ---------- pregunta a tus datos ----------

IDENTIFICAR = re.compile(r"\b(qui[eé]n(es)?|qui|who|whom|nombres?|noms?|names?|dni|nie|correos?|e-?mail|"
                         r"tel[eé]fonos?|phone|qu[eé] ha dicho|identific\w*|identify\w*|despedi\w*|acomiadar|"
                         r"fire|sancion\w*|sancionar)\b", re.IGNORECASE)
MENSAJES_PRIVACIDAD = {
    "es": "Esta herramienta solo trabaja con resultados agregados de grupos de 5 personas o más. "
          "No puede identificar a nadie ni decir qué ha respondido una persona concreta.",
    "ca": "Aquesta eina només treballa amb resultats agregats de grups de 5 persones o més. "
          "No pot identificar ningú ni dir què ha respost una persona concreta.",
    "en": "This tool only works with aggregated results from groups of 5 people or more. "
          "It cannot identify anyone or say what a specific person answered.",
}
MENSAJE_PRIVACIDAD = MENSAJES_PRIVACIDAD["es"]
SIN_IA = {
    "es": ("Ahora mismo el servicio de IA no está disponible, así que no puedo responder en lenguaje natural. "
           "Estas son las cifras principales del análisis.", "respuestas en el periodo actual"),
    "ca": ("Ara mateix el servei d'IA no està disponible, així que no puc respondre en llenguatge natural. "
           "Aquestes són les xifres principals de l'anàlisi.", "respostes al període actual"),
    "en": ("The AI service is not available right now, so I cannot answer in natural language. "
           "These are the main figures of the analysis.", "responses in the current period"),
}


def _idioma_de(pregunta: str, idioma: str) -> str:
    """Detección muy simple del idioma de la pregunta; si no está claro, el de la pantalla."""
    p = f" {(pregunta or '').lower()} "
    if any(w in p for w in (" what ", " which ", " who ", " how ", " why ", " the ", " is ", " are ")):
        return "en"
    if any(w in p for w in (" què ", " quin ", " quina ", " qui ", " com ", " per què ", " més ", " són ")):
        return "ca"
    if any(w in p for w in (" qué ", " cuál ", " quién ", " cómo ", " por qué ", " más ", " son ")):
        return "es"
    return textos.idioma_valido(idioma)


def _preguntar_respaldo(pregunta: str, analisis: dict, idioma: str = "es") -> dict:
    idioma = _idioma_de(pregunta, idioma)
    if IDENTIFICAR.search(pregunta or ""):
        return {"respuesta": MENSAJES_PRIVACIDAD[idioma], "cifras": [], "confianza": "alta", "origen": "reglas"}
    texto, etiqueta = SIN_IA[idioma]
    cifras = [f"{analisis.get('n_respuestas', 0)} {etiqueta}"]
    for z in analisis.get("zonas", []):
        if z.get("media") is not None:
            cifras.append(f"{textos.nombre('colectivo', z['colectivo'], idioma)}: {textos.numero(z['media'], idioma)} / 5")
    return {"respuesta": texto, "cifras": cifras[:5], "confianza": "baja", "origen": "reglas"}


def preguntar(pregunta: str, analisis: dict, recomendaciones: dict, idioma: str = "es") -> dict:
    if IDENTIFICAR.search(pregunta or ""):  # privacidad primero, también si UPC 1 falla
        return _preguntar_respaldo(pregunta, analisis, idioma)
    try:
        from backend.ia.informe import preguntar as real
        return _con_idioma(real, pregunta, analisis, recomendaciones, idioma=idioma)
    except Exception as error:
        _aviso("preguntar", error)
    return _preguntar_respaldo(pregunta, analisis, idioma)


# ---------- comentarios simulados ----------

def banco_contextual(encuesta: dict, temas: list) -> dict:
    try:
        from backend.ia.simulados import banco_contextual as real
        return real(encuesta, temas) or {}
    except Exception as error:
        _aviso("banco_contextual", error)
    return {}



# ---------- v3: sugerencias y traducciones ----------

def sugerir_preguntas(analisis: dict, idioma: str = "es") -> dict:
    """{"preguntas": [3 textos], "origen": "ia|pendiente|ninguno"}. Sin IA: lista vacía, sin textos fijos."""
    try:
        from backend.ia.informe import sugerir_preguntas as real
        resultado = _con_idioma(real, analisis, idioma=idioma) or {}
        preguntas = [p for p in resultado.get("preguntas", []) if isinstance(p, str) and p.strip()]
        origen = resultado.get("origen") if resultado.get("origen") in ("ia", "pendiente", "ninguno") else "ninguno"
        return {"preguntas": preguntas[:3] if origen == "ia" else [], "origen": origen}
    except Exception as error:
        _aviso("sugerir_preguntas", error)
    return {"preguntas": [], "origen": "ninguno"}


def traducir_encuesta(encuesta: dict, idiomas: list, idioma_origen: str = "es") -> dict:
    """{"<idioma>": {...}, …} (formato de `traducciones`), traducido DESDE idioma_origen (v5 §1).
    Lanza la excepción si UPC 1 falla."""
    from backend.ia.traducir import traducir_encuesta as real
    try:
        acepta = "idioma_origen" in inspect.signature(real).parameters
    except (TypeError, ValueError):
        acepta = False
    if acepta:
        return real(encuesta, idiomas, idioma_origen=idioma_origen) or {}
    return real(encuesta, idiomas) or {}  # versión de UPC 1 anterior a v5: solo traduce desde castellano
