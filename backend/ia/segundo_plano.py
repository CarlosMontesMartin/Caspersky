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

# Sin prisa: estas llamadas no bloquean ninguna pantalla
TIMEOUT_SEG = 60

# Pocas tareas a la vez: la API del evento encola las peticiones y las demás superarían el timeout
_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ia")
# Cola aparte para lo que RRHH ve primero (lectura, recomendaciones, sugerencias): no espera
# detrás de los resúmenes de cada tema ni de los lotes de clasificación
_pool_prioritario = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ia-prioridad")
_bloqueo = threading.Lock()
_resultados: dict[Hashable, Any] = {}
_pendientes: dict[Hashable, Future] = {}


def obtener(clave: Hashable, funcion: Callable[[], Any], prioritario: bool = False) -> Any:
    """Devuelve el resultado si ya está calculado; si no, lo lanza en segundo plano y devuelve None."""
    with _bloqueo:
        if clave in _resultados:
            return _resultados[clave]
        if clave not in _pendientes:
            cola = _pool_prioritario if prioritario else _pool
            _pendientes[clave] = cola.submit(_ejecutar, clave, funcion)
    return None


def consultar(clave: Hashable, funcion: Callable[[], Any], prioritario: bool = False) -> tuple[str, Any]:
    """Devuelve ("listo", resultado) o ("pendiente", None); si no estaba lanzada, la lanza.

    Un resultado None con estado listo significa que la tarea falló o no dio nada válido.
    """
    with _bloqueo:
        if clave in _resultados:
            return "listo", _resultados[clave]
    obtener(clave, funcion, prioritario)
    with _bloqueo:
        return ("listo", _resultados[clave]) if clave in _resultados else ("pendiente", None)


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


def pendientes() -> int:
    """Número de tareas lanzadas que todavía no han terminado."""
    with _bloqueo:
        return len(_pendientes)


def esperar(timeout: float = 90) -> None:
    """Espera a que terminen las tareas pendientes. Pensado para pruebas y para precalentar."""
    with _bloqueo:
        tareas = list(_pendientes.values())
    wait(tareas, timeout=timeout)
