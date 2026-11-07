import json

import pytest

from backend.datos import almacen


@pytest.fixture(autouse=True)
def almacen_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(almacen, "BASE", tmp_path / "almacen")
    monkeypatch.setattr(almacen, "SINTETICOS", tmp_path / "respuestas.json")
    monkeypatch.setattr(almacen, "ENCUESTAS_SINTETICAS", tmp_path / "encuestas.json")
    return tmp_path


def respuesta(encuesta_id="enc_000", colectivo="planta", comentario="todo bien", **extra):
    return {"id": "r_1", "encuesta_id": encuesta_id, "fecha": "2026-10-15", "periodo": "2026-10",
            "colectivo": colectivo, "centro_tipo": "fabrica", "turno": "noche", "canal": "qr",
            "valores": {"p1": 3, "p2": "si"}, "comentario": comentario, **extra}


def test_guardar_y_leer_encuesta():
    almacen.guardar_encuesta({"id": "enc_001", "estado": "borrador"})
    assert almacen.leer_encuesta("enc_001")["estado"] == "borrador"
    assert almacen.leer_encuesta("enc_999") is None


def test_nuevo_id_salta_enc_000():
    assert almacen.nuevo_id() == "enc_001"
    almacen.guardar_encuesta({"id": "enc_000"})
    almacen.guardar_encuesta({"id": "enc_001"})
    assert almacen.nuevo_id() == "enc_002"


def test_anadir_respuesta_anonimiza():
    almacen.anadir_respuesta(respuesta(comentario="llamad a ramon al 612345678"))
    guardada = almacen.leer_respuestas("enc_000")[0]
    assert guardada["comentario"] == "llamad a [nombre] al [telefono]"


def test_id_malicioso_rechazado():
    with pytest.raises(ValueError):
        almacen.leer_encuesta("../../etc/passwd")


def test_inicializar_carga_sinteticos_una_vez(almacen_temporal):
    datos = [respuesta(), respuesta(colectivo="logistica", comentario="mi jefa Pilar grita"),
             respuesta(encuesta_id="enc_turnos")]
    (almacen_temporal / "respuestas.json").write_text(json.dumps(datos), encoding="utf-8")

    assert "Cargadas 3" in almacen.inicializar()
    assert len(almacen.leer_respuestas("enc_000")) == 2
    assert almacen.leer_encuesta("enc_000")["colectivo"] == "todos"
    assert almacen.leer_encuesta("enc_turnos")["colectivo"] == "planta"
    assert "[nombre]" in almacen.leer_respuestas("enc_000")[1]["comentario"]
    assert "ya tenía datos" in almacen.inicializar()


def test_inicializar_sin_archivo_sinteticos():
    assert "No existe" in almacen.inicializar()
