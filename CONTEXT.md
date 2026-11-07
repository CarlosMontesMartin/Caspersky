# Contexto del proyecto (pegar al inicio de cada prompt a la IA)

## Producto
Plataforma de escucha activa para el reto de Damm (UAB The Hack 2026).
Ciclo: RRHH describe una necesidad -> la IA genera una microencuesta adaptada a un colectivo
-> RRHH la edita y aprueba -> se publica con enlace y QR a nuestro propio formulario
-> se recogen respuestas (móvil por QR o modo quiosco) -> análisis (participación,
representatividad, temas, alertas) -> recomendaciones -> nueva encuesta de seguimiento.
No usamos Typeform ni base de datos SQL.

## Reglas no negociables
- Solo datos sintéticos. Nunca nombres, correos, teléfonos ni datos reales.
- Todo comentario pasa por anonimizar() (backend/datos/anonimizar.py) antes de guardarse.
- Solo resultados agregados. Ningún segmento con menos de 5 respuestas muestra medias,
  temas ni comentarios (los recuentos de participación sí se muestran).
- La IA nunca publica sin aprobación humana (publicar sin aprobar = error 409).
- No se guarda nada que identifique a quien responde (ni IP ni user agent).
- Los tokens solo en .env (nunca en el código ni en el repositorio).

## Carpetas y dueños (no toques archivos fuera de tu carpeta)
- CONTEXT.md, contratos/  Tech Lead (solo lectura para el equipo)
- frontend/         UAB 1  pantallas de RRHH y pantalla /responder/{id} (móvil y quiosco)
- backend/api/      UPC 2  servidor y endpoints (Python + FastAPI)
- backend/datos/    UPC 2  almacenamiento en JSON, métricas, anonimización
- backend/ia/       UPC 1  generar_encuesta, analizar_comentarios, recomendar
- datos_sinteticos/ UPC 1  generador y datos_sinteticos/respuestas.json
- contenido/        UAB 2  reglas por colectivo, plantilla.json, textos, escenarios
- pitch/            UAB 2

## Encuestas y sectores
- Cada encuesta va dirigida a UN colectivo: planta, logistica, comercial, oficina o manager.
  Si RRHH quiere preguntar a varios colectivos, se generan varias encuestas.
- Cada Respuesta guarda colectivo, turno, canal y periodo: así se comparan turnos dentro
  de una encuesta y colectivos o periodos entre encuestas.
- Excepción: enc_000 "Pulso de clima general", con colectivo "todos", contiene el histórico
  sintético de los 5 colectivos y 2 periodos (escenario C). Es el único caso con "todos".
- centro_tipo se deriva del colectivo: planta -> fabrica, logistica -> almacen, resto -> oficina.

## Almacenamiento (JSON, sin base de datos)
backend/datos/almacen/            se crea solo al arrancar · está en .gitignore
  encuestas/<encuesta_id>.json    una Encuesta
  respuestas/<encuesta_id>.json   lista de Respuesta de esa encuesta
- Solo backend/datos/ lee y escribe estos archivos; el resto usa la API.
- Al arrancar con almacen/ vacío se cargan los datos sintéticos de
  datos_sinteticos/respuestas.json (lista de Respuesta, cada una con su encuesta_id),
  pasando cada comentario por anonimizar().
- Reiniciar los datos: rm -rf backend/datos/almacen y ./run.sh

## Cómo trabajamos
- Arranque: ./run.sh desde la raíz (crea .venv, instala y levanta la API en :8000).
  Si da "Permiso denegado": chmod +x run.sh
- Documentación interactiva de la API: http://localhost:8000/docs
- Tests del backend: python -m pytest -q backend/datos
- Todos en main: git pull --rebase y comprobar ./run.sh antes de cada push.
- Nunca git add . : añade solo tus carpetas (git add backend/ia, git add frontend...).

## Formatos y API
Ver contratos/formatos.md, contratos/api.md y contratos/ejemplos/.
Usa exactamente esos nombres de campo y valores.