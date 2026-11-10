"""Almacenamiento en JSON.

Único módulo que lee y escribe archivos.

backend/datos/almacen/
  encuestas/<encuesta_id>.json    una Encuesta
  respuestas/<encuesta_id>.json   lista de Respuesta de esa encuesta

Las escrituras van bajo un bloqueo y son atómicas (archivo temporal +
renombrar): dos respuestas a la vez no se pisan y un archivo nunca queda a medias.
"""
import json
import os
import re
import threading
from pathlib import Path

from backend.datos.anonimizar import anonimizar

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent / "almacen"
SINTETICOS = RAIZ / "datos_sinteticos"
CONTENIDO = RAIZ / "contenido"

_bloqueo = threading.RLock()
_ID_VALIDO = re.compile(r"^[a-z0-9_]{1,40}$")


# ---------- utilidades internas ----------

def _ruta(tipo: str, encuesta_id: str) -> Path | None:
    """Ruta del archivo, o None si el id no es válido (evita escribir fuera del almacén)."""
    if not isinstance(encuesta_id, str) or not _ID_VALIDO.match(encuesta_id):
        return None
    return BASE / tipo / f"{encuesta_id}.json"


def _ruta_obligatoria(tipo: str, encuesta_id: str) -> Path:
    ruta = _ruta(tipo, encuesta_id)
    if ruta is None:
        raise ValueError(f"Id de encuesta no válido: {encuesta_id!r}")
    return ruta


def _leer_json(ruta: Path | None, defecto):
    if ruta is None or not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def _leer_texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)


def _anonimizar_textos(respuesta: dict, tipos: dict[str, str]) -> dict:
    """Mueve el texto libre a `comentario` y lo anonimiza.

    Las respuestas de preguntas de tipo texto salen de `valores` y se unen al
    comentario: el texto libre se guarda SOLO en `comentario`.
    """
    valores, textos = {}, []
    for clave, valor in respuesta.get("valores", {}).items():
        if tipos.get(clave) == "texto":
            if isinstance(valor, str) and valor.strip():
                textos.append(valor.strip())
        elif clave not in tipos and isinstance(valor, str) and valor not in ("si", "no"):
            valores[clave] = anonimizar(valor)  # tipo desconocido: se anonimiza por si acaso
        else:
            valores[clave] = valor
    comentario = respuesta.get("comentario")
    if isinstance(comentario, str) and comentario.strip():
        textos.append(comentario.strip())
    return dict(respuesta, valores=valores, comentario=anonimizar(" / ".join(textos)))


# ---------- arranque ----------

def inicializar() -> None:
    """Crea las carpetas y, si el almacén está vacío, carga los datos sintéticos."""
    with _bloqueo:
        for tipo in ("encuestas", "respuestas"):
            (BASE / tipo).mkdir(parents=True, exist_ok=True)
        vacio = not any((BASE / "encuestas").glob("*.json")) and not any((BASE / "respuestas").glob("*.json"))
    if vacio:
        n = cargar_sinteticos()
        print(f"[almacen] Cargadas {n} respuestas sintéticas.")
    else:
        print("[almacen] Ya había datos: no se cargan sintéticos.")


def cargar_sinteticos() -> int:
    """Lee datos_sinteticos/enc_000.json y respuestas.json, anonimiza y guarda. Devuelve nº de respuestas."""
    encuesta = _leer_json(SINTETICOS / "enc_000.json", None)
    respuestas = _leer_json(SINTETICOS / "respuestas.json", [])
    if encuesta is None:
        print("[almacen] Aviso: no existe datos_sinteticos/enc_000.json.")
    else:
        guardar_encuesta(encuesta)
    if not respuestas:
        return 0

    tipos = {p["id"]: p["tipo"] for p in (encuesta or {}).get("preguntas", [])}
    por_encuesta: dict[str, list[dict]] = {}
    for r in respuestas:
        r = _anonimizar_textos(r, tipos)
        if r.get("periodo"):  # minimización: solo el mes, no el día
            r["fecha"] = f"{r['periodo']}-01"
        por_encuesta.setdefault(r["encuesta_id"], []).append(r)
    with _bloqueo:
        for encuesta_id, lista in por_encuesta.items():
            _escribir(_ruta_obligatoria("respuestas", encuesta_id), lista)
    return sum(len(lista) for lista in por_encuesta.values())


# ---------- encuestas ----------

