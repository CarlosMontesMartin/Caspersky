"""Almacenamiento en JSON · UPC 2.

backend/datos/almacen/
  encuestas/<encuesta_id>.json    una Encuesta
  respuestas/<encuesta_id>.json   lista de Respuesta de esa encuesta

Solo este módulo lee y escribe esos archivos. Las escrituras son atómicas
(archivo temporal + renombrar) y van bajo un bloqueo, así que dos respuestas
a la vez no se pisan y un archivo nunca queda a medias.
"""
import json
import os
import re
import threading
from pathlib import Path

from backend.datos.anonimizar import anonimizar

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent / "almacen"
SINTETICOS = RAIZ / "datos_sinteticos" / "respuestas.json"
ENCUESTAS_SINTETICAS = RAIZ / "datos_sinteticos" / "encuestas.json"  # opcional

_bloqueo = threading.RLock()
_ID_VALIDO = re.compile(r"^[a-z0-9_]{1,40}$")


# ---------- utilidades internas ----------

def _ruta(tipo: str, encuesta_id: str) -> Path:
    # Evita que un id como "../../algo" escriba fuera del almacén.
    if not _ID_VALIDO.match(encuesta_id):
        raise ValueError(f"Id de encuesta no válido: {encuesta_id!r}")
    return BASE / tipo / f"{encuesta_id}.json"


def _leer(ruta: Path, defecto):
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)


# ---------- encuestas ----------

def leer_encuesta(encuesta_id: str) -> dict | None:
    return _leer(_ruta("encuestas", encuesta_id), None)


def guardar_encuesta(encuesta: dict) -> dict:
    with _bloqueo:
        _escribir(_ruta("encuestas", encuesta["id"]), encuesta)
    return encuesta


def listar_encuestas() -> list[dict]:
    carpeta = BASE / "encuestas"
    if not carpeta.exists():
        return []
    return [_leer(r, None) for r in sorted(carpeta.glob("*.json"))]


def nuevo_id() -> str:
    """enc_001, enc_002… (enc_000 está reservado para el pulso general)."""
    with _bloqueo:
        numeros = [int(e["id"][4:]) for e in listar_encuestas() if re.fullmatch(r"enc_\d+", e["id"])]
        return f"enc_{max(numeros + [0]) + 1:03d}"


# ---------- respuestas ----------

def leer_respuestas(encuesta_id: str) -> list[dict]:
    return _leer(_ruta("respuestas", encuesta_id), [])


def leer_todas_las_respuestas() -> list[dict]:
    carpeta = BASE / "respuestas"
    if not carpeta.exists():
        return []
    return [r for archivo in sorted(carpeta.glob("*.json")) for r in _leer(archivo, [])]


def anadir_respuesta(respuesta: dict) -> dict:
    """Guarda una respuesta. El comentario se anonimiza siempre aquí."""
    respuesta = dict(respuesta, comentario=anonimizar(respuesta.get("comentario")))
    with _bloqueo:
        ruta = _ruta("respuestas", respuesta["encuesta_id"])
        lista = _leer(ruta, [])
        lista.append(respuesta)
        _escribir(ruta, lista)
    return respuesta


# ---------- arranque y datos sintéticos ----------

def _inferir_encuesta(encuesta_id: str, respuestas: list[dict]) -> dict:
    """Si UPC 1 no da la definición de una encuesta, se deduce de sus respuestas."""
    colectivos = {r["colectivo"] for r in respuestas}
    claves = sorted({k for r in respuestas for k in r.get("valores", {})})
    preguntas = []
    for clave in claves:
        ejemplo = next(r["valores"][clave] for r in respuestas if clave in r.get("valores", {}))
        tipo = "escala_1_5" if isinstance(ejemplo, (int, float)) else "si_no" if ejemplo in ("si", "no") else "opcion"
        opciones = sorted({r["valores"][clave] for r in respuestas if clave in r.get("valores", {})}) if tipo == "opcion" else []
        preguntas.append({"id": clave, "texto": clave, "tipo": tipo, "opciones": opciones,
                          "dimension": "bienestar", "condicion": None})
    return {
        "id": encuesta_id,
        "estado": "publicada",
        "titulo": "Pulso de clima general" if encuesta_id == "enc_000" else f"Encuesta {encuesta_id}",
        "intro": "",
        "colectivo": colectivos.pop() if len(colectivos) == 1 else "todos",
        "periodo": max(r["periodo"] for r in respuestas),
        "tiempo_estimado_seg": 0,
        "url": None,
        "qr": None,
        "preguntas": preguntas,
    }


def inicializar() -> str:
    """Crea el almacén y, si está vacío, carga los datos sintéticos. Devuelve un mensaje."""
    with _bloqueo:
        (BASE / "encuestas").mkdir(parents=True, exist_ok=True)
        (BASE / "respuestas").mkdir(parents=True, exist_ok=True)
        if any((BASE / "respuestas").glob("*.json")) or any((BASE / "encuestas").glob("*.json")):
            return "Almacén ya tenía datos: no se cargan sintéticos."
        if not SINTETICOS.exists():
            return f"No existe {SINTETICOS}: almacén vacío."

        por_encuesta: dict[str, list[dict]] = {}
        for r in json.loads(SINTETICOS.read_text(encoding="utf-8")):
            r = dict(r, comentario=anonimizar(r.get("comentario")))
            por_encuesta.setdefault(r["encuesta_id"], []).append(r)

        definidas = {e["id"]: e for e in _leer(ENCUESTAS_SINTETICAS, [])}
        for encuesta_id, respuestas in por_encuesta.items():
            _escribir(_ruta("respuestas", encuesta_id), respuestas)
            _escribir(_ruta("encuestas", encuesta_id),
                      definidas.get(encuesta_id) or _inferir_encuesta(encuesta_id, respuestas))

        total = sum(len(v) for v in por_encuesta.values())
        return f"Cargadas {total} respuestas sintéticas en {len(por_encuesta)} encuestas."
