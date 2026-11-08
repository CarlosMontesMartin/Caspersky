"""Teams · UPC 2 (v3.md 3.4, v4.md P0-2 y v5.md P0-3) — listo para conectar.

El backend es la ÚNICA fuente de las tarjetas: el frontend (js/teams.js) solo dibuja lo que
devuelve /teams/vista_previa.

- GET  /integraciones                         → {"teams": bool, "aviso": str | null, ...}
- GET  /encuestas/{id}/teams/vista_previa     → la tarjeta (Adaptive Card 1.4) que se enviaría,
                                                 con datos reales y en el idioma pedido
- POST /encuestas/{id}/teams/publicar|resumen → sin configurar: 503
                                                 configurado: envía la tarjeta → {"enviado": true}

Para conectarlo basta con poner en el .env TEAMS_WEBHOOK_URL = la URL del workflow de Teams
"Post to a channel when a webhook request is received". La URL es un SECRETO: nunca se escribe
en los registros ni en los mensajes de error.

Para depurar sin Teams: copiad el JSON de GET /encuestas/{id}/teams/vista_previa en el
Adaptive Cards Designer (adaptivecards.io/designer, host "Microsoft Teams").
"""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException

from backend import textos
from backend.api import rutas_encuestas, traducciones
from backend.api.validacion import colectivos_de
from backend.datos import almacen
from backend.datos import compromisos as compromisos_datos
from backend.reglas import idioma_valido

router = APIRouter()

TIMEOUT_SEG = 10
DOMINIOS_TEAMS = ("logic.azure.com", "powerplatform.com", "powerautomate.com", "office.com")
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
AVISO_URL_NO_VALIDA = "TEAMS_WEBHOOK_URL no válida"
AVISO_LOCALHOST = "BASE_URL es localhost: los botones de Teams solo funcionarán en este ordenador"


# ---------- configuración ----------

def _url_webhook() -> str:
    return os.getenv("TEAMS_WEBHOOK_URL", "").strip()


def url_valida(url: str) -> bool:
    """Solo https y con un dominio de Microsoft (Power Automate / Logic Apps / Office)."""
    try:
        partes = urlparse(url)
    except ValueError:
        return False
    host = (partes.hostname or "").lower()
    return partes.scheme == "https" and any(host == d or host.endswith("." + d) for d in DOMINIOS_TEAMS)


def configurado() -> bool:
    url = _url_webhook()
    return bool(url) and url_valida(url)


def _base_url_local() -> bool:
    try:
        return (urlparse(rutas_encuestas.base_url()).hostname or "").lower() in HOSTS_LOCALES
    except ValueError:
        return False


def aviso() -> tuple[str | None, str | None]:
    """(código, texto) del aviso para la pantalla de Teams, o (None, None).
    El código coincide con la clave de i18n de UAB 2: teams.aviso_<código>."""
    if _url_webhook() and not configurado():
        return "url_no_valida", AVISO_URL_NO_VALIDA
    if configurado() and _base_url_local():
        return "localhost", AVISO_LOCALHOST
    return None, None


# ---------- envío ----------

