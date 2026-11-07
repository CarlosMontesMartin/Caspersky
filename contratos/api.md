# Endpoints (los implementa UPC 2 llamando a backend/ia de UPC 1; los usa UAB 1)

| Endpoint                            | Recibe           | Devuelve                                   | Pantalla |
|-------------------------------------|------------------|--------------------------------------------|----------|
| POST /encuestas/generar             | Necesidad        | Encuesta (borrador)                        | 1 -> 2   |
| PUT  /encuestas/{id}                | Encuesta editada | Encuesta                                   | 2        |
| POST /encuestas/{id}/aprobar        | -                | Encuesta (aprobada)                        | 2        |
| POST /encuestas/{id}/publicar       | -                | Encuesta con url y qr (solo si aprobada)   | 3        |
| POST /encuestas/{id}/sincronizar    | -                | {"nuevas": n} respuestas leídas de Typeform| 4        |
| GET  /encuestas/{id}/analisis       | -                | Analisis                                   | 4        |
| GET  /encuestas/{id}/recomendaciones| -                | Recomendaciones                            | 5        |

Funciones de UPC 1 (backend/ia):
- generar_encuesta(necesidad, reglas) -> Encuesta
- analizar_comentarios(respuestas, respuestas_periodo_anterior) -> lista de temas
- recomendar(analisis) -> Recomendaciones

Funciones de UPC 2 (backend/datos):
- anonimizar(texto) -> texto
- calcular_metricas(respuestas, plantilla) -> participacion, medias, alertas
