# Estructura de diapositivas · v3 · 7 slides · 3:30 min

> Dueño: UAB 2 · Guion palabra por palabra en `pitch/guion_pitch.md`.
> Las cifras entre `[corchetes]` salen del ensayo con el escenario D (multisector) y del dato de precisión de UPC 1 (`evaluar.py`). Se rellenan en el ensayo final y no se cambian después.
> Estilo: fondo claro, rojo Damm solo como acento, una idea por slide, cifras grandes, sin párrafos. Ninguna captura muestra tokens, `.env`, la URL del webhook de Teams, la terminal ni URLs de la API.

| # | Título en pantalla | Tiempo | Qué se ve | Criterio del jurado |
|---|---|---|---|---|
| 1 | Escuchamos… pero no a todos | 0:00–0:20 | Cifra grande | Adecuación al problema (20 %) |
| 2 | La IA propone. RRHH decide. | 0:20–0:55 | Demo `crear.html` | Uso útil de la IA (15 %) · Prototipo (15 %) |
| 3 | Respondes donde estás, en tu idioma | 0:55–1:20 | Demo `responder` en el móvil | Representatividad e inclusión (10 %) |
| 4 | El centro de mando, en directo | 1:20–1:50 | Demo maqueta 3D | Representatividad · Privacidad (15 %) |
| 5 | IA que se ve y se mide | 1:50–2:20 | Demo Resumen | Calidad de insights (10 %) · Uso de la IA |
| 6 | Pregunta a tus datos. Informe en un clic. | 2:20–2:55 | Demo pregunta + informe | Privacidad · Valor para las personas |
| 7 | Donde ya trabaja RRHH: Teams | 2:55–3:30 | Canal de Teams + cierre | Integración M365 (10 %) · Evolución (5 %) |

---

## Slide 1 · Escuchamos… pero no a todos

- **Visual:** cifra gigante **[7,5 %]**; debajo, pequeño: "participación del turno de noche de planta en nuestro demo · datos sintéticos".
- **Tres líneas:** "Responden siempre los mismos." · "Una encuesta no encaja con un operario, un comercial y un manager." · "Los comentarios se leen tarde."
- **Pie fijo:** "100 % datos sintéticos · resultados solo agregados · mínimo 5 respuestas".

## Slide 2 · La IA propone. RRHH decide.

- **Demo:** `crear.html` con el escenario **D · Encuesta multisector** (planta, logística y comercial).
- **Momentos a enseñar:**
  1. La IA crea el núcleo común y las preguntas propias de cada sector (pestañas por sector).
  2. RRHH vuelve al paso 1, cambia la necesidad y pulsa **Regenerar preguntas**: nada es una plantilla fija.
  3. RRHH edita una pregunta y **aprueba**. Sin aprobación no se publica.
- **Franja inferior:** "Sin respuestas predefinidas · cuando no hay IA, la pantalla lo dice ("Sin IA")".

## Slide 3 · Respondes donde estás, en tu idioma

- **Demo:** el jurado escanea el **QR de planta** con su móvil.
- **Momentos a enseñar:**
  1. Selector **ES · CA · EN** arriba a la derecha: la encuesta, traducida por la IA al aprobarla, cambia de idioma sin perder lo ya marcado.
  2. Botones grandes y caritas; en la tablet del quiosco vuelve al inicio tras cada respuesta y mantiene el idioma.
- **Texto en pantalla:** "Castellano, catalán e inglés: para una plantilla internacional." · "Las respuestas se analizan juntas: el idioma no parte los datos."

## Slide 4 · El centro de mando, en directo

- **Demo:** pestaña **Maqueta 3D** con la recarga automática activa.
- **Momentos a enseñar:**
  1. El edificio de planta **late** con la respuesta del jurado: "+1 respuestas en Planta".
  2. Botón **Día/Noche (turno de noche)**: planta en rojo.
  3. Un sector con menos de 5 respuestas: gris, "Oculto (n < 5)".
  4. Panel de zona → **"Crear encuesta para este sector"**.

## Slide 5 · IA que se ve y se mide

- **Demo:** pestaña Resumen.
- **Momentos a enseñar:**
  1. Mientras trabaja: esqueleto gris con **"La IA está preparando… ([75] de [101] comentarios analizados)"**; se rellena solo.
  2. **Temas: antes y ahora**, con "Nuevo" y "↑", y el resumen escrito por la IA.
- **Dato grande en la slide:** "La IA acierta el tema en el **[X] %** de los comentarios" (precisión contra `tema_real`, de UPC 1).
- **Línea de límites:** "Correlación no es causa · tamaño de muestra siempre visible".

## Slide 6 · Pregunta a tus datos. Informe en un clic.

- **Demo:**
  1. Las 3 preguntas sugeridas **las propone la IA** para estos resultados. Pulsar una → respuesta con cifras y confianza.
  2. Escribir en directo: **"¿Quién se queja del turno de noche?"** → la herramienta se niega: solo trabaja con datos agregados.
  3. Botón **Informe ejecutivo** → una hoja A4 con lectura, KPIs, hallazgos y acciones con responsable, plazo e indicador.

## Slide 7 · Donde ya trabaja RRHH: Teams

- **Demo (si Teams está configurado):** **Publicar en Teams** → la tarjeta aparece en el canal "Encuestas" con el botón "Responder". **Enviar resumen a Teams** → lectura, 3 datos, alertas y acciones, nunca comentarios.
- **Si no está configurado:** vista previa de la tarjeta y esquema: Escucha activa → webhook → Workflow de Teams → canal.
- **Cierre grande:** "Escoltar millor, actuar abans."

---

## Respaldo

- **Vídeo de 90 s** con el recorrido D → QR en catalán → maqueta → Resumen → pregunta → Teams.
- **Capturas** de cada momento, incluida la tarjeta publicada en el canal de Teams.
- **Anexo oculto:** tabla de privacidad (anonimización, n ≥ 5, sin identificadores, validación humana) y arquitectura.
