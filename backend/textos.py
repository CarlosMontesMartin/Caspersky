"""Textos que escribe el backend, en es / ca / en (v4.md, P0-3).

- nombre(tipo, codigo, idioma): nombres de sectores, turnos, temas, dimensiones y temas prohibidos
  de los escenarios ("tema_prohibido.salario", v5 P0-1). Se leen de
  frontend/i18n/<idioma>.json (claves "colectivo.planta", "turno.noche", "tema.descansos",
  "dimension.bienestar"), así frontend y backend dicen lo mismo. Si falta una clave, se usa
  la tabla de respaldo de abajo.
- frase(clave, idioma, **datos): plantillas de alertas, límites y textos fijos del backend.
"""
import json
from pathlib import Path

from backend.reglas import IDIOMAS, idioma_valido

I18N = Path(__file__).resolve().parents[1] / "frontend" / "i18n"

# Respaldo por si frontend/i18n aún no tiene la clave.
NOMBRES = {
    "es": {
        "colectivo": {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                      "oficina": "oficina", "manager": "managers", "todos": "todos los sectores"},
        "turno": {"manana": "mañana", "tarde": "tarde", "noche": "noche", "sin_turno": "sin turno"},
        "tema": {"descansos": "descansos", "turnos": "turnos", "carga_trabajo": "carga de trabajo",
                 "comunicacion": "comunicación", "liderazgo": "liderazgo", "herramientas": "herramientas",
                 "formacion": "formación", "reconocimiento": "reconocimiento", "seguridad": "seguridad",
                 "ambiente": "ambiente", "conciliacion": "conciliación", "otros": "otros"},
        "dimension": {"bienestar": "bienestar", "liderazgo": "liderazgo", "desarrollo": "desarrollo",
                      "cultura": "cultura", "entorno": "entorno", "condiciones": "condiciones"},
        "tema_prohibido": {"salario": "salario", "evaluacion_individual": "evaluación individual",
                           "salud_personal": "salud personal"},
    },
    "ca": {
        "colectivo": {"planta": "planta", "logistica": "logística", "comercial": "comercial",
                      "oficina": "oficina", "manager": "comandaments", "todos": "tots els sectors"},
        "turno": {"manana": "matí", "tarde": "tarda", "noche": "nit", "sin_turno": "sense torn"},
        "tema": {"descansos": "descansos", "turnos": "torns", "carga_trabajo": "càrrega de feina",
                 "comunicacion": "comunicació", "liderazgo": "lideratge", "herramientas": "eines",
                 "formacion": "formació", "reconocimiento": "reconeixement", "seguridad": "seguretat",
                 "ambiente": "ambient", "conciliacion": "conciliació", "otros": "altres"},
        "dimension": {"bienestar": "benestar", "liderazgo": "lideratge", "desarrollo": "desenvolupament",
                      "cultura": "cultura", "entorno": "entorn", "condiciones": "condicions"},
        "tema_prohibido": {"salario": "salari", "evaluacion_individual": "avaluació individual",
                           "salud_personal": "salut personal"},
    },
    "en": {
        "colectivo": {"planta": "production plant", "logistica": "logistics", "comercial": "sales",
                      "oficina": "office", "manager": "managers", "todos": "all sectors"},
        "turno": {"manana": "morning", "tarde": "afternoon", "noche": "night", "sin_turno": "no shift"},
        "tema": {"descansos": "breaks", "turnos": "shifts", "carga_trabajo": "workload",
                 "comunicacion": "communication", "liderazgo": "leadership", "herramientas": "tools",
                 "formacion": "training", "reconocimiento": "recognition", "seguridad": "safety",
                 "ambiente": "atmosphere", "conciliacion": "work-life balance", "otros": "other"},
        "dimension": {"bienestar": "wellbeing", "liderazgo": "leadership", "desarrollo": "development",
                      "cultura": "culture", "entorno": "environment", "condiciones": "conditions"},
        "tema_prohibido": {"salario": "salary", "evaluacion_individual": "individual performance review",
                           "salud_personal": "personal health"},
    },
}

