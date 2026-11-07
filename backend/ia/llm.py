"""Cliente del modelo de lenguaje (API compatible con OpenAI). Único punto de acceso al LLM.

Configuración en .env: LLM_API_KEY, LLM_BASE_URL y LLM_MODEL (por defecto ornith).
Usa la librería estándar en lugar del paquete openai para no añadir dependencias al arranque.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BASE_URL_POR_DEFECTO = "https://dcc-llm-gw.uab.cat/uabthehack/v1"
MODELO_POR_DEFECTO = "ornith"
TIMEOUT_SEG = 30


def _cargar_env() -> None:
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(ruta)
        return
    except ImportError:
        pass
    # Lectura mínima por si python-dotenv no está instalado
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


_cargar_env()


def _config() -> tuple[str, str, str]:
    clave = os.getenv("LLM_API_KEY", "").strip()
    base = (os.getenv("LLM_BASE_URL", "").strip() or BASE_URL_POR_DEFECTO).rstrip("/")
    modelo = os.getenv("LLM_MODEL", "").strip() or MODELO_POR_DEFECTO
    return clave, base, modelo


def hay_llm() -> bool:
    """Indica si están configuradas la clave y la URL del modelo."""
    return bool(os.getenv("LLM_API_KEY", "").strip() and os.getenv("LLM_BASE_URL", "").strip())


def llamar_llm(sistema: str, usuario: str, timeout: float = TIMEOUT_SEG) -> str:
    """Envía un mensaje de sistema y uno de usuario al modelo y devuelve el texto de respuesta."""
    clave, base, modelo = _config()
    if not hay_llm():
        raise RuntimeError("LLM_API_KEY o LLM_BASE_URL no configuradas")

    cuerpo = json.dumps({
        "model": modelo,
        "messages": [{"role": "system", "content": sistema},
                     {"role": "user", "content": usuario}],
        "temperature": 0.2,
    }).encode("utf-8")
    peticion = urllib.request.Request(
        f"{base}/chat/completions",
        data=cuerpo,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {clave}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # El cuerpo del error no incluye la clave; se recorta por si es largo
        detalle = error.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"LLM respondió {error.code}: {detalle}") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"No se pudo contactar con el LLM: {error}") from None

    texto = (datos.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    if not texto.strip():
        raise RuntimeError("El LLM devolvió una respuesta vacía")
    return texto


def _extraer_json(texto: str) -> dict | list:
    # Algunos modelos razonan entre etiquetas <think> antes de responder
    texto = re.sub(r"<think>[\s\S]*?</think>", "", texto).strip()
    candidatos = [texto]
    bloque = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", texto)
    if bloque:
        candidatos.append(bloque.group(1))
    llaves = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", texto)
    if llaves:
        candidatos.append(llaves.group(0))
    for candidato in candidatos:
        try:
            return json.loads(candidato.strip())
        except json.JSONDecodeError:
            continue
    raise ValueError("La respuesta no contiene un JSON válido")


def llamar_llm_json(sistema: str, usuario: str, timeout: float = TIMEOUT_SEG) -> dict | list:
    """Igual que llamar_llm, pero devuelve el JSON de la respuesta.

    El timeout es el tiempo total. Solo reintenta, una vez, si el JSON no es válido y queda
    margen; un fallo de red sube enseguida.
    """
    inicio = time.monotonic()
    texto = llamar_llm(sistema, usuario, timeout)
    try:
        return _extraer_json(texto)
    except ValueError:
        restante = timeout - (time.monotonic() - inicio)
        if restante < 3:
            raise
        texto = llamar_llm(sistema, usuario + "\n\nResponde solo con JSON válido.", restante)
        return _extraer_json(texto)


if __name__ == "__main__":
    # Prueba de conexión: python3 -m backend.ia.llm
    _, base, modelo = _config()
    print(f"Clave configurada: {'sí' if hay_llm() else 'no'} · URL: {base} · Modelo: {modelo}")
    if hay_llm():
        inicio = time.time()
        resultado = llamar_llm_json("Responde solo con JSON.",
                                    'Devuelve {"ok": true, "saludo": "hola"}')
        print(f"Respuesta en {time.time() - inicio:.1f} s: {resultado}")
