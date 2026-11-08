"""Rutas de las pantallas de RRHH · UPC 2 (modulos.md sección 3 y v2.md secciones 1.5 y 3.3)."""
import copy
import json
import os
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api import ia_o_respaldo as ia
from backend.api import simulacion, traducciones
from backend.api.qr import generar_qr
from backend.api.validacion import colectivos_de, etiqueta_colectivo, validar_necesidad, validar_preguntas
from backend.datos import almacen, metricas
from backend.reglas import IDIOMAS, idioma_valido

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
    origen_defecto = "ia" if ia.hay_llm() else "reglas"
    for t in temas:
        t.setdefault("resumen_origen", origen_defecto)
        t.setdefault("n_anterior", 0)
        t.setdefault("pct", round(t["n"] / total, 3) if total else 0.0)
        t.setdefault("pct_anterior", round(t["n_anterior"] / total_antes, 3) if total_antes else None)
    return temas


def analisis_y_recomendaciones(encuesta: dict, idioma: str = "es") -> tuple[dict, dict]:
    """Análisis y recomendaciones con las frases del backend y de la IA en `idioma`.
    Los textos de RRHH (título y preguntas) salen traducidos si existe traducciones[idioma]."""
    idioma = idioma_valido(idioma)
    vista = traducciones.aplicar(encuesta, idioma)  # mismos ids, textos en el idioma si hay traducción
    respuestas = almacen.leer_respuestas(encuesta["id"])
    base = metricas.calcular_metricas(respuestas, almacen.leer_plantilla(), vista, idioma)
    actual, anterior, _, _ = metricas.separar_periodos(respuestas)

    temas = _completar_temas(ia.analizar_comentarios(actual, anterior, idioma), actual, anterior)

    con_texto = [r for r in actual if r.get("comentario")]
    textos = [r["comentario"] for r in con_texto]
    temas_por_respuesta = dict(zip((r["id"] for r in con_texto), ia.clasificar_comentarios(textos))) if textos else {}
    zonas = metricas.calcular_zonas(actual, anterior, base["participacion"], encuesta,
                                    base["alertas"], temas_por_respuesta)

    analisis = {"encuesta_id": encuesta["id"], "titulo": vista.get("titulo", ""), "idioma": idioma, **base,
                "temas": temas, "zonas": zonas, "lectura": "", "estado_ia": {}}
    recomendaciones = ia.recomendar(analisis, encuesta, idioma)
    analisis["lectura"] = recomendaciones.get("lectura", "")

    llm = ia.hay_llm()
    clasificacion = ia.estado_clasificacion(textos) if textos else {"total": 0, "por_ia": 0}
    en_marcha = ia.pendientes()
    origen = recomendaciones.get("origen", "reglas")
    resumenes_listos = not any(t.get("resumen_origen") == "pendiente" for t in temas)
    recomendaciones_listas = origen != "pendiente"
    analisis["estado_ia"] = {
        "llm": llm, "pendientes": en_marcha,
        "comentarios_total": clasificacion.get("total", 0), "comentarios_ia": clasificacion.get("por_ia", 0),
        "listo": en_marcha == 0 and resumenes_listos and recomendaciones_listas
                 and (not llm or clasificacion.get("por_ia", 0) >= clasificacion.get("total", 0)),
        "origen_recomendaciones": origen,
        "resumenes_listos": resumenes_listos,
        "recomendaciones_listas": recomendaciones_listas,
    }
    return analisis, recomendaciones


# ---------- rutas ----------

@router.get("/salud")
def salud():
    return {"ok": True, "llm": ia.hay_llm(), "modo_demo": modo_demo()}


def _en_idioma(valor, idioma: str):
    """{"es": …, "ca": …, "en": …} → el del idioma (o castellano). Cualquier otro valor, tal cual."""
    if isinstance(valor, dict) and valor and set(valor) <= set(IDIOMAS):
        return valor.get(idioma) or valor.get("es") or next(iter(valor.values()))
    return valor


