# Contexto del proyecto (pegar al inicio de cada prompt a la IA)

## Producto
Plataforma de escucha activa para el reto de Damm (UAB The Hack 2026).
Ciclo: RRHH describe una necesidad -> la IA genera una microencuesta adaptada al colectivo
-> RRHH la edita y aprueba -> se publica con enlace y QR a nuestro propio formulario
-> se recogen respuestas (móvil por QR o modo quiosco) -> análisis (participación,
representatividad, temas, alertas) -> recomendaciones -> nueva encuesta de seguimiento.
No usamos Typeform: el formulario de respuesta es una pantalla del frontend.

## Reglas no negociables
- Solo datos sintéticos. Nunca nombres, correos, teléfonos ni datos reales.
- Todo comentario pasa por anonimizar() antes de guardarse.
- Solo resultados agregados. Ningún segmento con menos de 5 respuestas muestra medias,
  temas ni comentarios (los recuentos de participación sí se muestran).
- La IA nunca publica sin aprobación humana (publicar sin aprobar = error 409).
- No se guarda nada que identifique a quien responde (ni IP ni user agent).
- Los tokens solo en .env (nunca en el código ni en el repositorio).

## Carpetas y dueños (no toques archivos fuera de tu carpeta)
- contratos/        Tech Lead (solo lectura para el equipo)
- frontend/         UAB 1  pantallas de RRHH y pantalla /responder/{id} (móvil y quiosco)
- backend/api/      UPC 2  servidor y endpoints (Python + FastAPI)
- backend/datos/    UPC 2  base de datos SQLite, métricas, anonimización
- backend/ia/       UPC 1  generar_encuesta, analizar_comentarios, recomendar
- datos_sinteticos/ UPC 1  generador y datos_sinteticos/respuestas.json
- contenido/        UAB 2  reglas por colectivo, plantilla, textos, escenarios
- pitch/            UAB 2

## Cómo trabajamos
- Arranque: ./run.sh desde la raíz (crea .venv, instala y levanta la API en :8000).
- Documentación interactiva de la API: http://localhost:8000/docs
- Todos en main: git pull --rebase y comprobar ./run.sh antes de cada push.

## Formatos y API
Ver contratos/formatos.md, contratos/api.md y contratos/ejemplos/.
Usa exactamente esos nombres de campo y valores.
