"""Llamadas lentas al modelo ejecutadas en segundo plano, con caché por clave.

Permite que el dashboard responda al momento con el texto de respaldo y muestre el de la IA
en cuanto esté listo, sin repetir llamadas.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Callable, Hashable

log = logging.getLogger(__name__)

_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="ia")
_bloqueo = threading.Lock()
_resultados: dict[Hashable, Any] = {}
_pendientes: dict[Hashable, Future] = {}


def obtener(clave: Hashable, funcion: Callable[[], Any]) -> Any:
    """Devuelve el resultado si ya está calculado; si no, lo lanza en segundo plano y devuelve None."""
    with _bloqueo:
        if clave in _resultados:
            return _resultados[clave]
        if clave not in _pendientes:
            _pendientes[clave] = _pool.submit(_ejecutar, clave, funcion)
    return None


def _ejecutar(clave: Hashable, funcion: Callable[[], Any]) -> None:
    try:
        valor = funcion()
    except Exception as error:
        log.warning("Tarea en segundo plano sin resultado: %s", error)
        valor = None
    with _bloqueo:
        # Un fallo también se guarda (como None) para no repetir la llamada en cada recarga
        _resultados[clave] = valor
        _pendientes.pop(clave, None)


def esperar(timeout: float = 90) -> None:
    """Espera a que terminen las tareas pendientes. Pensado para pruebas y para precalentar."""
    with _bloqueo:
        tareas = list(_pendientes.values())
    wait(tareas, timeout=timeout)
