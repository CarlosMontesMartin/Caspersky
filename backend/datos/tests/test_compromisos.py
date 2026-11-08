"""Lógica de compromisos (backend/datos/compromisos.py): fechas, comillas, copias literales, después."""
from datetime import date

import pytest

from backend.datos import almacen, compromisos as comp


@pytest.fixture(autouse=True)
def almacen_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "BASE", tmp_path / "almacen")
    monkeypatch.setattr(almacen, "CONTENIDO", tmp_path / "contenido")
    return tmp_path


HOY = date(2026, 11, 8)


def test_fecha_desde_plazo():
    assert comp.fecha_desde_plazo("2 semanas", HOY) == date(2026, 11, 22)
    assert comp.fecha_desde_plazo("1 semana", HOY) == date(2026, 11, 15)
    assert comp.fecha_desde_plazo("1 mes", HOY) == date(2026, 12, 8)
    assert comp.fecha_desde_plazo("10 días", HOY) == date(2026, 11, 18)
    assert comp.fecha_desde_plazo("3 setmanes", HOY) == date(2026, 11, 29)
    assert comp.fecha_desde_plazo("2 weeks", HOY) == date(2026, 11, 22)
    assert comp.fecha_desde_plazo("una semana", HOY) == date(2026, 11, 15)
    assert comp.fecha_desde_plazo("Antes del próximo pulso", HOY) == date(2026, 11, 22)
    assert comp.fecha_desde_plazo(None, HOY) == date(2026, 11, 22)


def test_formatear_fecha():
    assert comp.formatear_fecha(date(2026, 11, 5), "es") == "05/11/2026"
    assert comp.formatear_fecha(date(2026, 11, 5), "en") == "5 Nov 2026"


def test_comillas_y_apostrofos():
    assert comp.tiene_comillas('dicen "no hay tiempo"') and comp.tiene_comillas("« cita »")
    assert not comp.tiene_comillas("l'acció d'avui don't")  # el apóstrofo es normal en catalán e inglés
    assert comp.sin_comillas('«hola» "mundo"') == "hola mundo"


def test_copia_literal_detecta_7_palabras_seguidas():
    comentarios = ["el descanso de la noche es muy corto y nadie nos lo explico"]
    assert comp.copia_literal("Dijisteis: el descanso de la noche es muy corto", comentarios)
    assert comp.copia_literal("EL DESCANSO de la NOCHE es muy corto!", comentarios)       # mayúsculas y signos
    assert not comp.copia_literal("Tres de cada diez comentarios hablan de descansos", comentarios)
    assert not comp.copia_literal("el descanso de la noche", comentarios)                    # 5 palabras: no es copia
    assert not comp.copia_literal("", comentarios) and not comp.copia_literal("hola", [])


ANALISIS = {"periodo_actual": "2026-10",
            "preguntas": [{"id": "p1", "texto": "¿Cómo estás?", "dimension": "bienestar"},
                          {"id": "p2", "texto": "¿Te da tiempo a la pausa?", "dimension": "condiciones"}],
            "medias": [{"pregunta": "p1", "colectivo": "planta", "media": 3.1, "n": 40},
                       {"pregunta": "p2", "colectivo": "planta", "media": 2.4, "n": 90},
                       {"pregunta": "p2", "colectivo": "oficina", "media": 1.5, "n": 30},
                       {"pregunta": "p2", "colectivo": "logistica", "media": 1.0, "n": 4}]}


def test_indicador_por_defecto_elige_la_media_mas_baja_con_n_suficiente():
    ind = comp.indicador_por_defecto(ANALISIS, ["planta", "logistica"])
    assert (ind["pregunta_origen"], ind["colectivo"], ind["antes"], ind["n_antes"]) == ("p2", "planta", 2.4, 90)
    assert ind["texto"] == "¿Te da tiempo a la pausa?" and ind["periodo_antes"] == "2026-10"
    # logística (media 1,0) tiene n=4: no cuenta
    assert comp.indicador_por_defecto(ANALISIS, ["logistica"])["antes"] is None


def test_recalcular_antes_no_se_fia_del_cliente():
    falso = {"pregunta_origen": "p2", "colectivo": "planta", "antes": 1.0, "n_antes": 99}
    assert comp.recalcular_antes(falso, ANALISIS)["antes"] == 2.4
    pequeno = {"pregunta_origen": "p2", "colectivo": "logistica", "antes": 1.0, "n_antes": 4}
    assert comp.recalcular_antes(pequeno, ANALISIS)["antes"] is None  # n < 5: no existe


