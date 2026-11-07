"""Puente con backend/ia/ (UPC 1) · UPC 2.

Cada función llama a la de UPC 1 con la firma de v2.md / modulos.md. Si el
módulo no está o falla, se usa un respaldo sencillo para que el ciclo
funcione igual. En el repo completo se usa siempre la de UPC 1, que ya trae
su propio modo sin IA: estos respaldos son solo la última red.
"""
import re

from backend.api.validacion import ORDEN_COLECTIVOS, colectivos_de, etiqueta_colectivo

NOMBRE = {"planta": "planta", "logistica": "logística", "comercial": "comercial",
          "oficina": "oficina", "manager": "managers"}


def _aviso(funcion: str, error: Exception) -> None:
    print(f"[ia] {funcion} usa respaldo: {error!r}")


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
    base = {"origen": "respaldo", "titulo": "Tu opinión cuenta", "periodo": None, "url": None, "qr": None,
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


def generar_encuesta(necesidad: dict, reglas: str) -> dict:
    try:
        from backend.ia.generar import generar_encuesta as real
        return real(necesidad, reglas)
    except Exception as error:
        _aviso("generar_encuesta", error)
    return _generar_respaldo(necesidad)


# ---------- analizar ----------

def analizar_comentarios(actual: list, anterior: list) -> list:
    try:
        from backend.ia.analizar import analizar_comentarios as real
        return real(actual, anterior)
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


def lectura_respaldo(analisis: dict) -> str:
    """2–3 frases con cifras, sin IA."""
    frases = [f"{analisis.get('n_respuestas', 0)} respuestas en {analisis.get('periodo_actual') or 'el periodo'}"
              + (f", con una participación global del {round(analisis.get('participacion_global', 0) * 100)} %."
                 if analisis.get("participacion_global") else ".")]
    zonas = [z for z in analisis.get("zonas", []) if z.get("media") is not None]
    if zonas:
        peor = min(zonas, key=lambda z: z["media"])
        cambio = f" ({peor['variacion']:+.1f} respecto al periodo anterior)".replace(".", ",") if peor.get("variacion") is not None else ""
        frases.append(f"La valoración más baja es la de {NOMBRE.get(peor['colectivo'], peor['colectivo'])}: "
                      f"{peor['media']:.1f}".replace(".", ",") + f" sobre 5{cambio}.")
    no_repr = [a for a in analisis.get("alertas", []) if a.get("tipo") == "representatividad"]
    if no_repr:
        frases.append(f"Hay {len(no_repr)} segmentos poco representados: sus datos deben leerse con cautela.")
    return " ".join(frases)


def recomendar(analisis: dict, encuesta: dict) -> dict:
    try:
        from backend.ia.recomendar import recomendar as real
        resultado = real(analisis, encuesta)
    except Exception as error:
        _aviso("recomendar", error)
        resultado = _recomendar_respaldo(analisis, encuesta)
    resultado.setdefault("origen", "reglas")
    if not resultado.get("lectura"):
        resultado["lectura"] = lectura_respaldo(analisis)
    return resultado


# ---------- pregunta a tus datos ----------

IDENTIFICAR = re.compile(r"\b(qui[eé]n(es)?|nombres?|dni|nie|correos?|e-?mail|tel[eé]fonos?|"
                         r"qu[eé] ha dicho|identific\w*|despedi\w*|sancion\w*)\b", re.IGNORECASE)
MENSAJE_PRIVACIDAD = ("Esta herramienta solo trabaja con resultados agregados de grupos de 5 personas o más. "
                      "No puede identificar a nadie ni decir qué ha respondido una persona concreta.")


def _preguntar_respaldo(pregunta: str, analisis: dict) -> dict:
    if IDENTIFICAR.search(pregunta or ""):
        return {"respuesta": MENSAJE_PRIVACIDAD, "cifras": [], "confianza": "alta", "origen": "reglas"}
    cifras = [f"{analisis.get('n_respuestas', 0)} respuestas en el periodo actual"]
    for z in analisis.get("zonas", []):
        if z.get("media") is not None:
            cifras.append(f"{NOMBRE.get(z['colectivo'], z['colectivo'])}: {z['media']:.1f}".replace(".", ",") + " / 5")
    return {"respuesta": "Ahora mismo el servicio de IA no está disponible, así que no puedo responder en lenguaje "
                         "natural. Estas son las cifras principales del análisis.",
            "cifras": cifras[:5], "confianza": "baja", "origen": "reglas"}


def preguntar(pregunta: str, analisis: dict, recomendaciones: dict) -> dict:
    if IDENTIFICAR.search(pregunta or ""):  # privacidad primero, también si UPC 1 falla
        return _preguntar_respaldo(pregunta, analisis)
    try:
        from backend.ia.informe import preguntar as real
        return real(pregunta, analisis, recomendaciones)
    except Exception as error:
        _aviso("preguntar", error)
    return _preguntar_respaldo(pregunta, analisis)


# ---------- comentarios simulados ----------

def banco_contextual(encuesta: dict, temas: list) -> dict:
    try:
        from backend.ia.simulados import banco_contextual as real
        return real(encuesta, temas) or {}
    except Exception as error:
        _aviso("banco_contextual", error)
    return {}

