"""API de escucha activa Damm · UPC 2 (ver modulos.md, sección 3).

Arranque: ./run.sh  ·  Documentación: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")  # BASE_URL, LLM_API_KEY…

from backend.api import rutas_encuestas, rutas_publico  # noqa: E402  (después de cargar .env)
from backend.datos import almacen  # noqa: E402

FRONTEND = RAIZ / "frontend"
EJEMPLOS = RAIZ / "contratos" / "ejemplos"


@asynccontextmanager
async def arranque(app):
    almacen.inicializar()
    yield


app = FastAPI(title="Damm · Escucha activa", version="0.3.0", lifespan=arranque)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(rutas_encuestas.router)
app.include_router(rutas_publico.router)


@app.get("/responder/{encuesta_id}", include_in_schema=False)
def pagina_responder(encuesta_id: str):
    pagina = FRONTEND / "responder.html"
    if not pagina.exists():
        raise HTTPException(404, "Falta frontend/responder.html")
    return FileResponse(pagina)


if EJEMPLOS.exists():
    app.mount("/ejemplos", StaticFiles(directory=EJEMPLOS), name="ejemplos")
# Al final: todo lo que no sea API se busca en frontend/ (index.html por defecto).
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
