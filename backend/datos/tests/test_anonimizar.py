from backend.datos.anonimizar import anonimizar


def test_correo():
    assert anonimizar("escribidme a pepe.lopez@gmail.com porfa") == "escribidme a [correo] porfa"


def test_telefonos():
    assert anonimizar("llamame al 612 345 678") == "llamame al [telefono]"
    assert anonimizar("mi movil +34 612-34-56-78 ok") == "mi movil [telefono] ok"
    assert anonimizar("fijo 932345678.") == "fijo [telefono]."


def test_no_borra_numeros_normales():
    assert anonimizar("hacemos 8 horas y 40 min de descanso") == "hacemos 8 horas y 40 min de descanso"
    assert anonimizar("en 2026 cambiaron los turnos") == "en 2026 cambiaron los turnos"


def test_dni_nie():
    assert anonimizar("mi dni es 12345678Z") == "mi dni es [dni]"
    assert anonimizar("NIE X1234567L") == "NIE [dni]"


def test_nombres_con_y_sin_mayuscula_y_acentos():
    assert anonimizar("el encargado ramon no explica nada") == "el encargado [nombre] no explica nada"
    assert anonimizar("Ramón García nos grita") == "[nombre] nos grita"
    assert anonimizar("hablé con Montse y con jordi") == "hablé con [nombre] y con [nombre]"


def test_nombre_tras_pista():
    assert anonimizar("mi jefe Fulgencio no escucha") == "mi jefe [nombre] no escucha"


def test_ambiguos_no_rompen_frases_normales():
    assert anonimizar("se va la luz en la nave") == "se va la luz en la nave"
    assert anonimizar("tengo dolores de espalda") == "tengo dolores de espalda"
    assert anonimizar("Clara mejora con el turno nuevo") == "Clara mejora con el turno nuevo"
    assert anonimizar("se lo dije a Pilar ayer") == "se lo dije a [nombre] ayer"


def test_vacios():
    assert anonimizar(None) == ""
    assert anonimizar("") == ""
