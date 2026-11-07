"""Respuestas simuladas para el modo demo · UPC 2 (v2.md sección 3.5).

Pasan por el MISMO camino que las reales (construir_respuesta: validación,
texto libre a comentario y anonimizar). La historia es la de modulos.md:
el turno de noche responde poco, las escalas de condiciones caen y suben
descansos, turnos y comunicación. ~5 % de comentarios llevan datos personales
inventados para que se vea anonimizar() en acción.

Con IA, los comentarios se sustituyen (p = 0,75) por frases del banco
contextual de UPC 1 (ia.banco_contextual), coherentes con esta encuesta y
del mismo tema, así que la historia del demo no cambia.
"""
import random
from datetime import date

from backend.api import ia_o_respaldo as ia
from backend.api.rutas_publico import construir_respuesta
from backend.api.validacion import colectivos_de, preguntas_de, turnos_de

PESO_TURNO_PLANTA = {"manana": 0.46, "tarde": 0.46, "noche": 0.08}
PESO_COLECTIVO = {"planta": 0.35, "oficina": 0.25, "comercial": 0.15, "manager": 0.10, "logistica": 0.15}

# Temas de la lista cerrada de modulos.md.
COMENTARIOS = {
    "descansos": ["el descanso de la noche es muy corto", "no da tiempo ni a comer en la pausa",
                  "las pausas estan mal repartidas", "la pausa del bocadillo se queda corta",
                  "el descans és massa curt"],
    "turnos": ["los turnos rotan demasiado rapido", "cuesta conciliar con el nuevo horario de turnos",
               "no sabemos el turno con tiempo suficiente", "el canvi de torn ens trenca la setmana",
               "turno de noche muy duro con la rotacion"],
    "comunicacion": ["nadie nos explico bien el cambio", "nos enteramos del cambio por los compañeros",
                     "falta informacion de por que se cambio el sistema", "no ens han explicat res del canvi"],
    "herramientas": ["la carretilla 3 falla cada semana", "faltan escaneres en el muelle",
                     "el programa de inventario va lentisimo"],
    "ambiente": ["buen ambiente con el equipo", "los compañeros ayudan mucho",
                 "hay roces entre turnos al hacer el relevo"],
}
DATOS_PERSONALES = ["habla con Ramón García al 612 345 678", "escribidme a jordi.puig@gmail.com",
                    "mi encargada Montse lo sabe", "llamad a pepe al 699112233"]
MEZCLA = {
    "actual": {"descansos": 0.30, "turnos": 0.25, "comunicacion": 0.20, "herramientas": 0.08,
               "ambiente": 0.07, None: 0.10},
    "anterior": {"descansos": 0.15, "turnos": 0.12, "herramientas": 0.25, "ambiente": 0.18, None: 0.30},
}
MEDIA_ESCALA = {"condiciones": (2.2, 3.5), "otras": (3.3, 3.6)}  # (actual, anterior)
PROB_BANCO = 0.75


def _mes_anterior(hoy: date) -> date:
    return date(hoy.year - 1, 12, 1) if hoy.month == 1 else date(hoy.year, hoy.month - 1, 1)


def _elegir(rng: random.Random, pesos: dict):
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def _valor(rng: random.Random, pregunta: dict, cual: str):
    tipo = pregunta["tipo"]
    if tipo == "escala_1_5":
        medias = MEDIA_ESCALA["condiciones" if pregunta.get("dimension") == "condiciones" else "otras"]
        return max(1, min(5, round(rng.gauss(medias[0] if cual == "actual" else medias[1], 0.9))))
    if tipo == "si_no":
        return "si" if rng.random() < (0.4 if cual == "actual" else 0.65) else "no"
    if tipo == "opcion" and pregunta.get("opciones"):
        opciones = pregunta["opciones"]
        return rng.choices(opciones, weights=range(len(opciones), 0, -1))[0]
    return None


def _variar(rng: random.Random, frase: str) -> str:
    """Pequeñas variaciones de estilo: minúscula inicial, sin punto final, "q"."""
    frase = frase.strip()
    if rng.random() < 0.6:
        frase = frase[:1].lower() + frase[1:]
    if rng.random() < 0.7:
        frase = frase.rstrip(".")
    if rng.random() < 0.3:
        frase = frase.replace(" que ", " q ")
    return frase


def _segmentos(encuesta: dict, n: int, rng: random.Random) -> list[str]:
    """Colectivo de cada respuesta: al menos una de cada colectivo de la encuesta y el resto por pesos."""
    colectivos = colectivos_de(encuesta) or list(PESO_COLECTIVO)
    pesos = {c: PESO_COLECTIVO.get(c, 0.1) for c in colectivos}
    lista = colectivos[:n] + [_elegir(rng, pesos) for _ in range(max(0, n - len(colectivos)))]
    rng.shuffle(lista)
    return lista


def simular(encuesta: dict, n: int, con_periodo_anterior: bool = True, semilla: int | None = None) -> list[dict]:
    """n respuestas del periodo actual (y n del anterior si se pide), listas para guardar."""
    rng = random.Random(semilla)
    hoy = date.today()
    periodos = [("anterior", _mes_anterior(hoy))] if con_periodo_anterior else []
    periodos.append(("actual", hoy))
    temas_presentes = sorted({t for mezcla in MEZCLA.values() for t in mezcla if t})
    banco = ia.banco_contextual(encuesta, temas_presentes)

    respuestas = []
    for cual, mes in periodos:
        ultimo_dia = hoy.day if cual == "actual" else 28
        for colectivo in _segmentos(encuesta, n, rng):
            turnos = turnos_de(colectivo)
            turno = _elegir(rng, PESO_TURNO_PLANTA) if turnos == list(PESO_TURNO_PLANTA) else turnos[0]
            preguntas = preguntas_de(encuesta, colectivo)

            valores = {}
            for p in preguntas:
                cond = p.get("condicion")
                previa = valores.get(cond.get("pregunta")) if cond else None
                if cond and isinstance(previa, int) and previa > cond.get("valor_max", 5):
                    continue  # pregunta condicional que no se muestra
                v = _valor(rng, p, cual)
                if v is not None:
                    valores[p["id"]] = v

            tema = _elegir(rng, MEZCLA[cual])
            comentario = rng.choice(COMENTARIOS[tema]) if tema else ""
            if comentario and rng.random() < 0.05:
                comentario += ", " + rng.choice(DATOS_PERSONALES)  # se conserva para enseñar la anonimización
            elif comentario and banco.get(tema) and rng.random() < PROB_BANCO:
                comentario = _variar(rng, rng.choice(banco[tema]))

            entrada = {"turno": turno, "canal": "qr" if rng.random() < 0.7 else "quiosco", "valores": valores}
            texto = next((p["id"] for p in preguntas if p["tipo"] == "texto"), None)
            if texto:
                entrada["valores"][texto] = comentario
            else:
                entrada["comentario"] = comentario

            fecha = mes.replace(day=rng.randint(1, max(1, min(28, ultimo_dia))))
            respuestas.append(construir_respuesta(encuesta, entrada, colectivo=colectivo,
                                                  fecha=fecha, tema_real=tema or "otros"))
    return respuestas
