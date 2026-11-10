# Configuración

## Variables de entorno

Copia `.env.example` a `.env` (excluido de git). Todas son opcionales: sin ninguna, la aplicación funciona en local con el respaldo sin IA.

| Variable | Uso | Ejemplo |
|---|---|---|
| `BASE_URL` | Dirección pública de la app. La usan los QR y los botones de Teams. | `http://localhost:8000` |
| `LLM_API_KEY` | Clave del proveedor del modelo. Vacía = respaldo por reglas. | *(secreta)* |
| `LLM_BASE_URL` | URL base de una API compatible con OpenAI, **sin** `/chat/completions`. | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | Modelo que se usa. | `openai/gpt-oss-120b` |
| `MODO_DEMO` | `1` activa la simulación de respuestas. | `1` |
| `TEAMS_WEBHOOK_URL` | URL del flujo de Power Automate «Post to a channel when a webhook request is received». Vacía = solo vista previa. | *(secreta)* |

Comprobación: `http://localhost:8000/salud` devuelve `"llm": true` cuando el modelo está configurado.

## Abrir el formulario desde un móvil

Los QR apuntan a `BASE_URL`, así que el móvil tiene que poder llegar al ordenador:

1. **Misma red wifi.** `BASE_URL=http://<IP del ordenador>:8000`. `run.py` muestra la IP al arrancar.
2. **Punto de acceso del móvil.** Útil cuando la wifi aísla los dispositivos entre sí (habitual en eventos y redes corporativas). Conecta el ordenador al punto de acceso y usa la IP que asigna.
3. **Túnel https temporal**, por ejemplo `cloudflared tunnel --url http://localhost:8000`, con su URL en `BASE_URL`. Expone la aplicación a internet: úsalo solo mientras haga falta.

Tras cambiar `BASE_URL`, reinicia el servidor y vuelve a publicar la encuesta para regenerar los QR.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Todo aparece como «Sin IA» | Falta `LLM_API_KEY` o el servidor no se reinició tras editar `.env`. Revisa `/salud`. |
| Error 404 del proveedor del modelo | `LLM_BASE_URL` termina en `/chat/completions`. Debe acabar en `/v1`: el cliente añade la ruta. |
| `Invalid API Key` | La clave no es válida, se revocó o no está en el `.env` que lee el servidor. |
| Las llamadas fallan desde el navegador | La página se abrió con Live Server u otro servidor estático. Usa siempre `http://localhost:8000`. |
| Cambios que no aparecen | Reinicia el servidor tras `git pull` y recarga con Ctrl+Shift+R. |
| Empezar de cero | Para el servidor, borra `backend/datos/almacen/` y vuelve a arrancar: se recargan los datos sintéticos. |
