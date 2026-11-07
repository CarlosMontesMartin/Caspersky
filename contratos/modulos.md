# Módulos: archivos, funciones y qué hace cada uno

Documento del Tech Lead. Junto con `CONTEXT.md`, `contratos/formatos.md` y `contratos/ejemplos/`
es la referencia para todas las IAs del equipo. Si algo no está aquí, no se inventa: se pregunta.

Reglas para cualquier IA que lea esto:
- Implementa SOLO los archivos de tu carpeta. Los demás módulos se usan tal como se describen aquí.
- Entre módulos solo viajan `dict` / `list` de Python (o JSON) con los formatos de `contratos/`.
  Nada de clases propias en las interfaces.
- No cambies nombres de archivos, funciones, parámetros ni campos. Si hace falta un cambio, se pide al Tech Lead.
- Todo debe funcionar SIN clave de IA (modo de respaldo), para que el demo nunca dependa de la red.
- Implementa primero lo marcado **[MVP]**. Lo marcado **[Después]** no se empieza hasta que el ciclo
  completo funcione de principio a fin (objetivo: H12).

## Alcance

**[MVP]** — el ciclo completo, simple:
datos sintéticos → generar encuesta (IA o respaldo) → editar texto / borrar preguntas y aprobar →
publicar con enlace y QR → responder en el móvil → dashboard (participación, alerta de
representatividad, medias, temas con tendencia, límites) → recomendaciones y encuesta de seguimiento.

**[Después]**, por este orden y solo si el MVP funciona:
1. Alerta de caída de medias entre periodos.
2. Mejor resumen de temas y recomendaciones con IA real.
3. Reordenar y añadir preguntas en la edición.
4. Preguntas condicionales (`condicion`).
5. `evaluar.py` (precisión de la clasificación para el pitch).

**Fuera del código** (solo en el pitch): Teams / Microsoft 365, catalán, señales débiles.

---

## 0. Valores cerrados (añadidos a los de `formatos.md`)

| Campo | Valores |
|---|---|
| `tema` / `tema_real` | descansos, turnos, carga_trabajo, comunicacion, liderazgo, herramientas, formacion, reconocimiento, seguridad, ambiente, conciliacion, otros |
| `turno` por colectivo | planta: manana, tarde, noche · resto de colectivos: sin_turno |
| `centro_tipo` | planta → fabrica · logistica → almacen · resto → oficina (lo calcula el servidor) |
| `periodo` | "AAAA-MM". Encuesta: mes de creación. Respuesta: mes en que se responde |
| Ids | Encuestas `enc_000`, `enc_001`, `enc_002`… · Respuestas `r_` + 8 caracteres hex aleatorios |

Constantes (definidas en `backend/datos/metricas.py`, el resto las importa de ahí):
- `UMBRAL_MINIMO = 5` → un segmento con menos respuestas no muestra medias, temas ni comentarios.
- `TASA_REPRESENTATIVA = 0.20` → un segmento es representativo si tiene ≥ 5 respuestas y tasa ≥ 20 %.
- `UMBRAL_CAIDA = 0.5` → alerta de caída si una media baja 0,5 puntos o más respecto al periodo anterior.

---

## 1. Formatos nuevos (además de los de `contratos/formatos.md`)

```json
// ResumenEncuesta (para la lista de la pantalla inicial)
{ "id": "enc_001", "titulo": "", "colectivo": "planta", "estado": "publicada",
  "periodo": "2026-11", "n_respuestas": 37 }

// EncuestaPublica (lo que ve quien responde: sin datos internos)
{ "id": "enc_001", "titulo": "", "intro": "", "colectivo": "planta",
  "tiempo_estimado_seg": 90, "preguntas": [ /* igual que en Encuesta */ ],
  "turnos": ["manana", "tarde", "noche"],        // ["sin_turno"] si el colectivo no tiene turnos
  "transparencia": "texto de contenido/transparencia.md" }

// RespuestaEntrada (lo que envía la pantalla /responder)
{ "turno": "noche", "canal": "qr",               // qr | quiosco
  "valores": { "p1": 2, "p2": "texto libre" } }  // todas las preguntas, también la de texto
```

