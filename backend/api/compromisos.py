"""Compromisos "Dijisteis → Hemos hecho".

  GET  /encuestas/{id}/compromisos/borrador?accion=<i>&idioma=   borrador (la IA propone; NO guarda nada)
  POST /encuestas/{id}/compromisos                               RRHH firma: guarda y traduce en 2º plano
  GET  /encuestas/{id}/compromisos?idioma=                       lista con el "después" ya calculado
  POST /compromisos/{cid}/hecho                                  estado = "hecho"
  GET  /compromisos/{cid}/seguimiento?idioma=                    Necesidad lista para crear.html
Teams (vista previa y envío) está en teams.py y el campo "compromisos" de la encuesta pública, en
rutas_publico.py. La lógica (sin FastAPI) está en backend/datos/compromisos.py.

La IA propone; una persona firma: nada se guarda ni se enseña a la plantilla hasta el POST, que exige
"hemos hecho" y "responsable" escritos por RRHH.
"""
import re
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date

from fastapi import APIRouter, HTTPException

from backend import reglas
from backend.api import ia_o_respaldo as ia
from backend.api import rutas_encuestas
from backend.api.validacion import DIMENSIONES, colectivos_de
from backend.datos import almacen
from backend.datos import compromisos as datos
from backend.datos.anonimizar import anonimizar
from backend.reglas import idioma_valido

router = APIRouter(tags=["Compromisos"])

_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="compromiso")
_tareas: list = []


# ---------- utilidades ----------

def _obtener(compromiso_id: str) -> dict:
    compromiso = almacen.leer_compromiso(compromiso_id)
    if compromiso is None:
        raise HTTPException(404, f"No existe el compromiso {compromiso_id}")
    return compromiso


def _texto(valor, campo: str, *, comillas: bool = False) -> str:
    """Texto obligatorio, de hasta MAX_TEXTO caracteres (y sin comillas si `comillas` es False)."""
    if not isinstance(valor, str) or not valor.strip():
        raise HTTPException(422, f"Falta «{campo}»")
    valor = valor.strip()
    if len(valor) > datos.MAX_TEXTO:
        raise HTTPException(422, f"«{campo}» tiene {len(valor)} caracteres: el máximo es {datos.MAX_TEXTO}")
    if not comillas and datos.tiene_comillas(valor):
        raise HTTPException(422, f"«{campo}» no puede llevar comillas ni citas: es un resumen agregado")
    return valor


def _colectivos_del_tema(analisis: dict, encuesta: dict, tema: str) -> list[str]:
    """Los sectores donde el tema sale con n ≥ 5 (zonas); si ninguno, los de la encuesta."""
    en_zonas = [z["colectivo"] for z in analisis.get("zonas", [])
                if any(t.get("tema") == tema for t in z.get("temas", []))]
    return en_zonas or colectivos_de(encuesta)


def _fecha_texto(dia: date, idioma: str) -> str:
    return datos.formatear_fecha(dia, idioma)


# ---------- traducción en segundo plano ----------

def _traducir(compromiso_id: str) -> None:
    """Reutiliza ia.traducir_encuesta con una pseudoencuesta: título = «dijisteis», intro = «hicimos»."""
    compromiso = almacen.leer_compromiso(compromiso_id)
    if compromiso is None:
        return
    origen = datos.idioma_original(compromiso)
    destinos = [i for i in reglas.IDIOMAS if i != origen]
    traducidas: dict = {}
    try:
        pseudo = {"titulo": compromiso["dijisteis"], "intro": compromiso["hicimos"], "preguntas": [],
                  "idioma_original": origen}
        for idioma, t in (ia.traducir_encuesta(pseudo, destinos, origen) or {}).items():
            if idioma in destinos and isinstance(t, dict) and str(t.get("titulo") or "").strip() \
                    and str(t.get("intro") or "").strip():
                traducidas[idioma] = {"dijisteis": datos.sin_comillas(t["titulo"]),
                                      "hicimos": datos.sin_comillas(t["intro"])}
    except Exception as error:  # sin IA o con fallo: se ve el original
        print(f"[compromisos] {compromiso_id}: traducción no disponible ({type(error).__name__})")
    almacen.actualizar_compromiso(compromiso_id, {"traducciones": traducidas})


def lanzar_traduccion(compromiso_id: str) -> None:
    _tareas.append(_pool.submit(_traducir, compromiso_id))


