"""API de escucha activa Damm.

Arranque: ./run.sh  ·  Documentación: http://localhost:8000/docs
"""
import threading
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

from backend.api import compromisos, rutas_encuestas, rutas_publico, teams  # noqa: E402  (después de cargar .env)
from backend.datos import almacen  # noqa: E402

FRONTEND = RAIZ / "frontend"
EJEMPLOS = RAIZ / "docs" / "ejemplos"


def precalentar_ia() -> None:
    """Al arrancar, con IA, prepara en segundo plano el análisis de las encuestas publicadas
    (clasificación, resúmenes, lectura, recomendaciones y sugerencias) para que el dashboard
    se abra ya listo. Idiomas en PRECALENTAR_IDIOMAS (por defecto "es"; p. ej. "es,ca")."""
    import os
    from backend.api import ia_o_respaldo as ia
    from backend.api.rutas_encuestas import analisis_y_recomendaciones
    if not ia.hay_llm():
        return
    try:
        from backend.ia import segundo_plano
    except Exception:
        return
    idiomas = [i.strip() for i in os.getenv("PRECALENTAR_IDIOMAS", "es").split(",") if i.strip()]
    for _ in range(5):  # cada vuelta lanza lo que ya se puede lanzar y espera a que acabe
        listo = True
        for fila in almacen.listar_encuestas():
            encuesta = almacen.leer_encuesta(fila["id"]) if fila.get("estado") == "publicada" else None
            if not encuesta:
                continue
            for idioma in idiomas:
                try:
                    datos, _ = analisis_y_recomendaciones(encuesta, idioma)
                    sugerencias = ia.sugerir_preguntas(datos, idioma)
                except Exception as error:
                    print(f"[precalentar] {fila['id']} ({idioma}): {error!r}")
                    continue
                listo = listo and datos["estado_ia"]["listo"] and sugerencias.get("origen") != "pendiente"
        if listo:
            print("[precalentar] análisis con IA listo")
            return
        segundo_plano.esperar(timeout=120)
    print("[precalentar] la IA no ha terminado en el tiempo previsto; el dashboard seguirá esperándola")


@asynccontextmanager
async def arranque(app):
    almacen.inicializar()
    threading.Thread(target=precalentar_ia, name="precalentar-ia", daemon=True).start()
    yield


app = FastAPI(
    title="Escucha activa · API",
    version="1.0.0",
    description=(
        "Plataforma de escucha activa para RRHH: microencuestas generadas con IA y validadas por "
        "personas, formulario público multilingüe, análisis agregado con umbral de anonimato y "
        "compromisos «Dijisteis → Hemos hecho». Todos los datos son sintéticos."
    ),
    lifespan=arranque,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(rutas_encuestas.router)
app.include_router(rutas_publico.router)
app.include_router(teams.router)
app.include_router(compromisos.router)


@app.exception_handler(StarletteHTTPException)
async def ruta_inexistente(request: Request, exc: StarletteHTTPException):
    """El frontend se sirve con StaticFiles en "/": un POST/PUT/DELETE a una ruta que este servidor
    no tiene acaba ahí y da 405. Lo convertimos en un 404 que explica la causa más probable."""
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
