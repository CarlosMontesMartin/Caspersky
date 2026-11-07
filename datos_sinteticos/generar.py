#!/usr/bin/env python3
"""Generador de respuestas sintéticas para la encuesta de clima laboral.

Uso:
    python datos_sinteticos/generar.py [--seed N] [--salida datos_sinteticos/respuestas.json]

Solo librería estándar. Datos 100 % ficticios.
"""

import argparse
import calendar
import json
import os
import random
import re
import sys
import unicodedata

# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

ENCUESTA_PATH = os.path.join(PROJECT_ROOT, "contratos", "ejemplos", "encuesta.json")
PLANTILLA_PATH = os.path.join(PROJECT_ROOT, "contenido", "plantilla.json")

COLECTIVOS = ["planta", "logistica", "comercial", "oficina", "manager"]
TURNOS = ["manana", "tarde", "noche", "sin_turno"]
CANALES = ["qr", "quiosco", "teams"]
CENTRO_MAP = {
    "planta": "fabrica",
    "logistica": "almacen",
    "comercial": "oficina",
    "oficina": "oficina",
    "manager": "oficina",
}
TEMAS = [
    "descansos", "comunicacion_cambio", "carga_trabajo", "herramientas",
    "liderazgo", "desarrollo", "seguridad", "conciliacion",
]
PERIODOS = ["2026-10", "2026-11"]

# Colectivos "de planta/logística" vs "de oficina/campo"
COLECTIVOS_PLANTA = {"planta", "logistica"}
COLECTIVOS_OFICINA = {"comercial", "oficina", "manager"}

# Plantilla por defecto (colectivo, turno, personas)
PLANTILLA_DEFAULT = [
    ("planta", "manana", 250),
    ("planta", "tarde", 250),
    ("planta", "noche", 200),
    ("logistica", "manana", 120),
    ("logistica", "tarde", 120),
    ("logistica", "noche", 100),
    ("comercial", "sin_turno", 150),
    ("oficina", "sin_turno", 180),
    ("manager", "sin_turno", 60),
]

# Tasas de respuesta por segmento
TASAS = {
    ("planta", "manana"): 0.25,
    ("planta", "tarde"): 0.22,
    ("planta", "noche"): 0.06,
    ("logistica", "manana"): 0.10,
    ("logistica", "tarde"): 0.08,
    ("logistica", "noche"): 0.05,
    ("comercial", "sin_turno"): 0.22,
    ("oficina", "sin_turno"): 0.40,
    ("manager", "sin_turno"): 0.50,
}

# Canal por colectivo: (canal, probabilidad)
CANAL_PROBS = {
    "planta": [("qr", 0.60), ("quiosco", 0.40)],
    "logistica": [("qr", 0.60), ("quiosco", 0.40)],
    "comercial": [("teams", 0.80), ("qr", 0.20)],
    "oficina": [("teams", 0.80), ("qr", 0.20)],
    "manager": [("teams", 0.80), ("qr", 0.20)],
}

# Media base de escala por colectivo
MEDIA_BASE = {
    "planta": 3.0,
    "logistica": 2.9,
    "comercial": 3.3,
    "oficina": 3.6,
    "manager": 3.8,
}

# Distribución de temas por periodo
TEMAS_PROB = {
    "2026-10": {
        "descansos": 0.10, "comunicacion_cambio": 0.00, "carga_trabajo": 0.19,
        "herramientas": 0.17, "liderazgo": 0.15, "desarrollo": 0.14,
        "seguridad": 0.10, "conciliacion": 0.15,
    },
    "2026-11": {
        "descansos": 0.21, "comunicacion_cambio": 0.13, "carga_trabajo": 0.16,
        "herramientas": 0.04, "liderazgo": 0.13, "desarrollo": 0.11,
        "seguridad": 0.09, "conciliacion": 0.13,
    },
}

# ---------------------------------------------------------------------------
# BANCO DE COMENTARIOS POR TEMA
#
# Cada frase lleva una marca:
#   "P" = solo para planta/logistica (menciona turno, noche, planta, fábrica,
#         almacén, máquinas, quiosco, EPIs, línea)
#   "N" = neutra, vale para cualquier colectivo
# ---------------------------------------------------------------------------

