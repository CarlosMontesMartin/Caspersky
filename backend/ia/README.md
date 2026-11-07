# Integración con modelos de lenguaje

## Archivos
- `llm.py`: cliente del modelo (API compatible con OpenAI) y salida en JSON.
- `generar.py`: encuestas para uno o varios colectivos (núcleo común y preguntas por sector) y su validación.
- `analizar.py`: clasificación de comentarios (palabras clave al momento, modelo en segundo plano), resúmenes y tendencias.
- `recomendar.py`: lectura ejecutiva, acciones con responsable, plazo e indicador, y encuesta de seguimiento.
- `informe.py`: Pregunta a tus datos, solo con datos agregados.
- `simulados.py`: comentarios simulados coherentes con cada encuesta para el modo demo.
- `segundo_plano.py`: llamadas lentas al modelo en segundo plano, con caché.
- `evaluar.py`: precisión de la clasificación frente a `tema_real`.
- `diagnostico.py`, `probar_generar.py`, `probar_analizar.py`: pruebas.
- `prompts/`: instrucciones de cada llamada al modelo.

## Variables de entorno
- `LLM_API_KEY`: clave del equipo.
- `LLM_BASE_URL`: por defecto `https://dcc-llm-gw.uab.cat/uabthehack/v1`.
- `LLM_MODEL`: `ornith` (único modelo disponible en el evento).

Sin clave, todo funciona con reglas y plantillas de respaldo.

## Pruebas
```bash
python3 -m backend.ia.probar_generar
python3 -m backend.ia.probar_analizar
python3 -m backend.ia.evaluar         # precisión para el pitch
python3 -m backend.ia.diagnostico     # conexión y tiempos con el modelo real
```