@router.get("/escenarios")
def escenarios(idioma: str = "es"):
    """contenido/escenarios.json (UAB 2) en el idioma pedido; si no existe, los de backend/api/escenarios.py."""
    idioma = idioma_valido(idioma)
    archivo = almacen.CONTENIDO / "escenarios.json"
    if archivo.exists():
        lista = json.loads(archivo.read_text(encoding="utf-8"))
    else:
        from backend.api.escenarios import ESCENARIOS
        lista = ESCENARIOS
    return [{k: (v if k == "necesidad" else _en_idioma(v, idioma)) for k, v in e.items()} for e in lista]


@router.get("/encuestas")
def listar(idioma: str = "es"):
    """Resumen de las encuestas; el título, traducido si existe traducciones[idioma]."""
    idioma = idioma_valido(idioma)
    lista = almacen.listar_encuestas()
    if idioma != "es":
        for fila in lista:
            encuesta = almacen.leer_encuesta(fila["id"]) or {}
            titulo = ((encuesta.get("traducciones") or {}).get(idioma) or {}).get("titulo")
            if isinstance(titulo, str) and titulo.strip():
                fila["titulo"] = titulo
    return lista


def _desde_necesidad(necesidad: dict, encuesta_id: str, periodo: str) -> dict:
    """Genera una Encuesta en borrador a partir de una Necesidad ya validada (generar y regenerar)."""
    encuesta = ia.generar_encuesta(necesidad, almacen.leer_reglas())
    colectivos = colectivos_de(encuesta) or colectivos_de(necesidad)
    encuesta.setdefault("origen", "ia")
    encuesta.setdefault("preguntas_por_colectivo", {})
    encuesta.update(id=encuesta_id, estado="borrador", periodo=periodo, url=None, qr=None,
                    colectivos=colectivos, colectivo=etiqueta_colectivo(colectivos),
                    necesidad=copy.deepcopy(necesidad))  # para volver al paso 1 con sus datos
    return traducciones.reiniciar(encuesta)


@router.post("/encuestas/generar")
def generar(necesidad: dict):
    validar_necesidad(necesidad)
    encuesta = _desde_necesidad(necesidad, "", date.today().strftime("%Y-%m"))  # la IA puede tardar: sin bloqueo
    with traducciones.bloqueo:
        encuesta["id"] = almacen.nuevo_id_encuesta()
        return almacen.guardar_encuesta(encuesta)


@router.post("/encuestas/{encuesta_id}/regenerar")
def regenerar(encuesta_id: str, necesidad: dict):
    """Preguntas nuevas con otra Necesidad: mismo id y periodo, vuelve a borrador."""
    validar_necesidad(necesidad)
    actual = obtener(encuesta_id)
    if actual["estado"] == "publicada":
        raise HTTPException(409, "No se puede regenerar una encuesta publicada: duplícala para editarla")
    nueva = _desde_necesidad(necesidad, encuesta_id, actual.get("periodo") or date.today().strftime("%Y-%m"))
    with traducciones.bloqueo:
        if obtener(encuesta_id)["estado"] == "publicada":
            raise HTTPException(409, "La encuesta se ha publicado mientras se regeneraba")
        return almacen.guardar_encuesta(nueva)


@router.post("/encuestas/{encuesta_id}/duplicar")
def duplicar(encuesta_id: str):
    """Copia en borrador con id nuevo (mismas preguntas y necesidad, sin respuestas)."""
    with traducciones.bloqueo:
        copia = copy.deepcopy(obtener(encuesta_id))
        for campo in ("url", "qr", "traducciones"):
            copia.pop(campo, None)
        copia.update(id=almacen.nuevo_id_encuesta(), estado="borrador", periodo=date.today().strftime("%Y-%m"),
                     url=None, qr=None)
        return almacen.guardar_encuesta(traducciones.reiniciar(copia))


@router.get("/encuestas/{encuesta_id}")
def ver(encuesta_id: str, idioma: str = "es"):
    """Siempre la encuesta original: es la que RRHH edita y guarda con PUT.
    (Si devolviéramos los textos traducidos, al guardar se perderían los originales.)
    Las traducciones van en encuesta["traducciones"] por si la pantalla quiere mostrarlas."""
    idioma_valido(idioma)
    return obtener(encuesta_id)


