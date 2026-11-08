"""Traducciones de encuestas · UPC 2 (v3.md sección 3.3 y v5.md §1).

- Cada encuesta tiene un idioma original (v5): el de la pantalla de RRHH al generarla
  (encuesta["idioma_original"]; las antiguas sin el campo cuentan como "es").
- Al aprobar, se traduce en segundo plano con ia.traducir_encuesta (UPC 1) DESDE el idioma
  original a los otros dos, y se guarda en encuesta["traducciones"] con
  estado_traduccion = "lista" | "error".
- Si la encuesta cambia mientras se traduce (editar, regenerar), el resultado se descarta.
- aplicar(): textos de la encuesta en un idioma (lo que falte, en el idioma original).
- valores_originales(): en las preguntas de opción se guarda siempre la opción en el idioma original.

`bloqueo` protege los "leer → cambiar → guardar" de una encuesta: lo usan las rutas que la
modifican y el hilo de traducción, para que nadie pise los cambios de otro.
"""
import copy
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from backend import reglas
from backend.api import ia_o_respaldo as ia
from backend.datos import almacen

IDIOMAS = list(reglas.IDIOMAS)
IDIOMAS_TRADUCIDOS = [i for i in IDIOMAS if i != "es"]  # solo para encuestas en castellano (compatibilidad)

bloqueo = threading.RLock()
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="traducir")
_en_curso: dict[str, object] = {}


idioma_valido = reglas.idioma_valido


def idioma_original(encuesta: dict) -> str:
    """Idioma en el que está escrita la encuesta. Sin el campo (encuestas antiguas, enc_000): "es"."""
    return idioma_valido(encuesta.get("idioma_original") or ((encuesta.get("necesidad") or {}).get("idioma")) or "es")


def destinos(encuesta: dict) -> list[str]:
    """Idiomas a los que hay que traducir: todos menos el original."""
    original = idioma_original(encuesta)
    return [i for i in IDIOMAS if i != original]


