"""API de escucha activa Damm · UPC 2.

Fase 1 (esqueleto): los endpoints devuelven los ejemplos de contratos/ejemplos/
y las encuestas viven en memoria. La regla de estados ya es la real:
nada se publica sin aprobación humana.
"""
import base64
import copy
import io
import json
from pathlib import Path

import qrcode
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

RAIZ = Path(__file__).resolve().parents[2]
EJEMPLOS = RAIZ / "contratos" / "ejemplos"

app = FastAPI(title="Damm · Escucha activa", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# En memoria hasta tener la base de datos (backend/datos/).
ENCUESTAS: dict[str, dict] = {}


def ejemplo(nombre: str) -> dict:
    ruta = EJEMPLOS / f"{nombre}.json"
    if not ruta.exists():
        raise HTTPException(500, f"Falta el ejemplo contratos/ejemplos/{ruta.name}")
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener(encuesta_id: str) -> dict:
    if encuesta_id not in ENCUESTAS:
        raise HTTPException(404, f"No existe la encuesta {encuesta_id}")
    return ENCUESTAS[encuesta_id]


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
    encuesta["id"] = f"enc_{len(ENCUESTAS) + 1:03d}"
    encuesta["estado"] = "borrador"
    encuesta["colectivo"] = necesidad.get("colectivo", encuesta["colectivo"])
    encuesta["url"] = encuesta["qr"] = None
    ENCUESTAS[encuesta["id"]] = encuesta
    return encuesta


@app.put("/encuestas/{encuesta_id}")
def editar(encuesta_id: str, editada: dict):
    actual = obtener(encuesta_id)
    exigir_estado(actual, "borrador", "editar")
    nueva = copy.deepcopy(editada)
    # El cliente no puede cambiar id, estado, url ni qr.
    for campo in ("id", "estado", "url", "qr"):
        nueva[campo] = actual[campo]
    ENCUESTAS[encuesta_id] = nueva
    return nueva


@app.post("/encuestas/{encuesta_id}/aprobar")
def aprobar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    exigir_estado(encuesta, "borrador", "aprobar")
    encuesta["estado"] = "aprobada"
    # TODO (post-MVP): registrar quién aprobó y cuándo.
    return encuesta


@app.post("/encuestas/{encuesta_id}/publicar")
def publicar(encuesta_id: str):
    encuesta = obtener(encuesta_id)
    exigir_estado(encuesta, "aprobada", "publicar")
    # TODO: crear el formulario en Typeform (backend/typeform/).
    url = f"https://form.typeform.com/to/DEMO?colectivo={encuesta['colectivo']}&canal=qr"
    encuesta.update(estado="publicada", url=url, qr=qr_base64(url))
    return encuesta


@app.post("/encuestas/{encuesta_id}/sincronizar")
def sincronizar(encuesta_id: str):
    exigir_estado(obtener(encuesta_id), "publicada", "sincronizar")
    # TODO: leer respuestas de Typeform, anonimizar y guardar.
    return {"nuevas": 0}


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
