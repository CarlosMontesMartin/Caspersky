# Contexto del proyecto (pegar al inicio de cada prompt a la IA)

## Producto
Plataforma de escucha activa para el reto de Damm (UAB The Hack 2026).
Ciclo: RRHH describe una necesidad -> la IA genera una microencuesta adaptada al colectivo
-> RRHH la edita y aprueba -> se publica en Typeform con QR -> se recogen respuestas
-> análisis (participación, representatividad, temas, alertas) -> recomendaciones
-> nueva encuesta de seguimiento.

## Reglas no negociables
- Solo datos sintéticos. Nunca nombres, correos, teléfonos ni datos reales.
- Solo resultados agregados. Ningún segmento con menos de 5 respuestas se muestra.
- La IA nunca publica sin aprobación humana.
- Los tokens solo en .env (nunca en el código ni en el repositorio).

## Carpetas y dueños (no toques archivos fuera de tu carpeta)
- contratos/        Tech Lead (solo lectura para el equipo)
- frontend/         UAB 1
- backend/api/      UPC 2  servidor y endpoints
- backend/datos/    UPC 2  base de datos, métricas, anonimización
- backend/typeform/ UPC 2  publicar y leer en Typeform
- backend/ia/       UPC 1  generar_encuesta, analizar_comentarios, recomendar
- datos_sinteticos/ UPC 1  generador de datos
- contenido/        UAB 2  reglas por colectivo, plantilla, textos, escenarios
- pitch/            UAB 2

## Formatos y API
Ver contratos/formatos.md, contratos/api.md y contratos/ejemplos/.
Usa exactamente esos nombres de campo y valores.