def enviar(tarjeta: dict) -> None:
    """POST de la tarjeta al workflow de Teams. 2xx → ok; si no, 502 (sin la URL en el mensaje)."""
    if not configurado():
        raise HTTPException(503, textos.frase("teams.no_disponible", "es"))
    cuerpo = {"type": "message", "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": tarjeta}]}
    peticion = urllib.request.Request(
        _url_webhook(), data=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEG) as respuesta:
            codigo = respuesta.status
    except urllib.error.HTTPError as error:  # antes que URLError: es una subclase
        print(f"[teams] el workflow respondió {error.code}")
        raise HTTPException(502, f"Teams respondió {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        print(f"[teams] sin conexión con Teams: {type(error).__name__}")
        raise HTTPException(502, "No se pudo contactar con Teams") from None
    if not 200 <= codigo < 300:
        print(f"[teams] el workflow respondió {codigo}")
        raise HTTPException(502, f"Teams respondió {codigo}")


# ---------- tarjetas ----------

def _texto(contenido: str, **extra) -> dict:
    return {"type": "TextBlock", "text": contenido, "wrap": True, **extra}


def _bloques(*bloques) -> list[dict]:
    """Quita los None y los TextBlock sin texto (Teams los pinta como huecos vacíos)."""
    return [b for b in bloques if b and not (b.get("type") == "TextBlock" and not str(b.get("text") or "").strip())]


def tarjeta_encuesta(encuesta: dict, idioma: str = "es") -> dict:
    """Título, intro, duración, sectores, "Anónima · resultados agregados" y botón Responder.
    Título e intro en `idioma` si hay traducción; si no, en el idioma original."""
    idioma = idioma_valido(idioma)
    vista = traducciones.aplicar(encuesta, idioma)
    minutos = max(1, -(-int(encuesta.get("tiempo_estimado_seg") or 60) // 60))
    sectores = ", ".join(textos.nombre("colectivo", c, idioma) for c in colectivos_de(encuesta))
    url = encuesta.get("url") or f"{rutas_encuestas.base_url()}/responder/{encuesta['id']}"
    separador = "&" if "?" in url else "?"
    hechos = [{"title": textos.frase("teams.duracion", idioma), "value": textos.frase("teams.menos_de", idioma, min=minutos)}]
    if sectores:
        hechos.append({"title": textos.frase("teams.sectores", idioma), "value": sectores})
    return {
        "type": "AdaptiveCard", "version": "1.4",
        "body": _bloques(
            _texto(vista.get("titulo", ""), weight="Bolder", size="Medium"),
            _texto(vista.get("intro", "")),
            {"type": "FactSet", "facts": hechos},
            _texto(textos.frase("teams.anonima", idioma), isSubtle=True, size="Small"),
        ),
        "actions": [{"type": "Action.OpenUrl", "title": textos.frase("teams.responder", idioma),
                     "url": f"{url}{separador}canal=teams&lang={idioma}"}],
    }


def tarjeta_resumen(analisis: dict, recomendaciones: dict, idioma: str = "es") -> dict:
    """Lectura, 3 cifras, hasta 3 alertas, 2 acciones y botón Ver análisis. Nunca comentarios."""
    idioma = idioma_valido(idioma)
    no_repr = sum(1 for z in analisis.get("zonas", []) if not z.get("representativo"))
    pct = round((analisis.get("participacion_global") or 0) * 100)
    alertas = [a for a in analisis.get("alertas", []) if str(a.get("mensaje") or "").strip()][:3]
    acciones = [a for a in (recomendaciones or {}).get("acciones", []) if str(a.get("titulo") or "").strip()][:2]
    cuerpo = _bloques(
        _texto(textos.frase("teams.resumen", idioma, titulo=analisis.get("titulo", "")), weight="Bolder", size="Medium"),
        _texto(analisis.get("lectura", "")),
        {"type": "FactSet", "facts": [
            {"title": textos.frase("teams.respuestas", idioma), "value": str(analisis.get("n_respuestas", 0))},
            {"title": textos.frase("teams.participacion", idioma), "value": f"{pct}%" if idioma == "en" else f"{pct} %"},
            {"title": textos.frase("teams.no_representativos", idioma),
             "value": f"{no_repr} / {len(analisis.get('zonas', []))}"},
        ]},
        _texto(textos.frase("teams.alertas", idioma), weight="Bolder", spacing="Medium") if alertas else None,
        *[_texto(f"• {a['mensaje']}", spacing="Small", color="Attention") for a in alertas],
        _texto(textos.frase("teams.acciones", idioma), weight="Bolder", spacing="Medium") if acciones else None,
        *[_texto(f"• {a['titulo']}", spacing="Small") for a in acciones],
    )
    return {"type": "AdaptiveCard", "version": "1.4", "body": cuerpo,
            "actions": [{"type": "Action.OpenUrl", "title": textos.frase("teams.ver_analisis", idioma),
                         "url": f"{rutas_encuestas.base_url()}/dashboard.html?id={analisis['encuesta_id']}"}]}


def tarjeta_compromiso(compromiso: dict, seguimiento: dict | None = None, idioma: str = "es") -> dict:
    """"Dijisteis" + texto, "Hemos hecho" + texto, responsable y fecha, y (si el seguimiento está publicado)
    el botón "¿Ha funcionado? Responde en 30 s". Solo resultados agregados: nunca comentarios."""
    idioma = idioma_valido(idioma)
    v = compromisos_datos.vista(compromiso, idioma)
    hechos = [{"title": textos.frase("teams.responsable", idioma), "value": v.get("responsable") or "—"},
              {"title": textos.frase("teams.fecha", idioma), "value": v.get("fecha") or "—"}]
    despues, antes = v.get("despues"), (v.get("indicador") or {}).get("antes")
    if despues and antes is not None:
        hechos.append({"title": textos.frase("teams.antes_ahora", idioma),
                       "value": f"{textos.numero(antes, idioma)} → {textos.numero(despues['media'], idioma)} (n = {despues['n']})"})
    acciones = []
    if seguimiento and seguimiento.get("estado") == "publicada":
        url = seguimiento.get("url") or f"{rutas_encuestas.base_url()}/responder/{seguimiento['id']}"
        acciones.append({"type": "Action.OpenUrl", "title": textos.frase("teams.ha_funcionado", idioma),
                         "url": f"{url}{'&' if '?' in url else '?'}canal=teams&lang={idioma}"})
    return {
        "type": "AdaptiveCard", "version": "1.4",
        "body": _bloques(
            _texto(textos.frase("teams.dijisteis", idioma), weight="Bolder", size="Medium"),
            _texto(v.get("dijisteis", "")),
            _texto(textos.frase("teams.hemos_hecho", idioma), weight="Bolder", size="Medium", spacing="Medium"),
            _texto(v.get("hicimos", "")),
            {"type": "FactSet", "facts": hechos},
            _texto(textos.frase("teams.no_causa", idioma), isSubtle=True, size="Small") if despues and antes is not None else None,
            _texto(textos.frase("teams.datos_simulados", idioma), isSubtle=True, size="Small")
            if despues and despues.get("simulado") else None,
        ),
        "actions": acciones,
    }


def _seguimiento_de(compromiso: dict) -> dict | None:
    return almacen.leer_encuesta(compromiso["seguimiento_id"]) if compromiso.get("seguimiento_id") else None


# ---------- rutas ----------

@router.get("/integraciones")
def integraciones():
    codigo, texto = aviso()
    teams = configurado()
    return {"teams": teams, "aviso": texto, "aviso_codigo": codigo, "estado": "conectado" if teams else "N/A"}


@router.get("/encuestas/{encuesta_id}/teams/vista_previa")
def vista_previa(encuesta_id: str, tipo: str = "publicar", idioma: str = "es"):
    idioma = idioma_valido(idioma)
    encuesta = rutas_encuestas.obtener(encuesta_id)
    if tipo == "resumen":
        analisis, recomendaciones = rutas_encuestas.analisis_y_recomendaciones(encuesta, idioma)
        return tarjeta_resumen(analisis, recomendaciones, idioma)
    return tarjeta_encuesta(encuesta, idioma)


@router.post("/encuestas/{encuesta_id}/teams/publicar")
def publicar_en_teams(encuesta_id: str, idioma: str = "es"):
    idioma = idioma_valido(idioma)
    encuesta = rutas_encuestas.obtener(encuesta_id)
    if encuesta.get("estado") != "publicada":
        raise HTTPException(409, "Publica la encuesta antes de enviarla a Teams")
    if not configurado():
        raise HTTPException(503, textos.frase("teams.no_disponible", idioma))
    enviar(tarjeta_encuesta(encuesta, idioma))
    return {"enviado": True}


@router.post("/encuestas/{encuesta_id}/teams/resumen")
def resumen_en_teams(encuesta_id: str, idioma: str = "es"):
    idioma = idioma_valido(idioma)
    encuesta = rutas_encuestas.obtener(encuesta_id)
    if not configurado():
        raise HTTPException(503, textos.frase("teams.no_disponible", idioma))
    analisis, recomendaciones = rutas_encuestas.analisis_y_recomendaciones(encuesta, idioma)
    enviar(tarjeta_resumen(analisis, recomendaciones, idioma))
    return {"enviado": True}


def _compromiso(compromiso_id: str) -> dict:
    compromiso = almacen.leer_compromiso(compromiso_id)
    if compromiso is None:
        raise HTTPException(404, f"No existe el compromiso {compromiso_id}")
    return compromiso


@router.get("/compromisos/{compromiso_id}/teams/vista_previa")
def vista_previa_compromiso(compromiso_id: str, idioma: str = "es"):
    compromiso = _compromiso(compromiso_id)
    return tarjeta_compromiso(compromiso, _seguimiento_de(compromiso), idioma)


@router.post("/compromisos/{compromiso_id}/teams")
def compromiso_en_teams(compromiso_id: str, idioma: str = "es"):
    idioma = idioma_valido(idioma)
    compromiso = _compromiso(compromiso_id)
    if not configurado():
        raise HTTPException(503, textos.frase("teams.no_disponible", idioma))
    enviar(tarjeta_compromiso(compromiso, _seguimiento_de(compromiso), idioma))
    return {"enviado": True}
