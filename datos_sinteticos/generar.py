#!/usr/bin/env python3
"""Generador de datos sintéticos (UPC 1) · según MODULOS.md, sección 5.

Uso:
    python datos_sinteticos/generar.py            # busca una semilla con la historia del demo
    python datos_sinteticos/generar.py --seed 42  # semilla fija

Escribe:
    datos_sinteticos/enc_000.json      Encuesta "Pulso de clima general"
    datos_sinteticos/respuestas.json   ~600 Respuesta (periodos 2026-09 y 2026-10)

Solo librería estándar. Datos 100 % ficticios.
"""

import argparse
import calendar
import contextlib
import io
import json
import os
import random
import re
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PLANTILLA_PATH = os.path.join(PROJECT_ROOT, "contenido", "plantilla.json")
SALIDA_ENCUESTA = os.path.join(SCRIPT_DIR, "enc_000.json")
SALIDA_RESPUESTAS = os.path.join(SCRIPT_DIR, "respuestas.json")

# ---------------------------------------------------------------------------
# VALORES CERRADOS (MODULOS.md §0 y contratos/formatos.md)
# ---------------------------------------------------------------------------

COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
TURNOS_PLANTA = ["manana", "tarde", "noche"]
CENTRO_MAP = {"planta": "fabrica", "logistica": "almacen",
              "comercial": "oficina", "oficina": "oficina", "manager": "oficina"}
TEMAS = ["descansos", "turnos", "carga_trabajo", "comunicacion", "liderazgo",
         "herramientas", "formacion", "reconocimiento", "seguridad", "ambiente",
         "conciliacion", "otros"]
PERIODO_ANTERIOR, PERIODO_ACTUAL = "2026-09", "2026-10"
PERIODOS = [PERIODO_ANTERIOR, PERIODO_ACTUAL]
ENCUESTA_ID = "enc_000"

# ---------------------------------------------------------------------------
# PLANTILLA Y PARTICIPACIÓN
# ---------------------------------------------------------------------------

# Por defecto, si contenido/plantilla.json no existe o no es válido.
PLANTILLA_DEFAULT = [
    {"colectivo": "planta", "turno": "manana", "personas": 300},
    {"colectivo": "planta", "turno": "tarde", "personas": 280},
    {"colectivo": "planta", "turno": "noche", "personas": 220},
    {"colectivo": "logistica", "turno": "sin_turno", "personas": 220},
    {"colectivo": "comercial", "turno": "sin_turno", "personas": 130},
    {"colectivo": "oficina", "turno": "sin_turno", "personas": 170},
    {"colectivo": "manager", "turno": "sin_turno", "personas": 50},
]

# Tasas de respuesta por periodo (MODULOS.md §5)
TASAS = {
    ("planta", "manana"): 0.25, ("planta", "tarde"): 0.25, ("planta", "noche"): 0.07,
    ("logistica", "sin_turno"): 0.10, ("comercial", "sin_turno"): 0.30,
    ("oficina", "sin_turno"): 0.45, ("manager", "sin_turno"): 0.60,
}

CANAL_PROBS = {  # canal: qr | quiosco | teams
    "planta": [("qr", 0.6), ("quiosco", 0.4)],
    "logistica": [("qr", 0.6), ("quiosco", 0.4)],
    "comercial": [("teams", 0.8), ("qr", 0.2)],
    "oficina": [("teams", 0.8), ("qr", 0.2)],
    "manager": [("teams", 0.8), ("qr", 0.2)],
}

# ---------------------------------------------------------------------------
# HISTORIA DEL DEMO
# ---------------------------------------------------------------------------

# Peso de cada tema por periodo y tipo de colectivo (se normaliza).
# En 2026-10, en planta suben descansos y turnos y aparece comunicacion.
PESOS_TEMA = {
    ("planta", PERIODO_ANTERIOR): {
        "descansos": 8, "turnos": 7, "carga_trabajo": 13, "comunicacion": 0,
        "liderazgo": 10, "herramientas": 11, "formacion": 8, "reconocimiento": 9,
        "seguridad": 10, "ambiente": 8, "conciliacion": 10, "otros": 6},
    ("planta", PERIODO_ACTUAL): {   # igual que septiembre + los temas que suben
        "descansos": 19, "turnos": 16, "carga_trabajo": 13, "comunicacion": 8,
        "liderazgo": 10, "herramientas": 11, "formacion": 8, "reconocimiento": 9,
        "seguridad": 10, "ambiente": 8, "conciliacion": 10, "otros": 6},
    ("resto", PERIODO_ANTERIOR): {
        "descansos": 6, "turnos": 1, "carga_trabajo": 15, "comunicacion": 0,
        "liderazgo": 13, "herramientas": 12, "formacion": 12, "reconocimiento": 11,
        "seguridad": 3, "ambiente": 10, "conciliacion": 11, "otros": 6},
    ("resto", PERIODO_ACTUAL): {
        "descansos": 6, "turnos": 1, "carga_trabajo": 15, "comunicacion": 3,
        "liderazgo": 13, "herramientas": 12, "formacion": 12, "reconocimiento": 11,
        "seguridad": 3, "ambiente": 10, "conciliacion": 11, "otros": 6},
}

