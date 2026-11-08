# Integración con modelos de lenguaje

## Archivos
- `llm.py`: cliente del modelo (API compatible con OpenAI) y salida en JSON.
- `generar.py`: encuestas para uno o varios colectivos (núcleo común y preguntas por sector) y su validación.
- `analizar.py`: clasificación de comentarios (palabras clave al momento, modelo en segundo plano), resúmenes y tendencias.
- `recomendar.py`: lectura ejecutiva, acciones con responsable, plazo e indicador, y encuesta de seguimiento.
- `informe.py`: Pregunta a tus datos (castellano, catalán e inglés) y preguntas sugeridas, solo con datos agregados.
- `traducir.py`: traducción de encuestas al catalán y al inglés, con los mismos ids y opciones.
- `plantillas_respaldo.py`: encuestas de respaldo (sin modelo) en castellano, catalán e inglés y temas prohibidos en cualquier idioma.
- `textos_respaldo.py`: textos de respaldo (sin modelo) en castellano, catalán e inglés; nombres de sectores, turnos y temas.
- `simulados.py`: comentarios simulados coherentes con cada encuesta para el modo demo.
- `segundo_plano.py`: llamadas lentas al modelo en segundo plano, con caché.
- `evaluar.py`: precisión de la clasificación frente a `tema_real`.
- `diagnostico.py`, `probar_generar.py`, `probar_analizar.py`: pruebas.
- `prompts/`: instrucciones de cada llamada al modelo.

Las reglas de las encuestas (límites de preguntas, segundos por tipo, duración mínima, idiomas) están en `backend/reglas.py`.

## Variables de entorno
- `LLM_API_KEY`: clave del equipo.
- `LLM_BASE_URL`: por defecto `https://dcc-llm-gw.uab.cat/uabthehack/v1`.
- `LLM_MODEL`: `ornith` (único modelo disponible en el evento).

## Idioma
Cada encuesta tiene un idioma original (`es`, `ca` o `en`): el de la pantalla de RRHH al generarla. `generar_encuesta(necesidad, reglas, idioma)` escribe en ese idioma (también el respaldo) y devuelve `idioma_original`; `traducir_encuesta(encuesta, idiomas_destino, idioma_origen)` traduce desde él a los otros dos. Las palabras clave de la clasificación cubren castellano, catalán e inglés.

`analizar_comentarios`, `resumir_tema`, `recomendar`, `sugerir_preguntas` y `preguntar` reciben `idioma` (`es`, `ca` o `en`, por defecto `es`): el de la pantalla de RRHH. Todo lo que redactan (también los textos de respaldo) sale en ese idioma, y el idioma forma parte de la clave de caché. `preguntar` responde en el idioma de la pregunta y, si no se puede detectar, en el de la pantalla. `banco_contextual` acepta `idioma` pero escribe siempre en castellano.

Cada texto de la IA lleva su origen: `ia`, `pendiente` (el modelo trabaja; la pantalla no lo muestra) o `reglas` (sin modelo o si ha fallado). Sin clave, todo funciona con reglas y no hay sugerencias ni traducciones.

## Pruebas
```bash
python3 -m backend.ia.probar_generar
python3 -m backend.ia.probar_analizar
python3 -m backend.ia.evaluar         # precisión para el pitch
python3 -m backend.ia.diagnostico     # conexión y tiempos con el modelo real
```
