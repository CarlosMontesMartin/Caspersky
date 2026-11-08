"""Generación y validación de encuestas adaptadas a uno o varios colectivos.

Con varios colectivos la encuesta tiene un núcleo común (c1..c3) y preguntas propias de cada
sector. Si no hay clave de modelo o la llamada falla, recurre a plantillas de respaldo.
La encuesta se escribe en su idioma original (es, ca o en): el de la pantalla de RRHH al generarla.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import reglas

from . import plantillas_respaldo as plantillas
from .llm import hay_llm, llamar_llm_json
from .textos_respaldo import NOMBRE_IDIOMA, idioma_valido, nombre

ORDEN_COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
COLECTIVOS_VALIDOS = set(ORDEN_COLECTIVOS)
DIMENSIONES_VALIDAS = {
    "bienestar",
    "liderazgo",
    "desarrollo",
    "cultura",
    "entorno",
    "condiciones",
}
TIPOS_VALIDOS = {"escala_1_5", "opcion", "si_no", "texto"}

REGLAS_POR_DEFECTO = {
    "planta": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano y directo, pensado para operarios de fábrica desde el móvil.",
    "logistica": "Máximo 4 preguntas. Frases de menos de 12 palabras. Tono cercano, adaptado a personal de almacén en movimiento.",
    "comercial": "Máximo 5 preguntas. Frases claras y directas, enfocado a equipo en ruta y visitas comerciales.",
    "oficina": "Máximo 6 preguntas. Tono profesional, claro y respetuoso, enfocado a personal de sede y puestos administrativos.",
    "manager": "Máximo 6 preguntas. Tono profesional y constructivo, enfocado a liderazgo, recursos y coordinación de equipos.",
}

# RRHH está esperando delante de la pantalla: pasado este tiempo se usa la plantilla de respaldo
TIMEOUT_GENERAR_SEG = 20
TIMEOUT_GENERAR_SECTORES_SEG = 30

# Tiempo máximo por colectivo (contenido/reglas_colectivos.md, sección 3)
TIEMPO_MAX_COLECTIVO = {"planta": 90, "logistica": 60, "comercial": 120, "oficina": 180,
                        "manager": 120}

log = logging.getLogger(__name__)

# Sin IA, en estos colectivos la pregunta abierta solo sale a quien puntúa 1-2 la primera escala:
# menos texto para quien va justo de tiempo (v6, P1-1)
COLECTIVOS_CONDICIONAL = {"planta", "logistica"}
MAX_PREGUNTAS = {"planta": 4, "logistica": 4, "comercial": 5, "oficina": 6, "manager": 5}

# Respaldo multisector en el idioma de la encuesta (plantillas_respaldo.py)
PREGUNTAS_SECTOR = plantillas.PREGUNTAS_SECTOR["es"]


def _normalizar_texto(texto: str) -> str:
    texto_lower = texto.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto_lower)
        if unicodedata.category(c) != "Mn"
    )


def _extraer_reglas_colectivo(reglas_texto: str, colectivo: str) -> str:
    # Admite "## planta" y "### 3.1 `planta` — Producción", como en contenido/reglas_colectivos.md
    if not reglas_texto:
        return ""
    patron = (rf"^(#{{2,4}})\s+(?:[\d.]+\s+)?`?{re.escape(colectivo)}`?\b.*$"
              rf"([\s\S]*?)(?=^#{{2,4}}\s|\Z)")
    match = re.search(patron, reglas_texto, re.MULTILINE | re.IGNORECASE)
    return match.group(2).strip() if match else ""


def colectivos_de(datos: dict[str, Any]) -> list[str]:
    """Devuelve los colectivos de una necesidad o encuesta, en orden fijo (formato nuevo o antiguo)."""
    lista = datos.get("colectivos")
    if isinstance(lista, list) and lista:
        validos = [c for c in ORDEN_COLECTIVOS if c in lista]
        if validos:
            return validos
    colectivo = datos.get("colectivo")
    if colectivo == "todos":
        return list(ORDEN_COLECTIVOS)
    return [colectivo] if colectivo in COLECTIVOS_VALIDOS else ["planta"]


def etiqueta_colectivo(colectivos: list[str]) -> str:
    """Valor del campo antiguo colectivo: el único, todos o varios."""
    if len(colectivos) == 1:
        return colectivos[0]
    return "todos" if set(colectivos) == COLECTIVOS_VALIDOS else "varios"


def preguntas_de(encuesta: dict[str, Any], colectivo: str) -> list[dict[str, Any]]:
    """Preguntas que ve un colectivo: el núcleo común más las propias de su sector."""
    return (encuesta.get("preguntas") or []) + (
        encuesta.get("preguntas_por_colectivo") or {}).get(colectivo, [])


def _cargar_prompt_sistema() -> str:
    prompt_path = Path(__file__).resolve().parent / "prompts" / "generar.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Eres un experto en clima laboral. Genera una microencuesta en JSON "
        "con titulo, intro y preguntas (id, texto, tipo, opciones, dimension)."
    )


def _idioma(datos: dict[str, Any]) -> str:
    """Idioma original de una necesidad o encuesta (es si no lo dice)."""
    return idioma_valido(datos.get("idioma") or datos.get("idioma_original"))


def _empieza_palabra(texto: str, raiz: str) -> bool:
    return re.search(rf"\b{re.escape(raiz)}", texto) is not None


def _plantilla_respaldo_colectivo(colectivo: str, objetivo: str, contexto: str = "",
                                  idioma: str = "es") -> dict[str, Any]:
    idioma = idioma_valido(idioma)
    texto = _normalizar_texto(f"{objetivo} {contexto}")
    tema = next((t for t in plantillas.TEMAS_RESPALDO
                 if any(_empieza_palabra(texto, clave) for clave in t["claves"])), None)
    elegido = tema["textos"][idioma] if tema else plantillas.RESPALDO_GENERAL[idioma]
    *escalas, abierta = elegido["preguntas"]
    preguntas = [
        {"id": f"p{i}", "texto": txt, "tipo": "escala_1_5", "opciones": [],
         "dimension": dim, "condicion": None}
        for i, (txt, dim) in enumerate(escalas, start=1)
    ]
    condicional = colectivo in COLECTIVOS_CONDICIONAL
    preguntas.append({"id": "p4", "texto": plantillas.QUE_HA_PASADO[idioma] if condicional else abierta[0],
                      "tipo": "texto", "opciones": [], "dimension": abierta[1],
                      "condicion": {"pregunta": "p1", "valor_max": 2} if condicional else None})
    return {
        "titulo": elegido["titulo"],
        "intro": plantillas.INTRO[idioma].format(sobre=elegido["sobre"]),
        "preguntas": preguntas,
    }


def _construir_terminos_prohibidos(temas_prohibidos: list[str]) -> set[str]:
    """Expresiones (al principio de palabra, sin tildes) que no pueden aparecer en la encuesta.

    La lista puede venir en cualquier idioma: "salario", "sou" o "salary" bloquean el dinero en
    castellano, catalán e inglés.
    """
    terminos = set()
    for tema in temas_prohibidos or []:
        norm = _normalizar_texto(str(tema).strip())
        if not norm:
            continue
        terminos.add(re.escape(norm[:-1] if len(norm) >= 6 and " " not in norm else norm))
        for grupo in plantillas.GRUPOS_PROHIBIDOS:
            if any(norm.startswith(clave) or _empieza_palabra(norm, clave) for clave in grupo["claves"]):
                terminos.update(grupo["raices"])
    return terminos


def _texto_contiene_prohibido(texto: str, terminos_prohibidos: set[str]) -> bool:
    if not terminos_prohibidos:
        return False
    texto_norm = _normalizar_texto(texto)
    # Límite de palabra al principio para evitar falsos positivos
    return any(re.search(rf"\b{term}", texto_norm) for term in terminos_prohibidos)


def _limpiar_pregunta(p: Any, terminos_prohibidos: set[str]) -> dict[str, Any] | None:
    if not isinstance(p, dict):
        return None
    texto = str(p.get("texto", "")).strip()
    if not texto:
        return None
    opciones_txt = " ".join(str(o) for o in p.get("opciones") or [])
    if _texto_contiene_prohibido(texto + " " + opciones_txt, terminos_prohibidos):
        return None
    tipo = p.get("tipo") if p.get("tipo") in TIPOS_VALIDOS else "escala_1_5"
    opciones: list[str] = []
    if tipo == "opcion":
        opciones = [str(o).strip() for o in p.get("opciones") or [] if str(o).strip()]
        if len(opciones) < 2:
            tipo, opciones = "escala_1_5", []
    dimension = p.get("dimension") if p.get("dimension") in DIMENSIONES_VALIDAS else "bienestar"
    return {"texto": texto, "tipo": tipo, "opciones": opciones, "dimension": dimension,
            "condicion": _condicion_bruta(p.get("condicion")), "_id": str(p.get("id") or "")}


def _condicion_bruta(condicion: Any) -> dict[str, Any] | None:
    """{"pregunta": id, "valor_max": 1..4} o None. Que la pregunta exista, sea escala_1_5 y vaya
    antes se comprueba al final (_resolver_condiciones), cuando ya están los ids definitivos."""
    if not isinstance(condicion, dict) or not str(condicion.get("pregunta") or "").strip():
        return None
    try:
        valor = int(float(condicion.get("valor_max")))
    except (TypeError, ValueError):
        return None
    return {"pregunta": str(condicion["pregunta"]).strip(), "valor_max": valor} if 1 <= valor <= 4 else None


def _pregunta_fija(necesidad: dict[str, Any]) -> dict[str, Any] | None:
    """La pregunta del indicador de un compromiso (v6): va la primera, tal cual y sin recortes."""
    fija = necesidad.get("pregunta_fija")
    if not isinstance(fija, dict) or not str(fija.get("texto") or "").strip():
        return None
    tipo = fija.get("tipo") if fija.get("tipo") in ("escala_1_5", "si_no", "opcion") else "escala_1_5"
    opciones = [str(o).strip() for o in fija.get("opciones") or [] if str(o).strip()]
    if tipo == "opcion" and len(opciones) < 2:
        tipo = "escala_1_5"
    return {"texto": str(fija["texto"]).strip(), "tipo": tipo,
            "opciones": opciones if tipo == "opcion" else [],
            "dimension": fija.get("dimension") if fija.get("dimension") in DIMENSIONES_VALIDAS else "bienestar",
            "condicion": None, "_id": "", "fija": True}


def _parecidas(a: str, b: str) -> bool:
    """Misma pregunta con otras palabras al final ("¿Te da tiempo a hacer la pausa completa?" y
    "¿Te da tiempo a hacer la pausa completa en tu turno?")."""
    pa, pb = re.findall(r"\w+", _normalizar_texto(a)), re.findall(r"\w+", _normalizar_texto(b))
    n = min(len(pa), len(pb), 6)
    return n >= 4 and pa[:n] == pb[:n]


def _con_fija(preguntas: list[dict[str, Any]], fija: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Pone la pregunta fija la primera y quita las que la repiten."""
    if not fija:
        return preguntas
    return [dict(fija)] + [p for p in preguntas if not _parecidas(p["texto"], fija["texto"])]