def esperar(timeout: float = 30) -> None:
    """Espera a las traducciones en curso (para las pruebas)."""
    wait(list(_tareas), timeout=timeout)
    _tareas.clear()


# ---------- rutas ----------

@router.get("/encuestas/{encuesta_id}/compromisos/borrador")
def borrador(encuesta_id: str, accion: int = 0, idioma: str = "es"):
    """Borrador de compromiso a partir de la acción `accion` de las recomendaciones. No guarda nada."""
    idioma = idioma_valido(idioma)
    encuesta = rutas_encuestas.obtener(encuesta_id)
    analisis, recomendaciones = rutas_encuestas.analisis_y_recomendaciones(encuesta, idioma)
    acciones = recomendaciones.get("acciones") or []
    if not 0 <= accion < len(acciones):
        raise HTTPException(404, f"No existe la acción {accion}: hay {len(acciones)}")
    elegida = acciones[accion]
    tema = str(elegida.get("tema") or "otros")
    colectivos = _colectivos_del_tema(analisis, encuesta, tema)
    fecha = datos.fecha_desde_plazo(elegida.get("plazo"))
    redactado = ia.redactar_compromiso(tema, analisis, dict(elegida, fecha=fecha.isoformat()), colectivos, idioma)
    hecho = _fecha_texto(fecha, idioma)
    return {
        "tema": tema, "colectivos": colectivos,
        "dijisteis": datos.sin_comillas(redactado["dijisteis"]).replace("[fecha]", hecho),
        "hicimos": str(redactado["hicimos"]).replace("[fecha]", hecho),
        "responsable": str(elegida.get("responsable") or ""),
        "fecha": fecha.isoformat(),
        "indicador": datos.indicador_por_defecto(analisis, colectivos),
        "idioma": idioma, "origen_borrador": redactado.get("origen", "reglas"),
    }


@router.post("/encuestas/{encuesta_id}/compromisos")
def crear(encuesta_id: str, cuerpo: dict, idioma: str = "es"):
    """RRHH firma el compromiso. Exige «hicimos» y «responsable»; anonimiza los textos y traduce en 2º plano."""
    idioma = idioma_valido(cuerpo.get("idioma") or idioma)
    encuesta = rutas_encuestas.obtener(encuesta_id)
    del_ambito = colectivos_de(encuesta)

    tema = cuerpo.get("tema")
    if not isinstance(tema, str) or not re.fullmatch(r"[a-z_]{1,40}", tema):
        raise HTTPException(422, "Falta «tema» (uno de los temas del análisis)")
    colectivos = cuerpo.get("colectivos")
    if not isinstance(colectivos, list) or not colectivos or not all(isinstance(c, str) for c in colectivos):
        raise HTTPException(422, "Falta «colectivos»: la lista de sectores a los que va dirigido")
    fuera = [c for c in colectivos if c not in del_ambito]
    if fuera:
        raise HTTPException(422, f"Sectores que no son de esta encuesta: {fuera}")
    colectivos = [c for c in del_ambito if c in colectivos]  # en el orden fijo de los sectores

    dijisteis = _texto(cuerpo.get("dijisteis"), "dijisteis")
    hicimos = _texto(cuerpo.get("hicimos"), "hicimos", comillas=True)
    responsable = _texto(cuerpo.get("responsable"), "responsable", comillas=True)
    try:
        fecha = date.fromisoformat(str(cuerpo.get("fecha")))
    except ValueError:
        raise HTTPException(422, "«fecha» debe ser una fecha AAAA-MM-DD") from None
    marcador = _fecha_texto(fecha, idioma)
    dijisteis, hicimos = dijisteis.replace("[fecha]", marcador), hicimos.replace("[fecha]", marcador)

    comentarios = [r.get("comentario") for r in almacen.leer_respuestas(encuesta_id)]
    if datos.copia_literal(dijisteis, comentarios) or datos.copia_literal(hicimos, comentarios):
        raise HTTPException(422, "El texto contiene un comentario literal de la plantilla: "
                                 "un compromiso solo puede llevar resultados agregados")

    analisis, _ = rutas_encuestas.analisis_y_recomendaciones(encuesta, idioma)
    indicador = cuerpo.get("indicador")
    if indicador is None:
        indicador = datos.indicador_por_defecto(analisis, colectivos)
    elif isinstance(indicador, dict):
        dimension = indicador.get("dimension")
        if dimension is not None and dimension not in DIMENSIONES:
            raise HTTPException(422, f"Dimensión no válida en el indicador: {dimension}")
        sector = indicador.get("colectivo") or colectivos[0]
        if sector not in colectivos:
            raise HTTPException(422, "El sector del indicador debe estar entre los del compromiso")
        pregunta = next((p for p in analisis.get("preguntas", []) if p.get("id") == indicador.get("pregunta_origen")), {})
        texto = str(indicador.get("texto") or pregunta.get("texto") or "").strip()[:datos.MAX_TEXTO] or None
        indicador = datos.recalcular_antes({
            "texto": texto, "tipo": "escala_1_5", "dimension": dimension or pregunta.get("dimension"),
            "pregunta_origen": indicador.get("pregunta_origen"), "colectivo": sector,
            "antes": None, "n_antes": None, "periodo_antes": None}, analisis)
    else:
        raise HTTPException(422, "«indicador» debe ser un objeto")

    guardado = almacen.anadir_compromiso({
        "encuesta_id": encuesta_id, "tema": tema, "colectivos": colectivos,
        "dijisteis": anonimizar(dijisteis), "hicimos": anonimizar(hicimos),
        "responsable": anonimizar(responsable), "fecha": fecha.isoformat(), "estado": "comprometido",
        "idioma_original": idioma, "traducciones": {}, "indicador": indicador,
        "seguimiento_id": None, "despues": None,
        "origen_borrador": cuerpo.get("origen_borrador") if cuerpo.get("origen_borrador") in ("ia", "reglas") else "reglas",
    })
    lanzar_traduccion(guardado["id"])
    return datos.vista(guardado, idioma)