def nuevo_id_encuesta() -> str:
    """Siguiente id libre: enc_001, enc_002… (enc_000 está reservado)."""
    with _bloqueo:
        numeros = [int(r.stem[4:]) for r in (BASE / "encuestas").glob("enc_*.json") if r.stem[4:].isdigit()]
        return f"enc_{max(numeros + [0]) + 1:03d}"


def guardar_encuesta(encuesta: dict) -> dict:
    with _bloqueo:
        _escribir(_ruta_obligatoria("encuestas", encuesta["id"]), encuesta)
    return encuesta


def leer_encuesta(encuesta_id: str) -> dict | None:
    return _leer_json(_ruta("encuestas", encuesta_id), None)


def listar_encuestas() -> list[dict]:
    """Lista de ResumenEncuesta ordenada por id."""
    carpeta = BASE / "encuestas"
    if not carpeta.exists():
        return []
    resumen = []
    for archivo in sorted(carpeta.glob("*.json")):
        e = _leer_json(archivo, {})
        resumen.append({
            "id": e.get("id", archivo.stem),
            "titulo": e.get("titulo", ""),
            "colectivo": e.get("colectivo", ""),
            "estado": e.get("estado", ""),
            "periodo": e.get("periodo", ""),
            "n_respuestas": len(leer_respuestas(archivo.stem)),
        })
    return resumen


# ---------- respuestas ----------

def anadir_respuesta(encuesta_id: str, respuesta: dict) -> None:
    """Añade una Respuesta (ya anonimizada) al final de respuestas/<id>.json."""
    with _bloqueo:
        ruta = _ruta_obligatoria("respuestas", encuesta_id)
        lista = _leer_json(ruta, [])
        lista.append(respuesta)
        _escribir(ruta, lista)


def leer_respuestas(encuesta_id: str) -> list[dict]:
    return _leer_json(_ruta("respuestas", encuesta_id), [])


# ---------- compromisos ----------
# Un solo archivo con la lista: almacen/compromisos.json. Todas las operaciones van bajo _bloqueo.

def _ruta_compromisos() -> Path:
    return BASE / "compromisos.json"


def leer_compromisos() -> list[dict]:
    return _leer_json(_ruta_compromisos(), [])


def leer_compromiso(compromiso_id: str) -> dict | None:
    return next((c for c in leer_compromisos() if c.get("id") == compromiso_id), None)


def nuevo_id_compromiso() -> str:
    """cmp_001, cmp_002… (se asigna dentro de anadir_compromiso, bajo el bloqueo)."""
    with _bloqueo:
        numeros = [int(c["id"][4:]) for c in leer_compromisos()
                   if str(c.get("id", "")).startswith("cmp_") and str(c["id"])[4:].isdigit()]
        return f"cmp_{max(numeros + [0]) + 1:03d}"


def anadir_compromiso(datos: dict) -> dict:
    """Guarda un compromiso nuevo con el siguiente id libre y lo devuelve."""
    with _bloqueo:
        compromiso = dict(datos, id=nuevo_id_compromiso())
        _escribir(_ruta_compromisos(), leer_compromisos() + [compromiso])
    return compromiso


def guardar_compromiso(compromiso: dict) -> dict:
    """Reemplaza el compromiso con ese id (o lo añade si no existe)."""
    with _bloqueo:
        lista = leer_compromisos()
        for i, existente in enumerate(lista):
            if existente.get("id") == compromiso["id"]:
                lista[i] = compromiso
                break
        else:
            lista.append(compromiso)
        _escribir(_ruta_compromisos(), lista)
    return compromiso


def actualizar_compromiso(compromiso_id: str, cambios: dict) -> dict | None:
    """Lee-cambia-guarda de forma atómica (así un hilo de traducción no pisa un "hecho"). None si no existe."""
    with _bloqueo:
        actual = leer_compromiso(compromiso_id)
        if actual is None:
            return None
        return guardar_compromiso(dict(actual, **cambios))


# ---------- contenido editable (contenido/) ----------

def leer_plantilla() -> list[dict]:
    return _leer_json(CONTENIDO / "plantilla.json", [])


def leer_reglas() -> str:
    return _leer_texto(CONTENIDO / "reglas_colectivos.md")


def leer_transparencia(idioma: str = "es") -> str:
    """contenido/transparencia.md (es) o transparencia_<idioma>.md; si falta, la de castellano."""
    if idioma in ("ca", "en"):
        traducida = _leer_texto(CONTENIDO / f"transparencia_{idioma}.md")
        if traducida.strip():
            return traducida
    return _leer_texto(CONTENIDO / "transparencia.md")
