"""Métricas agregadas · UPC 2 (ver modulos.md, sección 2).

Todo lo que sale de aquí es agregado. Ningún segmento con menos de
UMBRAL_MINIMO respuestas muestra medias.
"""
UMBRAL_MINIMO = 5
TASA_REPRESENTATIVA = 0.20
UMBRAL_CAIDA = 0.5

NOMBRE_COLECTIVO = {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                    "oficina": "oficina", "manager": "managers"}
NOMBRE_TURNO = {"manana": "mañana", "tarde": "tarde", "noche": "noche"}


def _segmento(colectivo: str, turno: str) -> str:
    nombre = NOMBRE_COLECTIVO.get(colectivo, colectivo)
    if turno in NOMBRE_TURNO:
        return f"el turno de {NOMBRE_TURNO[turno]} de {nombre}"
    return nombre[0].upper() + nombre[1:]


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


def calcular_participacion(respuestas: list, plantilla: list, colectivo: str) -> list:
    """Una fila por fila de la plantilla del colectivo (todas si colectivo == "todos")."""
    filas = []
    for fila in plantilla:
        if colectivo != "todos" and fila["colectivo"] != colectivo:
            continue
        n = sum(1 for r in respuestas if r.get("colectivo") == fila["colectivo"] and r.get("turno") == fila["turno"])
        personas = fila.get("personas", 0)
        tasa = round(n / personas, 3) if personas else 0.0
        filas.append({"colectivo": fila["colectivo"], "turno": fila["turno"], "respuestas": n,
                      "personas": personas, "tasa": tasa,
                      "representativo": n >= UMBRAL_MINIMO and tasa >= TASA_REPRESENTATIVA})
    return filas


def calcular_medias(respuestas: list, encuesta: dict) -> list:
    """Media por pregunta escala_1_5 y colectivo. Omite segmentos con n < UMBRAL_MINIMO."""
    medias = []
    escalas = [p["id"] for p in encuesta.get("preguntas", []) if p.get("tipo") == "escala_1_5"]
    colectivos = sorted({r.get("colectivo") for r in respuestas if r.get("colectivo")})
    for pregunta in escalas:
        for colectivo in colectivos:
            valores = [r["valores"][pregunta] for r in respuestas
                       if r.get("colectivo") == colectivo and isinstance(r.get("valores", {}).get(pregunta), (int, float))]
            if len(valores) >= UMBRAL_MINIMO:
                medias.append({"pregunta": pregunta, "colectivo": colectivo,
                               "media": round(sum(valores) / len(valores), 1), "n": len(valores)})
    return medias


def calcular_alertas(participacion: list, medias_actual: list, medias_anterior: list) -> list:
    alertas = []
    for fila in participacion:
        if not fila["representativo"]:
            pct = round(fila["tasa"] * 100)
            texto = _segmento(fila['colectivo'], fila['turno'])
            alertas.append({"tipo": "representatividad",
                            "mensaje": f"{texto[0].upper()}{texto[1:]} solo ha respondido "
                                       f"un {pct} % ({fila['respuestas']} de {fila['personas']}): "
                                       f"los resultados pueden no representarle."})
    anteriores = {(m["pregunta"], m["colectivo"]): m["media"] for m in medias_anterior}
    for m in medias_actual:
        antes = anteriores.get((m["pregunta"], m["colectivo"]))
        if antes is not None and antes - m["media"] >= UMBRAL_CAIDA:
            alertas.append({"tipo": "caida",
                            "mensaje": f"La pregunta {m['pregunta']} baja de {antes} a {m['media']} en "
                                       f"{NOMBRE_COLECTIVO.get(m['colectivo'], m['colectivo'])} respecto al periodo anterior."})
    return alertas


def calcular_metricas(respuestas: list, plantilla: list, encuesta: dict) -> dict:
    actual, anterior, p_actual, p_anterior = separar_periodos(respuestas)
    participacion = calcular_participacion(actual, plantilla, encuesta.get("colectivo", "todos"))
    medias = calcular_medias(actual, encuesta)
    medias_anterior = calcular_medias(anterior, encuesta)

    limites = []
    for fila in participacion:
        if fila["respuestas"] < UMBRAL_MINIMO:
            limites.append(f"Muestra pequeña en {_segmento(fila['colectivo'], fila['turno'])} "
                           f"(n={fila['respuestas']}): no se muestran sus medias ni temas.")
    if not plantilla:
        limites.append("Sin plantilla de personas: no se puede calcular la representatividad.")
    limites.append(f"Segmentos con menos de {UMBRAL_MINIMO} respuestas ocultos.")
    limites.append("Una correlación no demuestra una causa.")

    return {"n_respuestas": len(actual), "periodo_actual": p_actual, "periodo_anterior": p_anterior,
            "participacion": participacion, "medias": medias,
            "alertas": calcular_alertas(participacion, medias, medias_anterior), "limites": limites}