@router.get("/encuestas/{encuesta_id}/compromisos")
def listar(encuesta_id: str, idioma: str = "es"):
    rutas_encuestas.obtener(encuesta_id)
    return datos.de_encuesta(encuesta_id, idioma_valido(idioma))


@router.post("/compromisos/{compromiso_id}/hecho")
def marcar_hecho(compromiso_id: str, idioma: str = "es"):
    _obtener(compromiso_id)
    return datos.vista(almacen.actualizar_compromiso(compromiso_id, {"estado": "hecho"}), idioma_valido(idioma))


FRASE_SEGUIMIENTO = {  # solo si recomendar() no devolvió un seguimiento
    "es": "Comprobar si ha mejorado {tema} después de lo que hemos hecho",
    "ca": "Comprovar si ha millorat {tema} després del que hem fet",
    "en": "Check whether {tema} has improved after what we did",
}


@router.get("/compromisos/{compromiso_id}/seguimiento")
def seguimiento(compromiso_id: str, idioma: str = "es"):
    """Necesidad lista para crear.html: el seguimiento recomendado + compromiso_id + la pregunta fija
    (la misma que se midió antes), para poder comparar antes → después."""
    from backend import textos
    idioma = idioma_valido(idioma)
    compromiso = _obtener(compromiso_id)
    encuesta = rutas_encuestas.obtener(compromiso["encuesta_id"])
    _, recomendaciones = rutas_encuestas.analisis_y_recomendaciones(encuesta, idioma)
    necesidad = dict(recomendaciones.get("seguimiento") or {})
    necesidad.pop("colectivo", None)
    colectivos = compromiso.get("colectivos") or colectivos_de(encuesta)
    necesidad.setdefault("objetivo", FRASE_SEGUIMIENTO[idioma].format(
        tema=textos.nombre("tema", compromiso.get("tema", "otros"), idioma).lower()))
    necesidad.setdefault("contexto", "")
    necesidad.setdefault("temas_prohibidos", ["salario"])
    necesidad.update(colectivos=colectivos, idioma=idioma, compromiso_id=compromiso_id)
    duracion = necesidad.get("duracion_max_seg")
    necesidad["duracion_max_seg"] = max(duracion if isinstance(duracion, int) else 60,
                                        reglas.duracion_minima(len(colectivos)))
    indicador = compromiso.get("indicador") or {}
    if indicador.get("texto"):
        necesidad["pregunta_fija"] = {"texto": indicador["texto"], "tipo": "escala_1_5",
                                      "dimension": indicador.get("dimension") or "bienestar"}
    return necesidad