def _resolver_condiciones(vistas: list[dict[str, Any]], desde: int = 0) -> None:
    """Cambia la condición bruta por el id definitivo de su pregunta, o la quita.

    Solo vale si la pregunta de referencia es escala_1_5 y va antes. Como mucho una pregunta
    condicional en lo que ve cada persona. `vistas` ya lleva los ids definitivos; solo se tocan
    las preguntas a partir de `desde` (las anteriores ya están resueltas).
    """
    hay_una = any(p.get("condicion") for p in vistas[:desde])
    for i in range(desde, len(vistas)):
        p = vistas[i]
        bruta, p["condicion"] = p.get("condicion"), None
        if not bruta or hay_una or p.get("fija"):
            continue
        referencia = next((q for q in vistas[:i] if q.get("_id") == bruta["pregunta"]
                           and q["tipo"] == "escala_1_5"), None)
        if referencia is not None:
            p["condicion"] = {"pregunta": referencia["id"], "valor_max": bruta["valor_max"]}
            hay_una = True


def _tiempo(preguntas: list[dict[str, Any]]) -> int:
    return reglas.segundos(preguntas)


def _numerar(preguntas: list[dict[str, Any]], prefijo: str) -> list[dict[str, Any]]:
    """Pone los ids definitivos (p1, c1, planta_p1...) en las mismas preguntas y las devuelve."""
    for i, p in enumerate(preguntas, start=1):
        p["id"] = f"{prefijo}{i}"
    return preguntas


