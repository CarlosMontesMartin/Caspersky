# API

API REST en FastAPI. Con el servidor arrancado, la documentación interactiva generada a partir del código está en **http://localhost:8000/docs** (Swagger) y **/redoc**. En [`ejemplos/`](ejemplos/) hay un JSON de ejemplo de cada respuesta.

Convenciones:
- Todas las respuestas son JSON. Los errores tienen la forma `{"detail": "..."}` y un código coherente: 422 datos no válidos, 404 no existe, 409 estado incorrecto (por ejemplo, publicar sin aprobar), 403 función desactivada y 502/503 servicio externo no disponible.
- El parámetro `?idioma=es|ca|en` traduce los textos generados por el servidor. El contenido de la encuesta se sirve en su idioma original o en su traducción.
- Los textos producidos por un modelo llevan `origen`: `ia`, `reglas` (respaldo determinista) o `pendiente` (el modelo aún trabaja en segundo plano).

## Encuestas y análisis

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/salud` | Estado del servidor y si hay modelo configurado. |
| GET | `/escenarios` | Escenarios predefinidos para empezar una encuesta. |
| GET | `/encuestas` | Lista de encuestas con estado y participación. |
| POST | `/encuestas/generar` | Genera un borrador a partir de una necesidad ([ejemplo](ejemplos/necesidad.json)). |
| POST | `/encuestas/{id}/regenerar` | Vuelve a generar el borrador con indicaciones nuevas. |
| POST | `/encuestas/{id}/duplicar` | Copia una encuesta como borrador nuevo (por ejemplo, para el seguimiento). |
| GET | `/encuestas/{id}` | Encuesta completa ([ejemplo](ejemplos/encuesta.json)). |
| PUT | `/encuestas/{id}` | Guarda las ediciones de RRHH. Valida las reglas de `backend/reglas.py`. |
| POST | `/encuestas/{id}/aprobar` | Aprobación humana. Lanza las traducciones. |
| POST | `/encuestas/{id}/publicar` | Publica y genera enlace y QR (general y por sector). |
| GET | `/encuestas/{id}/analisis` | Métricas agregadas con umbral de anonimato ([ejemplo](ejemplos/analisis.json)). |
| GET | `/encuestas/{id}/recomendaciones` | Acciones propuestas con responsable, plazo e indicador. |
| GET | `/encuestas/{id}/sugerencias` | Sugerencias de mejora para el borrador. |
| POST | `/encuestas/{id}/preguntar` | «Pregunta a tus datos»: respuesta en lenguaje natural sobre datos agregados. |
| POST | `/encuestas/{id}/simular` | Genera respuestas sintéticas (solo con `MODO_DEMO=1`; si no, 403). |

## Formulario público

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/publico/encuestas/{id}` | Versión pública de una encuesta publicada, sin datos internos ([ejemplo](ejemplos/encuesta_publica.json)). |
| POST | `/publico/encuestas/{id}/respuestas` | Envía una respuesta. Se anonimizan los comentarios antes de guardar ([ejemplo](ejemplos/respuesta_entrada.json)). |

## Compromisos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/encuestas/{id}/compromisos/borrador` | Propuesta de texto «Dijisteis → Hemos hecho» ([ejemplo](ejemplos/compromiso_borrador.json)). |
| POST | `/encuestas/{id}/compromisos` | Crea un compromiso firmado por RRHH. |
| GET | `/encuestas/{id}/compromisos` | Compromisos de una encuesta. |
| POST | `/compromisos/{id}/hecho` | Marca un compromiso como cumplido. |
| GET | `/compromisos/{id}/seguimiento` | Compara el indicador antes y después del compromiso. |

## Microsoft Teams

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/integraciones` | Qué integraciones están configuradas. |
| GET | `/encuestas/{id}/teams/vista_previa` | Adaptive Card de la encuesta, sin enviarla. |
| POST | `/encuestas/{id}/teams/publicar` | Envía la encuesta al canal configurado. |
| POST | `/encuestas/{id}/teams/resumen` | Envía un resumen de resultados agregados. |
| GET | `/compromisos/{id}/teams/vista_previa` | Adaptive Card de un compromiso. |
| POST | `/compromisos/{id}/teams` | Envía el compromiso al canal. |

Sin `TEAMS_WEBHOOK_URL`, las rutas de envío responden 503 y las de vista previa siguen funcionando. Para revisar una tarjeta sin Teams, pega su JSON en el [Adaptive Cards Designer](https://adaptivecards.io/designer/).
