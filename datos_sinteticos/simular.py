"""Respuestas simuladas para cualquier encuesta publicada, con la misma historia que enc_000.

Uso desde el código: simular_respuestas(encuesta, plantilla, n, periodos) devuelve una lista
de Respuesta; quien la llama decide si la guarda. Uso por terminal:

    python3 datos_sinteticos/simular.py ruta/encuesta.json [--n 300] [--salida respuestas.json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from typing import Any

try:
    from . import generar as base
except ImportError:  # Ejecutado como script
    import generar as base

DIMENSION_POR_TEMA = {
    # Qué dimensiones empeora cada tema, para que notas y comentarios cuenten lo mismo
    "descansos": {"bienestar": -0.6, "condiciones": -0.8},
    "turnos": {"bienestar": -0.4, "condiciones": -0.9},
    "carga_trabajo": {"bienestar": -0.5, "condiciones": -0.7},
    "comunicacion": {"liderazgo": -0.7, "cultura": -0.6},
    "liderazgo": {"liderazgo": -0.8},
    "formacion": {"desarrollo": -0.8},
    "reconocimiento": {"liderazgo": -0.3, "cultura": -0.5, "desarrollo": -0.3},
    "herramientas": {"condiciones": -0.4, "entorno": -0.4},
    "seguridad": {"entorno": -0.6},
    "ambiente": {"entorno": -0.8, "cultura": -0.4},
    "conciliacion": {"bienestar": -0.5, "condiciones": -0.3},
    "otros": {},
}
TEMAS_NEGATIVOS = {"descansos", "turnos", "carga_trabajo", "comunicacion"}

# Misma historia que enc_000 pero con subidas más suaves: aquí todos los colectivos siguen el
# patrón de planta y, si suben mucho unos temas, el resto aparenta bajar
PESOS_ANTERIOR = dict(base.PESOS_TEMA[("planta", base.PERIODO_ANTERIOR)])
PESOS_ACTUAL = {**PESOS_ANTERIOR, "descansos": 14, "turnos": 12, "comunicacion": 7}
TENDENCIAS_ESPERADAS = {"descansos": "sube", "turnos": "sube", "comunicacion": "nuevo"}
INTENTOS_SEMILLA = 40
N_MINIMO_HISTORIA = 300  # Por debajo, algún tema de la historia puede quedar oculto o desviarse


def _mes_anterior(periodo: str) -> str:
    anio, mes = map(int, periodo.split("-"))
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def _dias(periodo: str) -> list[str]:
    # En el mes en curso solo hasta hoy, para no generar respuestas con fecha futura
    hoy = dt.date.today().isoformat()
    dias = [d for d in base.dias_laborables(periodo) if d <= hoy]
    return dias or [f"{periodo}-01"]


def colectivos_de(encuesta: dict[str, Any]) -> list[str]:
    """Colectivos de la encuesta en orden fijo: colectivos (v2) o colectivo (todos o uno)."""
    lista = [c for c in base.COLECTIVOS if c in (encuesta.get("colectivos") or [])]
    if lista:
        return lista
    colectivo = encuesta.get("colectivo")
    if colectivo in (None, "todos", "varios"):
        return list(base.COLECTIVOS)
    return [colectivo] if colectivo in base.COLECTIVOS else []


def preguntas_de(encuesta: dict[str, Any], colectivo: str) -> list[dict[str, Any]]:
    """Preguntas que ve un colectivo: el núcleo común más las propias de su sector."""
    return (encuesta.get("preguntas") or []) + (
        encuesta.get("preguntas_por_colectivo") or {}).get(colectivo, [])


def _segmentos(encuesta: dict[str, Any], plantilla: list[dict[str, Any]]) -> list[dict]:
    colectivos = colectivos_de(encuesta)
    filas = [f for f in plantilla if f.get("colectivo") in colectivos and f.get("personas", 0) > 0]
    # Colectivos sin filas en la plantilla: una fila por defecto para que también respondan
    for c in colectivos:
        if not any(f["colectivo"] == c for f in filas):
            turnos = base.TURNOS_PLANTA if c == "planta" else ["sin_turno"]
            filas += [{"colectivo": c, "turno": t, "personas": 100} for t in turnos]
    return filas


def _repartir(total: int, pesos: list[float]) -> list[int]:
    cuotas = [total * p / sum(pesos) for p in pesos]
    partes = [int(c) for c in cuotas]
    for i in sorted(range(len(cuotas)), key=lambda i: cuotas[i] - partes[i], reverse=True)[
            : total - sum(partes)]:
        partes[i] += 1
    return partes


def _valor(pregunta: dict, tema: str, colectivo: str, actual: bool, rng: random.Random):
    tipo = pregunta.get("tipo")
    if tipo == "escala_1_5":
        mu = base.MEDIA_BASE.get(colectivo, 3.3)
        mu += DIMENSION_POR_TEMA.get(tema, {}).get(pregunta.get("dimension"), 0.0)
        if actual and colectivo == "planta" and pregunta.get("dimension") == "condiciones":
            mu += base.CAIDA_P4_PLANTA
        return base._nota(mu, rng)
    if tipo == "si_no":
        return "si" if rng.random() < (0.35 if tema in TEMAS_NEGATIVOS else 0.6) else "no"
    if tipo == "opcion":
        opciones = [o for o in pregunta.get("opciones") or [] if str(o).strip()]
        if not opciones:
            return None
        raices = base.quitar_tildes(tema.replace("_", " ")).lower().split()
        pesos = {o: 4.0 if any(r[:6] in base.quitar_tildes(o).lower() for r in raices) else 1.0
                 for o in opciones}
        return base.elegir_ponderado(pesos, rng)
    return None


def _condicion_cumplida(pregunta: dict, valores: dict) -> bool:
    condicion = pregunta.get("condicion")
    if not condicion:
        return True
    previo = valores.get(condicion.get("pregunta"))
    return isinstance(previo, int) and previo <= condicion.get("valor_max", 5)


def simular_respuestas(encuesta: dict[str, Any], plantilla: list[dict[str, Any]],
                       n: int = 300, periodos: list[str] | None = None,
                       semilla: int = 42) -> list[dict[str, Any]]:
    """Genera unas n respuestas repartidas entre dos periodos para una encuesta publicada.

    Respeta la participación desigual de la plantilla y reproduce la historia de enc_000:
    suben descansos y turnos, aparece comunicacion y en planta bajan las notas de condiciones.
    La respuesta a la pregunta de texto va en comentario, nunca en valores. Con menos de 300
    respuestas la historia puede no verse completa.
    """
    # Se prueba la primera semilla con la que el dashboard contaría exactamente esa historia
    for intento in range(INTENTOS_SEMILLA):
        respuestas = _simular(encuesta, plantilla, n, periodos, semilla + intento)
        if _historia_ok(respuestas):
            return respuestas
    return _simular(encuesta, plantilla, n, periodos, semilla)


def _historia_ok(respuestas: list[dict]) -> bool:
    if not any(r["comentario"] for r in respuestas):
        return True
    clasificar = _clasificador()
    periodos = sorted({r["periodo"] for r in respuestas})
    if len(periodos) < 2:
        return True
    cuenta, totales = {}, {p: 0 for p in periodos}
    for r in respuestas:
        if r["comentario"]:
            tema = clasificar(r["comentario"]) if clasificar else r["tema_real"]
            cuenta[(r["periodo"], tema)] = cuenta.get((r["periodo"], tema), 0) + 1
            totales[r["periodo"]] += 1
    anterior, actual = periodos[-2], periodos[-1]
    for tema in base.TEMAS:
        n_act = cuenta.get((actual, tema), 0)
        tendencia = base.calcular_tendencia(n_act, totales[actual],
                                            cuenta.get((anterior, tema), 0), totales[anterior])
        esperada = TENDENCIAS_ESPERADAS.get(tema)
        if esperada and (n_act < 5 or tendencia != esperada):
            return False
        if not esperada and n_act >= 5 and tendencia != "estable":
            return False
    return True


def _clasificador():
    # Se usa el mismo clasificador que el dashboard; si no está disponible, el tema real
    try:
        from backend.ia.analizar import clasificar_por_palabras
        return clasificar_por_palabras
    except ImportError:
        return None


def _simular(encuesta: dict[str, Any], plantilla: list[dict[str, Any]], n: int,
             periodos: list[str] | None, semilla: int) -> list[dict[str, Any]]:
    rng = random.Random(f"{encuesta.get('id')}-{semilla}")
    actual = (periodos or [None, encuesta.get("periodo") or dt.date.today().strftime("%Y-%m")])[-1]
    periodos = periodos or [_mes_anterior(actual), actual]
    anterior, actual = periodos[-2], periodos[-1]
    segmentos = _segmentos(encuesta, plantilla)
    if not segmentos:
        return []
    # Solo el núcleo puede tener la pregunta de texto (las propias de un sector nunca la tienen)
    hay_texto = any(p.get("tipo") == "texto" for c in colectivos_de(encuesta)
                    for p in preguntas_de(encuesta, c))

    # Huecos por periodo y segmento, proporcionales a personas por tasa de respuesta
    pesos = [f["personas"] * base.tasa_de(f["colectivo"], f["turno"])[0] for f in segmentos]
    huecos = []
    for periodo, n_periodo in zip((anterior, actual), _repartir(n, [1, 1])):
        for fila, n_fila in zip(segmentos, _repartir(n_periodo, pesos)):
            huecos += [{"periodo": periodo, "colectivo": fila["colectivo"], "turno": fila["turno"]}
                       for _ in range(n_fila)]

    # Reparto exacto de temas, como en enc_000: la historia no depende del azar
    for periodo, pesos_tema in ((anterior, PESOS_ANTERIOR), (actual, PESOS_ACTUAL)):
        for grupo in ("planta", "resto"):
            del_grupo = [h for h in huecos if h["periodo"] == periodo
                         and (h["colectivo"] == "planta") == (grupo == "planta")]
            rng.shuffle(del_grupo)
            n_vacios = round(len(del_grupo) * 0.15) if hay_texto else len(del_grupo)
            temas = base._reparto_exacto(pesos_tema, len(del_grupo) - n_vacios, rng)
            for i, h in enumerate(del_grupo):
                h["vacio"] = i < n_vacios
                h["tema"] = (base.elegir_ponderado(pesos_tema, rng) if h["vacio"]
                             else temas[i - n_vacios])

    dias = {anterior: _dias(anterior), actual: _dias(actual)}
    usados: set[str] = set()
    respuestas = []
    for h in huecos:
        valores: dict[str, Any] = {}
        for p in preguntas_de(encuesta, h["colectivo"]):
            if p.get("tipo") == "texto" or not _condicion_cumplida(p, valores):
                continue
            valor = _valor(p, h["tema"], h["colectivo"], h["periodo"] == actual, rng)
            if valor is not None:
                valores[p["id"]] = valor
        comentario = ("" if h["vacio"] else
                      base._comentario(h["tema"], h["colectivo"], rng, rng.random() < 0.06))
        while True:
            rid = "r_" + "".join(rng.choice("0123456789abcdef") for _ in range(8))
            if rid not in usados:
                usados.add(rid)
                break
        respuestas.append({
            "id": rid,
            "encuesta_id": encuesta.get("id"),
            "fecha": rng.choice(dias[h["periodo"]]),
            "periodo": h["periodo"],
            "colectivo": h["colectivo"],
            "centro_tipo": base.CENTRO_MAP[h["colectivo"]],
            "turno": h["turno"],
            "canal": base.elegir_ponderado(dict(base.CANAL_PROBS[h["colectivo"]]), rng),
            "valores": valores,
            "comentario": comentario,
            "tema_real": h["tema"],
        })
    return respuestas


def _resumen(respuestas: list[dict], periodos: list[str]) -> str:
    anterior, actual = periodos[-2], periodos[-1]
    cuenta = {}
    totales = {anterior: 0, actual: 0}
    for r in respuestas:
        if r["comentario"]:
            cuenta[(r["periodo"], r["tema_real"])] = cuenta.get((r["periodo"], r["tema_real"]), 0) + 1
            totales[r["periodo"]] += 1
    lineas = []
    for tema in base.TEMAS:
        n_ant, n_act = cuenta.get((anterior, tema), 0), cuenta.get((actual, tema), 0)
        tendencia = base.calcular_tendencia(n_act, totales[actual], n_ant, totales[anterior])
        lineas.append(f"    {tema:<16}{n_ant:>4} -> {n_act:<4} {tendencia if n_act >= 5 else 'oculto'}")
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simula respuestas para una encuesta publicada")
    parser.add_argument("encuesta", help="Ruta del JSON de la encuesta")
    parser.add_argument("--n", type=int, default=300, help="Número de respuestas (por defecto 300)")
    parser.add_argument("--salida", help="Ruta donde guardar las respuestas (por defecto, ninguna)")
    args = parser.parse_args()

    with open(args.encuesta, encoding="utf-8") as f:
        encuesta = json.load(f)
    plantilla = base.cargar_plantilla()
    if args.n < N_MINIMO_HISTORIA:
        print(f"  Aviso: con menos de {N_MINIMO_HISTORIA} respuestas algún tema puede quedar oculto")
    respuestas = simular_respuestas(encuesta, plantilla, args.n)
    periodos = sorted({r["periodo"] for r in respuestas})
    print(f"  {len(respuestas)} respuestas para {encuesta.get('id')} ({encuesta.get('colectivo')}) "
          f"en {' y '.join(periodos)}")
    if len(periodos) == 2:
        print(_resumen(respuestas, periodos))
    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(respuestas, f, ensure_ascii=False, indent=2)
        print(f"  Guardadas en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