def firma(encuesta: dict) -> str:
    """Huella de los textos traducibles: si cambia, una traducción en curso ya no vale."""
    textos = {k: encuesta.get(k) for k in ("titulo", "intro", "preguntas", "preguntas_por_colectivo")}
    return hashlib.sha1(json.dumps(textos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def reiniciar(encuesta: dict) -> dict:
    """Sin traducciones y pendiente (al crear, editar, regenerar o duplicar)."""
    encuesta["traducciones"] = {}
    encuesta["estado_traduccion"] = "pendiente"
    return encuesta


# ---------- traducir en segundo plano ----------

def _traducir(encuesta_id: str, huella: str, copia: dict) -> None:
    origen, faltan_por = idioma_original(copia), destinos(copia)
    try:
        resultado = ia.traducir_encuesta(copia, faltan_por, origen)
        traducciones = {i: t for i, t in (resultado or {}).items() if i in faltan_por and isinstance(t, dict) and t}
        estado = "lista" if all(i in traducciones for i in faltan_por) else "error"
        if estado == "error":
            print(f"[traducir] {encuesta_id} ({origen}): faltan idiomas {[i for i in faltan_por if i not in traducciones]}")
    except Exception as error:
        print(f"[traducir] {encuesta_id}: {error!r}")
        traducciones, estado = {}, "error"
    with bloqueo:
        _en_curso.pop(encuesta_id, None)
        actual = almacen.leer_encuesta(encuesta_id)
        if actual is None or firma(actual) != huella:
            return  # la encuesta ha cambiado: esta traducción ya no vale
        actual["traducciones"] = traducciones
        actual["estado_traduccion"] = estado
        almacen.guardar_encuesta(actual)


def lanzar(encuesta: dict) -> None:
    """Traduce en segundo plano si hace falta (no bloquea la petición)."""
    if encuesta.get("estado_traduccion") == "lista" and encuesta.get("traducciones"):
        return
    huella = firma(encuesta)
    with bloqueo:
        if _en_curso.get(encuesta["id"]) == huella:
            return
        _en_curso[encuesta["id"]] = huella
    _pool.submit(_traducir, encuesta["id"], huella, copy.deepcopy(encuesta))


def esperar(timeout: float = 60) -> None:
    """Espera a que terminen las traducciones en curso (para pruebas)."""
    import time
    fin = time.time() + timeout
    while _en_curso and time.time() < fin:
        time.sleep(0.05)


# ---------- aplicar un idioma ----------

def _traducir_pregunta(pregunta: dict, traducida: dict | None) -> dict:
    p = dict(pregunta)
    if not traducida:
        return p
    if isinstance(traducida.get("texto"), str) and traducida["texto"].strip():
        p["texto"] = traducida["texto"]
    opciones = traducida.get("opciones")
    if (pregunta.get("tipo") == "opcion" and isinstance(opciones, list)
            and len(opciones) == len(pregunta.get("opciones", [])) and all(isinstance(o, str) for o in opciones)):
        p["opciones"] = opciones
    return p


def _por_id(lista) -> dict:
    return {t.get("id"): t for t in (lista or []) if isinstance(t, dict)}


def idiomas_disponibles(encuesta: dict) -> list[str]:
    """El original primero y después los traducidos (en el orden de IDIOMAS)."""
    traducciones = encuesta.get("traducciones") or {}
    return [idioma_original(encuesta)] + [i for i in destinos(encuesta) if traducciones.get(i)]


def tiene_traduccion(encuesta: dict, idioma: str) -> bool:
    return idioma != idioma_original(encuesta) and bool((encuesta.get("traducciones") or {}).get(idioma))


def aplicar(encuesta: dict, idioma: str) -> dict:
    """Copia de la encuesta con los textos en `idioma`; lo que no esté traducido, en el idioma original.
    Con idioma == idioma original devuelve la encuesta tal cual."""
    t = (encuesta.get("traducciones") or {}).get(idioma) if tiene_traduccion(encuesta, idioma) else None
    if not t:
        return encuesta
    resultado = dict(encuesta)
    for campo in ("titulo", "intro"):
        if isinstance(t.get(campo), str) and t[campo].strip():
            resultado[campo] = t[campo]
    nucleo = _por_id(t.get("preguntas"))
    resultado["preguntas"] = [_traducir_pregunta(p, nucleo.get(p["id"])) for p in encuesta.get("preguntas", [])]
    sectores = t.get("preguntas_por_colectivo") or {}
    resultado["preguntas_por_colectivo"] = {
        c: [_traducir_pregunta(p, _por_id(sectores.get(c)).get(p["id"])) for p in lista]
        for c, lista in (encuesta.get("preguntas_por_colectivo") or {}).items()}
    return resultado


def valores_originales(valores: dict, encuesta: dict, preguntas: list[dict]) -> dict:
    """Si llega una opción traducida, la cambia por la del idioma original (misma posición)."""
    resultado = dict(valores)
    for p in preguntas:
        valor = resultado.get(p["id"])
        if p.get("tipo") != "opcion" or valor is None or valor in p.get("opciones", []):
            continue
        for idioma in destinos(encuesta):
            if not tiene_traduccion(encuesta, idioma):
                continue
            traducida = aplicar(encuesta, idioma)
            todas = traducida["preguntas"] + [q for lista in traducida["preguntas_por_colectivo"].values() for q in lista]
            opciones = next((q["opciones"] for q in todas if q["id"] == p["id"]), [])
            if valor in opciones and len(opciones) == len(p.get("opciones", [])):
                resultado[p["id"]] = p["opciones"][opciones.index(valor)]
                break
    return resultado


def titulo(encuesta: dict, idioma: str) -> str:
    """Título en `idioma` si hay traducción; si no, el original."""
    return aplicar(encuesta, idioma_valido(idioma)).get("titulo", "")