**Regla del texto libre:** cada encuesta tiene como máximo UNA pregunta de tipo `texto`. En la Respuesta
guardada, ese texto va SOLO en `comentario` (anonimizado) y no se repite en `valores`. `valores` solo
contiene `escala_1_5`, `opcion` y `si_no`. `analizar_comentarios` lee únicamente `comentario`.

```json

// Tema (salida de analizar_comentarios)
{ "tema": "descansos", "n": 57, "resumen": "", "tendencia": "sube" }

// Analisis: el de formatos.md con dos campos más
{ ..., "periodo_actual": "2026-10", "periodo_anterior": "2026-09" }   // anterior puede ser null
```

---

## 2. `backend/datos/` · UPC 2

### `almacen.py` · único módulo que lee y escribe archivos

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `inicializar()` | — | `None` | Crea `almacen/encuestas/` y `almacen/respuestas/` si no existen. Si están vacías, llama a `cargar_sinteticos()`. |
| `cargar_sinteticos()` | — | `int` (nº de respuestas cargadas) | Lee `datos_sinteticos/enc_000.json` (Encuesta) y `datos_sinteticos/respuestas.json` (lista de Respuesta). Pasa cada `comentario` y cada valor de texto por `anonimizar()` y lo guarda. |
| `nuevo_id_encuesta()` | — | `str` | Siguiente id libre: `enc_001`, `enc_002`… |
| `guardar_encuesta(encuesta)` | `dict` Encuesta | `dict` Encuesta | Escribe `encuestas/<id>.json` (sobrescribe). |
| `leer_encuesta(encuesta_id)` | `str` | `dict` Encuesta o `None` | |
| `listar_encuestas()` | — | `list[dict]` ResumenEncuesta | Ordenadas por id. `n_respuestas` = longitud de su archivo de respuestas. |
| `anadir_respuesta(encuesta_id, respuesta)` | `str`, `dict` Respuesta | `None` | Añade al final de `respuestas/<id>.json`. Asume que ya viene anonimizada. |
| `leer_respuestas(encuesta_id)` | `str` | `list[dict]` Respuesta | `[]` si no hay. |
| `leer_plantilla()` | — | `list[dict]` Plantilla | Lee `contenido/plantilla.json`. |
| `leer_reglas()` | — | `str` | Contenido de `contenido/reglas_colectivos.md` ("" si no existe). |
| `leer_transparencia()` | — | `str` | Contenido de `contenido/transparencia.md` ("" si no existe). |

### `anonimizar.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `anonimizar(texto)` | `str` o `None` | `str` | **[MVP]** Con expresiones regulares: correos → `[correo]`, teléfonos (9 cifras, con o sin +34 y espacios) → `[telefono]`, DNI/NIE → `[dni]`, y una lista de unos 50 nombres comunes en español y catalán → `[nombre]`. `None` → `""`. No toca nada más. |

### `metricas.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `separar_periodos(respuestas)` | `list` Respuesta | `(actual: list, anterior: list, periodo_actual: str, periodo_anterior: str \| None)` | Periodo actual = el más reciente que aparece; anterior = el inmediatamente previo. |
| `calcular_participacion(respuestas, plantilla, colectivo)` | `list`, `list`, `str` | `list` de `{colectivo, turno, respuestas, personas, tasa, representativo}` | Una fila por cada fila de la plantilla del colectivo (todas si `colectivo == "todos"`). Recuentos siempre visibles, aunque sean < 5. |
| `calcular_medias(respuestas, encuesta)` | `list`, `dict` Encuesta | `list` de `{pregunta, colectivo, media, n}` | Solo preguntas `escala_1_5`. Media redondeada a 1 decimal. Omite los segmentos con `n < UMBRAL_MINIMO`. |
| `calcular_alertas(participacion, medias_actual, medias_anterior)` | listas anteriores | `list` de `{tipo, mensaje}` | **[MVP]** `representatividad` por cada segmento no representativo. **[Después]** `caida` si una media baja ≥ `UMBRAL_CAIDA` (en el MVP, `medias_anterior` puede ignorarse). Mensajes en castellano, claros para RRHH (ej.: "El turno de noche de planta solo ha respondido un 7 %: los resultados pueden no representarle"). |
| `calcular_metricas(respuestas, plantilla, encuesta)` | `list`, `list`, `dict` | `dict` con `n_respuestas, periodo_actual, periodo_anterior, participacion, medias, alertas, limites` | Orquesta lo anterior sobre el periodo actual. `limites`: frases sobre muestra pequeña, segmentos ocultos y "una correlación no demuestra una causa". |

