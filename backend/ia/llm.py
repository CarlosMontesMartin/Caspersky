"""Integración con LLM para Antigravity / Damm Escucha Activa.

Importa el SDK solo dentro de este archivo.
No imprime nunca la API key.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

# Intentar cargar .env usando python-dotenv si está disponible
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


def hay_llm() -> bool:
    """Devuelve True si existe LLM_API_KEY no vacía en las variables de entorno."""
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
    except Exception:
        pass

    key = os.getenv("LLM_API_KEY", "").strip()
    return bool(key)


def llamar_llm(sistema: str, usuario: str) -> str:
    """Llama al proveedor de LLM configurado (Gemini con paquete google-genai).

    Usa LLM_API_KEY y opcionalmente LLM_MODEL.
    Timeout de 30 s. Lanza excepción si falla.
    Nunca imprime la clave.
    """
    if not hay_llm():
        raise RuntimeError("LLM_API_KEY no configurada")

    api_key = os.getenv("LLM_API_KEY", "").strip()
    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "El paquete 'google-genai' no está instalado en el entorno"
        ) from exc

    # El timeout lo aplica el propio cliente HTTP (en milisegundos): así la
    # llamada se corta de verdad a los 30 s y el demo no se queda colgado.
    client = genai.Client(api_key=api_key,
                          http_options=types.HttpOptions(timeout=30_000))
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        temperature=0.2,
        response_mime_type="application/json",
    )
    response = client.models.generate_content(
        model=model_name, contents=usuario, config=config,
    )
    if not response or not response.text:
        raise RuntimeError("El modelo LLM no devolvió contenido de texto")
    return response.text


def _extraer_json(texto: str) -> dict | list:
    """Extrae y parsea el primer bloque JSON del texto."""
    texto_limpio = texto.strip()
    try:
        return json.loads(texto_limpio)
    except Exception:
        pass

    # Markdown fenced blocks: ```json ... ``` o ``` ... ```
    match_bloque = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto)
    if match_bloque:
        try:
            return json.loads(match_bloque.group(1).strip())
        except Exception:
            pass

    # Primer bloque {...} o [...]
    match_llaves = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", texto)
    if match_llaves:
        try:
            return json.loads(match_llaves.group(0).strip())
        except Exception:
            pass

    raise ValueError("No se pudo extraer ningún bloque JSON válido de la respuesta")


def llamar_llm_json(sistema: str, usuario: str) -> dict | list:
    """Llama al LLM, extrae el primer bloque JSON del texto y lo parsea.

    Solo reintenta (una vez) si el JSON no es válido. Si la llamada falla
    (sin red, timeout, clave mala), la excepción sube enseguida para que
    quien llama pase al modo de respaldo sin esperar otros 30 s.
    """
    texto = llamar_llm(sistema, usuario)
    try:
        return _extraer_json(texto)
    except ValueError:
        texto = llamar_llm(sistema, usuario + "\n\nResponde SOLO con JSON válido.")
        return _extraer_json(texto)