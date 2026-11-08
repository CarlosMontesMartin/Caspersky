"""Métricas agregadas · UPC 2 (modulos.md sección 2 y v2.md secciones 1.3 y 3.4).

Todo lo que sale de aquí es agregado. Ningún segmento con menos de
UMBRAL_MINIMO respuestas muestra medias, distribuciones ni temas.
"""
from collections import Counter

from backend import textos
from backend.reglas import COLECTIVOS

UMBRAL_MINIMO = 5
TASA_REPRESENTATIVA = 0.20
UMBRAL_CAIDA = 0.5

ORDEN_COLECTIVOS = list(COLECTIVOS)
TEMAS_SIN_ZONA = {None, "", "otros", "ninguno"}


# ---------- utilidades ----------

def _colectivos(datos) -> list[str]:
    """Lista de colectivos a partir de una lista, un str ("todos" o uno) o una Encuesta."""
    if isinstance(datos, dict):
        lista = datos.get("colectivos")
        datos = lista if isinstance(lista, list) and lista else datos.get("colectivo", "todos")
    if isinstance(datos, str):
        return list(ORDEN_COLECTIVOS) if datos == "todos" else [datos]
    return [c for c in ORDEN_COLECTIVOS if c in (datos or [])]


def _todas_las_preguntas(encuesta: dict) -> list[tuple[dict, str]]:
    """(pregunta, ambito): ambito = "comun" o el colectivo."""
    resultado = [(p, "comun") for p in encuesta.get("preguntas", [])]
    for colectivo, lista in (encuesta.get("preguntas_por_colectivo") or {}).items():
        resultado += [(p, colectivo) for p in lista]
    return resultado


def _escalas(encuesta: dict) -> list[dict]:
    return [p for p, _ in _todas_las_preguntas(encuesta) if p.get("tipo") == "escala_1_5"]


