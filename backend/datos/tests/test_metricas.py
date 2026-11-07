from backend.datos import metricas

ENCUESTA = {"colectivo": "planta", "preguntas": [{"id": "p1", "tipo": "escala_1_5"}, {"id": "p2", "tipo": "texto"}]}
PLANTILLA = [{"colectivo": "planta", "turno": "manana", "personas": 20},
             {"colectivo": "planta", "turno": "noche", "personas": 100},
             {"colectivo": "oficina", "turno": "sin_turno", "personas": 10}]


def r(turno, p1, periodo="2026-10", colectivo="planta"):
    return {"colectivo": colectivo, "turno": turno, "periodo": periodo, "valores": {"p1": p1}}


def test_separar_periodos():
    act, ant, pa, pant = metricas.separar_periodos([r("noche", 3, "2026-09"), r("noche", 3, "2026-10")])
    assert (len(act), len(ant), pa, pant) == (1, 1, "2026-10", "2026-09")
    assert metricas.separar_periodos([]) == ([], [], None, None)


def test_participacion_y_alerta_turno_noche():
    resp = [r("manana", 4)] * 10 + [r("noche", 2)] * 3
    part = metricas.calcular_participacion(resp, PLANTILLA, "planta")
    assert [(f["turno"], f["respuestas"], f["representativo"]) for f in part] == [("manana", 10, True), ("noche", 3, False)]
    alertas = metricas.calcular_alertas(part, [], [])
    assert alertas[0]["tipo"] == "representatividad" and "noche" in alertas[0]["mensaje"]


def test_medias_ocultan_segmentos_pequenos():
    resp = [r("manana", 4)] * 5 + [r("sin_turno", 1, colectivo="oficina")] * 4
    medias = metricas.calcular_medias(resp, ENCUESTA)
    assert medias == [{"pregunta": "p1", "colectivo": "planta", "media": 4.0, "n": 5}]


def test_alerta_caida():
    alertas = metricas.calcular_alertas([], [{"pregunta": "p1", "colectivo": "planta", "media": 2.9}],
                                        [{"pregunta": "p1", "colectivo": "planta", "media": 3.8}])
    assert alertas[0]["tipo"] == "caida"


def test_calcular_metricas_completo():
    resp = [r("manana", 4, "2026-09")] * 6 + [r("manana", 2, "2026-10")] * 6
    m = metricas.calcular_metricas(resp, PLANTILLA, ENCUESTA)
    assert m["n_respuestas"] == 6 and m["periodo_anterior"] == "2026-09"
    assert {a["tipo"] for a in m["alertas"]} == {"representatividad", "caida"}
    assert any("correlación" in x for x in m["limites"])
