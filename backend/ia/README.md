# Integración con modelos de lenguaje

## Archivos
- `__init__.py`: Definición del paquete Python.
- `llm.py`: Cliente de llamada al modelo e invocación con salida estructurada en JSON.
- `generar.py`: Generación y validación de microencuestas adaptadas al colectivo.
- `analizar.py`: Clasificación temática de comentarios, resúmenes y tendencias.
- `recomendar.py`: Propuestas de acción y configuración de encuestas de seguimiento.
- `probar_generar.py`: Pruebas de integración para la generación de encuestas.
- `probar_analizar.py`: Pruebas de análisis temático y recomendaciones.

## Variables de entorno
- `LLM_API_KEY`: clave del equipo.
- `LLM_BASE_URL`: por defecto `https://dcc-llm-gw.uab.cat/uabthehack/v1`.
- `LLM_MODEL`: `ornith` (único modelo disponible en el evento).

Si no se configura una clave, el sistema opera en modo de respaldo determinista mediante reglas y plantillas predefinidas.

## Pruebas
```bash
python3 -m backend.ia.probar_generar
python3 -m backend.ia.probar_analizar
python3 -m backend.ia.llm        # prueba de conexión con el modelo
```
