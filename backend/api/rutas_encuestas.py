"""Rutas de las pantallas de RRHH · UPC 2 (ver modulos.md, sección 3)."""
import os
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api import ia_o_respaldo as ia
from backend.api.qr import generar_qr
from backend.api.validacion import validar_necesidad, validar_preguntas
from backend.datos import almacen, metricas

router = APIRouter()


def base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def obtener(encuesta_id: str) -> dict:
    encuesta = almacen.leer_encuesta(encuesta_id)
    if encuesta is None:
        raise HTTPException(404, f"No existe la encuesta {encuesta_id}")
    return encuesta


def construir_analisis(encuesta: dict) -> dict:
    respuestas = almacen.leer_respuestas(encuesta["id"])
    resultado = metricas.calcular_metricas(respuestas, almacen.leer_plantilla(), encuesta)
    actual, anterior, _, _ = metricas.separar_periodos(respuestas)
    return {"encuesta_id": encuesta["id"], **resultado, "temas": ia.analizar_comentarios(actual, anterior)}


@router.get("/salud")
def salud():
    return {"ok": True, "llm": ia.hay_llm()}


@router.get("/encuestas")
def listar():
    return almacen.listar_encuestas()


@router.post("/encuestas/generar")
def generar(necesidad: dict):
    validar_necesidad(necesidad)
    encuesta = ia.generar_encuesta(necesidad, almacen.leer_reglas())
    encuesta.update(id=almacen.nuevo_id_encuesta(), estado="borrador",
                    periodo=date.today().strftime("%Y-%m"), url=None, qr=None)
    return almacen.guardar_encuesta(encuesta)


@router.get("/encuestas/{encuesta_id}")
def ver(encuesta_id: str):
    return obtener(encuesta_id)


@router.put("/encuestas/{encuesta_id}")
def editar(encuesta_id: str, editada: dict):
    actual = obtener(encuesta_id)
    if actual["estado"] == "publicada":
        raise HTTPException(409, "No se puede editar una encuesta publicada")
    validar_preguntas(editada)
    nueva = dict(editada, id=actual["id"], colectivo=actual["colectivo"], periodo=actual["periodo"],
                 estado="borrador", url=None, qr=None)  # si estaba aprobada, vuelve a borrador
    return almacen.guardar_encuesta(nueva)


@router.post("/encuestas/{encuesta_id}/aprobar")
def aprobar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    if encuesta["estado"] == "publicada":
        raise HTTPException(409, "La encuesta ya está publicada")
    validar_preguntas(encuesta)
    encuesta["estado"] = "aprobada"
    return almacen.guardar_encuesta(encuesta)


@router.post("/encuestas/{encuesta_id}/publicar")
def publicar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    if encuesta["estado"] != "aprobada":
        raise HTTPException(409, f"No se puede publicar: la encuesta está '{encuesta['estado']}' y debe estar aprobada")
    url = f"{base_url()}/responder/{encuesta_id}"
    encuesta.update(estado="publicada", url=url, qr=generar_qr(url))
    return almacen.guardar_encuesta(encuesta)


@router.get("/encuestas/{encuesta_id}/analisis")
def analisis(encuesta_id: str):
    return construir_analisis(obtener(encuesta_id))


@router.get("/encuestas/{encuesta_id}/recomendaciones")
def recomendaciones(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    return ia.recomendar(construir_analisis(encuesta), encuesta)