### `tests/` · `test_anonimizar.py`, `test_metricas.py`, `test_almacen.py`
Pytest. **[MVP]** solo `test_anonimizar.py`: correos, teléfonos y nombres desaparecen.
**[Después]** segmentos con < 5 no tienen media; la alerta de representatividad aparece con el turno de noche.

---

## 3. `backend/api/` · UPC 2

### `main.py`
- Crea la app FastAPI y llama a `almacen.inicializar()` al arrancar.
- CORS abierto (es local).
- Sirve `frontend/` como estáticos en `/` (index.html por defecto) y `contratos/ejemplos/` en `/ejemplos`.
- Ruta `GET /responder/{encuesta_id}` → devuelve el archivo `frontend/responder.html`.
- `BASE_URL` sale de `.env` (ej. `http://192.168.1.20:8000`, la IP del portátil del demo en la wifi). Por defecto `http://localhost:8000`.

### `rutas_encuestas.py` · pantallas de RRHH

| Método y ruta | Recibe | Devuelve | Errores | Qué hace |
|---|---|---|---|---|
| `GET /salud` | — | `{"ok": true, "llm": bool}` | | `llm` = `ia.llm.hay_llm()` |
| `GET /encuestas` | — | `list` ResumenEncuesta | | `almacen.listar_encuestas()` |
| `POST /encuestas/generar` | Necesidad | Encuesta (borrador) | 422 | `ia.generar.generar_encuesta(necesidad, almacen.leer_reglas())`, pone `id`, `estado="borrador"`, `periodo`, `url=None`, `qr=None` y la guarda. |
| `GET /encuestas/{id}` | — | Encuesta | 404 | |
| `PUT /encuestas/{id}` | Encuesta | Encuesta | 404, 409 si está publicada, 422 | Guarda la versión editada por RRHH (en el MVP: textos cambiados y preguntas borradas). Si estaba `aprobada`, vuelve a `borrador`. |
| `POST /encuestas/{id}/aprobar` | — | Encuesta | 404, 422 si no tiene 1–6 preguntas válidas | `estado="aprobada"`. |
| `POST /encuestas/{id}/publicar` | — | Encuesta con `url` y `qr` | 404, **409 si no está aprobada** | `url = BASE_URL + "/responder/" + id`, `qr = qr.generar_qr(url)`, `estado="publicada"`. |
| `GET /encuestas/{id}/analisis` | — | Analisis | 404 | `metricas.calcular_metricas(...)` + `temas = ia.analizar.analizar_comentarios(actual, anterior)`. |
| `GET /encuestas/{id}/recomendaciones` | — | Recomendaciones | 404 | `ia.recomendar.recomendar(analisis, encuesta)`. |

### `rutas_publico.py` · quien responde

| Método y ruta | Recibe | Devuelve | Errores | Qué hace |
|---|---|---|---|---|
| `GET /publico/encuestas/{id}` | — | EncuestaPublica | 404 si no existe o no está publicada | Añade `turnos` y `transparencia`. |
| `POST /publico/encuestas/{id}/respuestas` | RespuestaEntrada | `{"ok": true}` | 404, 422 (turno no válido para el colectivo, valor fuera de 1–5…) | Construye la Respuesta: `id` aleatorio, `fecha` de hoy, `periodo`, `colectivo` y `centro_tipo` de la encuesta. **Saca de `valores` la respuesta de la pregunta `texto`, la pasa por `anonimizar()` y la guarda en `comentario`** (`""` si no hay). Sin `tema_real`. No guarda IP, user agent ni hora exacta. |

### `qr.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `generar_qr(url)` | `str` | `str` | PNG del QR en `data:image/png;base64,...` (librería `qrcode`). |

---

## 4. `backend/ia/` · UPC 1

Todas las funciones devuelven datos válidos aunque no haya clave de IA o la IA falle:
en ese caso usan el **modo de respaldo** descrito en cada una.

