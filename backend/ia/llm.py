"""Cliente del modelo de lenguaje. Único módulo que importa el SDK."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

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
    """Comprueba si existe la clave de API configurada en el entorno."""
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
    """Ejecuta una petición al modelo de lenguaje y devuelve la respuesta en texto."""
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

    # Timeout explícito para evitar bloqueos si la red no responde
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
    texto_limpio = texto.strip()
    try:
        return json.loads(texto_limpio)
    except Exception:
        pass

    match_bloque = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto)
    if match_bloque:
        try:
            return json.loads(match_bloque.group(1).strip())
        except Exception:
            pass

    match_llaves = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", texto)
    if match_llaves:
        try:
            return json.loads(match_llaves.group(0).strip())
        except Exception:
            pass

    raise ValueError("No se pudo extraer ningún bloque JSON válido de la respuesta")


def llamar_llm_json(sistema: str, usuario: str) -> dict | list:
    """Ejecuta una petición al modelo de lenguaje y devuelve el resultado parseado como JSON.

    Reintenta una vez si la respuesta no contiene un JSON válido.
    """
    texto = llamar_llm(sistema, usuario)
    try:
        return _extraer_json(texto)
    except ValueError:
        texto = llamar_llm(sistema, usuario + "\n\nResponde SOLO con JSON válido.")
        return _extraer_json(texto)
