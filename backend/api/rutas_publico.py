"""Rutas para quien responde · UPC 2 (modulos.md sección 3 y v2.md sección 3.3)."""
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api import traducciones
from backend.api.validacion import (colectivos_de, preguntas_de, turnos_de,
                                    turnos_por_colectivo, validar_respuesta_entrada)
from backend.datos import almacen
from backend.datos.anonimizar import anonimizar

router = APIRouter(prefix="/publico")
CENTRO_TIPO = {"planta": "fabrica", "logistica": "almacen"}  # resto -> oficina


def obtener_publicada(encuesta_id: str) -> dict:
    encuesta = almacen.leer_encuesta(encuesta_id)
    if encuesta is None or encuesta.get("estado") != "publicada":
        raise HTTPException(404, "Esta encuesta no existe o no está abierta")
    return encuesta


def colectivo_de_entrada(encuesta: dict, entrada: dict) -> str:
    """El de la entrada (obligatorio si la encuesta tiene varios) o el único de la encuesta."""
    colectivos = colectivos_de(encuesta)
    elegido = entrada.get("colectivo")
    if elegido is None:
        if len(colectivos) != 1:
            raise HTTPException(422, f"Indica tu colectivo: esta encuesta es para {colectivos}")
        return colectivos[0]
    if elegido not in colectivos:
        raise HTTPException(422, f"El colectivo {elegido!r} no es de esta encuesta")
    return elegido


def construir_respuesta(encuesta: dict, entrada: dict, *, colectivo: str | None = None,
                        fecha: date | None = None, tema_real: str | None = None) -> dict:
    """Valida una RespuestaEntrada y la convierte en Respuesta (anonimizada).

    El texto libre (preguntas de tipo texto + campo comentario) se guarda SOLO en
    `comentario`. La usan la ruta pública y la simulación: mismo camino para todo.
    """
    colectivo = colectivo or colectivo_de_entrada(encuesta, entrada)
    idioma = entrada.get("idioma", "es")
    if idioma not in traducciones.IDIOMAS:
        raise HTTPException(422, f"idioma debe ser uno de {traducciones.IDIOMAS}")
    preguntas = preguntas_de(encuesta, colectivo)
    if isinstance(entrada.get("valores"), dict):  # opción traducida → la del idioma original
        entrada = dict(entrada, valores=traducciones.valores_originales(entrada["valores"], encuesta, preguntas))
    validar_respuesta_entrada(entrada, encuesta, colectivo)
    tipos = {p["id"]: p["tipo"] for p in preguntas}

    valores, textos = {}, []
    for clave, valor in entrada.get("valores", {}).items():
        if tipos[clave] == "texto":
            if isinstance(valor, str) and valor.strip():
                textos.append(valor.strip())
        elif valor is not None and valor != "":
            valores[clave] = valor
    comentario = entrada.get("comentario")
    if isinstance(comentario, str) and comentario.strip():
        textos.append(comentario.strip())
    if not valores and not textos:
        raise HTTPException(422, "La respuesta está vacía: contesta al menos una pregunta")

    fecha = fecha or date.today()
    respuesta = {
        "id": f"r_{uuid.uuid4().hex[:8]}",
        "encuesta_id": encuesta["id"],
        "fecha": fecha.isoformat(),
        "periodo": fecha.strftime("%Y-%m"),
        "colectivo": colectivo,
        "centro_tipo": CENTRO_TIPO.get(colectivo, "oficina"),
        "turno": entrada["turno"],
        "canal": entrada.get("canal", "qr"),
        "idioma": idioma,
        "valores": valores,
        "comentario": anonimizar(" / ".join(textos)),
    }
    if tema_real:  # solo en respuestas simuladas
        respuesta["tema_real"] = tema_real
    return respuesta


@router.get("/encuestas/{encuesta_id}")
def ver_publica(encuesta_id: str, idioma: str = "es"):
    original = obtener_publicada(encuesta_id)
    idioma = traducciones.idioma_valido(idioma)
    e = traducciones.aplicar(original, idioma)
    colectivos = colectivos_de(original)
    return {"id": e["id"], "titulo": e.get("titulo", ""), "intro": e.get("intro", ""),
            "colectivo": e.get("colectivo", ""), "colectivos": colectivos,
            "tiempo_estimado_seg": e.get("tiempo_estimado_seg", 0),
            "idioma": idioma, "idiomas_disponibles": traducciones.idiomas_disponibles(original),
            "idioma_original": traducciones.idioma_original(original),
            "transparencia": almacen.leer_transparencia(idioma),
            "preguntas": e["preguntas"], "preguntas_por_colectivo": e.get("preguntas_por_colectivo") or {},
            "turnos": turnos_de(colectivos[0]) if colectivos else ["sin_turno"],
            "turnos_por_colectivo": turnos_por_colectivo(colectivos)}


@router.post("/encuestas/{encuesta_id}/respuestas")
def responder(encuesta_id: str, entrada: dict):
    encuesta = obtener_publicada(encuesta_id)
    # Solo los campos del contrato: nada de IP, user agent ni hora exacta.
    almacen.anadir_respuesta(encuesta_id, construir_respuesta(encuesta, entrada))
    return {"ok": True}

