"""Reglas de las encuestas: ÚNICO sitio con estos números.

Lo importan backend/api/validacion.py y backend/ia/generar.py.
Nadie copia estos valores: si hay que cambiar una regla, se cambia aquí.
"""
SEG_POR_TIPO = {"escala_1_5": 15, "si_no": 15, "opcion": 15, "texto": 30}

NUCLEO_MIN, NUCLEO_MAX = 1, 3      # al menos 1 escala_1_5; máximo 1 texto y al final
PROPIAS_MIN, PROPIAS_MAX = 1, 3    # nunca texto
TOTAL_MIN, TOTAL_MAX = 3, 6        # por sector (núcleo + propias)

DURACION_MIN_UN_SECTOR = 45        # segundos
DURACION_MIN_VARIOS = 60

IDIOMAS = ["es", "ca", "en"]

# Valores cerrados del contrato
COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]   # en este orden
TURNOS = ["manana", "tarde", "noche", "sin_turno"]
TIPOS = ["escala_1_5", "opcion", "si_no", "texto"]
TIPOS_PROPIAS = ["escala_1_5", "opcion", "si_no"]
DIMENSIONES = ["bienestar", "liderazgo", "desarrollo", "cultura", "entorno", "condiciones"]


def duracion_minima(n_sectores: int) -> int:
    """Segundos mínimos para que quepan TOTAL_MIN preguntas en cada sector."""
    return DURACION_MIN_UN_SECTOR if n_sectores <= 1 else DURACION_MIN_VARIOS


def segundos(preguntas: list) -> int:
    """Tiempo estimado de una lista de preguntas."""
    return sum(SEG_POR_TIPO.get(p.get("tipo"), 15) for p in preguntas if isinstance(p, dict))


def idioma_valido(idioma) -> str:
    """El idioma si es uno de IDIOMAS; si no, "es"."""
    return idioma if idioma in IDIOMAS else "es"