# Tendencias que deben salir (regla de calcular_tendencia en MODULOS.md §4).
TENDENCIAS_ESPERADAS = {"descansos": "sube", "turnos": "sube", "comunicacion": "nuevo"}

# Media base de las escalas por colectivo
MEDIA_BASE = {"planta": 3.2, "logistica": 3.0, "comercial": 3.4,
              "oficina": 3.6, "manager": 3.8}

# Qué pregunta penaliza cada tema (p1 bienestar, p2 liderazgo, p3 desarrollo,
# p4 condiciones: carga y turnos, p5 entorno)
EFECTO_TEMA = {
    "descansos": {"p1": -0.6, "p4": -0.8}, "turnos": {"p1": -0.4, "p4": -0.9},
    "carga_trabajo": {"p1": -0.5, "p4": -0.7}, "comunicacion": {"p2": -0.7},
    "liderazgo": {"p2": -0.8}, "formacion": {"p3": -0.8},
    "reconocimiento": {"p2": -0.3, "p3": -0.4}, "herramientas": {"p4": -0.4},
    "seguridad": {"p5": -0.6}, "ambiente": {"p5": -0.8},
    "conciliacion": {"p1": -0.5, "p4": -0.3}, "otros": {},
}
CAIDA_P4_PLANTA = -1.2  # p4 de planta en 2026-10 (debe bajar >= 0,8 de media)

# ---------------------------------------------------------------------------
# BANCO DE COMENTARIOS
# "P" = solo planta/logistica (habla de turnos, planta, almacén, máquinas, quiosco...)
# "N" = neutra, vale para cualquier colectivo
# ---------------------------------------------------------------------------

