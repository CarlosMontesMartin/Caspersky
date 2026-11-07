"""Validaciones y utilidades de colectivos · UPC 2 (v2.md, secciones 1.1 y 3.2).

Lanzan HTTPException 422 con un mensaje claro.
"""
from fastapi import HTTPException

ORDEN_COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
COLECTIVOS = set(ORDEN_COLECTIVOS)
TIPOS = {"escala_1_5", "opcion", "si_no", "texto"}
TIPOS_SECTOR = {"escala_1_5", "opcion", "si_no"}
DIMENSIONES = {"bienestar", "liderazgo", "desarrollo", "cultura", "entorno", "condiciones"}
CANALES_PUBLICOS = {"qr", "quiosco"}
TURNOS_PLANTA = ["manana", "tarde", "noche"]


def error(mensaje: str):
    raise HTTPException(422, mensaje)


# ---------- colectivos ----------

def colectivos_de(datos: dict) -> list[str]:
    """Colectivos de una Necesidad o Encuesta, en orden fijo. Acepta el formato nuevo y el antiguo."""
    lista = datos.get("colectivos")
    if isinstance(lista, list) and lista:
        return [c for c in ORDEN_COLECTIVOS if c in lista]
    colectivo = datos.get("colectivo")
    if colectivo == "todos":
        return list(ORDEN_COLECTIVOS)
    return [colectivo] if colectivo in COLECTIVOS else []


def etiqueta_colectivo(colectivos: list[str]) -> str:
    """El único colectivo, "todos" si están los 5, o "varios"."""
    if len(colectivos) == 1:
        return colectivos[0]
    return "todos" if set(colectivos) == COLECTIVOS else "varios"


def turnos_de(colectivo: str) -> list[str]:
    if colectivo == "planta":
        return list(TURNOS_PLANTA)
    if colectivo == "todos":  # compatibilidad con encuestas antiguas
        return TURNOS_PLANTA + ["sin_turno"]
    return ["sin_turno"]


def turnos_por_colectivo(colectivos: list[str]) -> dict[str, list[str]]:
    return {c: turnos_de(c) for c in colectivos}


def preguntas_de(encuesta: dict, colectivo: str) -> list[dict]:
    """Núcleo común + preguntas propias del colectivo (mismo comportamiento que en backend/ia/generar.py)."""
    return encuesta["preguntas"] + encuesta.get("preguntas_por_colectivo", {}).get(colectivo, [])


def todas_las_preguntas(encuesta: dict) -> list[dict]:
    propias = [p for lista in encuesta.get("preguntas_por_colectivo", {}).values() for p in lista]
    return encuesta.get("preguntas", []) + propias


# ---------- necesidad ----------

def validar_necesidad(necesidad: dict) -> None:
    if not str(necesidad.get("objetivo", "")).strip():
        error("Falta el objetivo")
    if "colectivos" in necesidad:
        lista = necesidad["colectivos"]
        if not isinstance(lista, list) or not lista:
            error("colectivos debe ser una lista con al menos un sector")
        malos = [c for c in lista if c not in COLECTIVOS]
        if malos:
            error(f"Colectivos no válidos: {malos}. Usa {ORDEN_COLECTIVOS}")
    elif necesidad.get("colectivo") not in COLECTIVOS | {"todos"}:
        error(f"Indica colectivos (lista) con valores de {ORDEN_COLECTIVOS}")
    duracion = necesidad.get("duracion_max_seg")
    if not isinstance(duracion, int) or duracion <= 0:
        error("duracion_max_seg debe ser un número entero de segundos")
    if not isinstance(necesidad.get("temas_prohibidos", []), list):
        error("temas_prohibidos debe ser una lista")


# ---------- encuesta ----------

def _validar_pregunta(p: dict, tipos_validos: set, donde: str) -> None:
    pid = p.get("id")
    if not pid or not isinstance(pid, str):
        error(f"Hay una pregunta sin id en {donde}")
    if not str(p.get("texto", "")).strip():
        error(f"La pregunta {pid} no tiene texto")
    if p.get("tipo") not in tipos_validos:
        error(f"Tipo no válido en {pid}: {p.get('tipo')} (en {donde} se admite {sorted(tipos_validos)})")
    if p.get("dimension") not in DIMENSIONES:
        error(f"Dimensión no válida en {pid}: {p.get('dimension')}")
    if p.get("tipo") == "opcion" and not p.get("opciones"):
        error(f"La pregunta {pid} es de opción pero no tiene opciones")


