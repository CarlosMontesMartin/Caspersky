from backend.datos import metricas

ENCUESTA = {"colectivo": "planta", "preguntas": [{"id": "p1", "tipo": "escala_1_5", "texto": "¿Qué tal los turnos?"},
                                                 {"id": "p2", "tipo": "texto"}]}
MULTI = {"colectivo": "varios", "colectivos": ["planta", "logistica"],
         "preguntas": [{"id": "c1", "tipo": "escala_1_5", "texto": "¿Qué tal?", "dimension": "condiciones"}],
         "preguntas_por_colectivo": {
             "planta": [{"id": "planta_p1", "tipo": "si_no", "texto": "¿Pausa?", "dimension": "bienestar"}],
             "logistica": [{"id": "logistica_p1", "tipo": "escala_1_5", "texto": "¿Rutas?", "dimension": "condiciones"}]}}
PLANTILLA = [{"colectivo": "planta", "turno": "manana", "personas": 20},
             {"colectivo": "planta", "turno": "noche", "personas": 100},
             {"colectivo": "logistica", "turno": "sin_turno", "personas": 30},
             {"colectivo": "oficina", "turno": "sin_turno", "personas": 10}]


def r(turno, p1, periodo="2026-10", colectivo="planta", id_=None, comentario=""):
    clave = "c1" if colectivo in ("planta", "logistica") else "p1"
    return {"id": id_, "colectivo": colectivo, "turno": turno, "periodo": periodo,
            "valores": {"p1": p1, clave: p1}, "comentario": comentario}


def test_separar_periodos():
    act, ant, pa, pant = metricas.separar_periodos([r("noche", 3, "2026-09"), r("noche", 3, "2026-10")])
    assert (len(act), len(ant), pa, pant) == (1, 1, "2026-10", "2026-09")
    assert metricas.separar_periodos([]) == ([], [], None, None)


def test_participacion_con_lista_de_colectivos():
    resp = [r("manana", 4)] * 10 + [r("sin_turno", 3, colectivo="logistica")] * 2
    part = metricas.calcular_participacion(resp, PLANTILLA, ["logistica", "planta"])
    assert [(f["colectivo"], f["turno"]) for f in part] == [("planta", "manana"), ("planta", "noche"),
                                                            ("logistica", "sin_turno")]
    assert metricas.calcular_participacion(resp, PLANTILLA, "planta")[0]["representativo"] is True


def test_alerta_representatividad_con_colectivo_y_turno():
    part = metricas.calcular_participacion([r("noche", 2)] * 3, PLANTILLA, ["planta"])
    alerta = next(a for a in metricas.calcular_alertas(part, [], []) if a.get("turno") == "noche")
    assert alerta["colectivo"] == "planta" and "noche" in alerta["mensaje"]


def test_alerta_caida_usa_texto_de_la_pregunta():
    alertas = metricas.calcular_alertas([], [{"pregunta": "p1", "colectivo": "planta", "media": 2.9}],
                                        [{"pregunta": "p1", "colectivo": "planta", "media": 3.8}], ENCUESTA)
    assert alertas[0]["tipo"] == "caida" and alertas[0]["pregunta"] == "p1"
    assert "«¿Qué tal los turnos?»" in alertas[0]["mensaje"] and "3,8" in alertas[0]["mensaje"]


def test_medias_ocultan_segmentos_pequenos():
    resp = [r("manana", 4)] * 5 + [r("sin_turno", 1, colectivo="oficina")] * 4
    assert metricas.calcular_medias(resp, ENCUESTA) == [{"pregunta": "p1", "colectivo": "planta", "media": 4.0, "n": 5}]


def test_distribuciones_solo_con_n_suficiente():
    resp = [r("manana", v, colectivo="planta") for v in (1, 2, 2, 5, 5)]
    d = metricas.calcular_distribuciones(resp, MULTI)
    assert d == [{"pregunta": "c1", "texto": "¿Qué tal?", "dimension": "condiciones",
                  "conteos": [1, 2, 0, 0, 2], "n": 5, "media": 3.0}]
    assert metricas.calcular_distribuciones(resp[:4], MULTI) == []


