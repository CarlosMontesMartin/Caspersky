"""Validaciones de entrada · UPC 2. Lanzan HTTPException 422 con un mensaje claro."""
from fastapi import HTTPException

COLECTIVOS = {"planta", "logistica", "comercial", "oficina", "manager"}
TIPOS = {"escala_1_5", "opcion", "si_no", "texto"}
DIMENSIONES = {"bienestar", "liderazgo", "desarrollo", "cultura", "entorno", "condiciones"}
CANALES_PUBLICOS = {"qr", "quiosco"}
TURNOS_PLANTA = ["manana", "tarde", "noche"]


def error(mensaje: str):
    raise HTTPException(422, mensaje)


def turnos_de(colectivo: str) -> list[str]:
    if colectivo == "planta":
        return TURNOS_PLANTA
    if colectivo == "todos":
        return TURNOS_PLANTA + ["sin_turno"]
    return ["sin_turno"]


def validar_necesidad(necesidad: dict) -> None:
    if not str(necesidad.get("objetivo", "")).strip():
        error("Falta el objetivo")
    if necesidad.get("colectivo") not in COLECTIVOS:
        error(f"colectivo debe ser uno de {sorted(COLECTIVOS)}")
    duracion = necesidad.get("duracion_max_seg")
    if not isinstance(duracion, int) or duracion <= 0:
        error("duracion_max_seg debe ser un número entero de segundos")
    if not isinstance(necesidad.get("temas_prohibidos", []), list):
        error("temas_prohibidos debe ser una lista")


def validar_preguntas(encuesta: dict) -> None:
    preguntas = encuesta.get("preguntas")
    if not isinstance(preguntas, list) or not 1 <= len(preguntas) <= 6:
        error("La encuesta debe tener entre 1 y 6 preguntas")
    ids = set()
    for p in preguntas:
        if not str(p.get("texto", "")).strip():
            error(f"La pregunta {p.get('id')} no tiene texto")
        if p.get("tipo") not in TIPOS:
            error(f"Tipo no válido en {p.get('id')}: {p.get('tipo')}")
        if p.get("dimension") not in DIMENSIONES:
            error(f"Dimensión no válida en {p.get('id')}: {p.get('dimension')}")
        if p.get("tipo") == "opcion" and not p.get("opciones"):
            error(f"La pregunta {p.get('id')} es de opción pero no tiene opciones")
        if p.get("id") in ids:
            error(f"Id de pregunta repetido: {p.get('id')}")
        ids.add(p.get("id"))


def validar_respuesta_entrada(entrada: dict, encuesta: dict) -> None:
    if entrada.get("turno") not in turnos_de(encuesta["colectivo"]):
        error(f"Turno no válido para {encuesta['colectivo']}: {entrada.get('turno')}")
    if entrada.get("canal", "qr") not in CANALES_PUBLICOS:
        error("canal debe ser qr o quiosco")
    valores = entrada.get("valores", {})
    if not isinstance(valores, dict):
        error("valores debe ser un objeto")
    preguntas = {p["id"]: p for p in encuesta["preguntas"]}
    for clave, valor in valores.items():
        p = preguntas.get(clave)
        if p is None:
            error(f"La pregunta {clave} no existe en esta encuesta")
        if p["tipo"] == "escala_1_5" and (not isinstance(valor, int) or not 1 <= valor <= 5):
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