def validar_preguntas(encuesta: dict) -> None:
    nucleo = encuesta.get("preguntas")
    por_colectivo = encuesta.get("preguntas_por_colectivo") or {}
    if not isinstance(nucleo, list) or not isinstance(por_colectivo, dict):
        error("preguntas debe ser una lista y preguntas_por_colectivo un objeto")

    if not por_colectivo:  # un solo colectivo (o enc_000): como siempre
        if not 1 <= len(nucleo) <= 6:
            error("La encuesta debe tener entre 1 y 6 preguntas")
        for p in nucleo:
            _validar_pregunta(p, TIPOS, "la encuesta")
    else:
        colectivos = colectivos_de(encuesta)
        if not 1 <= len(nucleo) <= 3:
            error("El núcleo común debe tener entre 1 y 3 preguntas")
        for p in nucleo:
            _validar_pregunta(p, TIPOS, "el núcleo común")
        if not any(p["tipo"] == "escala_1_5" for p in nucleo):
            error("El núcleo común necesita al menos una pregunta de escala 1–5")
        textos = [i for i, p in enumerate(nucleo) if p["tipo"] == "texto"]
        if len(textos) > 1 or (textos and textos[0] != len(nucleo) - 1):
            error("El núcleo admite como máximo una pregunta de texto, y debe ser la última")
        sobran = set(por_colectivo) - set(colectivos)
        if sobran:
            error(f"Hay preguntas para sectores que no son de la encuesta: {sorted(sobran)}")
        for colectivo in colectivos:
            propias = por_colectivo.get(colectivo, [])
            if not 1 <= len(propias) <= 3:
                error(f"{colectivo} debe tener entre 1 y 3 preguntas propias")
            for p in propias:
                _validar_pregunta(p, TIPOS_SECTOR, f"las preguntas de {colectivo}")
            if not 3 <= len(nucleo) + len(propias) <= 6:
                error(f"{colectivo} debe tener entre 3 y 6 preguntas en total (núcleo + propias)")

    ids = [p["id"] for p in todas_las_preguntas(encuesta)]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        error(f"Ids de pregunta repetidos: {repetidos}")


# ---------- respuesta ----------

def validar_respuesta_entrada(entrada: dict, encuesta: dict, colectivo: str) -> None:
    if colectivo not in colectivos_de(encuesta):
        error(f"El colectivo {colectivo!r} no es de esta encuesta")
    if entrada.get("turno") not in turnos_de(colectivo):
        error(f"Turno no válido para {colectivo}: {entrada.get('turno')}")
    if entrada.get("canal", "qr") not in CANALES_PUBLICOS:
        error("canal debe ser qr o quiosco")
    valores = entrada.get("valores", {})
    if not isinstance(valores, dict):
        error("valores debe ser un objeto")
    preguntas = {p["id"]: p for p in preguntas_de(encuesta, colectivo)}
    for clave, valor in valores.items():
        p = preguntas.get(clave)
        if p is None:
            error(f"La pregunta {clave} no es de esta encuesta para {colectivo}")
        if valor is None or valor == "":
            continue  # pregunta sin contestar
        if p["tipo"] == "escala_1_5" and (not isinstance(valor, int) or isinstance(valor, bool) or not 1 <= valor <= 5):
            error(f"{clave} debe ser un número del 1 al 5")
        if p["tipo"] == "si_no" and valor not in ("si", "no"):
            error(f"{clave} debe ser 'si' o 'no'")
        if p["tipo"] == "opcion" and valor not in p.get("opciones", []):
            error(f"{clave} debe ser una de las opciones")
        if p["tipo"] == "texto" and (not isinstance(valor, str) or len(valor) > 1000):
            error(f"{clave} debe ser texto de hasta 1000 caracteres")
    comentario = entrada.get("comentario")
    if comentario is not None and (not isinstance(comentario, str) or len(comentario) > 1000):
        error("comentario debe ser texto de hasta 1000 caracteres")
