# Estructura de diapositivas · v2 · 6 slides · 3:30 min

> Dueño: UAB 2 · Guion palabra por palabra en `pitch/guion_pitch.md`.
> Las cifras entre `[corchetes]` salen del ensayo con el escenario D (multisector) y del dato de precisión de UPC 1 (`evaluar.py`). Se rellenan en H22 y no se cambian después.
> Estilo: fondo crema, rojo Damm solo como acento, una idea por slide, cifras grandes, sin párrafos. Ninguna captura muestra tokens, `.env`, terminal ni URLs de API.

| # | Título en pantalla | Tiempo | Qué se ve | Criterio del jurado |
|---|---|---|---|---|
| 1 | Escuchamos… pero no a todos | 0:00–0:25 | Cifra grande | Adecuación al problema (20 %) |
| 2 | Una encuesta. Cada sector, sus preguntas. | 0:25–1:05 | Demo `crear.html` | Uso útil de la IA (15 %) · Prototipo (15 %) |
| 3 | El centro de mando, en directo | 1:05–1:45 | Demo maqueta 3D | Representatividad (10 %) · Privacidad (15 %) |
| 4 | De cientos de comentarios a temas, con IA medible | 1:45–2:20 | Demo Resumen | Calidad de insights (10 %) · Uso de la IA |
| 5 | Pregunta a tus datos. Informe en un clic. | 2:20–3:00 | Demo pregunta + informe | Privacidad · Valor para las personas |
| 6 | Respondes donde ya estás | 3:00–3:30 | Cierre | Integración M365 (10 %) · Evolución (5 %) |

---

## Slide 1 · Escuchamos… pero no a todos

- **Visual:** cifra gigante **[7,5 %]** y debajo, pequeño: "participación del turno de noche de planta en nuestro demo · datos sintéticos".
- **Tres líneas:** "Responden siempre los mismos." · "Una encuesta no encaja con un operario, un comercial y un manager." · "Los comentarios se leen tarde."
- **Pie fijo:** "100 % datos sintéticos · resultados solo agregados · mínimo 5 respuestas".

## Slide 2 · Una encuesta. Cada sector, sus preguntas. (función diferencial 1)

- **Demo:** `crear.html` con el escenario **D · Encuesta multisector** (planta, logística y comercial).
- **Momentos a enseñar:**
  1. Chips de sectores seleccionados y el aviso "La IA crea preguntas comunes para comparar y preguntas propias de cada sector".
  2. Paso 2: pestaña "Comunes" y pestañas por sector. Se ve que planta habla de pausas y cuadrante, logística de rutas y muelles, comercial de visitas.
  3. RRHH edita una pregunta y pulsa **Aprobar** (validación humana).
  4. Paso 3: QR general y **QR por sector** para los carteles.
- **Esquema de respaldo si falla:** dos columnas, "Núcleo común (comparable)" a la izquierda y tres tarjetas de sector a la derecha.

## Slide 3 · El centro de mando, en directo (función diferencial 2)

- **Demo:** pestaña **Maqueta 3D** del dashboard con la recarga cada 10 s activa.
- **Momentos a enseñar:**
  1. Se invita al jurado a escanear el QR de planta. Su edificio **late** y aparece "+1 respuestas en Planta".
  2. Capa **Participación**: edificios en verde, ámbar y rojo según la tasa.
  3. Botón **Día/Noche (turno de noche)**: planta se pone en rojo; logística y comercial salen atenuados con "Sin turno de noche".
  4. Un sector con menos de 5 respuestas en capa **Valoración**: gris, "Oculto (n < 5)".
  5. Panel de zona → **"Crear encuesta para este sector"**: el ciclo vuelve a empezar desde la maqueta.

## Slide 4 · De cientos de comentarios a temas, con IA medible (función diferencial 5)

- **Demo:** pestaña Resumen.
- **Momentos a enseñar:**
  1. Indicador "Analizando comentarios con IA · [75] de [101]" → "Análisis con IA listo".
  2. Gráfico **Temas: antes y ahora** con "Nuevo" y "↑". Pulsar un tema para ver el resumen.
  3. **Mapa de calor** del núcleo común: los tres sectores comparados con la misma pregunta.
- **Dato grande en la slide:** "La IA acierta el tema en el **[X] %** de los comentarios" (precisión contra `tema_real`, de UPC 1).
- **Línea de límites:** "Correlación no es causa · tamaño de muestra siempre visible".

## Slide 5 · Pregunta a tus datos. Informe en un clic. (funciones diferenciales 3 y 4)

- **Demo "Pregunta a tus datos":**
  1. Pulsar la sugerencia "¿Qué sector está peor y por qué?" → respuesta con cifras y confianza.
  2. Escribir en directo: **"¿Quién se queja del turno de noche?"** → "Esta herramienta solo trabaja con resultados agregados…". Privacidad demostrada, no solo explicada.
- **Demo "Informe ejecutivo":** botón en la cabecera → página A4 con lectura, 4 KPIs, 3 hallazgos, acciones con responsable, plazo e indicador. Pulsar "Imprimir / Guardar PDF".
- **Texto en pantalla:** "Para RRHH: preguntar. Para dirección: decidir."

## Slide 6 · Respondes donde ya estás

- **Tres columnas:**
  - Fábrica y almacén: QR por sector y tablet en modo quiosco que vuelve a "¿Dónde trabajas?" tras cada respuesta.
  - Oficina y comercial: tarjeta de Teams con la encuesta (propuesta M365, ver `propuesta_m365_accesibilidad.md`).
  - People: alerta de baja participación en el canal de Teams.
- **Siguiente paso:** versiones en catalán y castellano y pulsos trimestrales.
- **Cierre grande:** "Escoltar millor, actuar abans."

---

## Respaldo

- **Vídeo de 90 s** con el recorrido D → maqueta → Resumen → pregunta → informe, grabado con los mismos datos del ensayo.
- **Capturas** de cada momento por si falla también el vídeo.
- **Anexo oculto:** tabla de privacidad (anonimización, n ≥ 5, sin identificadores, validación humana) y arquitectura de carpetas.
