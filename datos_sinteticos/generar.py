#!/usr/bin/env python3
"""Generador de respuestas sintéticas para la encuesta de clima laboral.

Uso:
    python datos_sinteticos/generar.py [--seed 42] [--salida datos_sinteticos/respuestas.json]

Solo librería estándar. Datos 100 % ficticios.
"""

import argparse
import calendar
import json
import math
import os
import random
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
        "descansos": 0.25, "comunicacion_cambio": 0.15, "carga_trabajo": 0.16,
        "herramientas": 0.06, "liderazgo": 0.12, "desarrollo": 0.10,
        "seguridad": 0.07, "conciliacion": 0.09,
    },
}

# ---------------------------------------------------------------------------
# BANCO DE COMENTARIOS POR TEMA (>=12 por tema, ~20% en catalán)
# ---------------------------------------------------------------------------

COMENTARIOS = {
    "descansos": [
        "entre turno y turno no da tiempo ni a comer bien",
        "el descanso es muy corto, acabas agotado",
        "necesitamos mas tiempo de pausa, no llegamos",
        "yo pido q amplien el descanso de noche, es inhumano",
        "els descansos son massa curts, no puc ni seure",
        "no hay ni 10 min para tomar algo entre turnos",
        "la pausa no da para nada, ni para ir al baño tranquilo",
        "hace falta un descanso mas largo x la noche",
        "descansem molt poc entre torn i torn",
        "si empalmas dos noches seguidas se nota mucho la falta de descanso",
        "las pausas de antes eran mejores, ahora no llegan",
        "el descanso de 15 min es una broma con 8h de turno",
        "amb el nou sistema no tenim temps de desconnectar",
    ],
    "comunicacion_cambio": [
        "nos enteramos del cambio x el grupo de wasa",
        "nadie nos dijo nada oficial del cambio de turnos",
        "me entere por un compañero, no por la empresa",
        "la comunicacion del cambio fue pesima",
        "ens van avisar amb molt poc temps, fatal",
        "no hubo reunion ni correo, nos enteramos de rebote",
        "si van a cambiar los turnos almenos q avisen bien",
        "el cambio llego de un dia para otro sin explicacion",
        "no hi va haver cap comunicat oficial, molt malament",
        "falta informacion clara sobre los nuevos horarios",
        "me cambiaron el turno sin preguntarme",
        "la info llego tarde y mal, como siempre",
        "ens haurien d'haver informat amb mes antelacio",
    ],
    "carga_trabajo": [
        "hay demasiado trabajo para la gente que somos",
        "desde el cambio la carga ha subido un monton",
        "no damos abasto en el turno de tarde",
        "la carga de trabajo es excesiva ultimamente",
        "cada vez mas faena amb menys gent",
        "necesitamos mas personal en linea",
        "se nota la falta de gente en los turnos rotativos",
        "la carrega de treball ha augmentat molt",
        "hay picos de trabajo q no se pueden gestionar",
        "estamos al limite de capacidad",
        "falta personal para cubrir todos los turnos",
        "no pueden pedir mas con menos gente",
        "la produccion sube pero el equipo no crece",
    ],
    "herramientas": [
        "las maquinas fallan mucho y nadie las arregla rapido",
        "necesitamos herramientas mas modernas",
        "el software de gestion es lentisimo",
        "les eines que fem servir son molt antigues",
        "faltan EPIs en condiciones",
        "las tablets del quiosco van fatal",
        "el sistema se cuelga cada dos por tres",
        "no tenemos material suficiente para trabajar bien",
        "les eines no estan al dia, necessitem actualitzar",
        "la wifi en planta es malisima, no carga nada",
        "hay herramientas rotas q llevan meses sin reparar",
        "necesitamos mejor equipo para el turno de noche",
        "el material de proteccion esta viejo",
    ],
    "liderazgo": [
        "mi jefe no escucha las quejas del equipo",
        "falta apoyo de los mandos intermedios",
        "el responsable no esta cuando se le necesita",
        "el lideratge ha de millorar molt",
        "necesitamos jefes q bajen a planta mas a menudo",
        "no hay feedback de los superiores nunca",
        "el encargado no sabe gestionar conflictos",
        "els caps haurien de comunicar-se millor amb nosaltres",
        "siento q las decisiones se toman sin contar con nosotros",
        "los mandos no se mojan cuando hay problemas",
        "falta liderazgo de verdad, no solo ordenes",
        "el responsable deberia preguntar mas al equipo",
        "a mi jefe le da igual lo q le digamos",
    ],
    "desarrollo": [
        "no hay formacion para las nuevas maquinas",
        "quiero crecer en la empresa pero no hay plan",
        "no hi ha opcions de formacio aqui",
        "llevamos meses sin hacer ningun curso",
        "me gustaria aprender cosas nuevas pero no hay oferta",
        "la formacion es nula, todo se aprende sobre la marcha",
        "necessitem formacio per als nous processos",
        "no se promociona a nadie de planta",
        "quiero mejorar pero no me dan oportunidades",
        "falta un plan de carrera claro",
        "la empresa no invierte en formacion del personal",
        "no hay cursos ni nada para mejorar",
        "el desenvolupament professional es inexistent",
    ],
    "seguridad": [
        "hay zonas de la planta que son peligrosas",
        "falta señalizacion en la zona de carga",
        "el suelo esta resbaladizo y nadie lo limpia",
        "la seguretat a la fabrica ha de millorar",
        "los extintores estan caducados",
        "no hay protocolos claros de emergencia",
        "he visto cables sueltos cerca de las maquinas",
        "necesitamos mas formacion en prevencion",
        "les sortides d'emergencia estan bloquejades",
        "la iluminacion en el almacen es muy pobre",
        "no tenemos botiquin actualizado en la zona",
        "falta un plan de evacuacion visible",
        "la seguridad deberia ser prioridad uno",
    ],
    "conciliacion": [
        "con los nuevos turnos no veo a mis hijos",
        "no puedo compaginar el trabajo con mi vida",
        "el horario nuevo es imposible para conciliar",
        "la conciliacio es molt dificil amb aquests torns",
        "necesito mas flexibilidad para temas de familia",
        "no llego a recoger a los niños del cole",
        "el turno de noche me esta destrozando la vida social",
        "necessito canviar de torn per motius familiars",
        "me gustaria poder elegir turno en algun momento",
        "no hay ningun tipo de flexibilidad horaria",
        "la empresa no se preocupa de la conciliacion",
        "amb el nou horari no puc portar els nens a escola",
        "necesito q me tengan en cuenta para conciliar",
    ],
}