def test_zonas_con_menos_de_5_ocultan_media_y_temas():
    actual = [r("manana", 2, colectivo="planta", id_=f"a{i}", comentario="x") for i in range(6)]
    actual += [r("sin_turno", 4, colectivo="logistica", id_=f"b{i}", comentario="x") for i in range(3)]
    temas = {f"a{i}": "descansos" for i in range(6)} | {f"b{i}": "herramientas" for i in range(3)}
    part = metricas.calcular_participacion(actual, PLANTILLA, MULTI["colectivos"])
    alertas = metricas.calcular_alertas(part, [], [], MULTI)
    zonas = {z["colectivo"]: z for z in metricas.calcular_zonas(actual, [], part, MULTI, alertas, temas)}
    assert list(zonas) == ["planta", "logistica"]
    assert zonas["planta"]["media"] == 2.0 and zonas["planta"]["temas"] == [{"tema": "descansos", "n": 6}]
    assert zonas["logistica"]["media"] is None and zonas["logistica"]["temas"] == []
    assert zonas["planta"]["representativo"] is False  # el turno de noche no llega
    assert any("noche" in a for a in zonas["planta"]["alertas"])
    noche = next(t for t in zonas["planta"]["turnos"] if t["turno"] == "noche")
    assert noche["media"] is None


def test_calcular_metricas_campos_ampliados():
    resp = [r("manana", 4, "2026-09")] * 6 + [dict(r("manana", 2, "2026-10"), tema_real="turnos")] * 6
    m = metricas.calcular_metricas(resp, PLANTILLA, ENCUESTA)
    assert m["n_respuestas"] == 6 and m["n_anterior"] == 6 and m["n_simuladas"] == 6
    assert m["colectivos"] == ["planta"] and m["participacion_global"] == round(6 / 120, 3)
    assert m["medias_anterior"][0]["media"] == 4.0
    assert m["preguntas"][0]["ambito"] == "comun"
    assert {a["tipo"] for a in m["alertas"]} == {"representatividad", "caida"}


def test_alertas_y_limites_en_catalan_e_ingles():
    resp = [r("manana", 4, "2026-09")] * 6 + [r("manana", 2, "2026-10")] * 6 + [r("noche", 2, "2026-10")] * 2
    ca = metricas.calcular_metricas(resp, PLANTILLA, ENCUESTA, "ca")
    en = metricas.calcular_metricas(resp, PLANTILLA, ENCUESTA, "en")
    representatividad = next(a for a in ca["alertas"] if a["tipo"] == "representatividad" and a["turno"] == "noche")
    assert "ha respost" in representatividad["mensaje"] and representatividad["tasa"] == 0.02
    caida = next(a for a in en["alertas"] if a["tipo"] == "caida")
    assert "drops from 4.0 to 2.0" in caida["mensaje"] and caida["antes"] == 4.0 and caida["despues"] == 2.0
    assert any("correlació" in x for x in ca["limites"]) and any("causation" in x for x in en["limites"])


def test_idioma_desconocido_en_castellano():
    m = metricas.calcular_metricas([r("manana", 4)] * 6, PLANTILLA, ENCUESTA, "pt")
    assert any("correlación" in x for x in m["limites"])


# ---------- supresión complementaria (no se puede deducir restando) ----------

def _zonas(actual, encuesta=ENCUESTA, anterior=()):
    colectivos = metricas._colectivos(encuesta)
    part = metricas.calcular_participacion(actual, PLANTILLA, colectivos)
    return metricas.calcular_zonas(actual, list(anterior), part, encuesta, [], {})


def test_turno_pequeno_oculta_las_medias_de_todos_los_turnos():
    """5 de noche y 1 de mañana: la media de planta (n=6) se ve, pero la de noche NO, porque
    restándola de la de planta se deduciría la de la persona de mañana."""
    actual = [r("noche", 2, id_=f"n{i}") for i in range(5)] + [r("manana", 5, id_="m0")]
    z = _zonas(actual)[0]
    assert z["media"] == 2.5 and z["turnos_ocultos"] is True
    assert all(t["media"] is None for t in z["turnos"])
    assert {t["turno"]: t["respuestas"] for t in z["turnos"]} == {"manana": 1, "noche": 5}  # recuentos visibles


def test_turnos_todos_grandes_si_publican_su_media():
    actual = [r("noche", 2) for _ in range(5)] + [r("manana", 4) for _ in range(5)]
    z = _zonas(actual)[0]
    assert z["turnos_ocultos"] is False
    assert {t["turno"]: t["media"] for t in z["turnos"]} == {"manana": 4.0, "noche": 2.0}


def test_turno_sin_respuestas_no_oculta_a_los_demas():
    z = _zonas([r("manana", 4) for _ in range(6)])[0]
    assert z["turnos_ocultos"] is False
    assert next(t for t in z["turnos"] if t["turno"] == "manana")["media"] == 4.0


def test_turno_pequeno_sin_fila_en_la_plantilla_tambien_cuenta():
    """Respuestas de un turno que la plantilla no tiene: igualmente se deduciría restando."""
    plantilla = [f for f in PLANTILLA if f["turno"] != "noche"]
    actual = [r("manana", 4) for _ in range(6)] + [r("noche", 1) for _ in range(3)]
    part = metricas.calcular_participacion(actual, plantilla, ["planta"])
    z = metricas.calcular_zonas(actual, [], part, ENCUESTA, [], {})[0]
    assert z["turnos_ocultos"] is True and all(t["media"] is None for t in z["turnos"])