def _salida(preguntas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Formato del contrato (fuera los campos internos); "fija": true solo en la pregunta fija."""
    return [{**{k: p[k] for k in ("id", "texto", "tipo", "opciones", "dimension", "condicion")},
             **({"fija": True} if p.get("fija") else {})} for p in preguntas]


def _limite_tiempo(colectivo: str, duracion_max: int, n_sectores: int = 1) -> int:
    # El tope del colectivo nunca baja de la duración mínima, para que siempre quepan 3 preguntas
    tope = max(TIEMPO_MAX_COLECTIVO.get(colectivo, duracion_max), reglas.duracion_minima(n_sectores))
    return min(duracion_max, tope)


def _orden_recorte(preguntas: list[dict[str, Any]]) -> list[int]:
    """Índices en el orden en que se pueden quitar: si_no u opción, escalas sobrantes y texto.

    La última escala_1_5 no aparece nunca: no se puede quitar.
    """
    libres = [(i, p) for i, p in enumerate(preguntas) if not p.get("fija")]
    escalas = [i for i, p in libres if p["tipo"] == "escala_1_5"]
    otras = [i for i, p in libres if p["tipo"] in ("si_no", "opcion")]
    textos = [i for i, p in libres if p["tipo"] == "texto"]
    # Si la pregunta fija ya es una escala, las demás escalas se pueden quitar todas
    protegidas = 0 if any(p.get("fija") and p["tipo"] == "escala_1_5" for p in preguntas) else 1
    return otras[::-1] + escalas[protegidas:][::-1] + textos


def _con_escala(preguntas: list[dict[str, Any]], escala: dict[str, Any]) -> list[dict[str, Any]]:
    # Al menos una escala_1_5, al principio si hay que añadirla; como mucho un texto, al final
    abiertas = [p for p in preguntas if p["tipo"] == "texto"][-1:]
    cerradas = [p for p in preguntas if p["tipo"] != "texto"]
    if not any(p["tipo"] == "escala_1_5" for p in cerradas):
        # Al principio, pero siempre después de la pregunta fija
        cerradas.insert(1 if cerradas and cerradas[0].get("fija") else 0, dict(escala))
    return cerradas + abiertas


def _textos_generales(encuesta: dict[str, Any], respaldo: dict[str, Any],
                      terminos: set[str]) -> tuple[str, str]:
    titulo, intro = encuesta.get("titulo"), encuesta.get("intro")
    if not isinstance(titulo, str) or not titulo.strip() or _texto_contiene_prohibido(titulo, terminos):
        titulo = respaldo["titulo"]
    if not isinstance(intro, str) or not intro.strip() or _texto_contiene_prohibido(intro, terminos):
        intro = respaldo["intro"]
    return titulo.strip(), intro.strip()


def _error_no_caben(necesidad: dict[str, Any], colectivo: str) -> ValueError:
    idioma = _idioma(necesidad)
    return ValueError(plantillas.ERRORES[idioma]["no_caben"].format(
        segundos=necesidad.get("duracion_max_seg"), total=reglas.TOTAL_MIN,
        colectivo=nombre("colectivo", colectivo, idioma)))


def comprobar_duracion(necesidad: dict[str, Any]) -> None:
    """Lanza ValueError, en el idioma de la necesidad, si la duración no llega al mínimo."""
    n = len(colectivos_de(necesidad))
    duracion = int(necesidad.get("duracion_max_seg", 120))
    if duracion < reglas.duracion_minima(n):
        textos = plantillas.ERRORES[_idioma(necesidad)]
        raise ValueError(textos["duracion"].format(minimo=reglas.duracion_minima(n), n=n,
                                                   sectores=textos["sector" if n == 1 else "sectores"]))


def validar_encuesta(encuesta: dict[str, Any], necesidad: dict[str, Any]) -> dict[str, Any]:
    """Ajusta una encuesta a las reglas del contrato: tipos, tiempos, temas prohibidos e ids.

    Con un colectivo todo va en preguntas (p1...). Con varios, núcleo común (c1...) y preguntas
    propias de cada sector (planta_p1...), con 3 a 6 preguntas y el tiempo de cada colectivo.
    """
    colectivos = colectivos_de(necesidad)
    comprobar_duracion(necesidad)
    if len(colectivos) == 1:
        resultado = _validar_un_colectivo(encuesta, necesidad, colectivos[0])
    else:
        resultado = _validar_sectores(encuesta, necesidad, colectivos)
    resultado["origen"] = encuesta.get("origen", "respaldo")
    resultado["idioma_original"] = _idioma(necesidad)
    return resultado


def _validar_un_colectivo(encuesta: dict[str, Any], necesidad: dict[str, Any],
                          colectivo: str) -> dict[str, Any]:
    objetivo = necesidad.get("objetivo", "clima laboral")
    limite = _limite_tiempo(colectivo, int(necesidad.get("duracion_max_seg", 120)))
    terminos = _construir_terminos_prohibidos(necesidad.get("temas_prohibidos", []))
    respaldo = _plantilla_respaldo_colectivo(colectivo, objetivo, necesidad.get("contexto", ""),
                                             _idioma(necesidad))
    titulo, intro = _textos_generales(encuesta, respaldo, terminos)
    # Las del respaldo que se usan para completar no pueden ser referencia de una condición
    de_respaldo = [{**_limpiar_pregunta(p, set()), "_id": "", "condicion": None}
                   for p in respaldo["preguntas"]]
    escala = next(p for p in de_respaldo if p["tipo"] == "escala_1_5")

    preguntas = _con_escala(_con_fija([q for q in (_limpiar_pregunta(p, terminos)
                                                   for p in encuesta.get("preguntas") or []) if q],
                                      _pregunta_fija(necesidad)), escala)
    maximo = min(reglas.TOTAL_MAX, MAX_PREGUNTAS.get(colectivo, reglas.TOTAL_MAX))
    # Recorte por número y por tiempo sin quitar nunca la última escala
    while len(preguntas) > maximo or _tiempo(preguntas) > limite:
        orden = _orden_recorte(preguntas)
        if not orden:
            break
        preguntas.pop(orden[0])
    # Completar hasta el mínimo con preguntas cerradas del respaldo, si caben
    for p in de_respaldo:
        if len(preguntas) >= reglas.TOTAL_MIN:
            break
        if (p["tipo"] != "texto" and not _texto_contiene_prohibido(p["texto"], terminos)
                and all(_normalizar_texto(p["texto"]) != _normalizar_texto(q["texto"]) for q in preguntas)):
            preguntas.insert(len([q for q in preguntas if q["tipo"] != "texto"]), dict(p))
            while _tiempo(preguntas) > limite and _orden_recorte(preguntas):
                indice = _orden_recorte(preguntas)[-1] if preguntas[-1]["tipo"] == "texto" \
                    else _orden_recorte(preguntas)[0]
                preguntas.pop(indice)
    if len(preguntas) < reglas.TOTAL_MIN or _tiempo(preguntas) > limite:
        raise _error_no_caben(necesidad, colectivo)

    preguntas = _numerar(preguntas, "p")
    _resolver_condiciones(preguntas)
    preguntas = _salida(preguntas)
    tiempo = _tiempo(preguntas)
    return {
        "titulo": titulo, "intro": intro,
        "colectivo": colectivo, "colectivos": [colectivo],
        "estado": "borrador", "periodo": datetime.now().strftime("%Y-%m"),
        "tiempo_estimado_seg": tiempo, "tiempo_por_colectivo": {colectivo: tiempo},
        "url": None, "qr": None,
        "preguntas": preguntas, "preguntas_por_colectivo": {},
    }


def _respaldo_sectores(necesidad: dict[str, Any], colectivos: list[str]) -> dict[str, Any]:
    idioma = _idioma(necesidad)
    base = _plantilla_respaldo_colectivo(colectivos[0], necesidad.get("objetivo", ""),
                                         necesidad.get("contexto", ""), idioma)
    primera = next(p for p in base["preguntas"] if p["tipo"] == "escala_1_5")
    condicional = bool(set(colectivos) & COLECTIVOS_CONDICIONAL)
    return {
        "titulo": base["titulo"],
        "intro": base["intro"],
        "preguntas": [dict(primera),
                      {"id": "p_abierta",
                       "texto": plantillas.QUE_HA_PASADO[idioma] if condicional
                       else plantillas.QUE_CAMBIARIAS[idioma],
                       "tipo": "texto", "opciones": [], "dimension": "condiciones",
                       "condicion": ({"pregunta": primera["id"], "valor_max": 2}
                                     if condicional else None)}],
        "preguntas_por_colectivo": {
            c: [{"texto": t, "tipo": tipo, "opciones": [], "dimension": d, "condicion": None}
                for t, tipo, d in plantillas.PREGUNTAS_SECTOR[idioma][c]]
            for c in colectivos
        },
    }


def _propias_candidatas(propuestas: Any, respaldo: list[dict[str, Any]], nucleo: list[dict],
                        terminos: set[str]) -> list[dict[str, Any]]:
    """Preguntas propias válidas de un sector: primero las del modelo, después las del respaldo."""
    textos_nucleo = {_normalizar_texto(p["texto"]) for p in nucleo}
    elegidas: list[dict[str, Any]] = []
    for p in (propuestas if isinstance(propuestas, list) else []) + respaldo:
        q = _limpiar_pregunta(p, terminos)
        # Las propias nunca son de texto ni repiten el núcleo ni otra propia
        if (q and q["tipo"] != "texto" and _normalizar_texto(q["texto"]) not in textos_nucleo
                and not any(p.get("fija") and _parecidas(q["texto"], p["texto"]) for p in nucleo)
                and all(_normalizar_texto(q["texto"]) != _normalizar_texto(x["texto"]) for x in elegidas)):
            elegidas.append(q)
    return elegidas


def _cuantas_propias(nucleo: list[dict], candidatas: list[dict], limite: int, colectivo: str) -> int:
    """Cuántas propias caben (0 si no se puede cumplir el mínimo con este núcleo)."""
    maximo_total = min(reglas.TOTAL_MAX, MAX_PREGUNTAS.get(colectivo, reglas.TOTAL_MAX))
    tope = min(reglas.PROPIAS_MAX, maximo_total - len(nucleo), len(candidatas))
    minimo = max(reglas.PROPIAS_MIN, reglas.TOTAL_MIN - len(nucleo))
    for k in range(tope, minimo - 1, -1):
        if _tiempo(nucleo + candidatas[:k]) <= limite:
            return k
    return 0


def _validar_sectores(encuesta: dict[str, Any], necesidad: dict[str, Any],
                      colectivos: list[str]) -> dict[str, Any]:
    duracion = int(necesidad.get("duracion_max_seg", 120))
    terminos = _construir_terminos_prohibidos(necesidad.get("temas_prohibidos", []))
    respaldo = _respaldo_sectores(necesidad, colectivos)
    titulo, intro = _textos_generales(encuesta, respaldo, terminos)
    limites = {c: _limite_tiempo(c, duracion, len(colectivos)) for c in colectivos}
    escala = {**_limpiar_pregunta(respaldo["preguntas"][0], set()), "_id": "", "condicion": None}

    # Núcleo: 1-3 preguntas, siempre con una escala_1_5, como mucho un texto y al final
    nucleo = _con_escala(_con_fija([q for q in (_limpiar_pregunta(p, terminos)
                                                for p in encuesta.get("preguntas") or []) if q],
                                   _pregunta_fija(necesidad)), escala)
    while len(nucleo) > reglas.NUCLEO_MAX:
        nucleo.pop(_orden_recorte(nucleo)[0])

    propuestas = encuesta.get("preguntas_por_colectivo")
    propuestas = propuestas if isinstance(propuestas, dict) else {}
    # Último recurso si faltan propias (p. ej. la pregunta fija coincide con una del sector):
    # las escalas generales de la plantilla de respaldo
    generales = [p for p in _plantilla_respaldo_colectivo(
        colectivos[0], necesidad.get("objetivo", ""), necesidad.get("contexto", ""),
        _idioma(necesidad))["preguntas"] if p["tipo"] == "escala_1_5"]
    while True:
        candidatas = {c: _propias_candidatas(propuestas.get(c),
                                             respaldo["preguntas_por_colectivo"][c] + generales,
                                             nucleo, terminos) for c in colectivos}
        cuantas = {c: _cuantas_propias(nucleo, candidatas[c], limites[c], c) for c in colectivos}
        if all(cuantas.values()):
            break
        # Algún sector no cabe: se reduce el núcleo (nunca la última escala)
        orden = _orden_recorte(nucleo)
        if not orden:
            sector = next(c for c in colectivos if not cuantas[c])
            raise _error_no_caben(necesidad, sector)
        nucleo.pop(orden[0])

    nucleo = _numerar(nucleo, "c")
    _resolver_condiciones(nucleo)
    por_colectivo = {}
    for c in colectivos:
        propias = _numerar([dict(p) for p in candidatas[c][:cuantas[c]]], f"{c}_p")
        _resolver_condiciones(nucleo + propias, desde=len(nucleo))  # pueden depender del núcleo
        por_colectivo[c] = _salida(propias)
    nucleo = _salida(nucleo)
    tiempos = {c: _tiempo(nucleo + por_colectivo[c]) for c in colectivos}
    return {
        "titulo": titulo, "intro": intro,
        "colectivo": etiqueta_colectivo(colectivos), "colectivos": colectivos,
        "estado": "borrador", "periodo": datetime.now().strftime("%Y-%m"),
        "tiempo_estimado_seg": max(tiempos.values()), "tiempo_por_colectivo": tiempos,
        "url": None, "qr": None,
        "preguntas": nucleo, "preguntas_por_colectivo": por_colectivo,
    }


def _leer_prompt(nombre: str) -> str:
    ruta = Path(__file__).resolve().parent / "prompts" / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def _texto_necesidad(necesidad: dict[str, Any], colectivos: list[str]) -> str:
    return (
        f"Necesidad de RRHH:\n"
        f"- Colectivos: {', '.join(colectivos)}\n"
        f"- Objetivo: {necesidad.get('objetivo', '')}\n"
        f"- Contexto: {necesidad.get('contexto', '')}\n"
        f"- Duración máxima: {necesidad.get('duracion_max_seg', 120)} segundos\n"
        f"- Temas prohibidos: {', '.join(necesidad.get('temas_prohibidos', [])) or 'ninguno'}\n"
        + (f"- Pregunta fija (se añade sola como primera pregunta: no la repitas ni la cuentes): "
           f"{necesidad['pregunta_fija'].get('texto')}\n" if _pregunta_fija(necesidad) else "")
    )


def _instruccion_idioma(idioma: str) -> str:
    return (f"\n\nEscribe el título, la introducción, las preguntas y las opciones en "
            f"{NOMBRE_IDIOMA[idioma]}.")


def generar_encuesta(necesidad: dict[str, Any], reglas: str = "",
                     idioma: str | None = None) -> dict[str, Any]:
    """Genera una encuesta en borrador para uno o varios colectivos, escrita en `idioma`.

    `idioma` (es, ca o en) es el idioma original de la encuesta; si no se pasa, el de
    necesidad["idioma"] y, si tampoco está, es. Una sola llamada al modelo (20 s con un colectivo,
    30 s con varios); si no hay modelo o falla, plantillas de respaldo en ese idioma. Devuelve
    siempre origen, idioma_original, colectivos y colectivo. Lanza ValueError (en ese idioma) si la
    duración no permite una encuesta válida (la ruta responde 422).
    """
    colectivos = colectivos_de(necesidad)
    idioma = idioma_valido(idioma or necesidad.get("idioma"))
    necesidad = {**necesidad, "colectivos": colectivos, "idioma": idioma}
    comprobar_duracion(necesidad)  # Antes de llamar al modelo: un error claro y sin esperas
    candidata: dict[str, Any] | None = None

    if hay_llm():
        inicio = time.monotonic()
        try:
            if len(colectivos) == 1:
                c = colectivos[0]
                reglas_c = _extraer_reglas_colectivo(reglas, c) or REGLAS_POR_DEFECTO[c]
                usuario = (_texto_necesidad(necesidad, colectivos)
                           + f"- Tiempo máximo del colectivo: {TIEMPO_MAX_COLECTIVO[c]} s\n\n"
                           + f"Reglas específicas para el colectivo '{c}':\n{reglas_c}\n\n"
                           + "Genera el JSON de la encuesta cumpliendo todas las indicaciones.")
                respuesta = llamar_llm_json(_cargar_prompt_sistema() + _instruccion_idioma(idioma),
                                            usuario, TIMEOUT_GENERAR_SEG)
            else:
                bloques = [f"### {c} (tiempo máximo {TIEMPO_MAX_COLECTIVO[c]} s)\n"
                           f"{_extraer_reglas_colectivo(reglas, c) or REGLAS_POR_DEFECTO[c]}"
                           for c in colectivos]
                varios = _extraer_reglas_colectivo(reglas, "varios")
                usuario = (_texto_necesidad(necesidad, colectivos)
                           + (f"\nReglas del núcleo común:\n{varios}\n" if varios else "")
                           + "\nReglas de cada colectivo:\n\n" + "\n\n".join(bloques)
                           + "\n\nGenera el JSON con el núcleo común y las preguntas de cada "
                             f"colectivo ({', '.join(colectivos)}).")
                respuesta = llamar_llm_json(_leer_prompt("generar_sectores.md")
                                            + _instruccion_idioma(idioma), usuario,
                                            TIMEOUT_GENERAR_SECTORES_SEG)
            if isinstance(respuesta, dict) and respuesta.get("preguntas"):
                candidata = {**respuesta, "origen": "ia"}
                log.info("Encuesta generada por el modelo en %.1f s (%s)", time.monotonic() - inicio, idioma)
        except Exception as error:
            log.warning("Encuesta generada con la plantilla de respaldo: %s", error)

    if candidata is None:
        if len(colectivos) == 1:
            candidata = _plantilla_respaldo_colectivo(
                colectivos[0], necesidad.get("objetivo", ""), necesidad.get("contexto", ""), idioma)
        else:
            candidata = _respaldo_sectores(necesidad, colectivos)
        candidata["origen"] = "respaldo"

    return validar_encuesta(candidata, necesidad)
