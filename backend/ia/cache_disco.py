"""Resultados de la IA guardados en disco, para no repetir llamadas al reiniciar el servidor.

Se guarda lo que cuesta tiempo y no cambia si no cambian los datos: el tema de cada comentario,
los resúmenes de temas, la lectura y las acciones, las preguntas sugeridas, las respuestas de
"Pregunta a tus datos" y los borradores de compromisos.

Privacidad: las claves son huellas (sha256) de los datos de entrada, así que en el archivo no hay
ningún comentario. Las entradas caducan a los 30 días. El archivo está fuera de git.
Para empezar de cero: borrar backend/ia/cache/ (o IA_CACHE=0 en .env para no usarla).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

RUTA = Path(os.getenv("IA_CACHE_RUTA") or Path(__file__).resolve().parent / "cache" / "resultados.json")
CADUCIDAD_SEG = 30 * 24 * 3600
_bloqueo = threading.RLock()
_datos: dict[str, dict[str, dict[str, Any]]] | None = None


def activa() -> bool:
    return os.getenv("IA_CACHE", "1").strip() != "0"


def huella(clave: Any) -> str:
    """Huella estable entre ejecuciones (hash() de Python cambia en cada arranque)."""
    texto = clave if isinstance(clave, str) else json.dumps(clave, ensure_ascii=False,
                                                            sort_keys=True, default=str)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:32]


def _cargar() -> dict[str, dict[str, dict[str, Any]]]:
    global _datos
    if _datos is None:
        _datos = {}
        try:
            if RUTA.exists():
                leido = json.loads(RUTA.read_text(encoding="utf-8"))
                limite = time.time() - CADUCIDAD_SEG
                _datos = {espacio: {h: e for h, e in entradas.items() if e.get("t", 0) >= limite}
                          for espacio, entradas in (leido.get("entradas") or {}).items()}
                log.info("Caché de IA: %d resultados guardados",
                         sum(len(e) for e in _datos.values()))
        except (OSError, ValueError, AttributeError) as error:
            log.warning("Caché de IA ilegible, se empieza de cero: %s", error)
            _datos = {}
    return _datos


def _escribir() -> None:
    try:
        RUTA.parent.mkdir(parents=True, exist_ok=True)
        temporal = RUTA.with_suffix(".tmp")
        temporal.write_text(json.dumps({"version": 1, "entradas": _datos}, ensure_ascii=False),
                            encoding="utf-8")
        os.replace(temporal, RUTA)
    except OSError as error:
        log.warning("No se pudo guardar la caché de IA: %s", error)


def leer(espacio: str, clave: Any) -> Any:
    """El valor guardado o None."""
    if not activa():
        return None
    with _bloqueo:
        entrada = _cargar().get(espacio, {}).get(huella(clave))
    return entrada.get("v") if entrada else None


def guardar(espacio: str, clave: Any, valor: Any) -> None:
    guardar_varios(espacio, {clave: valor})


def guardar_varios(espacio: str, valores: dict[Any, Any]) -> None:
    """Guarda varios resultados de una vez (una sola escritura). None no se guarda: un fallo se
    vuelve a intentar en el siguiente arranque."""
    if not activa() or not valores:
        return
    ahora = time.time()
    nuevos = {}
    for clave, valor in valores.items():
        if valor is None:
            continue
        try:
            json.dumps(valor)
        except (TypeError, ValueError):
            continue
        nuevos[huella(clave)] = {"v": valor, "t": ahora}
    if not nuevos:
        return
    with _bloqueo:
        _cargar().setdefault(espacio, {}).update(nuevos)
        _escribir()


def borrar() -> None:
    """Vacía la caché (memoria y disco)."""
    global _datos
    with _bloqueo:
        _datos = {}
        try:
            RUTA.unlink()
        except OSError:
            pass