def _compromiso(**extra):
    base = {"encuesta_id": "enc_000", "tema": "descansos", "colectivos": ["planta"], "dijisteis": "d", "hicimos": "h",
            "responsable": "r", "fecha": "2026-11-10", "estado": "comprometido", "idioma_original": "es",
            "traducciones": {"ca": {"dijisteis": "dc", "hicimos": "hc"}},
            "indicador": {"colectivo": "planta", "antes": 2.4, "pregunta_origen": "p2"}, "seguimiento_id": None}
    return almacen.anadir_compromiso(dict(base, **extra))


def test_en_idioma_usa_la_traduccion_o_el_original():
    c = _compromiso()
    assert comp.en_idioma(c, "ca")["dijisteis"] == "dc" and comp.en_idioma(c, "ca")["idioma_vista"] == "ca"
    assert comp.en_idioma(c, "en")["dijisteis"] == "d" and comp.en_idioma(c, "en")["idioma_vista"] == "es"  # sin traducción
    assert comp.en_idioma(c, "es")["idioma_vista"] == "es"


def _seguimiento(n_planta, valores=None, estado="publicada", simulada=False):
    almacen.guardar_encuesta({"id": "enc_010", "estado": estado, "colectivos": ["planta"], "colectivo": "planta",
                              "preguntas": [{"id": "p1", "tipo": "escala_1_5", "texto": "¿?", "fija": True}]})
    almacen._escribir(almacen._ruta_obligatoria("respuestas", "enc_010"), [])  # siempre parte de cero
    for i in range(n_planta):
        r = {"id": f"r{i}", "periodo": "2026-11", "colectivo": "planta", "turno": "noche",
             "valores": {"p1": (valores or [4])[i % len(valores or [4])]}}
        if simulada:
            r["tema_real"] = "descansos"
        almacen.anadir_respuesta("enc_010", r)


def test_despues_solo_con_5_o_mas_respuestas():
    c = _compromiso(seguimiento_id="enc_010")
    _seguimiento(4)
    assert comp.calcular_despues(c) is None
    _seguimiento(5, [3, 4, 4, 4, 5])
    assert comp.calcular_despues(c) == {"media": 4.0, "n": 5, "periodo": "2026-11", "simulado": False}


def test_despues_marca_si_es_simulado_y_exige_seguimiento_publicado():
    c = _compromiso(seguimiento_id="enc_010")
    _seguimiento(6, simulada=True)
    assert comp.calcular_despues(c)["simulado"] is True
    _seguimiento(6, estado="aprobada")
    assert comp.calcular_despues(c) is None
    assert comp.calcular_despues(_compromiso()) is None  # sin seguimiento_id


def test_para_publico_cruza_colectivos_y_limita_a_dos():
    _compromiso(colectivos=["planta"])
    _compromiso(colectivos=["oficina"])
    _compromiso(colectivos=["planta", "logistica"], dijisteis="reciente")
    _compromiso(colectivos=["planta"], dijisteis="el más reciente")
    visibles = comp.para_publico(["planta"], "es")
    assert [v["dijisteis"] for v in visibles] == ["el más reciente", "reciente"]
    assert set(visibles[0]) == {"dijisteis", "hicimos", "fecha", "estado"}   # nada más: ni responsable ni indicador
    assert comp.para_publico(["manager"], "es") == []


def test_para_zona_solo_enseña_antes_y_despues_donde_mide_el_indicador():
    c = _compromiso(colectivos=["planta", "oficina"], seguimiento_id="enc_010")
    _seguimiento(6, [4])
    vistas = [comp.vista(c)]
    planta = comp.para_zona(vistas, "planta")[0]
    assert (planta["antes"], planta["despues"], planta["estado"]) == (2.4, 4.0, "comprometido")
    oficina = comp.para_zona(vistas, "oficina")[0]
    assert oficina["antes"] is None and oficina["despues"] is None
    assert comp.para_zona(vistas, "manager") == []


def test_almacen_compromisos_ids_y_actualizacion():
    a, b = _compromiso(), _compromiso()
    assert (a["id"], b["id"]) == ("cmp_001", "cmp_002")
    assert almacen.actualizar_compromiso("cmp_001", {"estado": "hecho"})["estado"] == "hecho"
    assert almacen.leer_compromiso("cmp_002")["estado"] == "comprometido"
    assert almacen.actualizar_compromiso("cmp_999", {}) is None
