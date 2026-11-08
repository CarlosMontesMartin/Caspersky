"""Compromisos "Dijisteis → Hemos hecho" · UPC 2 (v6.md §4.1, §4.2 y §4.3 P0-2).

Lógica sin FastAPI (la usan las rutas de compromisos, la encuesta pública, la maqueta y Teams).

Reglas de privacidad que se cumplen aquí:
- un compromiso nunca contiene comentarios literales (copia_literal) ni datos de grupos con n < 5
  (el "antes" y el "después" solo salen de medias con n ≥ UMBRAL_MINIMO);
- el "antes → después" nunca afirma una causa: la pantalla lo acompaña de "No demuestra que la
  acción sea la causa" y aquí se marca "simulado" si alguna respuesta lo es.
"""
import re
import unicodedata
from datetime import date, timedelta

from backend.datos import almacen, metricas
from backend.datos.metricas import UMBRAL_MINIMO
from backend.reglas import idioma_valido

ESTADOS = ("comprometido", "hecho")
MAX_TEXTO = 300
PALABRAS_COPIA = 7                      # 7 palabras seguidas iguales a un comentario = copia literal
COMILLAS = "\"“”«»„‟"                   # el apóstrofo no cuenta: es normal en catalán e inglés
DIAS_POR_DEFECTO = 14

_UNIDAD = re.compile(r"(\d+|una?|un|one)\s*(d[ií]as?|dies|days?|semanas?|setmanes?|weeks?|mes(?:es)?|mesos|months?)",
                     re.IGNORECASE)
_MESES_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------- textos ----------

def idioma_original(compromiso: dict) -> str:
    return idioma_valido(compromiso.get("idioma_original"))


def en_idioma(compromiso: dict, idioma: str) -> dict:
    """Copia con "dijisteis" y "hicimos" en `idioma` si existe la traducción y, si no, en el original.
    Añade "idioma_vista" (el idioma en el que están los textos que se devuelven)."""
    idioma = idioma_valido(idioma)
    original = idioma_original(compromiso)
    resultado = dict(compromiso)
    vista = original
    if idioma != original:
        t = (compromiso.get("traducciones") or {}).get(idioma)
        if isinstance(t, dict) and str(t.get("dijisteis") or "").strip() and str(t.get("hicimos") or "").strip():
            resultado["dijisteis"], resultado["hicimos"] = t["dijisteis"], t["hicimos"]
            vista = idioma
    resultado["idioma_vista"] = vista
    return resultado


def sin_comillas(texto: str) -> str:
    return "".join(c for c in str(texto) if c not in COMILLAS).strip()


def tiene_comillas(texto: str) -> bool:
    return any(c in COMILLAS for c in str(texto))


def formatear_fecha(dia: date, idioma: str = "es") -> str:
    """24/11/2026 (es, ca) o 24 Nov 2026 (en)."""
    if idioma_valido(idioma) == "en":
        return f"{dia.day} {_MESES_EN[dia.month - 1]} {dia.year}"
    return dia.strftime("%d/%m/%Y")


def fecha_desde_plazo(plazo, hoy: date | None = None) -> date:
    """"2 semanas" → hoy + 14 días; "1 mes" → +30; "10 días" → +10 (también en catalán e inglés).
    Si no se entiende ("Antes del próximo pulso"), 14 días."""
    hoy = hoy or date.today()
    encontrado = _UNIDAD.search(str(plazo or ""))
    if not encontrado:
        return hoy + timedelta(days=DIAS_POR_DEFECTO)
    cantidad = encontrado.group(1).lower()
    n = int(cantidad) if cantidad.isdigit() else 1
    unidad = encontrado.group(2).lower()
    dias = 1 if unidad.startswith(("d", "day")) else 7 if unidad.startswith(("sem", "set", "wee")) else 30
    return hoy + timedelta(days=max(1, n) * dias)


# ---------- comentarios literales ----------

def _palabras(texto: str) -> list[str]:
    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", str(texto).lower()) if not unicodedata.combining(c))
    return re.findall(r"\w+", sin_acentos)


def _grupos(palabras: list[str], n: int):
    return (tuple(palabras[i:i + n]) for i in range(len(palabras) - n + 1))


def copia_literal(texto: str, comentarios: list[str], n: int = PALABRAS_COPIA) -> bool:
    """¿Hay `n` palabras seguidas del texto que aparezcan igual en algún comentario?"""
    del_texto = set(_grupos(_palabras(texto), n))
    if not del_texto:
        return False
    return any(del_texto & set(_grupos(_palabras(c), n)) for c in comentarios if c)


# ---------- indicador (con qué se mide el compromiso) ----------

def _media_publicada(analisis: dict, pregunta: str, colectivo: str) -> dict | None:
    """La media de analisis["medias"] solo si existe (ya trae n ≥ UMBRAL_MINIMO)."""
    return next((m for m in analisis.get("medias", [])
                 if m.get("pregunta") == pregunta and m.get("colectivo") == colectivo
                 and m.get("n", 0) >= UMBRAL_MINIMO), None)


