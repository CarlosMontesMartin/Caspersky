# API · contrato (Tech Lead)

La referencia completa de la API está en **modulos.md, sección 3**
(rutas, qué recibe y devuelve cada una, errores). Este archivo solo resume.

Base: http://localhost:8000 · Documentación interactiva: http://localhost:8000/docs
Errores: `{"detail": "mensaje"}` con 404 (no existe), 409 (estado no permite la acción)
o 422 (datos no válidos).

## Pantallas de RRHH

| Método y ruta | Recibe | Devuelve |
|---|---|---|
| GET /salud | — | `{"ok": true, "llm": bool}` |
| GET /encuestas | — | lista de ResumenEncuesta |
| POST /encuestas/generar | Necesidad | Encuesta en borrador |
| GET /encuestas/{id} | — | Encuesta |
| PUT /encuestas/{id} | Encuesta | Encuesta (409 si está publicada; si estaba aprobada vuelve a borrador) |
| POST /encuestas/{id}/aprobar | — | Encuesta aprobada (422 si no tiene 1–6 preguntas válidas) |
| POST /encuestas/{id}/publicar | — | Encuesta con url y qr (409 si no está aprobada) |
| GET /encuestas/{id}/analisis | — | Analisis (con periodo_actual y periodo_anterior) |
| GET /encuestas/{id}/recomendaciones | — | Recomendaciones |

## Quien responde

| Método y ruta | Recibe | Devuelve |
|---|---|---|
| GET /publico/encuestas/{id} | — | EncuestaPublica (404 si no está publicada) |
| POST /publico/encuestas/{id}/respuestas | RespuestaEntrada | `{"ok": true}` |

## Páginas servidas por el backend

- `/` → `frontend/` (index.html por defecto)
- `/responder/{id}` → `frontend/responder.html` (canal por `?canal=quiosco`, por defecto qr)
- `/ejemplos/…` → `contratos/ejemplos/`
- `url` de una encuesta publicada = `BASE_URL` (en `.env`, por defecto http://localhost:8000) + `/responder/{id}`
