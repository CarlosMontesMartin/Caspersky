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
    validar_respuesta_entrada(entrada, encuesta)
    tipos = {p["id"]: p["tipo"] for p in encuesta["preguntas"]}
    valores = {k: anonimizar(v) if tipos[k] == "texto" else v for k, v in entrada.get("valores", {}).items()}
    hoy = date.today()
    # Solo los campos del contrato: nada de IP, user agent ni hora exacta.
    almacen.anadir_respuesta(encuesta_id, {
        "id": f"r_{uuid.uuid4().hex[:8]}",
        "encuesta_id": encuesta_id,
        "fecha": hoy.isoformat(),
        "periodo": hoy.strftime("%Y-%m"),
        "colectivo": encuesta["colectivo"],
        "centro_tipo": CENTRO_TIPO.get(encuesta["colectivo"], "oficina"),
        "turno": entrada["turno"],
        "canal": entrada.get("canal", "qr"),
        "valores": valores,
        "comentario": anonimizar(entrada.get("comentario")),
    })
    return {"ok": True}
