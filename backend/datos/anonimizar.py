"""Anonimización de comentarios · UPC 2.

anonimizar(texto) quita correos, teléfonos, DNI/NIE y nombres de persona
antes de guardar cualquier comentario. Se aplica a TODO lo que entra en la
base de datos: respuestas sintéticas y respuestas del formulario.
"""
import re
import unicodedata

CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DNI_NIE = re.compile(r"(?<![\w])(?:\d{8}|[XYZxyz][\s-]?\d{7})[\s-]?[A-Za-z](?![\w])")
TELEFONO = re.compile(r"(?<![\d+])(?:(?:\+|00)34[\s.-]?)?[6-9](?:[\s.-]?\d){8}(?!\d)")
PALABRA = re.compile(r"[^\W\d_]+")

# Nombres que casi nunca son palabras comunes: se detectan en cualquier forma
# ("ramon", "Ramón", "RAMON").
NOMBRES = set("""
antonio jose manuel francisco juan david javier daniel carlos alejandro miguel
rafael pedro pablo sergio fernando jorge luis alberto alvaro adrian diego raul
ivan ruben enrique oscar ramon andres joaquin santiago victor roberto jaime
marcos mario hugo guillermo eduardo ricardo ignacio gonzalo alfonso salvador
emilio agustin julian lorenzo felipe tomas martin nicolas samuel ismael
jordi josep joan marc pere xavier oriol arnau albert toni pepe paco manolo
nacho quim sergi xavi jaume ferran lluis pol biel
maria carmen ana isabel laura cristina marta lucia elena sara paula raquel
beatriz nuria silvia patricia monica sonia julia irene andrea natalia eva
montserrat montse mercedes teresa rocio susana yolanda lorena carla claudia
sandra veronica ines alicia nerea judith laia anna merce aina mireia nuria
encarna lola maite pepa conchi
""".split())

# Nombres que también son palabras ("la luz", "dolores de espalda", "Clara
# mejora"): solo cuentan si van en mayúscula y no empiezan frase.
NOMBRES_AMBIGUOS = set("""
rosa luz mar sol paz pilar dolores remedios amparo consuelo blanca clara
gloria victoria esperanza angel angeles jesus cruz pau alba marina
""".split())

# Palabras tras las que una palabra en mayúscula suele ser un nombre.
PISTAS = set("""
llamo jefe jefa encargado encargada supervisor supervisora compañero compañera
responsable coordinador coordinadora gerente
""".split())


def _normalizar(palabra: str) -> str:
    sin_acentos = unicodedata.normalize("NFD", palabra)
    return "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn").lower()


def _empieza_frase(texto: str, inicio: int) -> bool:
    antes = texto[:inicio].rstrip()
    return not antes or antes[-1] in ".!?¡¿\n:;\"'("


def _quitar_nombres(texto: str) -> str:
    tokens = list(PALABRA.finditer(texto))
    marcar = [False] * len(tokens)

    for i, t in enumerate(tokens):
        palabra = t.group()
        norm = _normalizar(palabra)
        mayuscula = palabra[0].isupper()
        anterior = _normalizar(tokens[i - 1].group()) if i > 0 else ""
        if norm in NOMBRES:
            marcar[i] = True
        elif norm in NOMBRES_AMBIGUOS and mayuscula and not _empieza_frase(texto, t.start()):
            marcar[i] = True
        elif anterior in PISTAS and mayuscula:
            marcar[i] = True
        # Apellido: palabra en mayúscula justo después de un nombre.
        elif i > 0 and marcar[i - 1] and mayuscula and texto[tokens[i - 1].end():t.start()].isspace():
            marcar[i] = True

    resultado, cursor, i = [], 0, 0
    while i < len(tokens):
        if not marcar[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(tokens) and marcar[j + 1] and texto[tokens[j].end():tokens[j + 1].start()].isspace():
            j += 1
        resultado.append(texto[cursor:tokens[i].start()])
        resultado.append("[nombre]")
        cursor = tokens[j].end()
        i = j + 1
    resultado.append(texto[cursor:])
    return "".join(resultado)


def anonimizar(texto):
    """Devuelve el texto sin datos identificativos. None o "" se devuelven igual."""
    if not texto:
        return texto
    texto = CORREO.sub("[correo]", texto)
    texto = DNI_NIE.sub("[documento]", texto)
    texto = TELEFONO.sub("[telefono]", texto)
    return _quitar_nombres(texto)