### `llm.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `hay_llm()` | — | `bool` | `True` si `LLM_API_KEY` y `LLM_BASE_URL` tienen valor en `.env`. |
| `llamar_llm(sistema, usuario)` | `str`, `str` | `str` | Llama a la API del evento, compatible con OpenAI: `POST {LLM_BASE_URL}/chat/completions` con la librería estándar de Python (sin el paquete `openai`, para no añadir dependencias), cabecera `Authorization: Bearer {LLM_API_KEY}`, `model = LLM_MODEL` (por defecto `ornith`) y mensajes `system` + `user`. Timeout 30 s. Lanza excepción si falla. |
| `llamar_llm_json(sistema, usuario)` | `str`, `str` | `dict` o `list` | Llama a `llamar_llm`, extrae el primer bloque JSON del texto y lo parsea. Un reintento si el JSON no es válido. |

### `prompts/` · `generar.md`, `clasificar.md`, `resumir.md`, `recomendar.md`
Textos de los prompts de sistema. Cada uno exige responder solo en JSON con el formato exacto.

### `generar.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `generar_encuesta(necesidad, reglas)` | `dict` Necesidad, `str` reglas | `dict` Encuesta sin `id` | **[MVP]** Pide a la IA título, intro, 3–6 preguntas (`p1`, `p2`…), tipo, opciones, dimensión y tiempo estimado, siguiendo las reglas del colectivo. En el MVP `condicion` es siempre `null`. Después llama a `validar_encuesta`. |
| `validar_encuesta(encuesta, necesidad)` | `dict`, `dict` | `dict` corregida | **[MVP]** Fuerza: colectivo = el de la necesidad; 3–6 preguntas; tipos y dimensiones de la lista cerrada; `opciones` solo en `opcion`; `condicion = null`; **como máximo una pregunta `texto`**; ninguna pregunta que contenga un tema prohibido; `tiempo_estimado_seg ≤ duracion_max_seg` (≈ 15 s por escala/sí-no/opción, 30 s por texto; quita preguntas si se pasa). |
| Respaldo | | | Plantilla fija por colectivo: 3 escalas + 1 texto sobre el objetivo de la necesidad. |

### `analizar.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `clasificar_comentarios(textos)` | `list[str]` | `list[str]` (un tema por texto, mismo orden) | Clasificación híbrida en la lista cerrada de temas: primero las palabras clave por tema (ej. "descanso", "pausa" → descansos); solo los comentarios que no encajan en ninguna regla van a la IA, en lotes de 50. Sin IA, esos quedan como `otros`. |
| `resumir_tema(tema, textos)` | `str`, `list[str]` | `str` | 1–2 frases sobre lo que dicen, con una muestra de hasta 30 comentarios. Sin citas literales ni nada que identifique. Se genera en segundo plano y se cachea por encuesta y periodo: mientras no está listo, devuelve el respaldo "N comentarios sobre <tema>", y en la siguiente carga ya sale el resumen de la IA. Así el dashboard responde en unos 3 s. |
| `calcular_tendencia(n_actual, total_actual, n_anterior, total_anterior)` | `int`×4 | `str` | `nuevo` si antes < 2 y ahora ≥ 5 (tolera un comentario mal clasificado); `sube` / `baja` si el porcentaje cambia ±30 % o más; si no, `estable`. Sin periodo anterior → `estable`. |
| `analizar_comentarios(respuestas_actual, respuestas_anterior)` | `list` Respuesta ×2 | `list` Tema | Clasifica los comentarios no vacíos de ambos periodos, cuenta por tema, resume y calcula la tendencia. **Omite los temas con `n < 5`**. Orden: primero `nuevo` y `sube`, luego por `n`. |

### `recomendar.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `recomendar(analisis, encuesta)` | `dict` Analisis, `dict` Encuesta | `dict` Recomendaciones | 2–3 acciones concretas (título, motivo con el dato que la justifica, tema), priorizando alertas y temas `nuevo`/`sube`. `seguimiento` = Necesidad rellenada para el mismo colectivo, `duracion_max_seg` 60, centrada en el tema principal. Son propuestas: el texto nunca habla de personas concretas. Las acciones salen de reglas fijas por tema; la IA solo mejora la redacción, en segundo plano y con caché (igual que `resumir_tema`). |

