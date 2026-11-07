"""Respuestas simuladas para el modo demo · UPC 2 (datos de UPC 1).

Los datos salen de datos_sinteticos/simular.py (mismo banco de frases, temas de la lista cerrada
y misma historia que enc_000). Cada respuesta pasa por el MISMO camino que las reales
(construir_respuesta: validación + texto libre a comentario + anonimizar).
"""
import random
from datetime import date

from backend.api.rutas_publico import construir_respuesta
from backend.api.validacion import CANALES_PUBLICOS
from backend.datos import almacen
from datos_sinteticos.simular import simular_respuestas


def _mes_anterior(hoy: date) -> str:
    return f"{hoy.year - 1}-12" if hoy.month == 1 else f"{hoy.year}-{hoy.month - 1:02d}"


def simular(encuesta: dict, n: int, con_periodo_anterior: bool = True, semilla: int | None = None) -> list[dict]:
    """Devuelve n respuestas del periodo actual (y n del anterior si se pide), listas para guardar."""
    hoy = date.today()
    periodos = [_mes_anterior(hoy), hoy.strftime("%Y-%m")]
    semilla = semilla if semilla is not None else random.randrange(1_000_000)
    simuladas = simular_respuestas(encuesta, almacen.leer_plantilla(), 2 * n, periodos, semilla)
    if not con_periodo_anterior:
        simuladas = [r for r in simuladas if r["periodo"] == periodos[-1]]
    texto = next((p["id"] for p in encuesta["preguntas"] if p["tipo"] == "texto"), None)

    respuestas = []
    for r in simuladas:
        entrada = {"turno": r["turno"],
                   # La página pública solo admite qr y quiosco
                   "canal": r["canal"] if r["canal"] in CANALES_PUBLICOS else "qr",
                   "valores": dict(r["valores"])}
        if texto:
            entrada["valores"][texto] = r["comentario"]
        elif r["comentario"]:
            entrada["comentario"] = r["comentario"]
        if not entrada["valores"] and not entrada.get("comentario"):
            continue  # Encuesta solo de texto y respuesta sin comentario: se omite
        respuestas.append(construir_respuesta(encuesta, entrada, colectivo=r["colectivo"],
                                              fecha=date.fromisoformat(r["fecha"]),
                                              tema_real=r["tema_real"]))
    return respuestas