def _media_escalas(respuestas: list, encuesta: dict) -> float | None:
    """Media de todas las respuestas de escala; None si hay menos de UMBRAL_MINIMO personas."""
    if len(respuestas) < UMBRAL_MINIMO:
        return None
    ids = {p["id"] for p in _escalas(encuesta)}
    valores = [v for r in respuestas for k, v in r.get("valores", {}).items()
               if k in ids and isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(sum(valores) / len(valores), 2) if valores else None


# ---------- periodos ----------

def separar_periodos(respuestas: list) -> tuple:
    """(actual, anterior, periodo_actual, periodo_anterior). Periodos "AAAA-MM"."""
    periodos = sorted({r["periodo"] for r in respuestas if r.get("periodo")})
    if not periodos:
        return [], [], None, None
    p_actual = periodos[-1]
    p_anterior = periodos[-2] if len(periodos) > 1 else None
    actual = [r for r in respuestas if r.get("periodo") == p_actual]
    anterior = [r for r in respuestas if p_anterior and r.get("periodo") == p_anterior]
    return actual, anterior, p_actual, p_anterior


# ---------- participación, medias, distribuciones ----------

def calcular_participacion(respuestas: list, plantilla: list, colectivos) -> list:
    """Una fila por fila de la plantilla de los colectivos (lista, "todos" o un colectivo)."""
    incluidos = set(_colectivos(colectivos))
    filas = []
    for fila in plantilla:
        if fila["colectivo"] not in incluidos:
            continue
        n = sum(1 for r in respuestas if r.get("colectivo") == fila["colectivo"] and r.get("turno") == fila["turno"])
        personas = fila.get("personas", 0)
        tasa = round(n / personas, 3) if personas else 0.0
        filas.append({"colectivo": fila["colectivo"], "turno": fila["turno"], "respuestas": n,
                      "personas": personas, "tasa": tasa,
                      "representativo": n >= UMBRAL_MINIMO and tasa >= TASA_REPRESENTATIVA})
    orden = {c: i for i, c in enumerate(ORDEN_COLECTIVOS)}
    return sorted(filas, key=lambda f: orden.get(f["colectivo"], 99))


def calcular_medias(respuestas: list, encuesta: dict) -> list:
    """Media por pregunta escala_1_5 (núcleo y propias) y colectivo. Omite n < UMBRAL_MINIMO."""
    medias = []
    colectivos = [c for c in ORDEN_COLECTIVOS if any(r.get("colectivo") == c for r in respuestas)]
    for pregunta in _escalas(encuesta):
        for colectivo in colectivos:
            valores = [r["valores"][pregunta["id"]] for r in respuestas
                       if r.get("colectivo") == colectivo
                       and isinstance(r.get("valores", {}).get(pregunta["id"]), (int, float))]
            if len(valores) >= UMBRAL_MINIMO:
                medias.append({"pregunta": pregunta["id"], "colectivo": colectivo,
                               "media": round(sum(valores) / len(valores), 1), "n": len(valores)})
    return medias


def calcular_distribuciones(respuestas: list, encuesta: dict) -> list:
    """Conteos del 1 al 5 por pregunta escala_1_5 de todas las preguntas. Solo si n ≥ UMBRAL_MINIMO."""
    distribuciones = []
    for pregunta in _escalas(encuesta):
        valores = [r["valores"][pregunta["id"]] for r in respuestas
                   if isinstance(r.get("valores", {}).get(pregunta["id"]), int)
                   and 1 <= r["valores"][pregunta["id"]] <= 5]
        if len(valores) < UMBRAL_MINIMO:
            continue
        conteos = [valores.count(i) for i in range(1, 6)]
        distribuciones.append({"pregunta": pregunta["id"], "texto": pregunta.get("texto", ""),
                               "dimension": pregunta.get("dimension", ""), "conteos": conteos,
                               "n": len(valores), "media": round(sum(valores) / len(valores), 2)})
    return distribuciones


# ---------- alertas ----------

def calcular_alertas(participacion: list, medias_actual: list, medias_anterior: list,
                     encuesta: dict | None = None, idioma: str = "es") -> list:
    """Alertas con campos estructurados (tipo, colectivo, turno, pregunta, tasa, antes, despues)
    y el mensaje ya escrito en `idioma`."""
    textos_pregunta = {p["id"]: p.get("texto", p["id"]) for p, _ in _todas_las_preguntas(encuesta or {})}
    alertas = []
    for fila in participacion:
        if not fila["representativo"]:
            alertas.append({
                "tipo": "representatividad", "colectivo": fila["colectivo"], "turno": fila["turno"],
                "tasa": fila["tasa"],
                "mensaje": textos.frase("alerta.representatividad", idioma,
                                        segmento=textos.segmento(fila["colectivo"], fila["turno"], idioma),
                                        pct=round(fila["tasa"] * 100), n=fila["respuestas"],
                                        personas=fila["personas"])})
    anteriores = {(m["pregunta"], m["colectivo"]): m["media"] for m in medias_anterior}
    for m in medias_actual:
        antes = anteriores.get((m["pregunta"], m["colectivo"]))
        if antes is not None and antes - m["media"] >= UMBRAL_CAIDA:
            alertas.append({
                "tipo": "caida", "colectivo": m["colectivo"], "pregunta": m["pregunta"],
                "antes": antes, "despues": m["media"],
                "mensaje": textos.frase("alerta.caida", idioma,
                                        pregunta=textos_pregunta.get(m["pregunta"], m["pregunta"]),
                                        antes=textos.numero(antes, idioma), despues=textos.numero(m["media"], idioma),
                                        colectivo=textos.nombre("colectivo", m["colectivo"], idioma).lower())})
    return alertas


# ---------- zonas (maqueta 3D) ----------

def calcular_zonas(actual: list, anterior: list, participacion: list, encuesta: dict,
                   alertas: list, temas_por_respuesta: dict) -> list:
    """Una zona por colectivo de la encuesta. temas_por_respuesta = {id de respuesta: tema}."""
    zonas = []
    for colectivo in _colectivos(encuesta):
        de_c = [r for r in actual if r.get("colectivo") == colectivo]
        de_c_antes = [r for r in anterior if r.get("colectivo") == colectivo]
        filas = [f for f in participacion if f["colectivo"] == colectivo]
        if not filas:  # sin plantilla: filas a partir de los turnos con respuestas
            turnos = sorted({r.get("turno") for r in de_c}) or ["sin_turno"]
            filas = [{"colectivo": colectivo, "turno": t, "respuestas": sum(1 for r in de_c if r.get("turno") == t),
                      "personas": 0, "tasa": 0.0, "representativo": False} for t in turnos]
        personas = sum(f["personas"] for f in filas)
        tasa = round(len(de_c) / personas, 3) if personas else 0.0
        media = _media_escalas(de_c, encuesta)
        media_anterior = _media_escalas(de_c_antes, encuesta)

        temas = []
        if len(de_c) >= UMBRAL_MINIMO:
            cuenta = Counter(temas_por_respuesta.get(r.get("id")) for r in de_c if r.get("comentario"))
            temas = [{"tema": t, "n": n} for t, n in cuenta.most_common()
                     if t not in TEMAS_SIN_ZONA and n >= UMBRAL_MINIMO][:3]

        zonas.append({
            "colectivo": colectivo, "respuestas": len(de_c), "personas": personas, "tasa": tasa,
            "representativo": len(de_c) >= UMBRAL_MINIMO and tasa >= TASA_REPRESENTATIVA
                              and all(f["representativo"] for f in filas),
            "media": media, "media_anterior": media_anterior,
            "variacion": round(media - media_anterior, 2) if media is not None and media_anterior is not None else None,
            "temas": temas,
            "alertas": [a["mensaje"] for a in alertas if a.get("colectivo") == colectivo],
            "turnos": [dict(f, media=_media_escalas([r for r in de_c if r.get("turno") == f["turno"]], encuesta))
                       for f in filas],
        })
    return zonas


# ---------- todo junto ----------

def calcular_metricas(respuestas: list, plantilla: list, encuesta: dict, idioma: str = "es") -> dict:
    """`encuesta` puede venir ya con los textos traducidos (los ids no cambian)."""
    actual, anterior, p_actual, p_anterior = separar_periodos(respuestas)
    colectivos = _colectivos(encuesta)
    participacion = calcular_participacion(actual, plantilla, colectivos)
    medias = calcular_medias(actual, encuesta)
    medias_anterior = calcular_medias(anterior, encuesta)
    personas = sum(f["personas"] for f in participacion)
    en_plantilla = sum(f["respuestas"] for f in participacion)

    limites = []
    for fila in participacion:
        if fila["respuestas"] < UMBRAL_MINIMO:
            limites.append(textos.frase("limite.muestra", idioma, n=fila["respuestas"],
                                        segmento=textos.segmento(fila["colectivo"], fila["turno"], idioma)))
    if not plantilla:
        limites.append(textos.frase("limite.sin_plantilla", idioma))
    if any(r.get("tema_real") for r in actual):
        limites.append(textos.frase("limite.simuladas", idioma))
    limites.append(textos.frase("limite.umbral", idioma, umbral=UMBRAL_MINIMO))
    limites.append(textos.frase("limite.correlacion", idioma))

    return {
        "n_respuestas": len(actual), "periodo_actual": p_actual, "periodo_anterior": p_anterior,
        "participacion": participacion, "medias": medias,
        "alertas": calcular_alertas(participacion, medias, medias_anterior, encuesta, idioma),
        "limites": limites,
        "n_anterior": len(anterior),
        "n_simuladas": sum(1 for r in actual if r.get("tema_real")),
        "colectivos": colectivos,
        "participacion_global": round(en_plantilla / personas, 3) if personas else 0.0,
        "medias_anterior": medias_anterior,
        "preguntas": [{"id": p["id"], "texto": p.get("texto", ""), "tipo": p.get("tipo", ""),
                       "dimension": p.get("dimension", ""), "ambito": ambito}
                      for p, ambito in _todas_las_preguntas(encuesta)],
        "distribuciones": calcular_distribuciones(actual, encuesta),
    }
