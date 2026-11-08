"""Métricas agregadas · UPC 2 (modulos.md sección 2 y v2.md secciones 1.3 y 3.4).

Todo lo que sale de aquí es agregado. Ningún segmento con menos de
UMBRAL_MINIMO respuestas muestra medias, distribuciones ni temas.

Supresión complementaria (v6 §4.1): ocultar un grupo pequeño no basta si se puede deducir
RESTANDO. Por eso:
- si un turno tiene entre 1 y UMBRAL_MINIMO-1 respuestas, se ocultan las medias de TODOS los
  turnos de ese colectivo (la media del colectivo, si tiene n ≥ UMBRAL_MINIMO, se queda);
- las cifras globales (distribuciones, valoración) solo usan los colectivos que ya publican su
  propia media (n ≥ UMBRAL_MINIMO en esa pregunta), así que ningún grupo pequeño entra en ellas.
Los recuentos de participación siguen visibles: hacen falta para saber quién falta.
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
    """Conteos del 1 al 5 por pregunta escala_1_5 de todas las preguntas.

    Solo entran las respuestas de colectivos con n ≥ UMBRAL_MINIMO en esa pregunta (los mismos
    que publican su media en calcular_medias): así no se puede restar la distribución global
    y las medias por colectivo para deducir un grupo pequeño."""
    distribuciones = []
    for pregunta in _escalas(encuesta):
        por_colectivo: dict = {}
        for r in respuestas:
            v = r.get("valores", {}).get(pregunta["id"])
            if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5:
                por_colectivo.setdefault(r.get("colectivo"), []).append(v)
        valores = [v for lista in por_colectivo.values() if len(lista) >= UMBRAL_MINIMO for v in lista]
        if len(valores) < UMBRAL_MINIMO:
            continue
        conteos = [valores.count(i) for i in range(1, 6)]
        distribuciones.append({"pregunta": pregunta["id"], "texto": pregunta.get("texto", ""),
                               "dimension": pregunta.get("dimension", ""), "conteos": conteos,
                               "n": len(valores), "media": round(sum(valores) / len(valores), 2)})
    return distribuciones


def respuestas_excluidas(respuestas: list) -> int:
    """Respuestas de colectivos con menos de UMBRAL_MINIMO: no entran en las cifras globales."""
    por_colectivo = Counter(r.get("colectivo") for r in respuestas)
    return sum(n for n in por_colectivo.values() if n < UMBRAL_MINIMO)


def calcular_participacion_canal(respuestas: list) -> list:
    """Recuento simple por canal (sin cruzar con colectivo ni turno)."""
    cuenta = Counter(r.get("canal") for r in respuestas)
    canales = ["qr", "quiosco", "teams"] + sorted(c for c in cuenta if c not in ("qr", "quiosco", "teams") and c)
    return [{"canal": c, "respuestas": cuenta.get(c, 0)} for c in canales]


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
        # Supresión complementaria: con un turno pequeño (1 a UMBRAL-1) no se publica la media de ningún
        # turno del colectivo, porque restándola de la del colectivo se deduciría la del pequeño.
        por_turno = Counter(r.get("turno") for r in de_c)
        turnos_ocultos = any(0 < n < UMBRAL_MINIMO for n in por_turno.values()) or \
            any(0 < f["respuestas"] < UMBRAL_MINIMO for f in filas)

        temas = []
        if len(de_c) >= UMBRAL_MINIMO:
            cuenta = Counter(temas_por_respuesta.get(r.get("id")) for r in de_c if r.get("comentario"))
            temas = [{"tema": t, "n": n} for t, n in cuenta.most_common()
                     if t not in TEMAS_SIN_ZONA and n >= UMBRAL_MINIMO][:3]

        zonas.append({
            "colectivo": colectivo, "respuestas": len(de_c), "personas": personas, "tasa": tasa,
            "comentarios": sum(1 for r in de_c if r.get("comentario")),
            "representativo": len(de_c) >= UMBRAL_MINIMO and tasa >= TASA_REPRESENTATIVA
                              and all(f["representativo"] for f in filas),
            "media": media, "media_anterior": media_anterior,
            "variacion": round(media - media_anterior, 2) if media is not None and media_anterior is not None else None,
            "temas": temas,
            "alertas": [a["mensaje"] for a in alertas if a.get("colectivo") == colectivo],
            "turnos_ocultos": turnos_ocultos,
            "turnos": [dict(f, media=None if turnos_ocultos else
                            _media_escalas([r for r in de_c if r.get("turno") == f["turno"]], encuesta))
                       for f in filas],
        })
    return zonas


# ---------- valoración global: bruta y corregida por plantilla ----------

SESGO_MINIMO = 0.1


def calcular_valoracion(zonas: list, idioma: str = "es") -> tuple[dict, str | None]:
    """(valoracion, limite). Solo cuentan las zonas que publican su media (n ≥ UMBRAL_MINIMO).

    - bruta: media de las zonas ponderada por respuestas (quien más responde, más pesa).
    - corregida: media de las zonas ponderada por personas de la plantilla.
    - diferencia: corregida - bruta. Si |diferencia| ≥ SESGO_MINIMO se añade un límite que lo explica."""
    con_media = [z for z in zonas if z.get("media") is not None]
    vacia = {"bruta": None, "corregida": None, "diferencia": None}
    if not con_media:
        return vacia, None
    peso_resp = sum(z["respuestas"] for z in con_media)
    bruta = sum(z["media"] * z["respuestas"] for z in con_media) / peso_resp if peso_resp else None
    con_personas = [z for z in con_media if z.get("personas")]
    peso_pers = sum(z["personas"] for z in con_personas)
    corregida = sum(z["media"] * z["personas"] for z in con_personas) / peso_pers if peso_pers else None
    if bruta is None or corregida is None:
        return dict(vacia, bruta=round(bruta, 2) if bruta is not None else None), None
    diferencia = round(corregida - bruta, 2)
    valoracion = {"bruta": round(bruta, 2), "corregida": round(corregida, 2), "diferencia": diferencia}
    limite = None
    if abs(diferencia) >= SESGO_MINIMO:
        sentido = textos.frase("sesgo.arriba" if diferencia > 0 else "sesgo.abajo", idioma).lower()
        limite = textos.frase("limite.sesgo", idioma, x=textos.numero(abs(diferencia), idioma), sentido=sentido)
    return valoracion, limite


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
    excluidas = respuestas_excluidas(actual)
    if excluidas:
        limites.append(textos.frase("limite.excluidas", idioma, n=excluidas, umbral=UMBRAL_MINIMO))
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
        "por_canal": calcular_participacion_canal(actual),
    }