COMENTARIOS = {
    "descansos": [
        ("P", "entre turno y turno no da tiempo ni a comer bien"),
        ("P", "yo pido q amplien el descanso de noche, es inhumano"),
        ("P", "no hay ni 10 min para tomar algo en el turno"),
        ("P", "descansem molt poc entre torn i torn"),
        ("P", "si empalmas dos noches seguidas no descansas nada"),
        ("P", "el descanso de 15 min es una broma con 8h de turno"),
        ("P", "amb el nou sistema no tenim temps de desconnectar entre torns"),
        ("P", "en el almacen no hay sitio decente para descansar"),
        ("P", "desde el cambio de turnos la pausa se ha quedado en nada"),
        ("P", "en linea no te dejan parar ni cuando toca"),
        ("N", "el descanso es muy corto, acabas agotado"),
        ("N", "necesitamos mas tiempo de pausa, no llegamos"),
        ("N", "els descansos son massa curts, no puc ni seure"),
        ("N", "la pausa no da para nada, ni para ir al baño tranquilo"),
        ("N", "la pausa del mediodia se queda corta para desconectar"),
        ("N", "no tenemos tiempo real de descanso durante la jornada"),
        ("N", "falta un espacio tranquilo donde poder descansar de verdad"),
        ("N", "els descansos no son suficients per recuperar energia"),
    ],
    "turnos": [
        ("P", "el nuevo sistema de turnos es un caos"),
        ("P", "cambiar de turno cada semana te destroza el cuerpo"),
        ("P", "la rotacion nueva no tiene ningun sentido"),
        ("P", "els torns rotatius nous son impossibles"),
        ("P", "me ponen de noche mas veces q antes"),
        ("P", "no sabemos el cuadrante hasta el ultimo dia"),
        ("P", "con los turnos nuevos no hay manera de organizarse"),
        ("P", "el cuadrante cambia cada semana y asi no se puede"),
        ("P", "preferia el sistema de turnos de antes, era mas estable"),
        ("P", "el torn de nit s'hauria de repartir millor"),
        ("P", "los cambios de turno de ultima hora son constantes"),
        ("P", "deberiamos poder opinar sobre como se hacen los turnos"),
        ("N", "los horarios cambian demasiado a menudo"),
        ("N", "no se respeta el calendario que se publica"),
        ("N", "l'horari canvia massa sovint"),
    ],
    "carga_trabajo": [
        ("P", "no damos abasto en el turno de tarde"),
        ("P", "necesitamos mas personal en linea"),
        ("P", "falta personal para cubrir todos los turnos"),
        ("P", "la produccion sube pero el equipo no crece"),
        ("P", "el almacen necesita mas gente para los picos"),
        ("P", "a planta estem desbordats amb la feina"),
        ("N", "hay demasiado trabajo para la gente que somos"),
        ("N", "la carga de trabajo es excesiva ultimamente"),
        ("N", "cada vez mas faena amb menys gent"),
        ("N", "la carrega de treball ha augmentat molt"),
        ("N", "hay picos de trabajo q no se pueden gestionar"),
        ("N", "estamos al limite de capacidad"),
        ("N", "no pueden pedir mas con menos gente"),
        ("N", "el ritmo de trabajo no es sostenible asi"),
        ("N", "cada dia hay mas tareas y menos recursos"),
        ("N", "necessitem mes mans per treure la feina endavant"),
    ],
    "comunicacion": [
        ("P", "nadie nos dijo nada oficial del cambio de turnos"),
        ("P", "si van a cambiar los turnos almenos q avisen bien"),
        ("P", "me cambiaron el turno sin explicarme por que"),
        ("P", "no hi va haver cap comunicat oficial sobre els torns"),
        ("P", "el cambio de turnos llego de un dia para otro sin explicacion"),
        ("P", "en planta nos enteramos del cambio por casualidad"),
        ("P", "als de nit no ens van dir res del canvi"),
        ("P", "nos enteramos del cambio de turnos x el grupo de wasa"),
        ("N", "me entere del cambio por un compañero, no por la empresa"),
        ("N", "la comunicacion del cambio fue pesima"),
        ("N", "ens van avisar del canvi amb molt poc temps"),
        ("N", "no hubo reunion ni correo, nos enteramos de rebote"),
        ("N", "falta un canal oficial para avisar de los cambios"),
        ("N", "siempre nos enteramos de los cambios por rumores"),
    ],
    "liderazgo": [
        ("P", "necesitamos jefes q bajen a planta mas a menudo"),
        ("P", "el encargado de noche no sabe gestionar conflictos"),
        ("P", "el responsable del almacen nunca esta cuando se le necesita"),
        ("N", "mi jefe no escucha las quejas del equipo"),
        ("N", "falta apoyo de los mandos intermedios"),
        ("N", "el lideratge ha de millorar molt"),
        ("N", "no hay feedback de los superiores nunca"),
        ("N", "els caps haurien de comunicar-se millor amb nosaltres"),
        ("N", "siento q las decisiones se toman sin contar con nosotros"),
        ("N", "los mandos no se mojan cuando hay problemas"),
        ("N", "falta liderazgo de verdad, no solo ordenes"),
        ("N", "el responsable deberia preguntar mas al equipo"),
        ("N", "se necesita mas cercania por parte de los responsables"),
        ("N", "el lideratge hauria de ser mes participatiu"),
    ],
    "herramientas": [
        ("P", "las maquinas fallan mucho y nadie las arregla rapido"),
        ("P", "las tablets del quiosco van fatal"),
        ("P", "la wifi en planta es malisima, no carga nada"),
        ("P", "hay herramientas rotas q llevan meses sin reparar"),
        ("P", "les eines de la fabrica son molt antigues"),
        ("P", "en el almacen faltan carretillas en buen estado"),
        ("N", "necesitamos herramientas mas modernas"),
        ("N", "el software de gestion es lentisimo"),
        ("N", "el sistema se cuelga cada dos por tres"),
        ("N", "les eines no estan al dia, necessitem actualitzar"),
        ("N", "la plataforma interna va muy lenta y falla mucho"),
        ("N", "el portatil q tengo es muy antiguo y va fatal"),
        ("N", "el software nuevo tiene muchos bugs"),
        ("N", "falta inversion en tecnologia para el dia a dia"),
    ],
    "formacion": [
        ("P", "no hay formacion para las nuevas maquinas"),
        ("P", "al magatzem no hi ha cap formacio"),
        ("P", "nos ponen en linea nueva sin explicarnos nada"),
        ("N", "llevamos meses sin hacer ningun curso"),
        ("N", "no hi ha opcions de formacio aqui"),
        ("N", "me gustaria aprender cosas nuevas pero no hay oferta"),
        ("N", "la formacion es nula, todo se aprende sobre la marcha"),
        ("N", "necessitem formacio per als nous processos"),
        ("N", "falta un plan de carrera claro"),
        ("N", "la empresa no invierte en formacion del personal"),
        ("N", "me gustaria tener acceso a formacion online"),
        ("N", "no hi ha cap programa de mentoria ni res semblant"),
        ("N", "quiero crecer aqui pero no hay plan de formacion"),
    ],
    "reconocimiento": [
        ("P", "en planta nadie valora el esfuerzo q hacemos"),
        ("P", "los de noche somos invisibles para la empresa"),
        ("N", "nunca te dicen que has hecho algo bien"),
        ("N", "el esfuerzo no se reconoce para nada"),
        ("N", "ningu valora la feina que fem"),
        ("N", "solo te dicen algo cuando fallas"),
        ("N", "estaria bien un gracias de vez en cuando"),
        ("N", "los logros del equipo no se celebran nunca"),
        ("N", "no se reconoce a quien se esfuerza mas"),
        ("N", "falta reconeixement per part de la direccio"),
        ("N", "da igual lo q hagas, nadie lo ve"),
    ],
    "seguridad": [
        ("P", "hay zonas de la planta que son peligrosas"),
        ("P", "falta señalizacion en la zona de carga"),
        ("P", "el suelo esta resbaladizo y nadie lo limpia"),
        ("P", "la seguretat a la fabrica ha de millorar"),
        ("P", "he visto cables sueltos cerca de las maquinas"),
        ("P", "faltan EPIs nuevos en la zona de carga"),
        ("P", "la iluminacion en el almacen es muy pobre"),
        ("N", "no hay protocolos claros de emergencia"),
        ("N", "necesitamos mas formacion en prevencion"),
        ("N", "falta un plan de evacuacion visible"),
        ("N", "las visitas a cliente no tienen protocolo de seguridad"),
        ("N", "la silla y la pantalla no cumplen ergonomia basica"),
        ("N", "no se hacen simulacros de evacuacion desde hace mucho"),
    ],
    "ambiente": [
        ("P", "en planta el ambiente con los compañeros es bueno"),
        ("P", "hay mal rollo entre el turno de mañana y el de tarde"),
        ("N", "el ambiente con los compañeros es lo mejor de aqui"),
        ("N", "hay bastante tension en el equipo ultimamente"),
        ("N", "l'ambient entre companys es bo"),
        ("N", "falta compañerismo, cada uno va a lo suyo"),
        ("N", "hay grupitos y eso crea mal ambiente"),
        ("N", "el equipo se ayuda mucho, eso se agradece"),
        ("N", "se nota cansancio y mal humor en el equipo"),
        ("N", "hi ha bon rotllo pero molta pressio"),
        ("N", "deberiamos hacer mas cosas juntos como equipo"),
    ],
    "conciliacion": [
        ("P", "con los nuevos turnos no veo a mis hijos"),
        ("P", "el turno de noche me esta destrozando la vida social"),
        ("P", "la conciliacio es molt dificil amb aquests torns"),
        ("P", "necessito canviar de torn per motius familiars"),
        ("N", "no puedo compaginar el trabajo con mi vida"),
        ("N", "necesito mas flexibilidad para temas de familia"),
        ("N", "no llego a recoger a los niños del cole"),
        ("N", "no hay ningun tipo de flexibilidad horaria"),
        ("N", "amb l'horari actual no puc portar els nens a escola"),
        ("N", "no existe opcion de teletrabajo ni flexibilidad"),
        ("N", "falta flexibilidad real, no solo de palabra"),
        ("N", "l'horari no es compatible amb la meva vida familiar"),
    ],
    "otros": [
        ("P", "el comedor de la fabrica deja mucho q desear"),
        ("P", "los uniformes nuevos pican y dan calor"),
        ("N", "el parking siempre esta lleno"),
        ("N", "la maquina de cafe lleva semanas rota"),
        ("N", "la calefaccion no funciona bien"),
        ("N", "el menjador hauria de tenir mes opcions"),
        ("N", "el transporte para llegar es fatal"),
        ("N", "todo bien, nada especial q comentar"),
        ("N", "res a dir, tot correcte"),
        ("N", "los vestuarios necesitan una reforma"),
    ],
}

