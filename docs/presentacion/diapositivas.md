# Estructura de diapositivas · 7 slides · 3:15 min (+15 s de margen)

> Guion palabra por palabra en [`guion.md`](guion.md).
> Idea fuerza única: **"Escuchar, actuar y demostrarlo."**
> Las cifras entre `[corchetes]` salen del ensayo con datos sintéticos y del dato de precisión de la clasificación (`backend/ia/evaluar.py`). Se rellenan en el ensayo y no se cambian después. No prometáis porcentajes de participación: no hay datos reales de Damm.
> Estilo: fondo claro, rojo Damm solo como acento, una idea por slide y cifras grandes. Ninguna captura muestra tokens, `.env`, la URL del webhook de Teams, la terminal ni URLs de la API.

| # | Título en pantalla | Tiempo | Qué se ve | Criterio del jurado |
|---|---|---|---|---|
| 1 | Nadie responde si nunca ve qué pasa después | 0:00–0:20 | Cifra grande | Adecuación al problema (20 %) |
| 2 | La IA propone. RRHH decide. | 0:20–0:50 | Demo `crear.html` | Uso útil de la IA (15 %) · Prototipo (15 %) |
| 3 | Respondes donde estás, en tu idioma | 0:50–1:10 | Formulario en el móvil | Representatividad e inclusión (10 %) |
| 4 | El centro de mando, en directo | 1:10–1:35 | Maqueta 3D | Representatividad · Privacidad (15 %) |
| 5 | Entender, con la IA medida | 1:35–2:05 | Resumen + pregunta + informe | Calidad de insights (10 %) · Uso de la IA |
| 6 | **Dijisteis → Hemos hecho** | 2:05–2:45 | Compromiso + QR del jurado + maqueta | Valor para las personas (20 %) · ciclo completo |
| 7 | Donde ya trabaja RRHH: Teams | 2:45–3:15 | Tarjeta del compromiso + cierre | Integración M365 (10 %) · Evolución (5 %) |

---

## Slide 1 · Nadie responde si nunca ve qué pasa después

- **Visual:** cifra gigante **[7,5 %]**; debajo, pequeño: "participación del turno de noche de planta en nuestro demo · datos sintéticos".
- **Tres líneas:** "Responden siempre los mismos." · "¿Por qué? Porque nunca ven qué pasa después." · "Y los comentarios se leen cuando ya es tarde."
- **Pie fijo:** "100 % datos sintéticos · solo resultados agregados · mínimo 5 respuestas".

## Slide 2 · La IA propone. RRHH decide.

- **Demo:** escenario **D · Encuesta multisector** (planta, logística y comercial).
- **Momentos:** núcleo común + preguntas propias de cada sector → una pregunta condicional ("¿Qué ha pasado?" solo si se puntúa 1–2) → reordenar con ↑ → **Aprobar**. Sin aprobación no se publica.
- **Franja inferior:** "Sin respuestas predefinidas · cuando no hay IA, la pantalla lo dice".

## Slide 3 · Respondes donde estás, en tu idioma

- **Demo:** el formulario en el móvil del equipo, proyectado: QR del sector, selector **ES · CA · EN**, botones grandes y caritas.
- **Texto en pantalla:** "Castellano, catalán e inglés, ampliable a más idiomas." · "QR, quiosco o Teams: el mismo análisis."

## Slide 4 · El centro de mando, en directo

- **Demo:** pestaña **Maqueta 3D** → "Simular respuestas" → el edificio **late** y aparece un solo aviso, en el idioma de la pantalla.
- **Momentos:** botón **Día/Noche** (turno de noche en rojo) → un turno con menos de 5 respuestas sale oculto **y también sus vecinos** → "Ver en el análisis".
- **Texto en pantalla:** "Menos de 5: no se muestra, ni siquiera a sus vecinos. No se puede deducir restando."

## Slide 5 · Entender, con la IA medida

- **Demo rápida:** temas nuevos y en aumento con su resumen → una pregunta sugerida de "Pregunta a tus datos" → botón **Informe ejecutivo** (una hoja A4).
- **Dato grande:** "La IA acierta el tema en el **[X] %** de los comentarios" (precisión contra `tema_real`).
- **Línea de límites:** "Correlación no es causa · tamaño de muestra siempre visible".

## Slide 6 · Dijisteis → Hemos hecho

- **Demo (40 s):**
  1. Acciones → "Asegurar las pausas en planta" → **Comprometer**. El diálogo trae el "Dijisteis" con cifras y sin citas. Escribimos la fecha y el responsable → **Firmar**. "La IA propone el texto; tú lo firmas."
  2. **El jurado escanea el QR** de la encuesta de seguimiento: la primera pantalla es "Lo que nos dijisteis / Lo que hemos hecho", en el idioma de su móvil. Una pregunta y "Gracias".
  3. Maqueta: banderín **ámbar** sobre planta → "Simular respuestas" → el panel pasa a "Antes [2,4] → ahora [3,6] · n = [41]" y el banderín se pone **verde**. Con el aviso: "No demuestra que la acción sea la causa".
- **Texto en pantalla:** "Las encuestas no fallan por las preguntas: fallan por el silencio de después."

## Slide 7 · Donde ya trabaja RRHH: Teams

- **Demo:** tarjeta del compromiso en Teams: "Dijisteis / Hemos hecho / ¿Ha funcionado? Responde en 30 s". Si Teams no está conectado: vista previa y el JSON validado en el Adaptive Cards Designer.
- **Hoja de ruta (una línea):** radar de silencios (quién falta y cómo llegar a él) · inicio de sesión con Entra ID · más idiomas.
- **Cierre grande:** "Escoltar millor, actuar abans… i demostrar-ho."

---

## Respaldo

- **Vídeo de 90 s** grabado en el portátil de la demo después de la congelación: escenario D → móvil en catalán → maqueta → compromiso → QR del seguimiento → banderín verde → Teams.
- **Capturas** de cada momento, incluido el JSON de la tarjeta dibujado en el Adaptive Cards Designer.
- **Anexo oculto:** tabla de privacidad (umbral y supresión complementaria, anonimización, minimización, sin perfiles, validación humana) y arquitectura.
