"""Respuestas simuladas para el modo demo · UPC 2.

Genera respuestas sintéticas de una encuesta publicada para que el dashboard
tenga datos en directo. Pasan por el MISMO camino que las reales
(construir_respuesta: validación + texto libre a comentario + anonimizar).

La historia es la de modulos.md: en el periodo actual el turno de noche
responde poco, la pregunta de condiciones baja y suben descansos, turnos y
comunicación. ~5 % de comentarios llevan datos personales inventados para
que se vea anonimizar() en acción.
"""
import random
from datetime import date

from backend.api.rutas_publico import construir_respuesta
from backend.api.validacion import turnos_de

PESO_TURNO_PLANTA = {"manana": 0.46, "tarde": 0.46, "noche": 0.08}
PESO_COLECTIVO = {"planta": 0.35, "oficina": 0.30, "comercial": 0.15, "manager": 0.10, "logistica": 0.10}

COMENTARIOS = {
    "descansos": ["el descanso de la noche es muy corto", "no da tiempo ni a comer en la pausa",
                  "las pausas estan mal repartidas", "la pausa del bocadillo se queda corta",
                  "el descans és massa curt"],
    "turnos": ["los turnos rotan demasiado rapido", "cuesta conciliar con el nuevo horario",
               "no sabemos el turno con tiempo suficiente", "el canvi de torn ens trenca la setmana",
               "turno de noche muy duro con la rotacion"],
    "comunicacion": ["nadie nos explico bien el cambio", "nos enteramos del cambio por los compañeros",
                     "falta informacion de por que se cambio el sistema", "no ens han explicat res del canvi"],
    "herramientas": ["la carretilla 3 falla cada semana", "faltan escaneres en el muelle",
                     "el programa de inventario va lentisimo"],
    "companeros": ["buen ambiente con el equipo", "los compañeros ayudan mucho",
                   "hay roces entre turnos al hacer el relevo"],
}
DATOS_PERSONALES = ["habla con Ramón García al 612 345 678", "escribidme a jordi.puig@gmail.com",
                    "mi encargada Montse lo sabe", "llamad a pepe al 699112233"]
MEZCLA = {
    "actual": {"descansos": 0.30, "turnos": 0.25, "comunicacion": 0.20, "herramientas": 0.08,
               "companeros": 0.07, None: 0.10},
    "anterior": {"descansos": 0.15, "turnos": 0.12, "herramientas": 0.25, "companeros": 0.18, None: 0.30},
}
MEDIA_ESCALA = {  # (actual, anterior)
    "condiciones": (2.2, 3.5),
    "otras": (3.3, 3.6),
}


def _mes_anterior(hoy: date) -> date:
    return date(hoy.year - 1, 12, 1) if hoy.month == 1 else date(hoy.year, hoy.month - 1, 1)


def _elegir(rng: random.Random, pesos: dict):
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def _valor(rng: random.Random, pregunta: dict, cual: str):
    tipo = pregunta["tipo"]
    if tipo == "escala_1_5":
        media = MEDIA_ESCALA["condiciones" if pregunta.get("dimension") == "condiciones" else "otras"]
        media = media[0] if cual == "actual" else media[1]
        return max(1, min(5, round(rng.gauss(media, 0.9))))
    if tipo == "si_no":
        return "si" if rng.random() < (0.4 if cual == "actual" else 0.65) else "no"
    if tipo == "opcion" and pregunta.get("opciones"):
        opciones = pregunta["opciones"]
        return rng.choices(opciones, weights=range(len(opciones), 0, -1))[0]
    return None


def simular(encuesta: dict, n: int, con_periodo_anterior: bool = True, semilla: int | None = None) -> list[dict]:
    """Devuelve n respuestas del periodo actual (y n del anterior si se pide), listas para guardar."""
    rng = random.Random(semilla)
    hoy = date.today()
    periodos = [("actual", hoy)]
    if con_periodo_anterior:
        periodos.insert(0, ("anterior", _mes_anterior(hoy)))
    texto = next((p["id"] for p in encuesta["preguntas"] if p["tipo"] == "texto"), None)

    respuestas = []
    for cual, mes in periodos:
        ultimo_dia = hoy.day if cual == "actual" else 28
        for _ in range(n):
            colectivo = encuesta["colectivo"] if encuesta["colectivo"] != "todos" else _elegir(rng, PESO_COLECTIVO)
            turnos = turnos_de(colectivo)
            turno = _elegir(rng, PESO_TURNO_PLANTA) if turnos == list(PESO_TURNO_PLANTA) else turnos[0]

            valores = {}
            for p in encuesta["preguntas"]:
                cond = p.get("condicion")
                if cond and isinstance(valores.get(cond.get("pregunta")), int) and valores[cond["pregunta"]] > cond.get("valor_max", 5):
                    continue  # pregunta condicional que no se muestra
                v = _valor(rng, p, cual)
                if v is not None:
                    valores[p["id"]] = v

            tema = _elegir(rng, MEZCLA[cual])
            comentario = rng.choice(COMENTARIOS[tema]) if tema else ""
            if comentario and rng.random() < 0.05:
                comentario += ", " + rng.choice(DATOS_PERSONALES)
            entrada = {"turno": turno, "canal": "qr" if rng.random() < 0.7 else "quiosco", "valores": valores}
            if texto:
                entrada["valores"][texto] = comentario
            else:
                entrada["comentario"] = comentario

            fecha = mes.replace(day=rng.randint(1, max(1, min(28, ultimo_dia))))
            respuestas.append(construir_respuesta(encuesta, entrada, colectivo=colectivo,
                                                  fecha=fecha, tema_real=tema or "ninguno"))
    return respuestas
