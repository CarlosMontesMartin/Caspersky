# API · contrato (Tech Lead)

Base: http://localhost:8000 · JSON en todas las peticiones y respuestas.
Errores: 404 si la encuesta no existe, 409 si el estado no permite la acción.
Estados de una Encuesta: borrador -> aprobada -> publicada (solo hacia delante).

| Endpoint | Recibe | Devuelve | Quién lo usa |
|---|---|---|---|
| POST /encuestas/generar | Necesidad | Encuesta en borrador | Pantalla 1 → 2 |
| GET /encuestas/{id} | — | Encuesta | Pantalla 2 y /responder/{id} |
| PUT /encuestas/{id} | Encuesta editada (solo en borrador) | Encuesta | Pantalla 2 |
| POST /encuestas/{id}/aprobar | — | Encuesta aprobada (solo desde borrador) | Pantalla 2 |
| POST /encuestas/{id}/publicar | — | Encuesta con url y qr (solo si está aprobada) | Pantalla 3 |
| POST /encuestas/{id}/respuestas | RespuestaNueva (solo si está publicada) | {"ok": true} | /responder/{id} |
| GET /encuestas/{id}/analisis | — | Analisis | Pantalla 4 |
| GET /encuestas/{id}/recomendaciones | — | Recomendaciones | Pantalla 5 |

Eliminado: POST /encuestas/{id}/sincronizar (ya no hay Typeform).

## Detalles

PUT: el servidor ignora id, estado, url y qr que lleguen en el cuerpo.

publicar: url = http://<host>/responder/{id}?canal=qr · qr = imagen PNG como
data URL ("data:image/png;base64,...") que el frontend pinta con <img src=...>.

RespuestaNueva (lo que envía la pantalla /responder/{id}):
{ "turno": "noche", "canal": "qr", "valores": { "p1": 2, "p2": "no", "p3": "Los descansos", "p4": "texto libre" } }
- turno: lo elige la persona en una primera pantalla fija del formulario (no es una pregunta de la Encuesta).
- canal: se lee del parámetro ?canal= de la URL (qr | quiosco | teams).
- El servidor añade id, encuesta_id, fecha, periodo, colectivo y centro_tipo,
  pasa el texto de la pregunta de tipo "texto" por anonimizar() y lo guarda en comentario.
- centro_tipo se deriva del colectivo: planta -> fabrica, logistica -> almacen, resto -> oficina.

Analisis: representativo = respuestas >= 5 y tasa >= 0.20.
