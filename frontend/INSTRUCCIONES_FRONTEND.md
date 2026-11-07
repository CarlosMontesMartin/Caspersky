# Instrucciones del frontend (UAB 1)

Trabaja SOLO dentro de frontend/. No modifiques nada fuera (ni contratos/, ni backend/, ni CONTEXT.md).

## 0. Antes de escribir código
Lee y respeta al pie de la letra, por este orden de prioridad:
1. contratos/modulos.md (sección 6 "frontend/" y sección 1 "Formatos nuevos"). MANDA SOBRE TODO LO DEMÁS.
2. CONTEXT.md, contratos/formatos.md y contratos/ejemplos/*.json
Si algo no está en esos documentos, no lo inventes: pregúntame.
Usa EXACTAMENTE los nombres de archivos, funciones, campos y valores de los contratos.
NO hay Typeform. NO hay base de datos.

## 1. Tecnología (obligatorio)
- HTML + CSS + JavaScript puro, SIN compilación: nada de React, Vite, npm ni Tailwind.
  FastAPI sirve frontend/ como estáticos en "/".
- Archivos: index.html, crear.html, dashboard.html, responder.html, css/estilos.css, js/api.js
  (puedes añadir js/<pagina>.js por página si lo necesitas).
- Rutas a recursos SIEMPRE absolutas (/css/estilos.css, /js/api.js), porque responder.html
  se sirve en /responder/{id} y las rutas relativas fallarían.
- Las llamadas a la API van al mismo origen (rutas relativas tipo "/encuestas"), sin URL fija.
- Ninguna página llama a fetch directamente: todo pasa por js/api.js.

## 2. js/api.js
Exactamente estas funciones. Todas devuelven la promesa con el JSON y lanzan Error(detail)
si la respuesta no es ok (detail viene en el JSON de error de FastAPI).
- listarEncuestas()                     GET  /encuestas
- generarEncuesta(necesidad)            POST /encuestas/generar
- obtenerEncuesta(id)                   GET  /encuestas/{id}
- guardarEncuesta(encuesta)             PUT  /encuestas/{id}
- aprobarEncuesta(id)                   POST /encuestas/{id}/aprobar
- publicarEncuesta(id)                  POST /encuestas/{id}/publicar
- obtenerAnalisis(id)                   GET  /encuestas/{id}/analisis
- obtenerRecomendaciones(id)            GET  /encuestas/{id}/recomendaciones
- obtenerEncuestaPublica(id)            GET  /publico/encuestas/{id}
- enviarRespuesta(id, respuestaEntrada) POST /publico/encuestas/{id}/respuestas

Constante USAR_EJEMPLOS = true mientras el backend no esté listo: devuelve los JSON de
/ejemplos/ (encuesta.json, analisis.json, recomendaciones.json…) y simula en memoria el
paso borrador -> aprobada -> publicada. Como no hay ejemplo de ResumenEncuesta ni de
EncuestaPublica, constrúyelos a partir de encuesta.json con los campos exactos de
modulos.md sección 1 (turnos ["manana","tarde","noche"] para planta, ["sin_turno"] para el resto).

Formatos que envía el frontend (modulos.md):
- Necesidad: { objetivo, colectivo, contexto, duracion_max_seg, temas_prohibidos }
- RespuestaEntrada: { turno, canal, valores: { p1: 2, ... }, comentario }
  canal: "qr" o "quiosco".

## 3. Línea visual ("Mediterráneamente"), en css/estilos.css
- Variables CSS en :root: fondo blanco y arena/crema (#FAF7F2, #F3EDE3), bordes finos
  oscuros (1px, rgba(42,26,26,.12)), texto #2A1A1A, rojo Damm #B5121B.
- Titulares en serif elegante (Google Fonts "Fraunces"); texto en "Inter".
- Rojo SOLO para la marca, badges, segmentos no representativos y alertas. Nunca fondos rojos.
- Mucho aire, tarjetas limpias, estética de web de marca, no de panel saturado.
- Sin logos ni imágenes descargadas de webs de Damm: solo el texto "Damm" en serif.
- @media print para el cartel: solo título, QR grande y "2 minutos, anónimo".

## 4. Páginas [MVP]

### index.html  (/)
Lista de encuestas (listarEncuestas): título, colectivo, estado como badge y nº de respuestas.
Borrador o aprobada -> enlace a crear.html?id=<id>. Publicada -> enlace a dashboard.html?id=<id>.
Botón "Nueva necesidad" -> crear.html.

### crear.html  (/crear.html y /crear.html?id=)
Una sola página con 3 pasos visibles uno debajo de otro:
- Paso 1 · Necesidad: formulario Necesidad. colectivo: select con planta, logistica,
  comercial, oficina, manager. temas_prohibidos: separados por comas -> array.
  Si existe sessionStorage["necesidad_prefill"], rellena el formulario con él y bórralo.
  Botón "Generar" -> generarEncuesta, mostrando "Generando…" mientras tanto.
- Paso 2 · Revisar: cada pregunta con su texto editable (input) y botón "Borrar".
  Muestra tipo y dimension como badges (solo lectura en el MVP), las opciones y el
  tiempo_estimado_seg. Aviso visible: "La IA propone, tú decides".
  Botones "Guardar" (guardarEncuesta) y "Aprobar" (aprobarEncuesta).
  Si se edita algo después de aprobar, hay que volver a guardar y aprobar
  (el servidor la devuelve a borrador).
- Paso 3 · Publicar: deshabilitado salvo si el estado es "aprobada". Botón "Publicar" ->
  publicarEncuesta y muestra: la url con botón copiar, el QR con <img src={encuesta.qr}>,
  "Imprimir cartel" (window.print()) y "Abrir modo quiosco" (url + "?canal=quiosco").
Con ?id= carga la encuesta (obtenerEncuesta) y empieza en el paso que toque según su estado.
Muestra los errores (409, 422) del servidor en un aviso, sin romper la página.

### dashboard.html  (/dashboard.html?id=)
Carga obtenerAnalisis y obtenerRecomendaciones. Orden:
1. Alertas arriba (tipo representatividad | caida | tema_emergente).
2. n_respuestas y periodos (periodo_actual y periodo_anterior, que puede ser null).
3. Participación por colectivo y turno: respuestas, personas, tasa en %; los no
   representativos en rojo con badge "No representativo". Barras hechas con CSS (div con width).
4. Medias por pregunta (barras CSS de 1 a 5, con n).
5. Temas: tarjeta por tema con n, resumen y tendencia (↑ para nuevo y sube, → estable, ↓ baja;
   badge "Nuevo" para nuevo).
6. Bloque "Límites del análisis" con analisis.limites y el texto fijo
   "Segmentos con menos de 5 respuestas ocultos".
7. Debajo, Recomendaciones: tarjetas con titulo, motivo y tema, marcadas como
   "Propuesta para que RRHH decida". Botón "Crear encuesta de seguimiento": guarda
   recomendaciones.seguimiento en sessionStorage["necesidad_prefill"] (JSON.stringify)
   y abre crear.html.
Nunca muestres respuestas ni comentarios individuales.

### responder.html  (/responder/{id} y /responder/{id}?canal=quiosco)
Móvil primero. Lee el id del último segmento de location.pathname y el canal de
?canal= (por defecto "qr"). Carga obtenerEncuestaPublica(id).
En UNA sola página:
- Título, intro y el texto de transparencia.
- Selector de turno con botones grandes SOLO si encuesta.turnos tiene más de uno
  (si no, usa el único valor). Etiquetas: Mañana, Tarde, Noche, Sin turno.
- Todas las preguntas: escala_1_5 con 5 caritas grandes (valor 1-5), si_no con dos
  botones, opcion con botones, texto con textarea y aviso
  "No escribas nombres ni datos personales".
- "Enviar" -> enviarRespuesta(id, { turno, canal, valores, comentario }).
  El texto de las preguntas de tipo texto va también en comentario.
- Pantalla "¡Gracias!". Si canal = quiosco: letra y botones extra grandes y, a los 5 s,
  vuelve al inicio con todo vacío.
- No guardes nada en localStorage, sessionStorage ni cookies sobre quien responde.

## 5. [Después] (solo cuando el ciclo completo funcione con el backend, objetivo H12)
1. dashboard.html: selector "Vista analítica / Vista de instalaciones". La de instalaciones
   es un mapa isométrico en SVG inline (sin librerías) con 5 zonas: Fábrica (planta),
   Almacén (logistica), Oficinas (oficina) con planta superior Dirección (manager) y
   furgonetas (comercial). Color según la tasa de participación; hover/clic -> panel con
   la participación y alertas de ese colectivo. Si la encuesta es de un colectivo, muestra
   sus turnos. Usa solo campos que ya existen en Analisis. Segmentos con respuestas < 5:
   atenuados con "Oculto por privacidad (n<5)".
2. crear.html: reordenar y añadir preguntas, editar tipo y opciones.
3. responder.html: preguntas una a una y respetar condicion.

## 6. Orden de trabajo
1) css/estilos.css + js/api.js con USAR_EJEMPLOS = true.
2) index.html y dashboard.html.  3) crear.html.  4) responder.html.
Comprueba al final el ciclo con ejemplos:
index -> crear (generar, editar, aprobar, publicar) -> responder -> dashboard ->
"Crear encuesta de seguimiento" vuelve a crear.html prerrellenado.
Después pon USAR_EJEMPLOS = false y prueba contra el backend con ./run.sh (http://localhost:8000).
Nunca pongas tokens ni claves en el código. Al hacer commit usa solo: git add frontend