# Datos personales INVENTADOS para demostrar anonimizar() (~5 %)
DATOS_FICTICIOS_PLANTA = [
    "preguntale a Manolo q el lo sabe bien",
    "Carlos del turno de noche tb lo dice",
    "q se lo digan a la Maria del almacen",
    "llama al 612 345 678 q te lo explican",
]
DATOS_FICTICIOS_NEUTROS = [
    "yo soy Lucia y estoy harta de esto",
    "escribe a prueba@example.com y te lo confirmo",
    "el correo es demo@example.com por si quieres quejas",
    "contacta al +34 698 123 456 y pregunta por Pedro",
    "habla con Elena q ella te lo confirma",
    "pregunta a Jordi del equipo, el te lo cuenta",
    "mi movil es 655 111 222 si quereis mas info",
]

MULETILLAS = ["la verdad", "pues", "sinceramente", "bueno", "doncs", "la veritat",
              "mira", "oye", "vamos", "es que", "home"]
CIERRES = ["a ver si se arregla", "estamos cansados", "esto no puede seguir así",
           "a veure si millora", "ya está bien", "esperemos que cambien algo",
           "ojala mejore pronto", "a veure que fan", "en fin"]

ABREVIATURAS = {"que": "q", "porque": "xq", "también": "tb", "por": "x",
                "para": "pa", "muy": "mu", "nada": "na", "todos": "tos"}
