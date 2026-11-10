# Decisiones técnicas

Registro breve de las decisiones que más condicionan el diseño: qué se decidió, por qué y qué se sacrifica.

### 1. Formulario propio en lugar de Typeform
El reto proponía publicar en Typeform. Se descartó porque el plan gratuito limita a 10 respuestas al mes y porque varias funciones necesitan controlar el formulario: el idioma original con traducciones, el canal de respuesta (QR, quiosco o Teams), el umbral de anonimato, la pantalla «Dijisteis → Hemos hecho» y no guardar nada de quien responde.
**Coste:** hay que mantener el formulario. La publicación está aislada en una ruta, así que volver a Typeform (u otro proveedor) es sustituir una pieza, no rehacer el flujo.

### 2. JSON en disco en lugar de base de datos
Cero instalación y datos fáciles de inspeccionar, que en un prototipo valen más que la concurrencia. Solo `backend/datos/almacen.py` toca el disco, de modo que migrar a PostgreSQL afecta a un único módulo.
**Coste:** no apto para escrituras concurrentes intensas. La concurrencia dentro del proceso se protege con un cerrojo.

### 3. Frontend sin framework ni compilación
HTML, CSS y módulos ES servidos por el propio backend: arranca con un comando, funciona sin internet (Three.js y Chart.js van en `vendor/`) y cualquiera puede leer el código sin herramientas.
**Coste:** más código repetido entre pantallas. Se mitiga con módulos compartidos (`api.js`, `ui.js`, `layout.js`, `i18n.js`).

### 4. La IA nunca es imprescindible
Cada función que usa un modelo tiene un respaldo determinista: plantillas por colectivo, clasificación por palabras clave y recomendaciones por reglas. La interfaz marca el origen de cada texto. Así, una caída del proveedor no rompe el producto y las pruebas no dependen de la red.
**Coste:** mantener dos caminos. Las pruebas automáticas se ejecutan siempre sin clave para que el respaldo nunca se degrade.

### 5. Cliente del modelo con la librería estándar
`backend/ia/llm.py` habla con cualquier API compatible con OpenAI (`/chat/completions`) usando `urllib`. Cambiar de proveedor (gateway del evento, Groq, Gemini…) es cambiar tres variables de entorno, sin dependencias nuevas.

### 6. Clasificación híbrida de comentarios
Las palabras clave clasifican al instante (en es, ca y en) y el modelo revisa todos los comentarios en segundo plano. El dashboard nunca espera al modelo y mejora en cuanto este termina. Los resultados se guardan en una caché en disco con claves sha256, sin comentarios en claro.

### 7. Núcleo común y preguntas por sector
Una sola encuesta para varios colectivos: 1–3 preguntas comunes, que permiten comparar sectores, y 1–3 preguntas propias de cada uno, con su vocabulario. Resuelve la tensión entre adaptar la encuesta a cada colectivo y poder compararlos. Los límites viven en `backend/reglas.py` y los usan tanto la generación como la validación.

### 8. Idioma original y traducción al aprobar
La encuesta se escribe en el idioma de quien la crea y se traduce a los otros dos al aprobarla. Las opciones se guardan siempre en el idioma original, de modo que el análisis no se parte por idiomas.

### 9. Anonimato que resiste restas
Ningún grupo con menos de 5 respuestas muestra medias, temas ni comentarios. Además, si un turno queda oculto, también se ocultan los demás turnos de su sector y las cifras globales lo excluyen, para que no se pueda deducir restando (supresión complementaria). La valoración global se ofrece también corregida por el peso real de cada colectivo en la plantilla (post-estratificación), con la diferencia explicada.

### 10. Las personas deciden
La IA propone encuestas, acciones y textos de compromiso, pero nada se publica sin aprobación y ningún compromiso llega a la plantilla sin que RRHH escriba qué se ha hecho y quién es responsable. «Pregunta a tus datos» solo recibe datos agregados y rechaza preguntas que busquen identificar a alguien.