COMENTARIOS = {
    "descansos": [
        # -- Planta/logística --
        ("P", "entre turno y turno no da tiempo ni a comer bien"),
        ("P", "yo pido q amplien el descanso de noche, es inhumano"),
        ("P", "no hay ni 10 min para tomar algo entre turnos"),
        ("P", "hace falta un descanso mas largo x la noche"),
        ("P", "descansem molt poc entre torn i torn"),
        ("P", "si empalmas dos noches seguidas se nota mucho la falta de descanso"),
        ("P", "el descanso de 15 min es una broma con 8h de turno"),
        ("P", "amb el nou sistema no tenim temps de desconnectar entre torns"),
        ("P", "en el almacen no hay sitio decente para descansar"),
        # -- Neutras --
        ("N", "el descanso es muy corto, acabas agotado"),
        ("N", "necesitamos mas tiempo de pausa, no llegamos"),
        ("N", "els descansos son massa curts, no puc ni seure"),
        ("N", "la pausa no da para nada, ni para ir al baño tranquilo"),
        ("N", "las pausas de antes eran mejores, ahora no llegan"),
        ("N", "la pausa del mediodia se queda corta para desconectar"),
        ("N", "necesitamos pausas mas largas para rendir bien"),
        ("N", "no tenemos tiempo real de descanso durante la jornada"),
        ("N", "el tiempo de desconexion entre tareas es insuficiente"),
        ("N", "els descansos no son suficients per recuperar energia"),
        ("N", "falta un espacio tranquilo donde poder descansar de verdad"),
    ],
    "comunicacion_cambio": [
        # -- Planta/logística --
        ("P", "nadie nos dijo nada oficial del cambio de turnos"),
        ("P", "si van a cambiar los turnos almenos q avisen bien"),
        ("P", "me cambiaron el turno sin preguntarme"),
        ("P", "falta informacion clara sobre los nuevos horarios de planta"),
        ("P", "no hi va haver cap comunicat oficial sobre els torns, molt malament"),
        ("P", "el cambio de turnos llego de un dia para otro sin explicacion"),
        ("P", "en el almacen nos enteramos por casualidad del cambio"),
        ("P", "als de nit no ens van dir res del canvi"),
        # -- Neutras --
        ("N", "nos enteramos del cambio x el grupo de wasa"),
        ("N", "me entere por un compañero, no por la empresa"),
        ("N", "la comunicacion del cambio fue pesima"),
        ("N", "ens van avisar amb molt poc temps, fatal"),
        ("N", "no hubo reunion ni correo, nos enteramos de rebote"),
        ("N", "el cambio llego de un dia para otro sin explicacion"),
        ("N", "la info llego tarde y mal, como siempre"),
        ("N", "ens haurien d'haver informat amb mes antelacio"),
        ("N", "no se comunican los cambios con tiempo suficiente"),
        ("N", "falta un canal oficial para avisar de novedades"),
        ("N", "siempre nos enteramos de los cambios por rumores"),
        ("N", "la comunicacion interna es el punto mas debil"),
    ],
    "carga_trabajo": [
        # -- Planta/logística --
        ("P", "no damos abasto en el turno de tarde"),
        ("P", "necesitamos mas personal en linea"),
        ("P", "se nota la falta de gente en los turnos rotativos"),
        ("P", "falta personal para cubrir todos los turnos"),
        ("P", "la produccion sube pero el equipo no crece"),
        ("P", "en la fabrica estamos al limite cada noche"),
        ("P", "el almacen necesita mas gente para los picos"),
        ("P", "a planta estem desbordats amb la feina"),
        # -- Neutras --
        ("N", "hay demasiado trabajo para la gente que somos"),
        ("N", "desde el cambio la carga ha subido un monton"),
        ("N", "la carga de trabajo es excesiva ultimamente"),
        ("N", "cada vez mas faena amb menys gent"),
        ("N", "la carrega de treball ha augmentat molt"),
        ("N", "hay picos de trabajo q no se pueden gestionar"),
        ("N", "estamos al limite de capacidad"),
        ("N", "no pueden pedir mas con menos gente"),
        ("N", "se necesita refuerzo en los momentos de mas volumen"),
        ("N", "el ritmo de trabajo no es sostenible asi"),
        ("N", "cada dia hay mas tareas y menos recursos"),
        ("N", "necessitem mes mans per treure la feina endavant"),
    ],
    "herramientas": [
        # -- Planta/logística --
        ("P", "las maquinas fallan mucho y nadie las arregla rapido"),
        ("P", "faltan EPIs en condiciones"),
        ("P", "las tablets del quiosco van fatal"),
        ("P", "la wifi en planta es malisima, no carga nada"),
        ("P", "hay herramientas rotas q llevan meses sin reparar"),
        ("P", "necesitamos mejor equipo para el turno de noche"),
        ("P", "el material de proteccion esta viejo"),
        ("P", "les eines de la fabrica son molt antigues"),
        ("P", "en el almacen faltan carretillas en buen estado"),
        # -- Neutras --
        ("N", "necesitamos herramientas mas modernas"),
        ("N", "el software de gestion es lentisimo"),
        ("N", "les eines que fem servir son molt antigues"),
        ("N", "el sistema se cuelga cada dos por tres"),
        ("N", "no tenemos material suficiente para trabajar bien"),
        ("N", "les eines no estan al dia, necessitem actualitzar"),
        ("N", "la plataforma interna va muy lenta y falla mucho"),
        ("N", "necesitamos herramientas digitales decentes"),
        ("N", "el portatil q tengo es muy antiguo y va fatal"),
        ("N", "el software nuevo tiene muchos bugs"),
        ("N", "falta inversion en tecnologia para el dia a dia"),
    ],
    "liderazgo": [
        # -- Planta/logística --
        ("P", "necesitamos jefes q bajen a planta mas a menudo"),
        ("P", "el encargado de noche no sabe gestionar conflictos"),
        ("P", "el responsable del almacen nunca esta cuando se le necesita"),
        # -- Neutras --
        ("N", "mi jefe no escucha las quejas del equipo"),
        ("N", "falta apoyo de los mandos intermedios"),
        ("N", "el responsable no esta cuando se le necesita"),
        ("N", "el lideratge ha de millorar molt"),
        ("N", "no hay feedback de los superiores nunca"),
        ("N", "el encargado no sabe gestionar conflictos"),
        ("N", "els caps haurien de comunicar-se millor amb nosaltres"),
        ("N", "siento q las decisiones se toman sin contar con nosotros"),
        ("N", "los mandos no se mojan cuando hay problemas"),
        ("N", "falta liderazgo de verdad, no solo ordenes"),
        ("N", "el responsable deberia preguntar mas al equipo"),
        ("N", "a mi jefe le da igual lo q le digamos"),
        ("N", "se necesita mas cercania por parte de los responsables"),
        ("N", "falta comunicacion entre jefes y equipo"),
        ("N", "las decisiones se toman arriba sin consultar"),
        ("N", "el lideratge hauria de ser mes participatiu"),
    ],
    "desarrollo": [
        # -- Planta/logística --
        ("P", "no hay formacion para las nuevas maquinas"),
        ("P", "no se promociona a nadie de planta"),
        ("P", "al magatzem no hi ha cap opcio de creixer"),
        # -- Neutras --
        ("N", "quiero crecer en la empresa pero no hay plan"),
        ("N", "no hi ha opcions de formacio aqui"),
        ("N", "llevamos meses sin hacer ningun curso"),
        ("N", "me gustaria aprender cosas nuevas pero no hay oferta"),
        ("N", "la formacion es nula, todo se aprende sobre la marcha"),
        ("N", "necessitem formacio per als nous processos"),
        ("N", "quiero mejorar pero no me dan oportunidades"),
        ("N", "falta un plan de carrera claro"),
        ("N", "la empresa no invierte en formacion del personal"),
        ("N", "no hay cursos ni nada para mejorar"),
        ("N", "el desenvolupament professional es inexistent"),
        ("N", "no existe un plan real de crecimiento interno"),
        ("N", "me gustaria tener acceso a formacion online"),
        ("N", "las oportunidades de mejora son nulas"),
        ("N", "no hi ha cap programa de mentoria ni res semblant"),
    ],
    "seguridad": [
        # -- Planta/logística --
        ("P", "hay zonas de la planta que son peligrosas"),
        ("P", "falta señalizacion en la zona de carga"),
        ("P", "el suelo esta resbaladizo y nadie lo limpia"),
        ("P", "la seguretat a la fabrica ha de millorar"),
        ("P", "he visto cables sueltos cerca de las maquinas"),
        ("P", "les sortides d'emergencia estan bloquejades a la fabrica"),
        ("P", "la iluminacion en el almacen es muy pobre"),
        ("P", "faltan EPIs nuevos en la zona de carga"),
        ("P", "el almacen tiene zonas con poca visibilidad"),
        # -- Neutras --
        ("N", "los extintores estan caducados"),
        ("N", "no hay protocolos claros de emergencia"),
        ("N", "necesitamos mas formacion en prevencion"),
        ("N", "no tenemos botiquin actualizado en la zona"),
        ("N", "falta un plan de evacuacion visible"),
        ("N", "la seguridad deberia ser prioridad uno"),
        ("N", "las visitas a cliente no tienen protocolo de seguridad"),
        ("N", "falta formacion en seguridad vial para los comerciales"),
        ("N", "no hay revision periodica de riesgos en la oficina"),
        ("N", "la silla y la pantalla no cumplen ergonomia basica"),
        ("N", "caldria revisar els protocols de seguretat de l'oficina"),
        ("N", "no se hacen simulacros de evacuacion desde hace mucho"),
    ],
    "conciliacion": [
        # -- Planta/logística --
        ("P", "con los nuevos turnos no veo a mis hijos"),
        ("P", "el turno de noche me esta destrozando la vida social"),
        ("P", "la conciliacio es molt dificil amb aquests torns"),
        ("P", "necessito canviar de torn per motius familiars"),
        ("P", "me gustaria poder elegir turno en algun momento"),
        ("P", "el horario del almacen no me permite conciliar"),
        # -- Neutras --
        ("N", "no puedo compaginar el trabajo con mi vida"),
        ("N", "el horario nuevo es imposible para conciliar"),
        ("N", "necesito mas flexibilidad para temas de familia"),
        ("N", "no llego a recoger a los niños del cole"),
        ("N", "no hay ningun tipo de flexibilidad horaria"),
        ("N", "la empresa no se preocupa de la conciliacion"),
        ("N", "amb el nou horari no puc portar els nens a escola"),
        ("N", "necesito q me tengan en cuenta para conciliar"),
        ("N", "no existe opcion de teletrabajo ni flexibilidad"),
        ("N", "la jornada no permite compaginar con la vida personal"),
        ("N", "falta flexibilidad real, no solo de palabra"),
        ("N", "el horari no es compatible amb la meva vida familiar"),
        ("N", "necesitamos mas opciones para la conciliacion"),
    ],
}

