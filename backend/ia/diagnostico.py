"""Diagnóstico del LLM: conexión, clasificación, resumen y tiempo de generación de encuestas.

Uso: python3 -m backend.ia.diagnostico [modelo ...]   (por defecto el de LLM_MODEL)
"""

from __future__ import annotations

import logging
import os
import sys
import time

from .analizar import _extraer_temas, _leer_prompt, _recortar, TEMAS
from .llm import _config, hay_llm, llamar_llm

PRUEBA = [
    ("el descanso de 15 min es una broma con 8h", "descansos"),
    ("no sabemos el cuadrante hasta el ultimo dia", "turnos"),
    ("no damos abasto, falta gente en linea", "carga_trabajo"),
    ("nos enteramos del cambio x el grupo de wasa", "comunicacion"),
    ("mi jefe no escucha las quejas del equipo", "liderazgo"),
    ("las tablets del quiosco van fatal", "herramientas"),
    ("llevamos meses sin hacer ningun curso", "formacion"),
    ("nadie valora el esfuerzo que hacemos", "reconocimiento"),
    ("hay cables sueltos cerca de las maquinas", "seguridad"),
    ("el ambiente con los compañeros es bueno", "ambiente"),
    ("con los nuevos horarios no veo a mis hijos", "conciliacion"),
    ("el parking siempre esta lleno", "otros"),
]


def probar(modelo: str) -> None:
    os.environ["LLM_MODEL"] = modelo
    print(f"\n=== {modelo} ===")
    usuario = (
        f"Temas permitidos: {', '.join(TEMAS)}\n\n"
        f"Clasifica estos {len(PRUEBA)} comentarios. Devuelve exactamente {len(PRUEBA)} temas "
        f'en el mismo orden, con el formato {{"temas": [...]}}.\n\n'
        + "\n".join(f"{i}. {t}" for i, (t, _) in enumerate(PRUEBA, start=1))
    )
    inicio = time.time()
    try:
        crudo = llamar_llm(_leer_prompt("clasificar.md"), usuario)
    except Exception as error:
        print(f"Clasificación: ERROR tras {time.time() - inicio:.1f} s -> {error}")
        return
    print(f"Clasificación: {time.time() - inicio:.1f} s")
    print("Respuesta (inicio):", crudo[:300].replace("\n", " "))
    from .llm import _extraer_json
    try:
        temas = _extraer_temas(_extraer_json(crudo), len(PRUEBA))
        aciertos = sum(t == real for t, (_, real) in zip(temas, PRUEBA))
        print(f"Aciertos: {aciertos}/{len(PRUEBA)}  {temas}")
    except Exception as error:
        print(f"No se pudo leer la clasificación: {error}")

    inicio = time.time()
    try:
        crudo = llamar_llm(_leer_prompt("resumir.md"),
                           "Tema: descansos\nMuestra de 4 comentarios:\n"
                           "- el descanso es muy corto\n- no da tiempo ni a comer\n"
                           "- la pausa de noche no llega\n- necesitamos pausas mas largas")
        print(f"Resumen: {time.time() - inicio:.1f} s -> {_recortar(crudo.strip())[:250]}")
    except Exception as error:
        print(f"Resumen: ERROR tras {time.time() - inicio:.1f} s -> {error}")


NECESIDADES = [
    {"objetivo": "Saber cómo afecta a planta el nuevo sistema de turnos implantado en octubre",
     "colectivo": "planta", "contexto": "Cambio de turnos rotativos", "duracion_max_seg": 120,
     "temas_prohibidos": ["salario"]},
    {"objetivo": "Detectar dificultades en la preparación de pedidos", "colectivo": "logistica",
     "contexto": "Picos de trabajo en el almacén", "duracion_max_seg": 60, "temas_prohibidos": []},
    {"objetivo": "Conocer la adopción de la nueva herramienta de gestión", "colectivo": "oficina",
     "contexto": "Migración de software", "duracion_max_seg": 180, "temas_prohibidos": []},
    {"objetivo": "Saber cómo afecta el cambio de turnos a la coordinación entre áreas",
     "colectivos": ["planta", "logistica", "comercial"], "contexto": "Nuevo sistema de turnos",
     "duracion_max_seg": 120, "temas_prohibidos": ["salario"]},
]


class _Origen(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.origen = "respaldo"

    def emit(self, registro):
        if "generada por el modelo" in registro.getMessage():
            self.origen = "modelo"


def cronometrar_generacion() -> None:
    from .generar import TIMEOUT_GENERAR_SECTORES_SEG, TIMEOUT_GENERAR_SEG, generar_encuesta
    print(f"\n=== generar_encuesta (límite {TIMEOUT_GENERAR_SEG} s con un colectivo y "
          f"{TIMEOUT_GENERAR_SECTORES_SEG} s con varios; si no, respaldo) ===")
    registro = logging.getLogger("backend.ia.generar")
    registro.setLevel(logging.INFO)
    for necesidad in NECESIDADES:
        origen = _Origen()
        registro.addHandler(origen)
        inicio = time.time()
        encuesta = generar_encuesta(necesidad, "")
        registro.removeHandler(origen)
        nombre = necesidad.get("colectivo") or "+".join(necesidad["colectivos"])
        total = len(encuesta["preguntas"]) + sum(len(l) for l in encuesta["preguntas_por_colectivo"].values())
        print(f"{nombre:<26} {time.time() - inicio:5.1f} s  {encuesta.get('origen', origen.origen):<9} "
              f"{total} preguntas · {encuesta['titulo']}")


if __name__ == "__main__":
    if not hay_llm():
        sys.exit("No hay LLM_API_KEY en .env")
    print(f"URL: {_config()[1]}")
    for modelo in sys.argv[1:] or [_config()[2]]:
        probar(modelo)
    cronometrar_generacion()
