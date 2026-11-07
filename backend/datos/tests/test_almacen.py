import json

import pytest

from backend.datos import almacen


@pytest.fixture(autouse=True)
def rutas_temporales(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "BASE", tmp_path / "almacen")
    monkeypatch.setattr(almacen, "SINTETICOS", tmp_path / "sinteticos")
    monkeypatch.setattr(almacen, "CONTENIDO", tmp_path / "contenido")
    (tmp_path / "sinteticos").mkdir()
    (tmp_path / "contenido").mkdir()
    return tmp_path


def encuesta(id_="enc_000"):
    return {"id": id_, "estado": "publicada", "titulo": "Pulso", "colectivo": "todos", "periodo": "2026-10",
            "preguntas": [{"id": "p1", "tipo": "escala_1_5"}, {"id": "p6", "tipo": "texto"}]}


def respuesta(comentario="todo bien", p6="nada"):
    return {"id": "r_1", "encuesta_id": "enc_000", "fecha": "2026-10-15", "periodo": "2026-10",
            "colectivo": "planta", "centro_tipo": "fabrica", "turno": "noche", "canal": "qr",
            "valores": {"p1": 3, "p6": p6}, "comentario": comentario}


def test_guardar_leer_y_listar():
    almacen.guardar_encuesta(encuesta("enc_001"))
    almacen.anadir_respuesta("enc_001", respuesta())
    assert almacen.leer_encuesta("enc_001")["titulo"] == "Pulso"
    assert almacen.leer_encuesta("enc_999") is None
    assert almacen.listar_encuestas() == [{"id": "enc_001", "titulo": "Pulso", "colectivo": "todos",
                                           "estado": "publicada", "periodo": "2026-10", "n_respuestas": 1}]


def test_nuevo_id_encuesta():
    almacen.inicializar()
    assert almacen.nuevo_id_encuesta() == "enc_001"
    almacen.guardar_encuesta(encuesta("enc_000"))
    almacen.guardar_encuesta(encuesta("enc_001"))
    assert almacen.nuevo_id_encuesta() == "enc_002"


def test_id_malicioso():
    assert almacen.leer_encuesta("../../etc/passwd") is None
    assert almacen.leer_respuestas("../x") == []
    with pytest.raises(ValueError):
        almacen.anadir_respuesta("../x", respuesta())


def test_cargar_sinteticos_anonimiza_comentario_y_textos(rutas_temporales):
    s = rutas_temporales / "sinteticos"
    (s / "enc_000.json").write_text(json.dumps(encuesta()), encoding="utf-8")
    (s / "respuestas.json").write_text(json.dumps([respuesta("soy Jordi", "llamad al 612345678"), respuesta()]),
                                       encoding="utf-8")
    assert almacen.cargar_sinteticos() == 2
    r = almacen.leer_respuestas("enc_000")[0]
    assert r["comentario"] == "llamad al [telefono] / soy [nombre]"
    assert r["valores"] == {"p1": 3}  # el texto libre va solo a comentario


def test_inicializar_solo_carga_si_vacio(rutas_temporales):
    s = rutas_temporales / "sinteticos"
    (s / "enc_000.json").write_text(json.dumps(encuesta()), encoding="utf-8")
    (s / "respuestas.json").write_text(json.dumps([respuesta()]), encoding="utf-8")
    almacen.inicializar()
    almacen.inicializar()
    assert len(almacen.leer_respuestas("enc_000")) == 1


def test_sin_sinteticos_ni_contenido():
    almacen.inicializar()
    assert almacen.listar_encuestas() == []
    assert almacen.leer_plantilla() == []
    assert almacen.leer_reglas() == ""
    assert almacen.leer_transparencia() == ""


def test_leer_contenido(rutas_temporales):
    c = rutas_temporales / "contenido"
    (c / "plantilla.json").write_text('[{"colectivo": "planta", "turno": "noche", "personas": 120}]', encoding="utf-8")
    (c / "transparencia.md").write_text("Es anónimo.", encoding="utf-8")
    assert almacen.leer_plantilla()[0]["personas"] == 120
    assert almacen.leer_transparencia() == "Es anónimo."