# Datos ficticios para probar anonimización (nombres inventados, correos y
# teléfonos falsos; NO son datos reales).
DATOS_FICTICIOS_PLANTA = [
    "preguntale a Manolo q el lo sabe bien",
    "mi compañera Pepa dice q esto no puede seguir asi",
    "llama al 612 345 678 q te lo explican",
    "Carlos del turno de noche tb lo dice",
    "habla con Jordi q lleva 20 anios aqui",
    "q se lo digan a la Maria del almacen",
]
DATOS_FICTICIOS_NEUTROS = [
    "yo soy Lucia y estoy harta de esto",
    "escribe a prueba@example.com y te lo confirmo",
    "el correo es demo@example.com por si quieres quejas",
    "contacta al 698 123 456 y pregunta por Pedro",
    "habla con Elena q ella te lo confirma",
    "pregunta a Raul del equipo, el te lo cuenta",
]

# ---------------------------------------------------------------------------
# MULETILLAS Y CIERRES (variedad)
# ---------------------------------------------------------------------------

MULETILLAS = [
    "la verdad", "pues", "sinceramente", "bueno", "doncs", "la veritat",
    "mira", "oye", "jo", "vamos", "es que", "home",
]
CIERRES = [
    "a ver si se arregla", "estamos cansados", "esto no puede seguir así",
    "a veure si millora", "ya está bien", "no sé qué más decir",
    "esperemos que cambien algo", "ojala mejore pronto",
    "a veure que fan", "en fin",
]