_ABREV = [(re.compile(r"\b" + re.escape(l) + r"\b"), c) for l, c in ABREVIATURAS.items()]
EMOJIS = ["😤", "😞", "🤦", "💪", "👎", "😡", "🙄", "😩", "🤷", "👀"]

# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------


def quitar_tildes(texto):
    out = []
    for c in texto:
        if c in "ñÑçÇ":
            out.append(c)
        else:
            out.append("".join(ch for ch in unicodedata.normalize("NFKD", c)
                               if unicodedata.category(ch) != "Mn"))
    return "".join(out)


def aplicar_ruido(texto, rng):
    t = texto.lower()
    if rng.random() < 0.7:
        t = quitar_tildes(t)
    for patron, corta in _ABREV:
        if patron.search(t) and rng.random() < 0.4:
            t = patron.sub(corta, t, count=1)
    t = t.rstrip(".,;:!?")
    if rng.random() < 0.15 and len(t) > 10:
        pos = rng.randint(3, len(t) - 2)
        t = t[:pos] + t[pos] + t[pos:]
    if rng.random() < 0.12:
        t += " " + rng.choice(EMOJIS)
    return t


def elegir_ponderado(pesos, rng):
    """pesos: dict clave -> peso (>= 0). Devuelve una clave."""
    total = sum(pesos.values())
    r = rng.random() * total
    acum = 0.0
    for k, w in pesos.items():
        acum += w
        if r <= acum and w > 0:
            return k
    return [k for k, w in pesos.items() if w > 0][-1]


def dias_laborables(periodo):
    anio, mes = map(int, periodo.split("-"))
    _, n = calendar.monthrange(anio, mes)
    return [f"{anio}-{mes:02d}-{d:02d}" for d in range(1, n + 1)
            if calendar.weekday(anio, mes, d) < 5]


def tasa_de(colectivo, turno):
    if (colectivo, turno) in TASAS:
        return TASAS[(colectivo, turno)], False
    del_colectivo = [t for (c, _), t in TASAS.items() if c == colectivo]
    if del_colectivo:
        return sum(del_colectivo) / len(del_colectivo), True
    return 0.15, True