### `evaluar.py` · después del MVP

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `precision_clasificacion(respuestas)` | `list` Respuesta con `tema_real` | `{"precision": float, "n": int, "por_tema": {tema: float}}` | Compara `clasificar_comentarios` con `tema_real`. Se ejecuta con `python -m backend.ia.evaluar` y el dato va al pitch. |

---

## 5. `datos_sinteticos/` · UPC 1

### `generar.py` · se ejecuta con `python datos_sinteticos/generar.py`

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `generar_encuesta_base()` | — | `dict` Encuesta | `enc_000` "Pulso de clima general", colectivo `todos`, estado `publicada`, periodo `2026-10`. Preguntas: p1 bienestar, p2 liderazgo, p3 desarrollo, p4 condiciones (carga y turnos), p5 entorno (todas `escala_1_5`) y p6 `texto` "¿Qué cambiarías?". |
| `generar_respuestas(semilla=42)` | `int` | `list` Respuesta | Unas 600 respuestas en periodos `2026-09` y `2026-10`, con `encuesta_id = "enc_000"` y `tema_real`. |
| `main()` | — | — | Escribe `datos_sinteticos/enc_000.json` y `datos_sinteticos/respuestas.json`. |

La historia que deben contar los datos (acordada con UAB 2 en `contenido/escenarios_demo.md`):
- Participación desigual: oficina ~45 %, comercial ~30 %, manager ~60 %, logística ~10 %, planta mañana/tarde ~25 %, **planta noche ~7 %**.
- En `2026-10`, planta: p4 baja ≥ 0,8 respecto a `2026-09`; temas **descansos** y **turnos** suben; **comunicacion** del cambio de turnos aparece como tema nuevo.
- Comentarios realistas: frases cortas, faltas, mezcla de castellano y catalán, algunos vacíos y ~5 % con datos personales inventados (nombres, correos falsos, teléfonos) para demostrar `anonimizar()`.

---

## 6. `frontend/` · UAB 1

HTML + CSS + JavaScript sin compilación (se abre tal cual servido por FastAPI).
Ninguna página llama a `fetch` directamente: todo pasa por `js/api.js`.

### `js/api.js`
Una función por endpoint; todas devuelven la promesa con el JSON y lanzan `Error(detail)` si falla.

| Función | Endpoint |
|---|---|
| `listarEncuestas()` | `GET /encuestas` |
| `generarEncuesta(necesidad)` | `POST /encuestas/generar` |
| `obtenerEncuesta(id)` | `GET /encuestas/{id}` |
| `guardarEncuesta(encuesta)` | `PUT /encuestas/{id}` |
| `aprobarEncuesta(id)` | `POST /encuestas/{id}/aprobar` |
| `publicarEncuesta(id)` | `POST /encuestas/{id}/publicar` |
| `obtenerAnalisis(id)` | `GET /encuestas/{id}/analisis` |
| `obtenerRecomendaciones(id)` | `GET /encuestas/{id}/recomendaciones` |
| `obtenerEncuestaPublica(id)` | `GET /publico/encuestas/{id}` |
| `enviarRespuesta(id, respuestaEntrada)` | `POST /publico/encuestas/{id}/respuestas` |

Mientras el backend no esté listo, `api.js` puede devolver los JSON de `/ejemplos/` (constante `USAR_EJEMPLOS = true`).

### Páginas [MVP]: solo 4

