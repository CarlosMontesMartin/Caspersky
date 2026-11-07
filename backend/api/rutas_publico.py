"""Rutas para quien responde · UPC 2 (ver modulos.md, sección 3)."""
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api.validacion import turnos_de, validar_respuesta_entrada
from backend.datos import almacen
from backend.datos.anonimizar import anonimizar

router = APIRouter(prefix="/publico")
CENTRO_TIPO = {"planta": "fabrica", "logistica": "almacen"}  # resto -> oficina


def obtener_publicada(encuesta_id: str) -> dict:
    encuesta = almacen.leer_encuesta(encuesta_id)
    if encuesta is None or encuesta.get("estado") != "publicada":
        raise HTTPException(404, "Esta encuesta no existe o no está abierta")
    return encuesta


def construir_respuesta(encuesta: dict, entrada: dict, *, colectivo: str | None = None,
                        fecha: date | None = None, tema_real: str | None = None) -> dict:
    """Valida una RespuestaEntrada y la convierte en Respuesta (anonimizada).

    El texto libre (preguntas de tipo texto + campo comentario) se guarda SOLO
    en `comentario`; `valores` queda con escalas, opciones y sí/no.
    La usan la ruta pública y la simulación del modo demo: mismo camino para todo.
    """
    colectivo = colectivo or encuesta["colectivo"]
    validar_respuesta_entrada(entrada, encuesta, colectivo)
    tipos = {p["id"]: p["tipo"] for p in encuesta["preguntas"]}

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
        "valores": valores,
        "comentario": anonimizar(" / ".join(textos)),
    }
    if tema_real:  # solo en respuestas simuladas
        respuesta["tema_real"] = tema_real
    return respuesta


@router.get("/encuestas/{encuesta_id}")
def ver_publica(encuesta_id: str):
    e = obtener_publicada(encuesta_id)
    return {"id": e["id"], "titulo": e.get("titulo", ""), "intro": e.get("intro", ""),
            "colectivo": e["colectivo"], "tiempo_estimado_seg": e.get("tiempo_estimado_seg", 0),
            "preguntas": e["preguntas"], "turnos": turnos_de(e["colectivo"]),
            "transparencia": almacen.leer_transparencia()}


@router.post("/encuestas/{encuesta_id}/respuestas")
def responder(encuesta_id: str, entrada: dict):
    encuesta = obtener_publicada(encuesta_id)
    # Solo los campos del contrato: nada de IP, user agent ni hora exacta.
    almacen.anadir_respuesta(encuesta_id, construir_respuesta(encuesta, entrada))
    return {"ok": True}