def cargar_plantilla():
    """contenido/plantilla.json si existe y es válido; si no, PLANTILLA_DEFAULT.
    Normaliza mayúsculas/tildes y corrige turnos imposibles."""
    if not os.path.exists(PLANTILLA_PATH):
        print(f"  Plantilla: {PLANTILLA_PATH} no existe → se usa la plantilla por defecto")
        return [dict(s) for s in PLANTILLA_DEFAULT]
    try:
        with open(PLANTILLA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        segmentos = []
        for item in data:
            c = quitar_tildes(str(item["colectivo"]).strip().lower())
            t = quitar_tildes(str(item["turno"]).strip().lower()).replace("ñ", "n").replace(" ", "_")
            p = int(item["personas"])
            if c not in COLECTIVOS or p <= 0:
                print(f"    ! Segmento ignorado (valor no válido): {item}")
                continue
            if c == "planta" and t not in TURNOS_PLANTA:
                print(f"    ! Segmento ignorado (planta necesita manana/tarde/noche): {item}")
                continue
            if c != "planta" and t != "sin_turno":
                print(f"    ! {c}/{t}: {c} no tiene turnos, se usa sin_turno")
                t = "sin_turno"
            segmentos.append({"colectivo": c, "turno": t, "personas": p})
        if not segmentos:
            raise ValueError("sin segmentos válidos")
        print(f"  Plantilla: {PLANTILLA_PATH}")
        for s in segmentos:
            if tasa_de(s["colectivo"], s["turno"])[1]:
                print(f"    - {s['colectivo']}/{s['turno']} usa tasa por defecto")
        return segmentos
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"  Plantilla no válida ({e}) → se usa la plantilla por defecto")
        return [dict(s) for s in PLANTILLA_DEFAULT]

# ---------------------------------------------------------------------------
# FUNCIONES DEL MÓDULO (MODULOS.md §5)
# ---------------------------------------------------------------------------


def generar_encuesta_base():
    """enc_000: "Pulso de clima general", colectivo todos, publicada, 2026-10."""
    def pregunta(pid, texto, tipo, dimension):
        return {"id": pid, "texto": texto, "tipo": tipo, "opciones": [],
                "dimension": dimension, "condicion": None}
    return {
        "id": ENCUESTA_ID,
        "estado": "publicada",
        "titulo": "Pulso de clima general",
        "intro": ("Queremos saber cómo te sientes en tu trabajo para mejorar lo que haga falta. "
                  "Es anónima: solo se ven resultados agregados."),
        "colectivo": "todos",
        "periodo": PERIODO_ACTUAL,
        "tiempo_estimado_seg": 5 * 15 + 30,
        "url": None,
        "qr": None,
        "preguntas": [
            pregunta("p1", "¿Cómo te sientes en general en tu trabajo?", "escala_1_5", "bienestar"),
            pregunta("p2", "¿Te sientes escuchado/a por tu responsable?", "escala_1_5", "liderazgo"),
            pregunta("p3", "¿Tienes oportunidades para aprender y crecer?", "escala_1_5", "desarrollo"),
            pregunta("p4", "¿Cómo valoras tu carga de trabajo y tus turnos u horarios?",
                     "escala_1_5", "condiciones"),
            pregunta("p5", "¿Cómo es el ambiente con tus compañeros?", "escala_1_5", "entorno"),
            pregunta("p6", "¿Qué cambiarías?", "texto", "condiciones"),
        ],
    }


def _nota(mu, rng):
    return max(1, min(5, round(rng.gauss(mu, 0.9))))


def _comentario(tema, colectivo, rng, con_dato_ficticio):
    planta_like = colectivo in ("planta", "logistica")

    def frases(t):
        return [txt for marca, txt in COMENTARIOS[t] if planta_like or marca == "N"]

    texto = rng.choice(frases(tema))
    if rng.random() < 0.10:  # mezcla con un segundo tema
        otro = rng.choice([t for t in TEMAS if t not in (tema, "otros")])
        texto += ", y " + rng.choice(frases(otro))
    if con_dato_ficticio:
        texto += ". " + rng.choice((DATOS_FICTICIOS_PLANTA if planta_like else [])
                                   + DATOS_FICTICIOS_NEUTROS)
    if rng.random() < 0.30:
        if rng.random() < 0.5:
            texto = rng.choice(MULETILLAS) + ", " + texto
        else:
            texto += ", " + rng.choice(CIERRES)
    if rng.random() < 0.60:
        texto = aplicar_ruido(texto, rng)
    return texto


def _reparto_exacto(pesos, n, rng):
    """Lista de n temas con las proporciones exactas de 'pesos' (mayor resto), barajada."""
    total = sum(pesos.values())
    cuotas = {t: n * w / total for t, w in pesos.items()}
    cuenta = {t: int(q) for t, q in cuotas.items()}
    restos = sorted(cuotas, key=lambda t: (cuotas[t] - cuenta[t], rng.random()), reverse=True)
    for t in restos[: n - sum(cuenta.values())]:
        cuenta[t] += 1
    lista = [t for t, k in cuenta.items() for _ in range(k)]
    rng.shuffle(lista)
    return lista