@router.put("/encuestas/{encuesta_id}")
def editar(encuesta_id: str, editada: dict):
    with traducciones.bloqueo:
        actual = obtener(encuesta_id)
        if actual["estado"] == "publicada":
            raise HTTPException(409, "No se puede editar una encuesta publicada")
        nueva = dict(editada, id=actual["id"], periodo=actual["periodo"], estado="borrador", url=None, qr=None,
                     colectivos=colectivos_de(actual), colectivo=actual.get("colectivo"),
                     origen=actual.get("origen", "ia"),
                     necesidad=actual.get("necesidad"))  # si estaba aprobada, vuelve a borrador
        nueva.setdefault("preguntas_por_colectivo", {})
        validar_preguntas(nueva)
        if traducciones.firma(nueva) == traducciones.firma(actual) and actual.get("estado_traduccion") == "lista":
            nueva["traducciones"] = actual.get("traducciones", {})  # sin cambios de texto: se conservan
            nueva["estado_traduccion"] = "lista"
        else:
            traducciones.reiniciar(nueva)
        return almacen.guardar_encuesta(nueva)


@router.post("/encuestas/{encuesta_id}/aprobar")
def aprobar(encuesta_id: str):
    with traducciones.bloqueo:
        encuesta = obtener(encuesta_id)
        if encuesta["estado"] == "publicada":
            raise HTTPException(409, "La encuesta ya está publicada")
        validar_preguntas(encuesta)
        encuesta["estado"] = "aprobada"
        encuesta.setdefault("traducciones", {})
        encuesta.setdefault("estado_traduccion", "pendiente")
        guardada = almacen.guardar_encuesta(encuesta)
    traducciones.lanzar(guardada)  # en segundo plano: al publicar normalmente ya está
    return guardada


@router.post("/encuestas/{encuesta_id}/publicar")
def publicar(encuesta_id: str):
    with traducciones.bloqueo:
        encuesta = obtener(encuesta_id)
        if encuesta["estado"] != "aprobada":
            raise HTTPException(409, f"No se puede publicar: la encuesta está '{encuesta['estado']}' y debe estar aprobada")
        url = f"{base_url()}/responder/{encuesta_id}"
        encuesta.update(estado="publicada", url=url, qr=generar_qr(url))
        encuesta.setdefault("traducciones", {})
        encuesta.setdefault("estado_traduccion", "pendiente")  # se publica aunque siga pendiente (v4 P1)
        guardada = almacen.guardar_encuesta(encuesta)
    if guardada.get("estado_traduccion") != "lista":
        traducciones.lanzar(guardada)  # por si la de aprobar falló o no llegó a lanzarse
    return guardada


@router.get("/encuestas/{encuesta_id}/analisis")
def analisis(encuesta_id: str, idioma: str = "es"):
    return analisis_y_recomendaciones(obtener(encuesta_id), idioma)[0]


@router.get("/encuestas/{encuesta_id}/recomendaciones")
def recomendaciones(encuesta_id: str, idioma: str = "es"):
    return analisis_y_recomendaciones(obtener(encuesta_id), idioma)[1]


@router.get("/encuestas/{encuesta_id}/sugerencias")
def sugerencias(encuesta_id: str, idioma: str = "es"):
    """Preguntas sugeridas para "Pregunta a tus datos" (las propone la IA; sin IA, ninguna)."""
    datos, _ = analisis_y_recomendaciones(obtener(encuesta_id), idioma)
    return ia.sugerir_preguntas(datos, idioma_valido(idioma))


@router.post("/encuestas/{encuesta_id}/preguntar")
def preguntar(encuesta_id: str, cuerpo: dict, idioma: str = "es"):
    pregunta = cuerpo.get("pregunta")
    if not isinstance(pregunta, str):
        raise HTTPException(422, "Envía {\"pregunta\": \"…\"}")
    idioma = idioma_valido(cuerpo.get("idioma") or idioma)
    datos, recs = analisis_y_recomendaciones(obtener(encuesta_id), idioma)
    return ia.preguntar(pregunta.strip()[:300], datos, recs, idioma)


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
