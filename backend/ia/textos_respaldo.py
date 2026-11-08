"""Textos de respaldo de la IA en castellano, catalán e inglés.

Se usan cuando no hay modelo o ha fallado. Los nombres de sectores, turnos, temas y dimensiones
salen de backend/textos.py o de frontend/i18n, para que frontend y backend digan lo mismo.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

IDIOMAS = ["es", "ca", "en"]
NOMBRE_IDIOMA = {"es": "castellano", "ca": "catalán", "en": "inglés"}
_I18N = Path(__file__).resolve().parents[2] / "frontend" / "i18n"

# Por si un nombre aún no está en frontend/i18n
_NOMBRES = {
    "es": {
        "colectivo": {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                      "oficina": "oficina", "manager": "managers"},
        "turno": {"manana": "mañana", "tarde": "tarde", "noche": "noche", "sin_turno": ""},
        "tema": {"descansos": "descansos", "turnos": "turnos", "carga_trabajo": "carga de trabajo",
                 "comunicacion": "comunicación", "liderazgo": "liderazgo",
                 "herramientas": "herramientas", "formacion": "formación",
                 "reconocimiento": "reconocimiento", "seguridad": "seguridad",
                 "ambiente": "ambiente", "conciliacion": "conciliación", "otros": "otros temas"},
    },
    "ca": {
        "colectivo": {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                      "oficina": "oficina", "manager": "managers"},
        "turno": {"manana": "matí", "tarde": "tarda", "noche": "nit", "sin_turno": ""},
        "tema": {"descansos": "descansos", "turnos": "torns", "carga_trabajo": "càrrega de treball",
                 "comunicacion": "comunicació", "liderazgo": "lideratge",
                 "herramientas": "eines", "formacion": "formació",
                 "reconocimiento": "reconeixement", "seguridad": "seguretat",
                 "ambiente": "ambient", "conciliacion": "conciliació", "otros": "altres temes"},
    },
    "en": {
        "colectivo": {"planta": "production", "logistica": "logistics", "comercial": "sales",
                      "oficina": "office", "manager": "managers"},
        "turno": {"manana": "morning", "tarde": "afternoon", "noche": "night", "sin_turno": ""},
        "tema": {"descansos": "breaks", "turnos": "shifts", "carga_trabajo": "workload",
                 "comunicacion": "communication", "liderazgo": "leadership",
                 "herramientas": "tools", "formacion": "training",
                 "reconocimiento": "recognition", "seguridad": "safety",
                 "ambiente": "team climate", "conciliacion": "work-life balance",
                 "otros": "other topics"},
    },
}


def idioma_valido(idioma: str | None) -> str:
    """El idioma pedido si es es, ca o en; si no, es."""
    return idioma if idioma in IDIOMAS else "es"


@lru_cache(maxsize=None)
def _i18n(idioma: str) -> dict:
    ruta = _I18N / f"{idioma}.json"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except (OSError, ValueError):
        return {}


def nombre(tipo: str, codigo: str, idioma: str = "es") -> str:
    """Nombre de un sector, turno, tema o dimensión, en minúscula para ir dentro de una frase.

    Orden: backend/textos.py (UPC 2) → frontend/i18n/<idioma>.json → tabla de este archivo.
    """
    idioma = idioma_valido(idioma)
    if not codigo:
        return ""
    valor = None
    try:
        from backend.textos import nombre as nombre_comun
        valor = nombre_comun(tipo, codigo, idioma)
    except Exception:
        valor = None
    if not isinstance(valor, str) or not valor.strip() or valor == codigo:
        valor = _i18n(idioma).get(f"{tipo}.{codigo}")
    if not isinstance(valor, str) or not valor.strip():
        valor = _NOMBRES[idioma].get(tipo, {}).get(codigo, codigo)
    return valor.strip().lower()


def instruccion_idioma(idioma: str) -> str:
    """Frase final de los prompts que redactan para RRHH."""
    return (f"\n\nEscribe TODOS los textos en {NOMBRE_IDIOMA[idioma_valido(idioma)]}, "
            "aunque los datos estén en otro idioma.")


def pct(valor: float | None, idioma: str = "es") -> str:
    if valor is None:
        return "—"
    numero = f"{valor * 100:.0f}"
    return f"{numero}%" if idioma == "en" else f"{numero} %"


# ---- Resúmenes de temas ----
DESCRIPCION_TEMA = {
    "es": {
        "descansos": "las pausas y el tiempo para descansar o desconectar",
        "turnos": "la organización de los turnos y los cambios de horario",
        "carga_trabajo": "el volumen de trabajo y la falta de personal",
        "comunicacion": "cómo y cuándo llega la información sobre los cambios",
        "liderazgo": "la relación con los responsables y la toma de decisiones",
        "herramientas": "el estado de las herramientas, los equipos y el software",
        "formacion": "las oportunidades de formación y de crecimiento",
        "reconocimiento": "el reconocimiento del esfuerzo y del trabajo bien hecho",
        "seguridad": "la seguridad y la prevención de riesgos",
        "ambiente": "el ambiente y la relación entre compañeros",
        "conciliacion": "la conciliación con la vida personal y familiar",
        "otros": "cuestiones variadas (instalaciones, servicios y otros)",
    },
    "ca": {
        "descansos": "les pauses i el temps per descansar o desconnectar",
        "turnos": "l'organització dels torns i els canvis d'horari",
        "carga_trabajo": "el volum de feina i la manca de personal",
        "comunicacion": "com i quan arriba la informació sobre els canvis",
        "liderazgo": "la relació amb els responsables i la presa de decisions",
        "herramientas": "l'estat de les eines, els equips i el programari",
        "formacion": "les oportunitats de formació i de creixement",
        "reconocimiento": "el reconeixement de l'esforç i de la feina ben feta",
        "seguridad": "la seguretat i la prevenció de riscos",
        "ambiente": "l'ambient i la relació entre companys",
        "conciliacion": "la conciliació amb la vida personal i familiar",
        "otros": "qüestions diverses (instal·lacions, serveis i altres)",
    },
    "en": {
        "descansos": "breaks and time to rest or switch off",
        "turnos": "how shifts are organised and schedule changes",
        "carga_trabajo": "workload and staff shortages",
        "comunicacion": "how and when information about changes arrives",
        "liderazgo": "the relationship with managers and decision-making",
        "herramientas": "the state of tools, equipment and software",
        "formacion": "training and growth opportunities",
        "reconocimiento": "recognition of effort and good work",
        "seguridad": "safety and risk prevention",
        "ambiente": "team climate and relationships between colleagues",
        "conciliacion": "work-life balance",
        "otros": "various issues (facilities, services and others)",
    },
}
_RESUMEN = {"es": "{n} comentarios sobre {d}.", "ca": "{n} comentaris sobre {d}.",
            "en": "{n} comments about {d}."}


def resumen_respaldo(tema: str, n: int, idioma: str = "es") -> str:
    idioma = idioma_valido(idioma)
    return _RESUMEN[idioma].format(n=n, d=DESCRIPCION_TEMA[idioma].get(tema, tema))


# ---- Recomendaciones ----
# tema: (título de la acción, objetivo de la encuesta de seguimiento)
ACCION_POR_TEMA = {
    "es": {
        "descansos": ("Revisar con los equipos la duración y el momento de las pausas",
                      "Saber qué cambios en las pausas ayudarían a descansar mejor"),
        "turnos": ("Abrir un espacio para recoger propuestas sobre el sistema de turnos",
                   "Entender qué dificultades concretas genera el nuevo sistema de turnos"),
        "carga_trabajo": ("Analizar los picos de trabajo y reforzar los momentos críticos",
                          "Detectar en qué momentos la carga de trabajo es más difícil de asumir"),
        "comunicacion": ("Comunicar los cambios por un canal oficial y con antelación",
                         "Saber por qué canal y con cuánta antelación quieren recibir los cambios"),
        "liderazgo": ("Reforzar las reuniones breves de equipo con los responsables",
                      "Conocer qué esperan los equipos de sus responsables en el día a día"),
        "herramientas": ("Priorizar la reparación y renovación de las herramientas más citadas",
                         "Identificar qué herramientas o equipos dificultan más el trabajo"),
        "formacion": ("Publicar una oferta de formación ligada a los nuevos procesos",
                      "Saber qué formación necesitan los equipos para su día a día"),
        "reconocimiento": ("Incorporar el reconocimiento en las reuniones de equipo",
                           "Entender cómo les gustaría que se reconociera su trabajo"),
        "seguridad": ("Revisar con prevención los puntos de riesgo señalados",
                      "Identificar las situaciones de riesgo que más preocupan"),
        "ambiente": ("Impulsar actividades que refuercen la colaboración entre equipos",
                     "Conocer qué mejoraría la relación entre compañeros"),
        "conciliacion": ("Estudiar medidas de flexibilidad compatibles con cada puesto",
                         "Saber qué medidas de flexibilidad serían más útiles"),
        "otros": ("Revisar las incidencias de instalaciones y servicios señaladas",
                  "Detectar qué servicios o instalaciones conviene mejorar primero"),
    },
    "ca": {
        "descansos": ("Revisar amb els equips la durada i el moment de les pauses",
                      "Saber quins canvis en les pauses ajudarien a descansar millor"),
        "turnos": ("Obrir un espai per recollir propostes sobre el sistema de torns",
                   "Entendre quines dificultats concretes genera el nou sistema de torns"),
        "carga_trabajo": ("Analitzar els pics de feina i reforçar els moments crítics",
                          "Detectar en quins moments la càrrega de feina és més difícil d'assumir"),
        "comunicacion": ("Comunicar els canvis per un canal oficial i amb antelació",
                         "Saber per quin canal i amb quanta antelació volen rebre els canvis"),
        "liderazgo": ("Reforçar les reunions breus d'equip amb els responsables",
                      "Conèixer què esperen els equips dels seus responsables en el dia a dia"),
        "herramientas": ("Prioritzar la reparació i renovació de les eines més esmentades",
                         "Identificar quines eines o equips dificulten més la feina"),
        "formacion": ("Publicar una oferta de formació lligada als nous processos",
                      "Saber quina formació necessiten els equips per al dia a dia"),
        "reconocimiento": ("Incorporar el reconeixement a les reunions d'equip",
                           "Entendre com els agradaria que es reconegués la seva feina"),
        "seguridad": ("Revisar amb prevenció els punts de risc assenyalats",
                      "Identificar les situacions de risc que més preocupen"),
        "ambiente": ("Impulsar activitats que reforcin la col·laboració entre equips",
                     "Conèixer què milloraria la relació entre companys"),
        "conciliacion": ("Estudiar mesures de flexibilitat compatibles amb cada lloc de treball",
                         "Saber quines mesures de flexibilitat serien més útils"),
        "otros": ("Revisar les incidències d'instal·lacions i serveis assenyalades",
                  "Detectar quins serveis o instal·lacions convé millorar primer"),
    },
    "en": {
        "descansos": ("Review break length and timing with the teams",
                      "Find out which changes to breaks would help people rest better"),
        "turnos": ("Open a channel to gather proposals on the shift system",
                   "Understand what specific difficulties the new shift system creates"),
        "carga_trabajo": ("Analyse workload peaks and reinforce critical moments",
                          "Identify when the workload is hardest to handle"),
        "comunicacion": ("Announce changes through an official channel and in advance",
                         "Find out through which channel and how far in advance people want changes announced"),
        "liderazgo": ("Strengthen short team meetings with managers",
                      "Understand what teams expect from their managers day to day"),
        "herramientas": ("Prioritise repairing and replacing the most cited tools",
                         "Identify which tools or equipment get most in the way of work"),
        "formacion": ("Offer training linked to the new processes",
                      "Find out what training teams need for their daily work"),
        "reconocimiento": ("Build recognition into team meetings",
                           "Understand how people would like their work to be recognised"),
        "seguridad": ("Review the reported risk points with the prevention team",
                      "Identify the risk situations that worry people most"),
        "ambiente": ("Promote activities that strengthen collaboration between teams",
                     "Find out what would improve relationships between colleagues"),
        "conciliacion": ("Study flexibility measures compatible with each role",
                         "Find out which flexibility measures would be most useful"),
        "otros": ("Review the reported facilities and services issues",
                  "Identify which services or facilities should be improved first"),
    },
}
RESPONSABLE = {
    "es": {"descansos": "Jefes de turno y RRHH", "turnos": "Dirección de planta y RRHH",
           "carga_trabajo": "Responsables de área", "comunicacion": "RRHH y Comunicación interna",
           "liderazgo": "Responsables de equipo", "herramientas": "Mantenimiento e IT",
           "formacion": "RRHH (Desarrollo)", "reconocimiento": "Responsables de equipo",
           "seguridad": "Prevención de riesgos", "ambiente": "Responsables de equipo y RRHH",
           "conciliacion": "RRHH", "otros": "Servicios generales",
           "participacion": "RRHH y jefes de turno"},
    "ca": {"descansos": "Caps de torn i RRHH", "turnos": "Direcció de planta i RRHH",
           "carga_trabajo": "Responsables d'àrea", "comunicacion": "RRHH i Comunicació interna",
           "liderazgo": "Responsables d'equip", "herramientas": "Manteniment i IT",
           "formacion": "RRHH (Desenvolupament)", "reconocimiento": "Responsables d'equip",
           "seguridad": "Prevenció de riscos", "ambiente": "Responsables d'equip i RRHH",
           "conciliacion": "RRHH", "otros": "Serveis generals",
           "participacion": "RRHH i caps de torn"},
    "en": {"descansos": "Shift leads and HR", "turnos": "Plant management and HR",
           "carga_trabajo": "Area managers", "comunicacion": "HR and Internal Communications",
           "liderazgo": "Team managers", "herramientas": "Maintenance and IT",
           "formacion": "HR (Development)", "reconocimiento": "Team managers",
           "seguridad": "Health and safety", "ambiente": "Team managers and HR",
           "conciliacion": "HR", "otros": "Facilities",
           "participacion": "HR and shift leads"},
}
PLAZO_TEMA = {"descansos": (2, "semana"), "turnos": (1, "mes"), "carga_trabajo": (1, "mes"),
              "comunicacion": (1, "semana"), "liderazgo": (1, "mes"), "herramientas": (1, "mes"),
              "formacion": (2, "mes"), "reconocimiento": (1, "mes"), "seguridad": (1, "semana"),
              "ambiente": (1, "mes"), "conciliacion": (2, "mes"), "otros": (1, "mes"),
              "participacion": (2, "semana")}
_UNIDAD = {"es": {"semana": ("semana", "semanas"), "mes": ("mes", "meses")},
           "ca": {"semana": ("setmana", "setmanes"), "mes": ("mes", "mesos")},
           "en": {"semana": ("week", "weeks"), "mes": ("month", "months")}}


def plazo(clave: str, idioma: str = "es") -> str:
    idioma = idioma_valido(idioma)
    n, unidad = PLAZO_TEMA[clave]
    singular, plural = _UNIDAD[idioma][unidad]
    return f"{n} {singular if n == 1 else plural}"


TEXTO_TENDENCIA = {
    "es": {"nuevo": "aparece como tema nuevo", "sube": "gana peso respecto al periodo anterior",
           "estable": "se mantiene estable", "baja": "pierde peso"},
    "ca": {"nuevo": "apareix com a tema nou", "sube": "guanya pes respecte al període anterior",
           "estable": "es manté estable", "baja": "perd pes"},
    "en": {"nuevo": "is new this period", "sube": "is gaining weight compared with the previous period",
           "estable": "remains stable", "baja": "is losing weight"},
}

FRASES = {
    "es": {
        "cifra": "{n} comentarios, {pct} del total",
        "cifra_antes": "; antes {pct}",
        "por_debajo": "por debajo del {pct}",
        "en_descenso": "en descenso",
        "motivo_tema": "El tema {tema} {tendencia} ({cifra}). Propuesta para valorar por RRHH.",
        "indicador_tema": "Peso de {tema} en los comentarios {objetivo} en el seguimiento",
        "titulo_participacion": "Reforzar la participación de {quien} con QR y quiosco en el centro",
        "motivo_participacion": ("Solo ha respondido un {pct} de {quien} ({r} de {p}): sus resultados "
                                 "pueden no estar representados. Propuesta para valorar por RRHH."),
        "indicador_participacion": "Participación de {quien} de al menos el 20 %",
        "contexto_seguimiento": "Seguimiento del análisis{periodo}: el tema {tema} destaca en los comentarios.",
        "periodo": " de {periodo}",
        "objetivo_sin_temas": "Conocer cómo se sienten las personas en su día a día",
        "contexto_sin_temas": "Seguimiento: todavía hay pocos comentarios para identificar temas.",
        "lectura_respuestas": "Han respondido {n} personas",
        "lectura_global": ", un {pct} de la plantilla consultada.",
        "lectura_destacados": "Ganan peso {temas}.",
        "lectura_tema": "{tema} ({pct} de los comentarios{extra})",
        "lectura_nuevo": ", tema nuevo",
        "lectura_antes": ", antes {pct}",
        "y": " y ",
        "sin_datos": "Todavía no hay datos suficientes para una lectura de resultados.",
        "titulo_mas_respuestas": "Recoger más respuestas antes de decidir",
        "motivo_mas_respuestas": "Todavía no hay datos suficientes para proponer acciones.",
        "indicador_mas_respuestas": "Al menos 5 respuestas por segmento",
    },
    "ca": {
        "cifra": "{n} comentaris, {pct} del total",
        "cifra_antes": "; abans {pct}",
        "por_debajo": "per sota del {pct}",
        "en_descenso": "en descens",
        "motivo_tema": "El tema {tema} {tendencia} ({cifra}). Proposta perquè RRHH la valori.",
        "indicador_tema": "Pes de {tema} en els comentaris {objetivo} en el seguiment",
        "titulo_participacion": "Reforçar la participació de {quien} amb QR i quiosc al centre",
        "motivo_participacion": ("Només ha respost un {pct} de {quien} ({r} de {p}): els seus resultats "
                                 "poden no estar representats. Proposta perquè RRHH la valori."),
        "indicador_participacion": "Participació de {quien} d'almenys el 20 %",
        "contexto_seguimiento": "Seguiment de l'anàlisi{periodo}: el tema {tema} destaca en els comentaris.",
        "periodo": " de {periodo}",
        "objetivo_sin_temas": "Conèixer com se senten les persones en el seu dia a dia",
        "contexto_sin_temas": "Seguiment: encara hi ha pocs comentaris per identificar temes.",
        "lectura_respuestas": "Han respost {n} persones",
        "lectura_global": ", un {pct} de la plantilla consultada.",
        "lectura_destacados": "Guanyen pes {temas}.",
        "lectura_tema": "{tema} ({pct} dels comentaris{extra})",
        "lectura_nuevo": ", tema nou",
        "lectura_antes": ", abans {pct}",
        "y": " i ",
        "sin_datos": "Encara no hi ha prou dades per fer una lectura dels resultats.",
        "titulo_mas_respuestas": "Recollir més respostes abans de decidir",
        "motivo_mas_respuestas": "Encara no hi ha prou dades per proposar accions.",
        "indicador_mas_respuestas": "Almenys 5 respostes per segment",
    },
    "en": {
        "cifra": "{n} comments, {pct} of the total",
        "cifra_antes": "; previously {pct}",
        "por_debajo": "below {pct}",
        "en_descenso": "decreasing",
        "motivo_tema": "The topic \"{tema}\" {tendencia} ({cifra}). Proposal for HR to consider.",
        "indicador_tema": "Share of {tema} in comments {objetivo} in the follow-up",
        "titulo_participacion": "Boost participation from the {quien} group with QR codes and kiosks on site",
        "motivo_participacion": ("Only {pct} of the {quien} group has responded ({r} of {p}): their results may "
                                 "not be represented. Proposal for HR to consider."),
        "indicador_participacion": "Participation from the {quien} group of at least 20%",
        "contexto_seguimiento": "Follow-up of the analysis{periodo}: the topic \"{tema}\" stands out in the comments.",
        "periodo": " for {periodo}",
        "objetivo_sin_temas": "Understand how people feel in their day-to-day work",
        "contexto_sin_temas": "Follow-up: there are still too few comments to identify topics.",
        "lectura_respuestas": "{n} people have responded",
        "lectura_global": ", {pct} of the workforce surveyed.",
        "lectura_destacados": "Gaining weight: {temas}.",
        "lectura_tema": "{tema} ({pct} of comments{extra})",
        "lectura_nuevo": ", new topic",
        "lectura_antes": ", previously {pct}",
        "y": " and ",
        "sin_datos": "There is not enough data yet for a reading of the results.",
        "titulo_mas_respuestas": "Collect more responses before deciding",
        "motivo_mas_respuestas": "There is not enough data yet to propose actions.",
        "indicador_mas_respuestas": "At least 5 responses per segment",
    },
}


def frase(clave: str, idioma: str = "es", **datos) -> str:
    return FRASES[idioma_valido(idioma)][clave].format(**datos)


def quien(colectivo: str, turno: str | None, idioma: str = "es") -> str:
    """'planta de noche', 'night production plant', 'logística'... para meter en una frase."""
    idioma = idioma_valido(idioma)
    grupo = nombre("colectivo", colectivo, idioma)
    if not turno or turno == "sin_turno":
        return grupo
    franja = nombre("turno", turno, idioma)
    if idioma == "en":
        return f"{franja} {grupo}"
    return f"{grupo} de {franja}"