def generar_respuestas(semilla=42, plantilla=None):
    """~600 Respuesta en 2026-09 y 2026-10 para enc_000, con tema_real.

    Los temas de los comentarios se reparten con proporciones exactas por periodo y
    grupo (planta / resto), así la historia del demo no depende del azar."""
    rng = random.Random(semilla)
    if plantilla is None:
        with contextlib.redirect_stdout(io.StringIO()):
            plantilla = cargar_plantilla()

    # 1. Huecos de respuesta por periodo y segmento
    huecos = []
    for periodo in PERIODOS:
        for seg in plantilla:
            c, t = seg["colectivo"], seg["turno"]
            tasa, _ = tasa_de(c, t)
            n = max(1, round(seg["personas"] * tasa * (1 + rng.uniform(-0.1, 0.1))))
            huecos += [{"periodo": periodo, "colectivo": c, "turno": t} for _ in range(n)]

    # 2. Comentario vacío (15 %) y tema: reparto exacto entre los que comentan
    for periodo in PERIODOS:
        for grupo in ("planta", "resto"):
            del_grupo = [h for h in huecos if h["periodo"] == periodo
                         and (h["colectivo"] == "planta") == (grupo == "planta")]
            rng.shuffle(del_grupo)
            n_vacios = round(len(del_grupo) * 0.15)
            pesos = PESOS_TEMA[(grupo, periodo)]
            temas = _reparto_exacto(pesos, len(del_grupo) - n_vacios, rng)
            for i, h in enumerate(del_grupo):
                h["vacio"] = i < n_vacios
                h["tema"] = elegir_ponderado(pesos, rng) if h["vacio"] else temas[i - n_vacios]

    # 3. Construir cada Respuesta
    ids = set()
    dias = {p: dias_laborables(p) for p in PERIODOS}
    respuestas = []
    for h in huecos:
        c, t, periodo, tema = h["colectivo"], h["turno"], h["periodo"], h["tema"]
        valores = {}
        for pid in ("p1", "p2", "p3", "p4", "p5"):
            mu = MEDIA_BASE[c] + EFECTO_TEMA[tema].get(pid, 0.0)
            if pid == "p4" and c == "planta" and periodo == PERIODO_ACTUAL:
                mu += CAIDA_P4_PLANTA
            valores[pid] = _nota(mu, rng)
        comentario = "" if h["vacio"] else _comentario(tema, c, rng, rng.random() < 0.06)
        while True:
            rid = "r_" + "".join(rng.choice("0123456789abcdef") for _ in range(8))
            if rid not in ids:
                ids.add(rid)
                break
        respuestas.append({
            "id": rid,
            "encuesta_id": ENCUESTA_ID,
            "fecha": rng.choice(dias[periodo]),
            "periodo": periodo,
            "colectivo": c,
            "centro_tipo": CENTRO_MAP[c],
            "turno": t,
            "canal": elegir_ponderado(dict(CANAL_PROBS[c]), rng),
            "valores": valores,          # p6 (texto) va en "comentario"
            "comentario": comentario,
            "tema_real": tema,
        })
    return respuestas

# ---------------------------------------------------------------------------
# COMPROBACIONES DE LA HISTORIA
# ---------------------------------------------------------------------------


def calcular_tendencia(n_actual, total_actual, n_anterior, total_anterior):
    """Misma regla que backend/ia/analizar.py (MODULOS.md §4)."""
    if total_anterior == 0:
        return "estable"
    if n_anterior == 0:
        return "nuevo" if n_actual >= 5 else "estable"
    p_act = n_actual / total_actual if total_actual else 0.0
    p_ant = n_anterior / total_anterior
    cambio = (p_act - p_ant) / p_ant
    if cambio >= 0.30:
        return "sube"
    if cambio <= -0.30:
        return "baja"
    return "estable"


def resumen_temas(respuestas):
    """Solo comentarios no vacíos (como hará analizar_comentarios). Temas con n < 5 se omiten."""
    cont = {}
    totales = {p: 0 for p in PERIODOS}
    for r in respuestas:
        if r["comentario"]:
            cont[(r["periodo"], r["tema_real"])] = cont.get((r["periodo"], r["tema_real"]), 0) + 1
            totales[r["periodo"]] += 1
    res = {}
    for tema in TEMAS:
        n_ant = cont.get((PERIODO_ANTERIOR, tema), 0)
        n_act = cont.get((PERIODO_ACTUAL, tema), 0)
        tend = calcular_tendencia(n_act, totales[PERIODO_ACTUAL], n_ant, totales[PERIODO_ANTERIOR])
        res[tema] = (n_ant, n_act, tend if n_act >= 5 else "oculto")
    return res