def indicador_por_defecto(analisis: dict, colectivos: list[str]) -> dict:
    """La pregunta escala_1_5 con la media más baja de esos colectivos (solo con n ≥ UMBRAL_MINIMO).
    Si no hay ninguna, el indicador sale con antes = null."""
    candidatas = [m for m in analisis.get("medias", []) if m.get("colectivo") in colectivos
                  and m.get("n", 0) >= UMBRAL_MINIMO]
    vacio = {"texto": None, "tipo": "escala_1_5", "dimension": None, "pregunta_origen": None,
             "colectivo": colectivos[0] if colectivos else None,
             "antes": None, "n_antes": None, "periodo_antes": None}
    if not candidatas:
        return vacio
    peor = min(candidatas, key=lambda m: (m["media"], m["colectivo"]))
    pregunta = next((p for p in analisis.get("preguntas", []) if p.get("id") == peor["pregunta"]), {})
    return {"texto": pregunta.get("texto") or None, "tipo": "escala_1_5",
            "dimension": pregunta.get("dimension") or None, "pregunta_origen": peor["pregunta"],
            "colectivo": peor["colectivo"], "antes": peor["media"], "n_antes": peor["n"],
            "periodo_antes": analisis.get("periodo_actual")}


def recalcular_antes(indicador: dict, analisis: dict) -> dict:
    """No nos fiamos del "antes" que llegue del cliente: se vuelve a leer del análisis (n ≥ UMBRAL_MINIMO)."""
    resultado = dict(indicador)
    media = _media_publicada(analisis, indicador.get("pregunta_origen"), indicador.get("colectivo"))
    resultado.update(antes=media["media"] if media else None, n_antes=media["n"] if media else None,
                     periodo_antes=analisis.get("periodo_actual") if media else None)
    return resultado


# ---------- seguimiento y "después" ----------

def pregunta_fija(encuesta: dict) -> dict | None:
    """La primera pregunta marcada con "fija": true (núcleo o de un sector)."""
    todas = list(encuesta.get("preguntas") or [])
    for lista in (encuesta.get("preguntas_por_colectivo") or {}).values():
        todas += lista
    return next((p for p in todas if p.get("fija") is True), None)


def calcular_despues(compromiso: dict) -> dict | None:
    """{"media", "n", "periodo", "simulado"} de la pregunta fija del seguimiento para el colectivo del
    indicador, en el último periodo del seguimiento. None si no hay seguimiento publicado o n < UMBRAL_MINIMO."""
    seguimiento_id = compromiso.get("seguimiento_id")
    colectivo = (compromiso.get("indicador") or {}).get("colectivo")
    if not seguimiento_id or not colectivo:
        return None
    seguimiento = almacen.leer_encuesta(seguimiento_id)
    if not seguimiento or seguimiento.get("estado") != "publicada":
        return None
    fija = pregunta_fija(seguimiento)
    if not fija:
        return None
    actual, _, periodo, _ = metricas.separar_periodos(almacen.leer_respuestas(seguimiento_id))
    del_colectivo = [r for r in actual if r.get("colectivo") == colectivo]
    valores = [r["valores"][fija["id"]] for r in del_colectivo
               if isinstance(r.get("valores", {}).get(fija["id"]), (int, float))
               and not isinstance(r["valores"][fija["id"]], bool)]
    if len(valores) < UMBRAL_MINIMO:
        return None
    simulado = any(r.get("tema_real") for r in del_colectivo)
    return {"media": round(sum(valores) / len(valores), 1), "n": len(valores), "periodo": periodo,
            "simulado": simulado}


def vincular_seguimiento(compromiso_id: str, encuesta_id: str) -> None:
    """Al publicar una encuesta con compromiso_id: el compromiso apunta a ella (la última publicada)."""
    almacen.actualizar_compromiso(compromiso_id, {"seguimiento_id": encuesta_id})


# ---------- vistas ----------

def vista(compromiso: dict, idioma: str = "es") -> dict:
    """Textos en `idioma` y el "después" calculado ahora mismo."""
    resultado = en_idioma(compromiso, idioma)
    resultado["despues"] = calcular_despues(compromiso)
    return resultado


def de_encuesta(encuesta_id: str, idioma: str = "es") -> list[dict]:
    """Compromisos hechos sobre esta encuesta o cuyo seguimiento es esta encuesta."""
    return [vista(c, idioma) for c in almacen.leer_compromisos()
            if c.get("encuesta_id") == encuesta_id or c.get("seguimiento_id") == encuesta_id]


def para_publico(colectivos: list[str], idioma: str = "es", maximo: int = 2) -> list[dict]:
    """Lo que ve quien responde: compromisos cuyos colectivos se cruzan con los de la encuesta (de
    CUALQUIER encuesta), los más recientes, solo {dijisteis, hicimos, fecha, estado}."""
    propios = set(colectivos)
    cercanos = [c for c in almacen.leer_compromisos()
                if c.get("estado") in ESTADOS and propios & set(c.get("colectivos") or [])]
    cercanos.sort(key=lambda c: c.get("id", ""), reverse=True)
    salida = []
    for c in cercanos[:maximo]:
        v = en_idioma(c, idioma)
        salida.append({"dijisteis": v["dijisteis"], "hicimos": v["hicimos"], "fecha": c.get("fecha"),
                       "estado": c.get("estado")})
    return salida


def para_zona(vistas: list[dict], colectivo: str) -> list[dict]:
    """Para la maqueta: [{tema, estado, antes, despues}] de los compromisos que incluyen ese colectivo.
    "antes" y "despues" solo si el indicador mide ese colectivo."""
    salida = []
    for c in vistas:
        if colectivo not in (c.get("colectivos") or []):
            continue
        indicador = c.get("indicador") or {}
        mide_aqui = indicador.get("colectivo") == colectivo
        salida.append({"id": c.get("id"), "tema": c.get("tema"), "estado": c.get("estado"),
                       "antes": indicador.get("antes") if mide_aqui else None,
                       "despues": (c.get("despues") or {}).get("media") if mide_aqui else None})
    return salida
