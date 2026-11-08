"""Teams · UPC 2 (v3.md 3.4 y v4.md P0-2) — versión SIN conexión real.

Decisión del equipo: por ahora no hay webhook. Para que el frontend funcione igual:
- GET  /integraciones                         → {"teams": false, "estado": "N/A"}
- GET  /encuestas/{id}/teams/vista_previa     → la tarjeta (Adaptive Card 1.4) que se enviaría,
                                                 con datos reales y en el idioma pedido
- POST /encuestas/{id}/teams/publicar|resumen → 503 "no disponible (N/A)"; el frontend
                                                 (js/teams.js) muestra entonces la vista previa

Si algún día se conecta, solo cambia este archivo: configurado() y enviar().
"""
from fastapi import APIRouter, HTTPException

from backend import textos
from backend.api import rutas_encuestas
from backend.api.validacion import colectivos_de
from backend.reglas import idioma_valido

router = APIRouter()


def configurado() -> bool:
    return False  # sin conexión real en esta versión


def enviar(tarjeta: dict) -> None:
    raise HTTPException(503, textos.frase("teams.no_disponible", "es"))


def _texto(contenido: str, **extra) -> dict:
    return {"type": "TextBlock", "text": contenido, "wrap": True, **extra}


def tarjeta_encuesta(encuesta: dict, idioma: str = "es") -> dict:
    """Título, intro, duración, sectores, "Anónima · resultados agregados" y botón Responder."""
    minutos = max(1, -(-int(encuesta.get("tiempo_estimado_seg") or 60) // 60))
    sectores = ", ".join(textos.nombre("colectivo", c, idioma) for c in colectivos_de(encuesta))
    url = encuesta.get("url") or f"{rutas_encuestas.base_url()}/responder/{encuesta['id']}"
    separador = "&" if "?" in url else "?"
    return {
        "type": "AdaptiveCard", "version": "1.4",
        "body": [
            _texto(encuesta.get("titulo", ""), weight="Bolder", size="Medium"),
            _texto(encuesta.get("intro", "")),
            {"type": "FactSet", "facts": [
                {"title": textos.frase("teams.duracion", idioma), "value": textos.frase("teams.menos_de", idioma, min=minutos)},
                {"title": textos.frase("teams.sectores", idioma), "value": sectores},
            ]},
            _texto(textos.frase("teams.anonima", idioma), isSubtle=True, size="Small"),
        ],
        "actions": [{"type": "Action.OpenUrl", "title": textos.frase("teams.responder", idioma),
                     "url": f"{url}{separador}canal=teams&lang={idioma}"}],
    }


def tarjeta_resumen(analisis: dict, recomendaciones: dict, idioma: str = "es") -> dict:
    """Lectura, 3 cifras, hasta 3 alertas, 2 acciones y botón Ver análisis. Nunca comentarios."""
    no_repr = sum(1 for z in analisis.get("zonas", []) if not z.get("representativo"))
    pct = round((analisis.get("participacion_global") or 0) * 100)
    cuerpo = [
        _texto(textos.frase("teams.resumen", idioma, titulo=analisis.get("titulo", "")), weight="Bolder", size="Medium"),
        _texto(analisis.get("lectura", "")),
        {"type": "FactSet", "facts": [
            {"title": textos.frase("teams.respuestas", idioma), "value": str(analisis.get("n_respuestas", 0))},
            {"title": textos.frase("teams.participacion", idioma), "value": f"{pct}%" if idioma == "en" else f"{pct} %"},
            {"title": textos.frase("teams.no_representativos", idioma),
             "value": f"{no_repr} / {len(analisis.get('zonas', []))}"},
        ]},
    ]
    alertas = analisis.get("alertas", [])[:3]
    if alertas:
        cuerpo.append(_texto(textos.frase("teams.alertas", idioma), weight="Bolder", spacing="Medium"))
        cuerpo += [_texto(f"• {a['mensaje']}", spacing="Small", color="Attention") for a in alertas]
    acciones = (recomendaciones or {}).get("acciones", [])[:2]
    if acciones:
        cuerpo.append(_texto(textos.frase("teams.acciones", idioma), weight="Bolder", spacing="Medium"))
        cuerpo += [_texto(f"• {a['titulo']}", spacing="Small") for a in acciones]
    return {"type": "AdaptiveCard", "version": "1.4", "body": cuerpo,
            "actions": [{"type": "Action.OpenUrl", "title": textos.frase("teams.ver_analisis", idioma),
                         "url": f"{rutas_encuestas.base_url()}/dashboard.html?id={analisis['encuesta_id']}"}]}


@router.get("/integraciones")
def integraciones():
    return {"teams": configurado(), "estado": "N/A"}


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
    encuesta = rutas_encuestas.obtener(encuesta_id)
    if encuesta.get("estado") != "publicada":
        raise HTTPException(409, "Publica la encuesta antes de enviarla a Teams")
    raise HTTPException(503, textos.frase("teams.no_disponible", idioma_valido(idioma)))


@router.post("/encuestas/{encuesta_id}/teams/resumen")
def resumen_en_teams(encuesta_id: str, idioma: str = "es"):
    rutas_encuestas.obtener(encuesta_id)
    raise HTTPException(503, textos.frase("teams.no_disponible", idioma_valido(idioma)))
