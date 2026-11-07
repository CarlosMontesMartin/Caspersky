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


def test_calcular_metricas_campos_v2():
    resp = [r("manana", 4, "2026-09")] * 6 + [dict(r("manana", 2, "2026-10"), tema_real="turnos")] * 6
    m = metricas.calcular_metricas(resp, PLANTILLA, ENCUESTA)
    assert m["n_respuestas"] == 6 and m["n_anterior"] == 6 and m["n_simuladas"] == 6
    assert m["colectivos"] == ["planta"] and m["participacion_global"] == round(6 / 120, 3)
    assert m["medias_anterior"][0]["media"] == 4.0
    assert m["preguntas"][0]["ambito"] == "comun"
    assert {a["tipo"] for a in m["alertas"]} == {"representatividad", "caida"}
