"""Pruebas de generación y validación de encuestas."""

from __future__ import annotations

import json
import sys
from typing import Any

from backend.ia.generar import (
    COLECTIVOS_VALIDOS,
    DIMENSIONES_VALIDAS,
    TIPOS_VALIDOS,
    _construir_terminos_prohibidos,
    _texto_contiene_prohibido,
    generar_encuesta,
    validar_encuesta,
)


def verificar_cumplimiento(
    encuesta: dict[str, Any], necesidad: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Verifica si la encuesta generada cumple los requisitos de estructura y contenido."""
    errores = []

    if "id" in encuesta:
        errores.append("La encuesta no debe tener 'id' en la raíz (lo añade la API).")

    preguntas = encuesta.get("preguntas", [])
    if not (3 <= len(preguntas) <= 6):
        errores.append(f"Número de preguntas fuera de rango (3-6): {len(preguntas)}")

    dur_max = necesidad.get("duracion_max_seg", 120)
    tiempo = encuesta.get("tiempo_estimado_seg", 0)
    if tiempo > dur_max:
        errores.append(f"Tiempo estimado ({tiempo}s) supera el máximo ({dur_max}s)")

    terminos_prohibidos = _construir_terminos_prohibidos(
        necesidad.get("temas_prohibidos", [])
    )
    for p in preguntas:
        texto = p.get("texto", "")
        if _texto_contiene_prohibido(texto, terminos_prohibidos):
            errores.append(f"Pregunta {p.get('id')} contiene tema prohibido: '{texto}'")

    for p in preguntas:
        c = p.get("condicion")
        anteriores = encuesta.get("preguntas", [])[:encuesta.get("preguntas", []).index(p)] \
            if p in encuesta.get("preguntas", []) else []
        if c is not None and not any(q["id"] == c.get("pregunta") and q["tipo"] == "escala_1_5"
                                     for q in anteriores):
            errores.append(f"Pregunta {p.get('id')} tiene una condición que no apunta a una escala anterior")

    if encuesta.get("colectivo") not in COLECTIVOS_VALIDOS:
        errores.append(f"Colectivo inválido: {encuesta.get('colectivo')}")
    if encuesta.get("estado") != "borrador":
        errores.append(f"Estado debe ser 'borrador', obtenido: {encuesta.get('estado')}")

    for idx, p in enumerate(preguntas, start=1):
        pid_esperado = f"p{idx}"
        if p.get("id") != pid_esperado:
            errores.append(f"Id de pregunta incorrecto: {p.get('id')} (esperado {pid_esperado})")
        if p.get("tipo") not in TIPOS_VALIDOS:
            errores.append(f"Tipo inválido en {p.get('id')}: {p.get('tipo')}")
        if p.get("dimension") not in DIMENSIONES_VALIDAS:
            errores.append(f"Dimensión inválida en {p.get('id')}: {p.get('dimension')}")
        if p.get("tipo") != "opcion" and p.get("opciones") != []:
            errores.append(f"Pregunta {p.get('id')} ({p.get('tipo')}) debe tener opciones = []")
        if p.get("tipo") == "opcion" and len(p.get("opciones", [])) < 2:
            errores.append(f"Pregunta opcion {p.get('id')} tiene menos de 2 opciones")

    textos = [p for p in preguntas if p.get("tipo") == "texto"]
    if len(textos) > 1:
        errores.append(f"Hay más de 1 pregunta de texto ({len(textos)})")
    if len(textos) == 1 and preguntas[-1].get("tipo") != "texto":
        errores.append("La pregunta de texto debe ser la última")

    return len(errores) == 0, errores


def imprimir_encuesta(encuesta: dict[str, Any]) -> None:
    """Imprime por consola la estructura detallada de una encuesta."""
    print(f"  Título: {encuesta.get('titulo')}")
    print(f"  Intro: {encuesta.get('intro')}")
    print(f"  Colectivo: {encuesta.get('colectivo')} | Estado: {encuesta.get('estado')} | Periodo: {encuesta.get('periodo')}")
    print(f"  Tiempo estimado: {encuesta.get('tiempo_estimado_seg')}s | Preguntas: {len(encuesta.get('preguntas', []))}")
    print("  Preguntas:")
    for p in encuesta.get("preguntas", []):
        opciones_str = f" | Opciones: {p['opciones']}" if p["tipo"] == "opcion" else ""
        print(f"    - [{p['id']}] ({p['tipo']} / {p['dimension']}) {p['texto']}{opciones_str}")


def probar_tres_necesidades() -> bool:
    """Ejecuta y valida la generación sobre tres casos representativos."""
    casos = [
        (
            "Caso 1: Planta - Nuevo sistema de turnos (120 s, prohibido salario)",
            {
                "objetivo": "Saber cómo afecta a planta el nuevo sistema de turnos implantado en octubre",
                "colectivo": "planta",
                "contexto": "Cambio de turnos rotativos en fábrica",
                "duracion_max_seg": 120,
                "temas_prohibidos": ["salario"],
            },
        ),
        (
            "Caso 2: Logística - Organización de almacén (< 60 s)",
            {
                "objetivo": "Evaluar la distribución y ritmo de carga en el almacén",
                "colectivo": "logistica",
                "contexto": "Picos de preparación de pedidos",
                "duracion_max_seg": 50,
                "temas_prohibidos": [],
            },
        ),
        (
            "Caso 3: Oficina - Nueva herramienta digital (180 s)",
            {
                "objetivo": "Adopción de la nueva herramienta interna de gestión",
                "colectivo": "oficina",
                "contexto": "Migración de software corporativo",
                "duracion_max_seg": 180,
                "temas_prohibidos": ["salario"],
            },
        ),
    ]

    todos_ok = True
    for nombre, necesidad in casos:
        print(f"\n{'='*70}")
        print(f"  {nombre}")
        print(f"{'='*70}")

        encuesta = generar_encuesta(necesidad)
        imprimir_encuesta(encuesta)

        ok, errores = verificar_cumplimiento(encuesta, necesidad)
        print(f"\n  Verificaciones:")
        print(f"    - 3 a 6 preguntas: {'OK' if 3 <= len(encuesta['preguntas']) <= 6 else 'FALLO'}")
        print(f"    - Tiempo <= máximo ({necesidad['duracion_max_seg']}s): {'OK' if encuesta['tiempo_estimado_seg'] <= necesidad['duracion_max_seg'] else 'FALLO'}")
        print(f"    - Sin temas prohibidos: {'OK' if not any('prohibido' in e for e in errores) else 'FALLO'}")
        print(f"    - Condición válida (null o a una escala anterior): "
              f"{'OK' if not comprobar_condiciones_y_fija(encuesta, {}) else 'FALLO'}")
        print(f"    - Valores cerrados: {'OK' if not any('inválid' in e for e in errores) else 'FALLO'}")

        if ok:
            print("  --> RESULTADO: CUMPLE TODOS LOS REQUISITOS [OK]")
        else:
            print("  --> RESULTADO: ERRORES DETECTADOS:")
            for err in errores:
                print(f"      * {err}")
            todos_ok = False

    return todos_ok


def probar_encuesta_mala() -> bool:
    """Comprueba que el validador corrija una encuesta con errores estructurales."""
    print(f"\n{'='*70}")
    print("  Caso 4: Prueba con encuesta 'MALA' (7 preguntas, tipo inválido, pregunta sobre sueldo)")
    print(f"{'='*70}")

    necesidad = {
        "objetivo": "Clima y condiciones generales",
        "colectivo": "planta",
        "duracion_max_seg": 90,
        "temas_prohibidos": ["salario"],
    }

    encuesta_mala = {
        "titulo": "Encuesta con fallos",
        "intro": "Intro de prueba.",
        "colectivo": "otro_colectivo_invalido",
        "preguntas": [
            {"id": "q1", "texto": "¿Cómo valoras el ambiente de trabajo?", "tipo": "escala_1_5", "opciones": [], "dimension": "bienestar"},
            {"id": "q2", "texto": "¿Qué te parece el sistema actual?", "tipo": "tipo_desconocido_inventado", "opciones": [], "dimension": "dimension_rara"},
            {"id": "q3", "texto": "¿Consideras que tu sueldo mensual es el adecuado?", "tipo": "escala_1_5", "opciones": [], "dimension": "condiciones"},
            {"id": "q4", "texto": "¿El horario te permite conciliar?", "tipo": "si_no", "opciones": ["si", "no"], "dimension": "bienestar"},
            {"id": "q5", "texto": "¿Qué turno prefieres?", "tipo": "opcion", "opciones": ["sola_opcion"], "dimension": "entorno"},
            {"id": "q6", "texto": "¿Recomendarías trabajar aquí?", "tipo": "escala_1_5", "opciones": [], "dimension": "cultura"},
            {"id": "q7", "texto": "Deja tus sugerencias finales", "tipo": "texto", "opciones": [], "dimension": "condiciones"},
        ],
    }

    print("  Entrada defectuosa:")
    print(f"    - Preguntas originales: {len(encuesta_mala['preguntas'])} (excede máx. 6)")
    print(f"    - Contiene pregunta prohibida: '{encuesta_mala['preguntas'][2]['texto']}' (sobre sueldo)")
    print(f"    - Tipo inválido: '{encuesta_mala['preguntas'][1]['tipo']}'")
    print(f"    - Colectivo incorrecto: '{encuesta_mala['colectivo']}'")
    print(f"    - Opción con menos de 2 opciones: {encuesta_mala['preguntas'][4]['opciones']}")

    corregida = validar_encuesta(encuesta_mala, necesidad)

    print("\n  Salida tras validar_encuesta():")
    imprimir_encuesta(corregida)

    ok, errores = verificar_cumplimiento(corregida, necesidad)
    if ok:
        print("\n  --> RESULTADO ENCUESTA MALA: CORREGIDA CON ÉXITO Y TOTALMENTE VÁLIDA [OK]")
    else:
        print("\n  --> RESULTADO: NO SE CORRIGIERON TODOS LOS ERRORES:")
        for err in errores:
            print(f"      * {err}")

    return ok


def prueba_robustez(n: int = 400, semilla: int = 1) -> list:
    """400 salidas del modelo inventadas: todas deben pasar validacion.validar_preguntas."""
    import copy
    import random

    from fastapi import HTTPException

    from backend.api.validacion import validar_preguntas
    from backend.reglas import duracion_minima

    sectores_posibles = ["planta", "logistica", "comercial", "oficina", "manager"]
    tipos = ["escala_1_5", "escala", "opcion", "si_no", "texto", "numero", None]

    def pregunta_rara(i):
        p = {"id": random.choice([f"x{i}", None, "c1"]), "tipo": random.choice(tipos),
             "texto": random.choice(["¿Cómo valoras el cambio de turnos?", "", "¿Qué cambiarías?",
                                     "Hablemos del salario"])}
        if random.random() < .5:
            p["opciones"] = random.choice([[], ["Sí", "No"], None, "a,b"])
        if random.random() < .7:
            p["dimension"] = random.choice(["condiciones", "bienestar", "foo", None])
        if random.random() < .4:  # condiciones inventadas: buenas, a ids que no existen o rotas
            p["condicion"] = random.choice([{"pregunta": random.choice(["x0", "x1", "c1", "p1", "zz"]),
                                             "valor_max": random.choice([2, "2", 0, 9, None])},
                                            "p1", None, {}])
        return p

    random.seed(semilla)
    fallos = []
    for _ in range(n):
        sectores = random.sample(sectores_posibles, random.randint(1, 5))
        duracion = random.choice([duracion_minima(len(sectores)), 90, 120, 300])
        necesidad = {"objetivo": "Saber cómo afecta el nuevo sistema de turnos", "colectivos": sectores,
                     "contexto": "x", "duracion_max_seg": duracion, "temas_prohibidos": ["salario"]}
        if random.random() < .3:
            necesidad["pregunta_fija"] = {"texto": "¿Te da tiempo a hacer la pausa completa?",
                                          "tipo": random.choice(["escala_1_5", "si_no", "texto", None]),
                                          "dimension": "bienestar"}
        salida_modelo = {
            "titulo": random.choice(["T", None, ""]), "intro": "i",
            "preguntas": [pregunta_rara(i) for i in range(random.randint(0, 6))],
            "preguntas_por_colectivo": {c: [pregunta_rara(j) for j in range(random.randint(0, 4))]
                                        for c in random.sample(sectores_posibles, random.randint(0, 5))}}
        try:
            encuesta = validar_encuesta(copy.deepcopy(salida_modelo), necesidad)
            validar_preguntas(encuesta)
        except HTTPException as error:
            fallos.append(error.detail)
            continue
        problema = comprobar_condiciones_y_fija(encuesta, necesidad)
        if problema:
            fallos.append(problema)
    return fallos


def comprobar_condiciones_y_fija(encuesta: dict, necesidad: dict) -> str | None:
    """Condición: a una escala_1_5 anterior, valor_max 1-4, como mucho una por persona.
    Pregunta fija: la primera, con fija: true, si la necesidad la trae."""
    nucleo = encuesta["preguntas"]
    vistas_por_sector = [nucleo + l for l in encuesta["preguntas_por_colectivo"].values()] or [nucleo]
    for vistas in vistas_por_sector:
        condicionales = [p for p in vistas if p.get("condicion")]
        if len(condicionales) > 1:
            return "más de una pregunta condicional"
        for p in condicionales:
            c = p["condicion"]
            anteriores = vistas[:vistas.index(p)]
            if not any(q["id"] == c["pregunta"] and q["tipo"] == "escala_1_5" for q in anteriores):
                return f"condición de {p['id']} sin escala anterior {c}"
            if not 1 <= c["valor_max"] <= 4:
                return f"valor_max fuera de rango en {p['id']}"
    if necesidad.get("pregunta_fija") and not (nucleo and nucleo[0].get("fija")):
        return "la pregunta fija no es la primera"
    if sum(1 for v in vistas_por_sector[0] if v.get("fija")) > 1:
        return "más de una pregunta fija"
    return None


def probar_robustez() -> bool:
    print(f"\n{'=' * 70}\n  Caso 5: robustez (400 salidas del modelo inventadas × 3 semillas)\n{'=' * 70}")
    fallos = [f for semilla in (1, 2, 3) for f in prueba_robustez(400, semilla)]
    print(f"  Fallos de validación: {len(fallos)} de 1200" + (f" · primero: {fallos[0]}" if fallos else ""))
    try:
        validar_encuesta({"preguntas": []}, {"objetivo": "x", "colectivos": ["planta", "logistica"],
                                             "duracion_max_seg": 30, "temas_prohibidos": []})
        print("  30 s con 2 sectores: se ha generado una encuesta (ERROR)")
        return False
    except ValueError as error:
        print(f"  30 s con 2 sectores → error claro: {error}")
    return not fallos


def probar_idiomas() -> bool:
    """Sin IA, una encuesta en catalán o en inglés sale entera en ese idioma."""
    print(f"\n{'=' * 70}\n  Caso 6: idioma original (es, ca, en) y temas prohibidos en cualquier idioma\n{'=' * 70}")
    from backend.api.validacion import validar_preguntas
    marcas = {"es": ("¿", "turnos"), "ca": ("torns", "Com "), "en": ("shift", "How ")}
    ajenas = {"es": ("torns", "shift"), "ca": ("¿", "shift"), "en": ("¿", "torns")}
    ok = True
    for idioma in ("es", "ca", "en"):
        for colectivos in (["planta"], ["planta", "logistica", "oficina"]):
            e = generar_encuesta({"colectivos": colectivos, "objetivo": "Nuevo sistema de turnos",
                                  "contexto": "", "duracion_max_seg": 120,
                                  "temas_prohibidos": ["salario"]}, "", idioma)
            textos = " ".join([e["titulo"], e["intro"]] + [p["texto"] for p in e["preguntas"]]
                              + [p["texto"] for l in e["preguntas_por_colectivo"].values() for p in l])
            bien = (e.get("idioma_original") == idioma and any(m in textos for m in marcas[idioma])
                    and not any(m in textos for m in ajenas[idioma]))
            try:
                validar_preguntas(e)
            except Exception as error:  # noqa: BLE001
                bien = False
                print(f"    validar_preguntas rechaza la encuesta: {error}")
            print(f"  {idioma} · {len(colectivos)} sector(es): {e['titulo']} → {'OK' if bien else 'ERROR'}")
            ok = ok and bien
    for lista in (["salario"], ["sou"], ["salary"]):
        t = _construir_terminos_prohibidos(lista)
        frases = ["¿Estás contento con tu sueldo?", "Estàs content amb el teu sou?", "Is your salary fair?"]
        bien = all(_texto_contiene_prohibido(f, t) for f in frases)
        print(f"  Prohibido {lista} bloquea es/ca/en: {'OK' if bien else 'ERROR'}")
        ok = ok and bien
    return ok


def probar_fija_y_condicional() -> bool:
    """Pregunta fija la primera (con y sin IA) y una condicional en el respaldo de planta."""
    print(f"\n{'=' * 70}\n  Caso 7: pregunta fija del compromiso y lógica condicional\n{'=' * 70}")
    from unittest import mock
    from backend.ia import generar
    fija = {"texto": "¿Te da tiempo a hacer la pausa completa?", "tipo": "escala_1_5", "dimension": "bienestar"}
    modelo = {"titulo": "Pausas", "intro": "Anónima.", "preguntas": [
        {"id": "p1", "texto": "¿Te da tiempo a hacer la pausa completa en tu turno?", "tipo": "escala_1_5"},
        {"id": "p2", "texto": "¿Cómo valoras el relevo?", "tipo": "escala_1_5"},
        {"id": "p3", "texto": "¿Qué ha pasado? Cuéntanos qué mejorarías", "tipo": "texto",
         "condicion": {"pregunta": "p2", "valor_max": 2}}]}
    ok = True
    for nombre, con_ia in (("sin IA", False), ("con IA", True)):
        for colectivos in (["planta"], ["planta", "oficina"]):
            necesidad = {"colectivos": colectivos, "objetivo": "Pausas", "duracion_max_seg": 120,
                         "temas_prohibidos": ["salario"], "pregunta_fija": fija}
            with mock.patch.object(generar, "hay_llm", lambda: con_ia), \
                    mock.patch.object(generar, "llamar_llm_json", lambda *a, **k: dict(modelo)):
                e = generar.generar_encuesta(necesidad)
            primera = e["preguntas"][0]
            bien = (primera.get("fija") is True and primera["texto"] == fija["texto"]
                    and primera["id"] in ("p1", "c1") and not comprobar_condiciones_y_fija(e, necesidad))
            print(f"  Fija {nombre} · {len(colectivos)} sector(es): {primera['id']} {primera['texto']} → "
                  f"{'OK' if bien else 'ERROR'}")
            ok = ok and bien
    with mock.patch.object(generar, "hay_llm", lambda: False):
        for colectivos in (["planta"], ["logistica"], ["planta", "oficina"]):
            e = generar.generar_encuesta({"colectivos": colectivos, "objetivo": "Turnos",
                                          "duracion_max_seg": 120, "temas_prohibidos": []})
            todas = e["preguntas"] + [p for l in e["preguntas_por_colectivo"].values() for p in l]
            condicionales = [p for p in todas if p.get("condicion")]
            bien = len(condicionales) == 1 and not comprobar_condiciones_y_fija(e, {})
            print(f"  Condicional sin IA · {'+'.join(colectivos)}: "
                  f"{condicionales[0]['id'] + ' si ' + str(condicionales[0]['condicion']) if condicionales else 'ninguna'}"
                  f" → {'OK' if bien else 'ERROR'}")
            ok = ok and bien
    return ok


def main() -> int:
    """Ejecuta el conjunto completo de pruebas de generación."""
    print("=" * 70)
    print("  SUITE DE PRUEBAS: backend.ia.probar_generar (Modo Respaldo / Sin Clave)")
    print("=" * 70)

    ok_casos = probar_tres_necesidades()
    ok_mala = probar_encuesta_mala()
    ok_mala = probar_robustez() and ok_mala
    ok_mala = probar_idiomas() and ok_mala
    ok_mala = probar_fija_y_condicional() and ok_mala

    print("\n" + "=" * 70)
    if ok_casos and ok_mala:
        print("  TODAS LAS PRUEBAS HAN PASADO SATISFACTORIAMENTE [OK]")
        print("=" * 70)
        return 0
    else:
        print("  ALGUNAS PRUEBAS HAN FALLADO [ERROR]")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
