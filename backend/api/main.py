"""API de escucha activa Damm · UPC 2.

Fase 1 (esqueleto): los endpoints devuelven los ejemplos de contratos/ejemplos/
y las encuestas viven en memoria. La regla de estados ya es la real:
nada se publica sin aprobación humana.
"""
import base64
import copy
import io
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import qrcode
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.datos import almacen

RAIZ = Path(__file__).resolve().parents[2]
EJEMPLOS = RAIZ / "contratos" / "ejemplos"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CENTRO_TIPO = {"planta": "fabrica", "logistica": "almacen"}  # resto -> oficina

@asynccontextmanager
async def arranque(app):
    print("[almacen]", almacen.inicializar())
    yield


app = FastAPI(title="Damm · Escucha activa", version="0.2.0", lifespan=arranque)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def ejemplo(nombre: str) -> dict:
    ruta = EJEMPLOS / f"{nombre}.json"
    if not ruta.exists():
        raise HTTPException(500, f"Falta el ejemplo contratos/ejemplos/{ruta.name}")
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener(encuesta_id: str) -> dict:
    try:
        encuesta = almacen.leer_encuesta(encuesta_id)
    except ValueError:
        encuesta = None
    if encuesta is None:
        raise HTTPException(404, f"No existe la encuesta {encuesta_id}")
    return encuesta


def exigir_estado(encuesta: dict, estado: str, accion: str) -> None:
    if encuesta["estado"] != estado:
        raise HTTPException(
            409, f"No se puede {accion}: la encuesta está '{encuesta['estado']}', debe estar '{estado}'"
        )


def qr_base64(url: str) -> str:
    buffer = io.BytesIO()
    qrcode.make(url).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


@app.get("/salud")
def salud():
    return {"ok": True}


@app.post("/encuestas/generar")
def generar(necesidad: dict):
    # TODO: llamar a backend.ia.generar_encuesta(necesidad, reglas) de UPC 1.
    encuesta = ejemplo("encuesta")
    encuesta["id"] = almacen.nuevo_id()
    encuesta["estado"] = "borrador"
    encuesta["colectivo"] = necesidad.get("colectivo", encuesta["colectivo"])
    encuesta["url"] = encuesta["qr"] = None
    return almacen.guardar_encuesta(encuesta)


@app.get("/encuestas/{encuesta_id}")
def ver(encuesta_id: str):
    return obtener(encuesta_id)


@app.put("/encuestas/{encuesta_id}")
def editar(encuesta_id: str, editada: dict):
    actual = obtener(encuesta_id)
    exigir_estado(actual, "borrador", "editar")
    nueva = copy.deepcopy(editada)
    # El cliente no puede cambiar id, estado, url ni qr.
    for campo in ("id", "estado", "url", "qr"):
        nueva[campo] = actual[campo]
    return almacen.guardar_encuesta(nueva)


@app.post("/encuestas/{encuesta_id}/aprobar")
def aprobar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    exigir_estado(encuesta, "borrador", "aprobar")
    encuesta["estado"] = "aprobada"
    # TODO (post-MVP): registrar quién aprobó y cuándo.
    return almacen.guardar_encuesta(encuesta)


@app.post("/encuestas/{encuesta_id}/publicar")
def publicar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    exigir_estado(encuesta, "aprobada", "publicar")
    url = f"{FRONTEND_URL}/responder/{encuesta_id}?canal=qr"
    encuesta.update(estado="publicada", url=url, qr=qr_base64(url))
    return almacen.guardar_encuesta(encuesta)


@app.post("/encuestas/{encuesta_id}/respuestas", status_code=201)
def responder(encuesta_id: str, nueva: dict):
    encuesta = obtener(encuesta_id)
    exigir_estado(encuesta, "publicada", "responder")
    valores = dict(nueva.get("valores", {}))
    comentario = None
    for pregunta in encuesta["preguntas"]:
        if pregunta["tipo"] == "texto" and pregunta["id"] in valores:
            comentario = valores.pop(pregunta["id"])  # almacen lo anonimiza
    hoy = date.today()
    # Solo lo del contrato: nada de IP, user agent ni hora exacta.
    almacen.anadir_respuesta({
        "id": f"r_{uuid.uuid4().hex[:8]}",
        "encuesta_id": encuesta_id,
        "fecha": hoy.isoformat(),
        "periodo": hoy.strftime("%Y-%m"),
        "colectivo": encuesta["colectivo"],
        "centro_tipo": CENTRO_TIPO.get(encuesta["colectivo"], "oficina"),
        "turno": nueva.get("turno", "sin_turno"),
        "canal": nueva.get("canal", "qr"),
        "valores": valores,
        "comentario": comentario,
    })
    return {"ok": True}


@app.get("/encuestas/{encuesta_id}/analisis")
def analisis(encuesta_id: str):
    # TODO: calcular_metricas() + ia.analizar_comentarios().
    resultado = ejemplo("analisis")
    resultado["encuesta_id"] = encuesta_id
    return resultado


@app.get("/encuestas/{encuesta_id}/recomendaciones")
def recomendaciones(encuesta_id: str):
    # TODO: ia.recomendar(analisis).
    return ejemplo("recomendaciones")
