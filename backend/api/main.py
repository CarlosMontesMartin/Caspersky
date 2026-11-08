"""API de escucha activa Damm · UPC 2 (ver modulos.md, sección 3).

Arranque: ./run.sh  ·  Documentación: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")  # BASE_URL, LLM_API_KEY…

from backend.api import rutas_encuestas, rutas_publico, teams  # noqa: E402  (después de cargar .env)
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
app.include_router(teams.router)


@app.exception_handler(StarletteHTTPException)
async def ruta_inexistente(request: Request, exc: StarletteHTTPException):
    """El frontend se sirve con StaticFiles en "/": un POST/PUT/DELETE a una ruta que este servidor
    no tiene acaba ahí y da 405. Lo convertimos en un 404 que explica la causa más probable (v4 P0-2)."""
    if exc.status_code == 405 and request.method != "GET":
        return JSONResponse(status_code=404, content={
            "detail": f"No existe la ruta {request.method} {request.url.path} en este servidor. "
                      "¿Has reiniciado el servidor después de git pull?"})
    return await http_exception_handler(request, exc)


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
