# Contexto del proyecto (pegar al inicio de cada prompt a la IA)

## Producto
Plataforma de escucha activa para el reto de Damm (UAB The Hack 2026).
Ciclo: RRHH describe una necesidad -> la IA genera una microencuesta adaptada a un colectivo
-> RRHH la edita y aprueba -> se publica con enlace y QR a nuestro propio formulario
-> se responde desde el móvil (QR) o en modo quiosco -> análisis (participación,
representatividad, medias, temas, alertas, límites) -> recomendaciones -> encuesta de seguimiento.
No usamos Typeform ni base de datos SQL: todo se guarda en archivos JSON.

## Documentos de referencia (en este orden)
1. modulos.md: archivos, funciones, firmas, rutas y qué hace cada cosa. Si algo no está ahí, se pregunta.
2. contratos/formatos.md y contratos/ejemplos/: formatos JSON exactos.
3. contratos/api.md: resumen de la API (detalle en modulos.md, sección 3).
4. Diseño del frontend: contratos/diseno.md

## Reglas no negociables
- Solo datos sintéticos. Nunca nombres, correos, teléfonos ni datos reales.
- Todo texto libre pasa por anonimizar() antes de guardarse.
- Solo resultados agregados: ningún segmento con menos de 5 respuestas muestra medias,
  temas ni comentarios (los recuentos de participación sí se muestran).
- La IA nunca publica sin aprobación humana (publicar sin aprobar = error 409).
- No se guarda nada que identifique a quien responde (ni IP ni user agent ni hora exacta).
- Todo funciona SIN clave de IA (modo de respaldo): el demo nunca depende de la red.
- Los tokens solo en .env (nunca en el código ni en el repositorio).

## Carpetas y dueños (no toques archivos fuera de tu carpeta)
- CONTEXT.md, modulos.md, contratos/   Tech Lead (solo lectura para el equipo)
- backend/api/      UPC 2  FastAPI: rutas, QR, validación, puente con la IA
- backend/datos/    UPC 2  almacén JSON, métricas, anonimización, tests
- backend/ia/       UPC 1  llm, generar, analizar, recomendar (firmas en modulos.md)
- datos_sinteticos/ UPC 1  generar.py -> enc_000.json y respuestas.json
- frontend/         UAB 1  HTML + CSS + JS sin compilación; todo fetch pasa por js/api.js
- contenido/        UAB 2  reglas_colectivos.md, plantilla.json, transparencia.md, escenarios_demo.md
- pitch/            UAB 2

## Cómo se ejecuta
- ./run.sh desde la raíz: crea .venv, instala y arranca en http://localhost:8000
  (si da "Permiso denegado": chmod +x run.sh).
- El backend sirve también el frontend: http://localhost:8000/ (index.html),
  /responder/{id}, /ejemplos/… y la documentación en /docs.
- Datos: backend/datos/almacen/ (no se sube a git). Al arrancar vacío carga los sintéticos.
  Reiniciar datos: rm -rf backend/datos/almacen y ./run.sh
- Tests: python -m pytest -q backend/datos
- Demo con móvil: en .env pon BASE_URL=http://<IP del portátil>:8000 (misma wifi) para que el QR funcione.

## Git
- Todos en main. Una vez: git config pull.rebase true
- Antes de cada push: git pull y comprobar que ./run.sh arranca.
- Nunca git add . : añade solo tus carpetas.