# ---------------------------------------------------------------------------
# ABREVIATURAS Y RUIDO
# ---------------------------------------------------------------------------

ABREVIATURAS = {
    "que": "q", "porque": "xq", "también": "tb",
    "por": "x", "para": "pa", "muy": "mu", "bueno": "bno",
    "nada": "na", "todos": "tos",
}
# Compilar patrones con word boundaries para no romper palabras parciales
_ABREV_PATTERNS = {
    re.compile(r"\b" + re.escape(larga) + r"\b", re.IGNORECASE): corta
    for larga, corta in ABREVIATURAS.items()
}

EMOJIS = ["😤", "😞", "🤦", "💪", "👎", "😡", "🙄", "😩", "🤷", "👀"]


def quitar_tildes(texto):
    """Elimina tildes manteniendo la ñ y la ç."""
    resultado = []
    for c in texto:
        if c in ("ñ", "Ñ", "ç", "Ç"):
            resultado.append(c)
        else:
            nfkd = unicodedata.normalize("NFKD", c)
            resultado.append("".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn"))
    return "".join(resultado)


def aplicar_ruido(texto, rng):
    """Aplica ruido casual al texto: quita tildes, abreviaturas, etc."""
    t = texto.lower()
    if rng.random() < 0.7:
        t = quitar_tildes(t)
    # Abreviaturas con word boundaries
    for patron, corta in _ABREV_PATTERNS.items():
        if patron.search(t) and rng.random() < 0.4:
            t = patron.sub(corta, t, count=1)
    # Quitar puntuación final
    t = t.rstrip(".,;:!?")
    # Duplicar alguna letra
    if rng.random() < 0.15 and len(t) > 10:
        pos = rng.randint(3, len(t) - 2)
        t = t[:pos] + t[pos] + t[pos:]
    # Emoji al final
    if rng.random() < 0.12:
        t = t + " " + rng.choice(EMOJIS)
    return t


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

def cargar_encuesta():
    with open(ENCUESTA_PATH, encoding="utf-8") as f:
        return json.load(f)


def obtener_tasa(colectivo, turno):
    """Obtiene la tasa de respuesta para un segmento (colectivo, turno).
    Devuelve (tasa, es_defecto, descripcion_motivo)."""
    if (colectivo, turno) in TASAS:
        return TASAS[(colectivo, turno)], False, ""

    tasas_colectivo = [t for (c, _), t in TASAS.items() if c == colectivo]
    if tasas_colectivo:
        media = sum(tasas_colectivo) / len(tasas_colectivo)
        return media, True, f"media de {colectivo} ({media:.3f})"

    return 0.15, True, "tasa por defecto 0.15 (colectivo no en TASAS)"


def cargar_plantilla():
    """Usa SIEMPRE contenido/plantilla.json si existe y es JSON válido.
    Para cada segmento (colectivo, turno), usa su tasa de TASAS; si no está,
    usa la media de las tasas de ese colectivo en TASAS; si el colectivo tampoco
    está, 0.15. Imprime qué segmentos usan tasa por defecto.
    Solo usa PLANTILLA_DEFAULT si el fichero no existe o no es válido."""
    if os.path.exists(PLANTILLA_PATH):
        try:
            with open(PLANTILLA_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                print(f"  Plantilla: {PLANTILLA_PATH}")
                segmentos = []
                por_defecto = []
                for item in data:
                    c = quitar_tildes(str(item["colectivo"]).strip().lower())
                    t = quitar_tildes(str(item["turno"]).strip().lower())
                    p = int(item["personas"])
                    if c not in COLECTIVOS or t not in TURNOS or p <= 0:
                        print(f"    ! Segmento ignorado (valor no válido): {item}")
                        continue
                    if c in COLECTIVOS_OFICINA and t != "sin_turno":
                        print(f"    ! {c}/{t}: {c} siempre es sin_turno, se corrige")
                        t = "sin_turno"
                    tasa, es_def, desc = obtener_tasa(c, t)
                    segmentos.append((c, t, p, tasa))
                    if es_def:
                        por_defecto.append((c, t, tasa, desc))
                if por_defecto:
                    print("  Segmentos con tasa por defecto:")
                    for c, t, tasa, desc in por_defecto:
                        print(f"    - {c}/{t}: {tasa:.3f} ({desc})")
                if segmentos:
                    return segmentos
                print("  Plantilla sin segmentos válidos. Se usa PLANTILLA_DEFAULT.")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"  Plantilla: {PLANTILLA_PATH} no es válida ({e}). Se usa PLANTILLA_DEFAULT.")
    else:
        print(f"  Plantilla: {PLANTILLA_PATH} no existe. Se usa PLANTILLA_DEFAULT.")

    segmentos = []
    for c, t, p in PLANTILLA_DEFAULT:
        tasa, _, _ = obtener_tasa(c, t)
        segmentos.append((c, t, p, tasa))
    return segmentos


def dias_laborables(anio, mes, dia_max=None):
    """Devuelve una lista de fechas laborables (lun-vie) del mes.
    Si dia_max se indica, solo hasta ese día (inclusive)."""
    dias = []
    _, n_dias = calendar.monthrange(anio, mes)
    tope = min(n_dias, dia_max) if dia_max else n_dias
    for d in range(1, tope + 1):
        wd = calendar.weekday(anio, mes, d)
        if wd < 5:  # lunes=0 .. viernes=4
            dias.append(f"{anio}-{mes:02d}-{d:02d}")
    return dias


def elegir_canal(colectivo, rng):
    probs = CANAL_PROBS[colectivo]
    r = rng.random()
    acum = 0.0
    for canal, p in probs:
        acum += p
        if r <= acum:
            return canal
    return probs[-1][0]


def normalizar_probs(d):
    """Normaliza un dict de probabilidades para que sume 1."""
    total = sum(d.values())
    if total == 0:
        n = len(d)
        return {k: 1.0 / n for k in d}
    return {k: v / total for k, v in d.items()}


def elegir_tema(periodo, colectivo, turno, rng):
    """Elige un tema_real con las probabilidades ajustadas por segmento."""
    probs = dict(TEMAS_PROB[periodo])

    # En 2026-11, "descansos" se concentra en planta/noche y planta/tarde
    if periodo == "2026-11" and colectivo == "planta" and turno in ("noche", "tarde"):
        probs["descansos"] *= 2.0

    # "seguridad" casi solo en planta y logistica (en ambos periodos)
    if colectivo not in ("planta", "logistica"):
        probs["seguridad"] *= 0.1

    probs = normalizar_probs(probs)
    r = rng.random()
    acum = 0.0
    for tema in TEMAS:
        acum += probs.get(tema, 0)
        if r <= acum:
            return tema
    return TEMAS[-1]


def generar_nota(media_base, tema, colectivo, turno, periodo, rng):
    """Genera una nota de escala 1-5 con sesgo por tema/segmento."""
    mu = media_base
    if tema in ("descansos", "carga_trabajo"):
        mu -= 0.8
    if colectivo == "planta" and turno == "noche" and periodo == "2026-11":
        mu -= 0.5
    # Generar con distribución normal discreta, truncada a 1-5
    valor = rng.gauss(mu, 1.0)
    valor = max(1, min(5, round(valor)))
    return valor


def generar_valores(encuesta, tema, colectivo, turno, periodo, rng):
    """Genera el dict de valores según las preguntas de la encuesta."""
    media_base = MEDIA_BASE[colectivo]
    preguntas = encuesta["preguntas"]
    valores = {}

    for p in preguntas:
        pid = p["id"]
        tipo = p["tipo"]

        # Omitir la pregunta de texto (va en "comentario")
        if tipo == "texto":
            continue

        # Evaluar condición
        if p["condicion"] is not None:
            ref = p["condicion"]["pregunta"]
            vmax = p["condicion"]["valor_max"]
            ref_val = valores.get(ref)
            if ref_val is None or ref_val > vmax:
                continue

        if tipo == "escala_1_5":
            valores[pid] = generar_nota(media_base, tema, colectivo, turno, periodo, rng)
        elif tipo == "opcion":
            opciones = p["opciones"]
            # Sesgar la opción según el tema
            pesos = [1.0] * len(opciones)
            for i, op in enumerate(opciones):
                op_lower = op.lower()
                if tema == "descansos" and "descanso" in op_lower:
                    pesos[i] = 4.0
                elif tema == "comunicacion_cambio" and "comunicaci" in op_lower:
                    pesos[i] = 4.0
                elif tema == "conciliacion" and "conciliaci" in op_lower:
                    pesos[i] = 4.0
                elif "nada" in op_lower or "especial" in op_lower:
                    if tema in ("descansos", "comunicacion_cambio", "carga_trabajo"):
                        pesos[i] = 0.3
            total_w = sum(pesos)
            pesos = [w / total_w for w in pesos]
            r = rng.random()
            acum = 0.0
            for i, w in enumerate(pesos):
                acum += w
                if r <= acum:
                    valores[pid] = opciones[i]
                    break
            else:
                valores[pid] = opciones[-1]
        elif tipo == "si_no":
            # Sesgar: si comunicacion_cambio, más probable "no"
            prob_si = 0.5
            if tema == "comunicacion_cambio":
                prob_si = 0.2
            elif tema in ("descansos", "carga_trabajo"):
                prob_si = 0.35
            valores[pid] = "si" if rng.random() < prob_si else "no"

    return valores


def _filtrar_frases(banco_tema, colectivo):
    """Devuelve solo las frases del banco válidas para el colectivo."""
    if colectivo in COLECTIVOS_PLANTA:
        return [texto for _, texto in banco_tema]
    else:
        return [texto for marca, texto in banco_tema if marca == "N"]


def generar_comentario(tema, colectivo, rng, usar_dato_ficticio=False):
    """Genera un comentario para el tema dado, filtrado por colectivo."""
    frases = _filtrar_frases(COMENTARIOS[tema], colectivo)
    comentario = rng.choice(frases)

    # 10 % mezcla con otro tema (filtrada por colectivo también)
    if rng.random() < 0.10:
        otro_tema = rng.choice([t for t in TEMAS if t != tema])
        frases_extra = _filtrar_frases(COMENTARIOS[otro_tema], colectivo)
        frase_extra = rng.choice(frases_extra)
        comentario = comentario + ", y " + frase_extra

    # Dato ficticio para probar anonimización
    if usar_dato_ficticio:
        if colectivo in COLECTIVOS_PLANTA:
            dato = rng.choice(DATOS_FICTICIOS_PLANTA + DATOS_FICTICIOS_NEUTROS)
        else:
            dato = rng.choice(DATOS_FICTICIOS_NEUTROS)
        comentario = comentario + ". " + dato

    # 30 % muletilla al inicio o cierre al final
    if rng.random() < 0.30:
        if rng.random() < 0.5:
            muletilla = rng.choice(MULETILLAS)
            comentario = muletilla + ", " + comentario
        else:
            cierre = rng.choice(CIERRES)
            comentario = comentario + ", " + cierre

    # Ruido al 60 %
    if rng.random() < 0.60:
        comentario = aplicar_ruido(comentario, rng)

    return comentario


# ---------------------------------------------------------------------------
# GENERACIÓN PRINCIPAL
# ---------------------------------------------------------------------------

TENDENCIAS_ESPERADAS = {
    "descansos": "SUBE", "comunicacion_cambio": "NUEVO", "herramientas": "BAJA",
}


def calcular_tendencias(respuestas):
    """Tendencia por tema (proporción sobre el total del periodo).
    NUEVO si oct < 3 y nov >= 5; SUBE si ratio >= 1.5; BAJA si <= 0.6."""
    cont = {}
    for r in respuestas:
        cont[(r["periodo"], r["tema_real"])] = cont.get((r["periodo"], r["tema_real"]), 0) + 1
    total_oct = sum(cont.get(("2026-10", t), 0) for t in TEMAS)
    total_nov = sum(cont.get(("2026-11", t), 0) for t in TEMAS)
    res = {}
    for tema in TEMAS:
        n_oct = cont.get(("2026-10", tema), 0)
        n_nov = cont.get(("2026-11", tema), 0)
        p_oct = n_oct / total_oct if total_oct else 0.0
        p_nov = n_nov / total_nov if total_nov else 0.0
        if n_oct < 3 and n_nov >= 5:
            tend = "NUEVO"
        elif p_oct > 0:
            ratio = p_nov / p_oct
            tend = "SUBE" if ratio >= 1.5 else "BAJA" if ratio <= 0.6 else "ESTABLE"
        else:
            tend = "SUBE" if p_nov > 0 else "ESTABLE"
        res[tema] = (n_oct, n_nov, tend)
    return res


def tendencias_ok(respuestas):
    """True si salen exactamente las tendencias del demo y el resto ESTABLE."""
    for tema, (_, _, tend) in calcular_tendencias(respuestas).items():
        if tend != TENDENCIAS_ESPERADAS.get(tema, "ESTABLE"):
            return False
    return True


def generar(seed=42, salida=None, guardar=True, verbose=True):
    rng = random.Random(seed)

    if salida is None:
        salida = os.path.join(SCRIPT_DIR, "respuestas.json")

    encuesta = cargar_encuesta()
    if verbose:
        plantilla = cargar_plantilla()
    else:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            plantilla = cargar_plantilla()

    # Generar IDs únicos
    ids_usados = set()

    def nuevo_id():
        while True:
            n = rng.randint(0, 99999)
            rid = f"r_{n:05d}"
            if rid not in ids_usados:
                ids_usados.add(rid)
                return rid

    # Precalcular días laborables
    # Noviembre: solo días laborables del 2 al 6 (demo el 8)
    dias_lab = {
        "2026-10": dias_laborables(2026, 10),
        "2026-11": dias_laborables(2026, 11, dia_max=6),
    }

    respuestas = []
    resumen_segmentos = {}  # (periodo, colectivo, turno) -> count
    resumen_temas = {}      # (periodo, tema) -> count
    comentarios_ficticios = 0
    indices_ficticios = []

    for periodo in PERIODOS:
        for colectivo, turno, personas, tasa in plantilla:
            n_base = round(personas * tasa)
            # Pequeña variación aleatoria (±12 %)
            variacion = rng.uniform(-0.12, 0.12)
            n_resp = max(1, round(n_base * (1 + variacion)))

            clave_seg = (periodo, colectivo, turno)
            resumen_segmentos[clave_seg] = {
                "respuestas": n_resp,
                "personas": personas,
                "tasa_real": n_resp / personas if personas > 0 else 0,
            }

            dias = dias_lab[periodo]

            for _ in range(n_resp):
                tema = elegir_tema(periodo, colectivo, turno, rng)
                valores = generar_valores(
                    encuesta, tema, colectivo, turno, periodo, rng
                )
                canal = elegir_canal(colectivo, rng)
                fecha = rng.choice(dias)

                # Comentario: 15 % vacío
                usar_ficticio = False
                if rng.random() < 0.15:
                    comentario = ""
                else:
                    # 3 % con datos ficticios
                    usar_ficticio = rng.random() < 0.035
                    comentario = generar_comentario(
                        tema, colectivo, rng, usar_dato_ficticio=usar_ficticio
                    )

                resp = {
                    "id": nuevo_id(),
                    "encuesta_id": encuesta["id"],
                    "fecha": fecha,
                    "periodo": periodo,
                    "colectivo": colectivo,
                    "centro_tipo": CENTRO_MAP[colectivo],
                    "turno": turno,
                    "canal": canal,
                    "valores": valores,
                    "comentario": comentario,
                    "tema_real": tema,
                }
                respuestas.append(resp)

                if usar_ficticio:
                    comentarios_ficticios += 1
                    indices_ficticios.append(len(respuestas) - 1)

                # Resumen de temas
                clave_tema = (periodo, tema)
                resumen_temas[clave_tema] = resumen_temas.get(clave_tema, 0) + 1

    if not guardar:
        return respuestas

    # Guardar JSON
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(respuestas, f, ensure_ascii=False, indent=2)

    # ---------------------------------------------------------------------------
    # RESUMEN POR CONSOLA
    # ---------------------------------------------------------------------------

    print(f"\n{'='*70}")
    print(f"  GENERADOR DE DATOS SINTÉTICOS — Resumen")
    print(f"{'='*70}")
    print(f"\n  Total de respuestas: {len(respuestas)}")
    print(f"  Semilla: {seed}")
    print(f"  Fichero: {salida}\n")

    print(f"  {'Periodo':<10} {'Colectivo':<12} {'Turno':<10} {'Resp':>5} {'Pers':>5} {'Tasa':>7}")
    print(f"  {'-'*55}")
    for (periodo, colectivo, turno), info in sorted(resumen_segmentos.items()):
        print(f"  {periodo:<10} {colectivo:<12} {turno:<10} {info['respuestas']:>5} "
              f"{info['personas']:>5} {info['tasa_real']:>6.1%}")

    print(f"\n  {'Periodo':<10} {'Tema':<24} {'N':>5}")
    print(f"  {'-'*42}")
    for (periodo, tema), n in sorted(resumen_temas.items()):
        print(f"  {periodo:<10} {tema:<24} {n:>5}")

    # Tendencias basadas en proporciones sobre el total del periodo
    print(f"\n  Tendencias (2026-10 vs 2026-11):")
    for tema, (n_oct, n_nov, tend) in calcular_tendencias(respuestas).items():
        marca = "" if tend == TENDENCIAS_ESPERADAS.get(tema, "ESTABLE") else "   <-- no esperada"
        print(f"    {tema:<24} oct={n_oct:>3}  nov={n_nov:>3}  -> {tend}{marca}")

    # Comentarios únicos
    comentarios_no_vacios = [r["comentario"] for r in respuestas if r["comentario"]]
    unicos = len(set(comentarios_no_vacios))
    print(f"\n  Comentarios no vacíos: {len(comentarios_no_vacios)}")
    print(f"  Comentarios únicos:   {unicos}")

    print(f"\n  Comentarios con datos ficticios (para probar anonimización): "
          f"{comentarios_ficticios}")
    if indices_ficticios:
        print(f"    IDs: {', '.join(respuestas[i]['id'] for i in indices_ficticios)}")

    # Verificación de fechas nov
    fechas_nov = [r["fecha"] for r in respuestas if r["periodo"] == "2026-11"]
    fecha_max_nov = max(fechas_nov) if fechas_nov else "N/A"
    print(f"\n  Fecha máxima en noviembre: {fecha_max_nov}")

    print(f"\n{'='*70}\n")

    return respuestas


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera respuestas sintéticas.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Semilla fija. Si no se indica, busca desde 42 la primera "
                             "semilla cuyas tendencias encajan con el demo.")
    parser.add_argument("--salida", type=str, default=None,
                        help="Ruta del JSON de salida (default: datos_sinteticos/respuestas.json)")
    args = parser.parse_args()
    if args.seed is not None:
        generar(seed=args.seed, salida=args.salida)
    else:
        for semilla in range(42, 42 + 200):
            if tendencias_ok(generar(seed=semilla, guardar=False, verbose=False)):
                print(f"  Semilla elegida automáticamente: {semilla}")
                generar(seed=semilla, salida=args.salida)
                break
        else:
            print("  Ninguna semilla da las tendencias esperadas; se usa 42.")
            generar(seed=42, salida=args.salida)
