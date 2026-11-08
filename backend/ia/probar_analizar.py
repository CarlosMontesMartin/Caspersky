"""Pruebas de integración para análisis temático y recomendaciones sobre datos sintéticos."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

from backend.ia import segundo_plano
from backend.ia.analizar import (TEMAS, analizar_comentarios, clasificar_comentarios,
                                 clasificar_por_palabras)
from backend.ia.llm import hay_llm
from backend.ia.recomendar import recomendar

RAIZ = Path(__file__).resolve().parents[2]


# 3 frases en inglés y 3 en catalán por tema: sin IA deben acertarse al menos el 85 % (v5, P0-3)
MINIMO_SIN_IA = 0.85
FRASES_EN_CA = {
    "descansos": [
        "There is no time to rest between shifts",
        "Breaks are too short, I can't even sit down",
        "I'm exhausted by the end of the day, we need proper breaks",
        "No tenim temps per fer la pausa sencera",
        "Els descansos són massa curts i no pots ni seure",
        "Acabo esgotat, necessitem poder desconnectar una estona",
    ],
    "turnos": [
        "The new rota changes every week",
        "Night shift every other week is hard",
        "The shift schedule was changed without notice",
        "El nou sistema de torns no s'entén",
        "Ens canvien el quadrant cada setmana",
        "Fer el torn de nit cada dues setmanes costa molt",
    ],
    "carga_trabajo": [
        "We need more staff, the workload is too high",
        "We are understaffed and the pace is crazy",
        "Too much work for so few people",
        "Falta personal i no arribem a tot",
        "La càrrega de feina és massa alta",
        "Som pocs i el ritme és bestial",
    ],
    "comunicacion": [
        "Nobody told us about the changes",
        "We find out about everything through rumours",
        "Communication from management arrives late",
        "Ningú ens va informar dels canvis",
        "Ens assabentem de tot per rumors",
        "La comunicació arriba tard i malament",
    ],
    "liderazgo": [
        "My manager never listens to us",
        "The supervisor doesn't give any feedback",
        "Our boss makes decisions without asking",
        "El meu responsable no ens escolta",
        "Els caps no donen mai feedback",
        "L'encarregat decideix sense preguntar",
    ],
    "herramientas": [
        "The forklift breaks down every week",
        "The software is slow and crashes",
        "We don't have the right equipment",
        "Les eines estan fetes pols",
        "La màquina s'espatlla cada dos per tres",
        "El programa nou va molt lent",
    ],
    "formacion": [
        "There is no training for the new line",
        "I'd like a course to improve my skills",
        "No career path or promotion opportunities",
        "No hi ha formació per a la línia nova",
        "M'agradaria fer algun curs",
        "No veig com puc créixer a l'empresa",
    ],
    "reconocimiento": [
        "Nobody ever says thank you",
        "I don't feel valued for my effort",
        "Good work goes unnoticed",
        "Ningú reconeix la feina ben feta",
        "No em sento valorat",
        "Un gràcies de tant en tant no costa res",
    ],
    "seguridad": [
        "Safety in the warehouse is poor",
        "There was almost an accident yesterday",
        "We lack PPE and the floor is dangerous",
        "La seguretat al magatzem deixa molt a desitjar",
        "Ahir gairebé hi va haver un accident",
        "Falten EPI i el terra rellisca",
    ],
    "ambiente": [
        "The atmosphere in the team is great",
        "There is tension between colleagues",
        "My coworkers always help each other",
        "L'ambient amb els companys és molt bo",
        "Hi ha mal rotllo a l'equip",
        "Els companys sempre ajuden",
    ],
    "conciliacion": [
        "I can't pick up my kids from school",
        "We need more flexible hours for family",
        "Work-life balance is impossible with this schedule",
        "No puc anar a buscar els nens a l'escola",
        "Necessitem més flexibilitat per a la família",
        "Amb aquest horari no puc conciliar",
    ],
    "otros": [
        "The canteen food is cold",
        "The parking is always full",
        "The coffee machine has been broken for weeks",
        "El menjador és massa petit",
        "No hi ha prou aparcament",
        "Res a dir, tot bé",
    ],
}


def precision_sin_ia() -> float:
    """Acierto de las palabras clave (sin modelo) con las frases en inglés y catalán."""
    filas = [(tema, f) for tema, lista in FRASES_EN_CA.items() for f in lista]
    fallos = [(tema, f, clasificar_por_palabras(f)) for tema, f in filas if clasificar_por_palabras(f) != tema]
    precision = 1 - len(fallos) / len(filas)
    print(f"Clasificación sin IA en inglés y catalán: {precision:.0%} ({len(filas) - len(fallos)}/{len(filas)})")
    for tema, frase, predicho in fallos:
        print(f"  {tema} → {predicho}: {frase}")
    return precision


def _cargar(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    """Ejecuta la validación de análisis temático, cálculo de tendencias y recomendaciones."""
    respuestas = _cargar(RAIZ / "datos_sinteticos" / "respuestas.json")
    encuesta = _cargar(RAIZ / "datos_sinteticos" / "enc_000.json")
    plantilla_ruta = RAIZ / "contenido" / "plantilla.json"
    plantilla = _cargar(plantilla_ruta) if plantilla_ruta.exists() else []

    periodos = sorted({r["periodo"] for r in respuestas})
    actual = [r for r in respuestas if r["periodo"] == periodos[-1]]
    anterior = [r for r in respuestas if len(periodos) > 1 and r["periodo"] == periodos[-2]]
    print(f"Modo: {'IA real' if hay_llm() else 'respaldo (sin clave)'}")
    print(f"Respuestas: {len(actual)} en {periodos[-1]} · {len(anterior)} en "
          f"{periodos[-2] if len(periodos) > 1 else '-'}")

    con_texto = [r for r in respuestas if r.get("comentario")]
    predichos = clasificar_comentarios([r["comentario"] for r in con_texto])
    aciertos = sum(p == r["tema_real"] for p, r in zip(predichos, con_texto))
    print(f"\nPrecisión de la clasificación: {aciertos / len(con_texto):.0%} "
          f"({aciertos}/{len(con_texto)})")
    fallos = Counter((r["tema_real"], p) for p, r in zip(predichos, con_texto) if p != r["tema_real"])
    if fallos:
        print("  Confusiones más frecuentes (real → predicho):",
              ", ".join(f"{a}→{b} ×{n}" for (a, b), n in fallos.most_common(4)))

    inicio = time.time()
    temas = analizar_comentarios(actual, anterior)
    print(f"\nPrimera carga del análisis: {time.time() - inicio:.1f} s")
    if hay_llm():
        inicio = time.time()
        segundo_plano.esperar()
        temas = analizar_comentarios(actual, anterior)
        print(f"Resúmenes del modelo listos en segundo plano tras {time.time() - inicio:.1f} s")
    print("\nTemas (n ≥ 5):")
    for t in temas:
        flecha = "↑" if t["tendencia"] in ("nuevo", "sube") else "↓" if t["tendencia"] == "baja" else "·"
        print(f"  {flecha} {t['tema']:<15}{t['n']:>4}  {t['tendencia']:<8} {t['resumen']}")

    participacion = []
    for fila in plantilla:
        n = sum(1 for r in actual if r["colectivo"] == fila["colectivo"] and r["turno"] == fila["turno"])
        tasa = n / fila["personas"] if fila["personas"] else 0.0
        participacion.append({**fila, "respuestas": n, "tasa": round(tasa, 3),
                              "representativo": n >= 5 and tasa >= 0.20})
    analisis = {"encuesta_id": encuesta["id"], "n_respuestas": len(actual),
                "periodo_actual": periodos[-1],
                "periodo_anterior": periodos[-2] if len(periodos) > 1 else None,
                "participacion": participacion, "medias": [], "temas": temas,
                "alertas": [], "limites": []}
    rec = recomendar(analisis, encuesta)
    if hay_llm():
        segundo_plano.esperar()
        rec = recomendar(analisis, encuesta)
    print(f"\nLectura ({rec.get('origen')}): {rec.get('lectura')}")
    print("\nRecomendaciones (propuestas):")
    for a in rec["acciones"]:
        print(f"  - {a['titulo']}  [{a['tema']}]\n      {a['motivo']}\n"
              f"      {a.get('responsable')} · {a.get('plazo')} · {a.get('indicador')}")
    print("Encuesta de seguimiento:", json.dumps(rec["seguimiento"], ensure_ascii=False))

    errores = []
    if any(t["tema"] not in TEMAS or t["n"] < 5 for t in temas):
        errores.append("tema fuera de la lista o con n < 5")
    if any(t["tendencia"] not in ("nuevo", "sube", "estable", "baja") for t in temas):
        errores.append("tendencia no válida")
    if not 1 <= len(rec["acciones"]) <= 3:
        errores.append("número de acciones fuera de 1–3")
    seg = rec["seguimiento"]
    if not {"objetivo", "colectivos", "contexto", "duracion_max_seg", "temas_prohibidos"} <= set(seg):
        errores.append("el seguimiento no tiene el formato Necesidad")
    if rec.get("origen") not in ("ia", "reglas") or not rec.get("lectura"):
        errores.append("faltan origen o lectura")
    if any(not {"responsable", "plazo", "indicador"} <= set(a) for a in rec["acciones"]):
        errores.append("acciones sin responsable, plazo o indicador")
    if any({"n_anterior", "pct", "pct_anterior"} - set(t) for t in temas):
        errores.append("temas sin n_anterior, pct o pct_anterior")
    if seg.get("duracion_max_seg") != 60:
        errores.append("duracion_max_seg del seguimiento distinta de 60")
    if precision_sin_ia() < MINIMO_SIN_IA:
        errores.append(f"clasificación sin IA en inglés y catalán por debajo del {MINIMO_SIN_IA:.0%}")
    print("\n" + ("TODAS LAS COMPROBACIONES OK" if not errores else "ERRORES: " + "; ".join(errores)))
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