| Archivo | Ruta | Qué hace |
|---|---|---|
| `index.html` | `/` | Lista de encuestas (título, colectivo, estado, nº respuestas). Borrador o aprobada → enlace a `crear.html?id=`; publicada → enlace a `dashboard.html?id=`. Botón "Nueva necesidad" → `crear.html`. |
| `crear.html` | `/crear.html` y `/crear.html?id=` | Una sola página en 3 pasos visibles uno debajo de otro. **Paso 1 · Necesidad:** formulario Necesidad (si existe `sessionStorage["necesidad_prefill"]`, lo usa y lo borra) y botón "Generar" → `generarEncuesta`, mostrando "Generando…". **Paso 2 · Revisar:** cada pregunta con su texto editable y un botón "Borrar"; tiempo estimado; aviso "La IA propone, tú decides"; botones "Guardar" (`guardarEncuesta`) y "Aprobar" (`aprobarEncuesta`). **Paso 3 · Publicar:** activo solo si está aprobada; botón "Publicar" → muestra enlace, QR, "Imprimir cartel" (`window.print()`) y "Abrir modo quiosco" (`url + "?canal=quiosco"`). Con `?id=` carga esa encuesta y empieza en el paso que le toque según su estado. |
| `dashboard.html` | `/dashboard.html?id=` | Arriba, las alertas. Después: nº de respuestas y periodos; participación por colectivo y turno con los no representativos en rojo; medias por pregunta; temas con tendencia (↑ para nuevo/sube); bloque "Límites del análisis" y el texto "Segmentos con menos de 5 respuestas ocultos". **Debajo, las recomendaciones** (`obtenerRecomendaciones`), marcadas como propuestas, con el botón "Crear encuesta de seguimiento": guarda `seguimiento` en `sessionStorage["necesidad_prefill"]` y abre `crear.html`. |
| `responder.html` | `/responder/{id}` (y `?canal=quiosco`) | Móvil primero. Lee el id de la ruta y el canal de la URL (por defecto `qr`). Muestra la transparencia, el selector de turno (si hay más de uno) y todas las preguntas en una sola página, con caritas para `escala_1_5`. Envía con `enviarRespuesta` y muestra "Gracias". En quiosco, tras 5 s vuelve al inicio vacío. |
| `css/estilos.css` | | Estilos comunes, incluido `@media print` para el cartel (título, QR grande y "2 minutos, anónimo"). |

[Después] en `crear.html`: reordenar y añadir preguntas, y editar tipo y opciones. En `responder.html`: preguntas una a una y respetar `condicion`.

---

## 7. `contenido/` · UAB 2 (lo leen otros módulos: respetad el formato)

| Archivo | Lo lee | Formato |
|---|---|---|
| `reglas_colectivos.md` | `almacen.leer_reglas()` → prompt de `generar_encuesta` | Una sección `## <colectivo>` por colectivo con: número de preguntas, tiempo máximo, tono, tipos de pregunta preferidos, canal y qué evitar. |
| `plantilla.json` | `almacen.leer_plantilla()` y el generador de datos sintéticos | Lista Plantilla con estas 7 filas (1.400 personas en total): planta manana 300, planta tarde 280, planta noche 220, logistica 240, comercial 160, oficina 150, manager 50. Planta con 3 turnos; resto con `sin_turno`. |
| `transparencia.md` | `almacen.leer_transparencia()` → pantalla de respuesta | Texto plano, máximo 3 frases: para qué es, que es anónimo y que solo se ven resultados agregados. |
| `escenarios_demo.md` | Personas (UPC 1 para los datos, todos para ensayar) | Necesidades exactas que se escriben en el demo y qué debe verse en cada pantalla. |

---

## 8. Orden de integración

Juntad algo cada 2 horas, aunque sea con ejemplos. Si a H12 el ciclo no funciona de principio a fin con
el modo de respaldo, se deja de añadir cosas y solo se arregla.

1. **UPC 2**: `almacen.py` + `GET /salud` + `GET /encuestas` funcionando con `enc_000`.
2. **UPC 1**: `datos_sinteticos/generar.py` (sin esto no hay `enc_000`) y `generar_encuesta` en modo de respaldo.
3. **UAB 1**: `api.js` + `index.html` + `dashboard.html` con `enc_000` contra la API real.
4. **UAB 1**: `crear.html` y `responder.html`. Si va justo de tiempo, UPC 2 hace `responder.html` en cuanto termine la API.
5. Ciclo completo con respaldo (sin IA): crear → aprobar → publicar → responder → dashboard → recomendaciones.
6. Activar la IA real en `backend/ia/` sin cambiar ninguna firma.
7. Lo marcado [Después], por orden de la sección "Alcance".
8. Cualquier campo nuevo → se pide al Tech Lead, que actualiza `contratos/` y este documento.

---

## 9. Simulación de respuestas y prueba automática del ciclo · [MVP]

