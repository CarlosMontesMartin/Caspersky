"""Rutas de las pantallas de RRHH · UPC 2 (modulos.md sección 3 y v2.md secciones 1.5 y 3.3)."""
import json
import os
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api import ia_o_respaldo as ia
from backend.api import simulacion
from backend.api.qr import generar_qr
from backend.api.validacion import colectivos_de, etiqueta_colectivo, validar_necesidad, validar_preguntas
from backend.datos import almacen, metricas

router = APIRouter()


def base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def modo_demo() -> bool:
    return os.getenv("MODO_DEMO", "0").strip().lower() in ("1", "true", "si", "sí")


def obtener(encuesta_id: str) -> dict:
    encuesta = almacen.leer_encuesta(encuesta_id)
    if encuesta is None:
        raise HTTPException(404, f"No existe la encuesta {encuesta_id}")
    return encuesta


# ---------- análisis (rápido: lo lento de la IA va en segundo plano en UPC 1) ----------

def _completar_temas(temas: list, actual: list, anterior: list) -> list:
    """Garantiza n_anterior, pct y pct_anterior aunque la versión de UPC 1 aún no los traiga."""
    total = sum(1 for r in actual if r.get("comentario"))
    total_antes = sum(1 for r in anterior if r.get("comentario"))
    for t in temas:
        t.setdefault("n_anterior", 0)
        t.setdefault("pct", round(t["n"] / total, 3) if total else 0.0)
        t.setdefault("pct_anterior", round(t["n_anterior"] / total_antes, 3) if total_antes else None)
    return temas


def analisis_y_recomendaciones(encuesta: dict) -> tuple[dict, dict]:
    respuestas = almacen.leer_respuestas(encuesta["id"])
    base = metricas.calcular_metricas(respuestas, almacen.leer_plantilla(), encuesta)
    actual, anterior, _, _ = metricas.separar_periodos(respuestas)

    temas = _completar_temas(ia.analizar_comentarios(actual, anterior), actual, anterior)

    con_texto = [r for r in actual if r.get("comentario")]
    textos = [r["comentario"] for r in con_texto]
    temas_por_respuesta = dict(zip((r["id"] for r in con_texto), ia.clasificar_comentarios(textos))) if textos else {}
    zonas = metricas.calcular_zonas(actual, anterior, base["participacion"], encuesta,
                                    base["alertas"], temas_por_respuesta)

    analisis = {"encuesta_id": encuesta["id"], "titulo": encuesta.get("titulo", ""), **base,
                "temas": temas, "zonas": zonas, "lectura": "", "estado_ia": {}}
    recomendaciones = ia.recomendar(analisis, encuesta)
    analisis["lectura"] = recomendaciones.get("lectura", "")

    llm = ia.hay_llm()
    clasificacion = ia.estado_clasificacion(textos) if textos else {"total": 0, "por_ia": 0}
    en_marcha = ia.pendientes()
    origen = recomendaciones.get("origen", "reglas")
    analisis["estado_ia"] = {
        "llm": llm, "pendientes": en_marcha,
        "comentarios_total": clasificacion.get("total", 0), "comentarios_ia": clasificacion.get("por_ia", 0),
        "listo": en_marcha == 0 and (not llm or (clasificacion.get("por_ia", 0) >= clasificacion.get("total", 0)
                                                 and origen == "ia")),
        "origen_recomendaciones": origen,
    }
    return analisis, recomendaciones


# ---------- rutas ----------

@router.get("/salud")
def salud():
    return {"ok": True, "llm": ia.hay_llm(), "modo_demo": modo_demo()}


@router.get("/escenarios")
def escenarios():
    """contenido/escenarios.json (UAB 2) si existe; si no, los escenarios de respaldo de backend/api."""
    archivo = almacen.CONTENIDO / "escenarios.json"
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    from backend.api.escenarios import ESCENARIOS
    return ESCENARIOS


@router.get("/encuestas")
def listar():
    return almacen.listar_encuestas()


@router.post("/encuestas/generar")
def generar(necesidad: dict):
    validar_necesidad(necesidad)
    encuesta = ia.generar_encuesta(necesidad, almacen.leer_reglas())
    colectivos = colectivos_de(encuesta) or colectivos_de(necesidad)
    encuesta.setdefault("origen", "ia")
    encuesta.setdefault("preguntas_por_colectivo", {})
    encuesta.update(id=almacen.nuevo_id_encuesta(), estado="borrador", periodo=date.today().strftime("%Y-%m"),
                    url=None, qr=None, colectivos=colectivos, colectivo=etiqueta_colectivo(colectivos))
    return almacen.guardar_encuesta(encuesta)


@router.get("/encuestas/{encuesta_id}")
def ver(encuesta_id: str):
    return obtener(encuesta_id)


@router.put("/encuestas/{encuesta_id}")
def editar(encuesta_id: str, editada: dict):
    actual = obtener(encuesta_id)
    if actual["estado"] == "publicada":
        raise HTTPException(409, "No se puede editar una encuesta publicada")
    nueva = dict(editada, id=actual["id"], periodo=actual["periodo"], estado="borrador", url=None, qr=None,
                 colectivos=colectivos_de(actual), colectivo=actual.get("colectivo"),
                 origen=actual.get("origen", "ia"))  # si estaba aprobada, vuelve a borrador
    nueva.setdefault("preguntas_por_colectivo", {})
    validar_preguntas(nueva)
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
    return analisis_y_recomendaciones(obtener(encuesta_id))[0]


@router.get("/encuestas/{encuesta_id}/recomendaciones")
def recomendaciones(encuesta_id: str):
    return analisis_y_recomendaciones(obtener(encuesta_id))[1]


@router.post("/encuestas/{encuesta_id}/preguntar")
def preguntar(encuesta_id: str, cuerpo: dict):
    pregunta = cuerpo.get("pregunta")
    if not isinstance(pregunta, str):
        raise HTTPException(422, "Envía {\"pregunta\": \"…\"}")
    datos, recs = analisis_y_recomendaciones(obtener(encuesta_id))
    return ia.preguntar(pregunta.strip()[:300], datos, recs)


@router.post("/encuestas/{encuesta_id}/simular")
def simular(encuesta_id: str, opciones: dict | None = None):
    """Solo con MODO_DEMO=1. Opciones: {"n": 40, "con_periodo_anterior": true, "semilla": null}."""
    if not modo_demo():
        raise HTTPException(403, "Solo disponible con MODO_DEMO=1 en el .env")
    encuesta = obtener(encuesta_id)
    if encuesta["estado"] != "publicada":
        raise HTTPException(409, "Solo se pueden simular respuestas de una encuesta publicada")
    opciones = opciones or {}
    n = opciones.get("n", 40)
    if not isinstance(n, int) or not 1 <= n <= 500:
        raise HTTPException(422, "n debe ser un entero entre 1 y 500")
    respuestas = simulacion.simular(encuesta, n, bool(opciones.get("con_periodo_anterior", True)),
                                    opciones.get("semilla"))
    for respuesta in respuestas:
        almacen.anadir_respuesta(encuesta_id, respuesta)
    return {"simuladas": len(respuestas), "periodos": sorted({r["periodo"] for r in respuestas})}