def test_distribuciones_excluyen_colectivos_con_menos_de_5():
    resp = [r("manana", v, colectivo="planta") for v in (1, 2, 2, 5, 5, 5)] + \
           [r("sin_turno", 1, colectivo="logistica") for _ in range(2)]
    d = metricas.calcular_distribuciones(resp, MULTI)
    assert d[0]["n"] == 6 and d[0]["conteos"] == [1, 2, 0, 0, 3]  # logística (n=2) no entra
    assert metricas.respuestas_excluidas(resp) == 2
    m = metricas.calcular_metricas(resp, PLANTILLA, MULTI, "es")
    assert any("Se excluyen 2 respuestas" in x for x in m["limites"])
    assert all(x["n"] == 6 for x in m["distribuciones"])


def test_sin_grupos_pequenos_no_hay_limite_de_exclusion():
    resp = [r("manana", 3, colectivo="planta") for _ in range(6)]
    m = metricas.calcular_metricas(resp, PLANTILLA, MULTI, "es")
    assert not any("excluyen" in x for x in m["limites"])


def test_invariantes_con_datos_aleatorios():
    """Para cualquier reparto: (1) con un turno de 1–4 no se publica ninguna media de turno de ese
    colectivo; (2) la distribución global usa exactamente las respuestas de los colectivos que
    publican su media (n global == suma de n publicados), así que no hay nada que restar."""
    import random
    azar = random.Random(11)
    for _ in range(300):
        resp = []
        for colectivo, turnos in (("planta", ["manana", "tarde", "noche"]), ("logistica", ["sin_turno"])):
            for turno in turnos:
                resp += [r(turno, azar.randint(1, 5), colectivo=colectivo)
                         for _ in range(azar.choice([0, 1, 2, 4, 5, 6, 9]))]
        if not resp:
            continue
        part = metricas.calcular_participacion(resp, PLANTILLA, MULTI["colectivos"])
        for z in metricas.calcular_zonas(resp, [], part, MULTI, [], {}):
            pequeno = any(0 < t["respuestas"] < 5 for t in z["turnos"])
            if pequeno:
                assert z["turnos_ocultos"] and all(t["media"] is None for t in z["turnos"])
            if z["respuestas"] < 5:
                assert z["media"] is None
        medias = metricas.calcular_medias(resp, MULTI)
        for dist in metricas.calcular_distribuciones(resp, MULTI):
            publicados = sum(m["n"] for m in medias if m["pregunta"] == dist["pregunta"])
            assert dist["n"] == publicados


def test_valoracion_corregida_por_plantilla():
    """Oficina responde mucho y valora alto; planta responde poco y valora bajo."""
    zonas = [{"colectivo": "planta", "respuestas": 6, "personas": 400, "media": 2.0},
             {"colectivo": "oficina", "respuestas": 60, "personas": 100, "media": 4.0},
             {"colectivo": "manager", "respuestas": 3, "personas": 40, "media": None}]
    v, limite = metricas.calcular_valoracion(zonas, "es")
    assert v["bruta"] == 3.82 and v["corregida"] == 2.4 and v["diferencia"] == -1.42
    assert limite and "1,4 puntos por debajo" in limite
    invertidas = [dict(zonas[0], media=4.0, personas=100), dict(zonas[1], media=2.0, personas=400)]
    v2, limite_en = metricas.calcular_valoracion(invertidas, "en")
    assert v2["diferencia"] == 0.22 and "0.2 points above" in limite_en


def test_valoracion_sin_zonas_con_media():
    assert metricas.calcular_valoracion([{"colectivo": "planta", "respuestas": 3, "personas": 10, "media": None}])[0] == \
        {"bruta": None, "corregida": None, "diferencia": None}


def test_valoracion_sin_sesgo_no_da_limite():
    zonas = [{"colectivo": "planta", "respuestas": 10, "personas": 100, "media": 3.0},
             {"colectivo": "oficina", "respuestas": 10, "personas": 100, "media": 3.0}]
    v, limite = metricas.calcular_valoracion(zonas, "es")
    assert v["diferencia"] == 0.0 and limite is None


def test_por_canal_cuenta_sin_cruzar():
    resp = [dict(r("manana", 3), canal="qr")] * 3 + [dict(r("manana", 3), canal="teams")] * 2
    assert metricas.calcular_participacion_canal(resp) == [
        {"canal": "qr", "respuestas": 3}, {"canal": "quiosco", "respuestas": 0}, {"canal": "teams", "respuestas": 2}]
