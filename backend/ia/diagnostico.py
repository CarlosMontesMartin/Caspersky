"""Diagnóstico del LLM: conexión, clasificación y resumen con cada modelo.

Uso: python3 -m backend.ia.diagnostico [modelo ...]   (por defecto ornith)
"""

from __future__ import annotations

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


if __name__ == "__main__":
    if not hay_llm():
        sys.exit("No hay LLM_API_KEY en .env")
    print(f"URL: {_config()[1]}")
    for modelo in sys.argv[1:] or ["ornith"]:
        probar(modelo)