Objetivo: poder comprobar el análisis sin responder encuestas a mano. Todo lo simulado son
datos sintéticos (la guía lo permite) y lleva `tema_real`, que es lo que lo distingue de una
respuesta real.

### `datos_sinteticos/simular.py` · UPC 1

| Función | Entrada | Salida | Qué hace |
|---|---|---|---|
| `simular_respuestas(encuesta, plantilla, n=80, periodos=2, semilla=None)` | `dict` Encuesta publicada, `list` Plantilla, `int`, `int` (1 o 2), `int\|None` | `list` Respuesta | Genera `n` respuestas por periodo. Periodo actual = `encuesta["periodo"]`; si `periodos == 2`, también el mes anterior. Reparte por turno según la plantilla del colectivo con tasas desiguales (turno de noche ~7 %). Rellena **todas** las preguntas: `escala_1_5` (en el periodo actual, más bajas en dimensiones `condiciones` y `bienestar` para planta), `opcion` y `si_no` con pesos realistas, y la pregunta `texto` en `comentario` (~70 % rellena, con el mismo banco de frases por tema que `generar.py`: en el periodo actual suben descansos y turnos, y aparece comunicacion; ~5 % con datos personales falsos). `canal` mezcla qr y quiosco. Pone `id`, `fecha` dentro del mes, `colectivo`, `centro_tipo` y `tema_real`. |

### Endpoint · UPC 2 (`rutas_encuestas.py`)

| Método y ruta | Recibe | Devuelve | Errores | Qué hace |
|---|---|---|---|---|
| `POST /encuestas/{id}/simular` | `{"n": 80, "periodos": 2}` | `{"anadidas": int}` | 403 si `MODO_DEMO` no es `1` en `.env`; 404; 409 si no está publicada | Llama a `simular_respuestas`, pasa cada `comentario` por `anonimizar()` y las añade con `almacen.anadir_respuesta`. |
| `GET /escenarios` | — | `list` de `{"id", "nombre", "necesidad"}` | | Lee `contenido/escenarios.json` (UAB 2). |
| `GET /salud` | — | `{"ok", "llm", "modo_demo"}` | | `modo_demo` = `MODO_DEMO == "1"`. |

`.env.example` añade `MODO_DEMO=1`.

### `backend/api/probar_ciclo.py` · UPC 2
Con el servidor arrancado: `python3 -m backend.api.probar_ciclo`. Solo librería estándar (`urllib`).
Recorre el ciclo por la API y escribe `OK` o `FALLO` en cada comprobación:
1. `/salud` responde.
2. Generar una encuesta con el primer escenario de `/escenarios` → 3–6 preguntas, máximo 1 `texto`.
3. Publicar sin aprobar → 409. Aprobar y publicar → `url` y `qr`.
4. Simular 80 respuestas en 2 periodos.
5. Análisis: `temas` no vacío; hay al menos un tema `sube` o `nuevo`; hay alerta de `representatividad`
   del turno de noche; ninguna media con `n < 5`; ningún `comentario` contiene `@` ni 9 cifras seguidas.
6. Recomendaciones: 2–3 acciones y un `seguimiento` con el mismo colectivo.
7. Lo mismo con `enc_000` (sin generar ni simular).

### `contenido/escenarios.json` · UAB 2
Lista de 3 escenarios (uno por escenario de la guía de Damm), con la Necesidad completa:
```json
[ { "id": "turnos_planta", "nombre": "Nuevo sistema de turnos en planta",
    "necesidad": { "objetivo": "", "colectivo": "planta", "contexto": "",
                   "duracion_max_seg": 120, "temas_prohibidos": ["salario"] } } ]
```

### Frontend · UAB 1
- `api.js` añade: `obtenerSalud()` → `GET /salud`, `listarEscenarios()` → `GET /escenarios`,
  `simularRespuestas(id, n = 80, periodos = 2)` → `POST /encuestas/{id}/simular`.
- `crear.html`, paso 1: selector "Empezar desde un escenario" que rellena el formulario.
- `dashboard.html`: si `modo_demo`, botón secundario "Simular respuestas" (abre un pequeño diálogo con
  n y periodos) y después recarga el análisis.