def caida_p4_planta(respuestas):
    def media(periodo):
        v = [r["valores"]["p4"] for r in respuestas
             if r["colectivo"] == "planta" and r["periodo"] == periodo]
        return sum(v) / len(v) if v else 0.0
    return media(PERIODO_ANTERIOR), media(PERIODO_ACTUAL)


def historia_ok(respuestas):
    for tema, (_, _, tend) in resumen_temas(respuestas).items():
        esperada = TENDENCIAS_ESPERADAS.get(tema)
        if esperada and tend != esperada:
            return False
        if not esperada and tend not in ("estable", "oculto"):
            return False
    antes, ahora = caida_p4_planta(respuestas)
    return antes - ahora >= 0.8

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def imprimir_resumen(respuestas, plantilla, semilla):
    print(f"\n{'=' * 66}\n  DATOS SINTÉTICOS · semilla {semilla} · {len(respuestas)} respuestas\n{'=' * 66}")
    print(f"\n  {'Periodo':<9}{'Colectivo':<11}{'Turno':<11}{'Resp':>5}{'Pers':>6}{'Tasa':>8}")
    for periodo in PERIODOS:
        for s in plantilla:
            n = sum(1 for r in respuestas if r["periodo"] == periodo
                    and r["colectivo"] == s["colectivo"] and r["turno"] == s["turno"])
            print(f"  {periodo:<9}{s['colectivo']:<11}{s['turno']:<11}{n:>5}{s['personas']:>6}"
                  f"{n / s['personas']:>8.1%}")
    print(f"\n  Temas (solo comentarios no vacíos)  {PERIODO_ANTERIOR} → {PERIODO_ACTUAL}")
    for tema, (n_ant, n_act, tend) in resumen_temas(respuestas).items():
        esperada = TENDENCIAS_ESPERADAS.get(tema, "estable")
        aviso = "" if tend in (esperada, "oculto") or (tema not in TENDENCIAS_ESPERADAS
                                                      and tend == "oculto") else "   <-- no esperada"
        print(f"    {tema:<16}{n_ant:>4} → {n_act:<4} {tend}{aviso}")
    antes, ahora = caida_p4_planta(respuestas)
    print(f"\n  p4 planta: {antes:.2f} → {ahora:.2f} (baja {antes - ahora:.2f}; debe ser ≥ 0.80)")
    com = [r["comentario"] for r in respuestas if r["comentario"]]
    ficticios = sum(1 for c in com if re.search(r"@example\.com|\d{3} \d{3} \d{3}|Manolo|Carlos|Maria|"
                                              r"Lucia|Pedro|Elena|Jordi", c, re.I))
    print(f"  Comentarios: {len(com)} no vacíos, {len(set(com))} distintos, "
          f"{ficticios} con datos personales inventados")
    print(f"  Fechas: {min(r['fecha'] for r in respuestas)} … {max(r['fecha'] for r in respuestas)}")
    print("=" * 66)


def main():
    parser = argparse.ArgumentParser(description="Genera enc_000.json y respuestas.json")
    parser.add_argument("--seed", type=int, default=None,
                        help="Semilla fija. Sin ella, busca desde 42 una que cuente la historia del demo.")
    args = parser.parse_args()

    plantilla = cargar_plantilla()
    if args.seed is not None:
        semilla = args.seed
    else:
        semilla = next((s for s in range(42, 42 + 300)
                        if historia_ok(generar_respuestas(s, plantilla))), None)
        if semilla is None:
            print("  ! Ninguna semilla cuenta la historia completa; se usa 42")
            semilla = 42
        else:
            print(f"  Semilla elegida automáticamente: {semilla}")
    respuestas = generar_respuestas(semilla, plantilla)

    with open(SALIDA_ENCUESTA, "w", encoding="utf-8") as f:
        json.dump(generar_encuesta_base(), f, ensure_ascii=False, indent=2)
    with open(SALIDA_RESPUESTAS, "w", encoding="utf-8") as f:
        json.dump(respuestas, f, ensure_ascii=False, indent=2)
    imprimir_resumen(respuestas, plantilla, semilla)
    print(f"  Escritos: {os.path.relpath(SALIDA_ENCUESTA, PROJECT_ROOT)} y "
          f"{os.path.relpath(SALIDA_RESPUESTAS, PROJECT_ROOT)}\n")


if __name__ == "__main__":
    main()