# Datos ficticios para probar anonimización (nombres inventados, correos y
# teléfonos falsos; NO son datos reales).
DATOS_FICTICIOS = [
    "preguntale a Manolo q el lo sabe bien",
    "yo soy Lucia y estoy harta de este turno",
    "mi compañera Pepa dice q esto no puede seguir asi",
    "escribe a prueba@example.com y te lo confirmo",
    "llama al 612 345 678 q te lo explican",
    "Carlos del turno de noche tb lo dice",
    "habla con Jordi q lleva 20 anios aqui",
    "q se lo digan a la Maria del almacen",
    "el correo es demo@example.com por si quieres quejas",
    "contacta al 698 123 456 y pregunta por Pedro",
]

# ---------------------------------------------------------------------------
# ABREVIATURAS Y RUIDO
# ---------------------------------------------------------------------------

ABREVIATURAS = {
    "que": "q", "porque": "xq", "por que": "xq", "también": "tb",
    "por": "x", "para": "pa", "muy": "mu", "bueno": "bno",
    "nada": "na", "todos": "tos",
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
    # Abreviaturas
    for larga, corta in ABREVIATURAS.items():
        if larga in t and rng.random() < 0.4:
            t = t.replace(larga, corta, 1)
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


def cargar_plantilla():
    """Carga la plantilla si existe y cubre todos los segmentos de TASAS; si no,
    usa la plantilla por defecto del enunciado (9 segmentos, ~1430 personas)."""
    if os.path.exists(PLANTILLA_PATH):
        try:
            with open(PLANTILLA_PATH, encoding="utf-8") as f:
                data = json.load(f)
            segmentos = []
            for item in data:
                c = item["colectivo"]
                t = item["turno"]
                p = item["personas"]
                if (c, t) in TASAS:
                    segmentos.append((c, t, p))
            # Solo la usamos si cubre TODOS los segmentos definidos en TASAS
            if len(segmentos) == len(TASAS):
                return segmentos
        except (json.JSONDecodeError, KeyError):
            pass
    return list(PLANTILLA_DEFAULT)


def dias_laborables(anio, mes):
    """Devuelve una lista de fechas laborables (lun-vie) del mes."""
    dias = []
    _, n_dias = calendar.monthrange(anio, mes)
    for d in range(1, n_dias + 1):
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

    # "seguridad" casi solo en planta y logistica
    if periodo == "2026-11" and colectivo not in ("planta", "logistica"):
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


def generar_comentario(tema, rng, usar_dato_ficticio=False):
    """Genera un comentario para el tema dado."""
    banco = COMENTARIOS[tema]
    comentario = rng.choice(banco)

    # 10 % mezcla con otro tema
    if rng.random() < 0.10:
        otro_tema = rng.choice([t for t in TEMAS if t != tema])
        frase_extra = rng.choice(COMENTARIOS[otro_tema])
        comentario = comentario + ", y " + frase_extra

    # Dato ficticio para probar anonimización
    if usar_dato_ficticio:
        dato = rng.choice(DATOS_FICTICIOS)
        comentario = comentario + ". " + dato

    # Ruido al 60 %
    if rng.random() < 0.60:
        comentario = aplicar_ruido(comentario, rng)

    return comentario


# ---------------------------------------------------------------------------
# GENERACIÓN PRINCIPAL
# ---------------------------------------------------------------------------

def generar(seed=42, salida=None):
    rng = random.Random(seed)

    if salida is None:
        salida = os.path.join(SCRIPT_DIR, "respuestas.json")

    encuesta = cargar_encuesta()
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
    dias_lab = {
        "2026-10": dias_laborables(2026, 10),
        "2026-11": dias_laborables(2026, 11),
    }

    respuestas = []
    resumen_segmentos = {}  # (periodo, colectivo, turno) -> count
    resumen_temas = {}      # (periodo, tema) -> count
    comentarios_ficticios = 0
    indices_ficticios = []

    for periodo in PERIODOS:
        for colectivo, turno, personas in plantilla:
            tasa = TASAS.get((colectivo, turno), 0.10)
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
                    usar_ficticio = rng.random() < 0.035  # ligeramente > 3% para compensar el 15% vacío
                    comentario = generar_comentario(tema, rng, usar_dato_ficticio=usar_ficticio)

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

    # Tendencias
    print(f"\n  Tendencias (2026-10 vs 2026-11):")
    for tema in TEMAS:
        n_oct = resumen_temas.get(("2026-10", tema), 0)
        n_nov = resumen_temas.get(("2026-11", tema), 0)
        if n_oct == 0 and n_nov > 0:
            tend = "NUEVO"
        elif n_nov > n_oct * 1.15:
            tend = "SUBE"
        elif n_nov < n_oct * 0.85:
            tend = "BAJA"
        else:
            tend = "ESTABLE"
        print(f"    {tema:<24} oct={n_oct:>3}  nov={n_nov:>3}  -> {tend}")

    print(f"\n  Comentarios con datos ficticios (para probar anonimización): "
          f"{comentarios_ficticios}")
    if indices_ficticios:
        print(f"    IDs: {', '.join(respuestas[i]['id'] for i in indices_ficticios)}")

    print(f"\n{'='*70}\n")

    return respuestas


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera respuestas sintéticas.")
    parser.add_argument("--seed", type=int, default=42, help="Semilla (default: 42)")
    parser.add_argument("--salida", type=str, default=None,
                        help="Ruta del JSON de salida (default: datos_sinteticos/respuestas.json)")
    args = parser.parse_args()
    generar(seed=args.seed, salida=args.salida)