FRASES = {
    "es": {
        "segmento.turno": "el turno de {turno} de {colectivo}",
        "alerta.representatividad": "{segmento} solo ha respondido un {pct} % ({n} de {personas}): "
                                    "los resultados pueden no representarle.",
        "alerta.caida": "«{pregunta}» baja de {antes} a {despues} en {colectivo} respecto al periodo anterior.",
        "limite.muestra": "Muestra pequeña en {segmento} (n={n}): no se muestran sus medias ni temas.",
        "limite.umbral": "Segmentos con menos de {umbral} respuestas ocultos.",
        "limite.correlacion": "Una correlación no demuestra una causa.",
        "limite.sin_plantilla": "Sin plantilla de personas: no se puede calcular la representatividad.",
        "limite.simuladas": "Incluye respuestas simuladas para la demostración.",
        "teams.duracion": "Duración", "teams.menos_de": "Menos de {min} min", "teams.sectores": "Sectores",
        "teams.anonima": "Anónima · resultados agregados", "teams.responder": "Responder",
        "teams.resumen": "Resumen · {titulo}", "teams.respuestas": "Respuestas",
        "teams.participacion": "Participación", "teams.no_representativos": "No representativos",
        "teams.alertas": "Alertas", "teams.acciones": "Acciones propuestas", "teams.ver_analisis": "Ver análisis",
        "teams.no_disponible": "Teams no está configurado en el servidor (falta TEAMS_WEBHOOK_URL en el .env).",
    },
    "ca": {
        "segmento.turno": "el torn de {turno} de {colectivo}",
        "alerta.representatividad": "{segmento} només ha respost un {pct} % ({n} de {personas}): "
                                    "els resultats poden no ser representatius.",
        "alerta.caida": "«{pregunta}» baixa de {antes} a {despues} a {colectivo} respecte al període anterior.",
        "limite.muestra": "Mostra petita a {segmento} (n={n}): no se'n mostren les mitjanes ni els temes.",
        "limite.umbral": "Segments amb menys de {umbral} respostes ocults.",
        "limite.correlacion": "Una correlació no demostra una causa.",
        "limite.sin_plantilla": "Sense plantilla de persones: no es pot calcular la representativitat.",
        "limite.simuladas": "Inclou respostes simulades per a la demostració.",
        "teams.duracion": "Durada", "teams.menos_de": "Menys de {min} min", "teams.sectores": "Sectors",
        "teams.anonima": "Anònima · resultats agregats", "teams.responder": "Respondre",
        "teams.resumen": "Resum · {titulo}", "teams.respuestas": "Respostes",
        "teams.participacion": "Participació", "teams.no_representativos": "No representatius",
        "teams.alertas": "Alertes", "teams.acciones": "Accions proposades", "teams.ver_analisis": "Veure l'anàlisi",
        "teams.no_disponible": "Teams no està configurat al servidor (falta TEAMS_WEBHOOK_URL al .env).",
    },
    "en": {
        "segmento.turno": "the {turno} shift in {colectivo}",
        "alerta.representatividad": "{segmento} has only responded {pct}% ({n} of {personas}): "
                                    "the results may not be representative.",
        "alerta.caida": "“{pregunta}” drops from {antes} to {despues} in {colectivo} compared with the previous period.",
        "limite.muestra": "Small sample in {segmento} (n={n}): its averages and topics are not shown.",
        "limite.umbral": "Segments with fewer than {umbral} responses are hidden.",
        "limite.correlacion": "A correlation does not prove causation.",
        "limite.sin_plantilla": "No headcount data: representativeness cannot be calculated.",
        "limite.simuladas": "Includes simulated responses for the demo.",
        "teams.duracion": "Duration", "teams.menos_de": "Under {min} min", "teams.sectores": "Sectors",
        "teams.anonima": "Anonymous · aggregated results", "teams.responder": "Respond",
        "teams.resumen": "Summary · {titulo}", "teams.respuestas": "Responses",
        "teams.participacion": "Participation", "teams.no_representativos": "Not representative",
        "teams.alertas": "Alerts", "teams.acciones": "Proposed actions", "teams.ver_analisis": "View analysis",
        "teams.no_disponible": "Teams is not configured on the server (TEAMS_WEBHOOK_URL is missing from .env).",
    },
}

_cache: dict[str, tuple[float, dict]] = {}


def _i18n(idioma: str) -> dict:
    """frontend/i18n/<idioma>.json aplanado ("a.b": valor). Se relee si el archivo cambia."""
    ruta = I18N / f"{idioma}.json"
    try:
        mtime = ruta.stat().st_mtime
    except OSError:
        return {}
    if idioma in _cache and _cache[idioma][0] == mtime:
        return _cache[idioma][1]

    def aplanar(datos, prefijo=""):
        plano = {}
        for k, v in datos.items():
            if isinstance(v, dict):
                plano.update(aplanar(v, f"{prefijo}{k}."))
            else:
                plano[f"{prefijo}{k}"] = v
        return plano

    try:
        plano = aplanar(json.loads(ruta.read_text(encoding="utf-8")))
    except (ValueError, AttributeError):
        plano = {}
    _cache[idioma] = (mtime, plano)
    return plano


def nombre(tipo: str, codigo: str, idioma: str = "es") -> str:
    """Nombre legible de un código (tipo: colectivo | turno | tema | dimension)."""
    idioma = idioma_valido(idioma)
    valor = _i18n(idioma).get(f"{tipo}.{codigo}")
    if isinstance(valor, str) and valor.strip():
        return valor
    return NOMBRES[idioma].get(tipo, {}).get(codigo) or NOMBRES["es"].get(tipo, {}).get(codigo) or str(codigo)


def numero(valor: float, idioma: str = "es", decimales: int = 1) -> str:
    """3,4 en es/ca y 3.4 en en."""
    texto = f"{valor:.{decimales}f}"
    return texto if idioma_valido(idioma) == "en" else texto.replace(".", ",")


def frase(clave: str, idioma: str = "es", **datos) -> str:
    """Plantilla de FRASES en el idioma pedido (castellano si falta), con la primera letra en mayúscula."""
    idioma = idioma_valido(idioma)
    plantilla = FRASES[idioma].get(clave) or FRASES["es"].get(clave) or clave
    texto = plantilla.format(**datos)
    return texto[:1].upper() + texto[1:]


def segmento(colectivo: str, turno: str | None, idioma: str = "es") -> str:
    """"el turno de noche de planta" / "logística" (en minúscula, para ir dentro de una frase)."""
    nombre_colectivo = nombre("colectivo", colectivo, idioma).lower()
    if turno in ("manana", "tarde", "noche"):
        plantilla = FRASES[idioma_valido(idioma)]["segmento.turno"]
        return plantilla.format(turno=nombre("turno", turno, idioma).lower(), colectivo=nombre_colectivo)
    return nombre_colectivo


__all__ = ["IDIOMAS", "nombre", "numero", "frase", "segmento"]
