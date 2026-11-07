# Guion del pitch · v2 · 3:30 min · palabra por palabra

> Dueño: UAB 2 · Slides en `pitch/estructura_slides.md`.
> Ritmo ~135 palabras/minuto (≈ 450 palabras habladas). Margen de 30 s hasta los 4 min para el demo.
> **Ponente 1** narra (UAB 2). **Ponente 2** maneja el demo (UAB 1). Lo que va entre [corchetes] son acotaciones o cifras que se rellenan en el ensayo de H22.
> Antes de empezar: escenario D ya generado, aprobado y publicado; dashboard abierto en la pestaña Maqueta 3D; cartel con el QR de planta impreso.

---

## Slide 1 · 0:00–0:25 · El problema

> "[Siete coma cinco] por ciento.
> Es lo que responde el turno de noche de planta en nuestro demo, con datos cien por cien sintéticos.
> Damm ya escucha. Pero responden siempre los mismos, una encuesta no encaja igual a un operario que a un comercial, y los comentarios se leen cuando ya es tarde.
> Escuchamos. Pero no a todos."

## Slide 2 · 0:25–1:05 · Una encuesta, cada sector con sus preguntas

[Ponente 2 abre Nueva necesidad y elige el escenario D.]

> "People escribe lo que quiere entender: cómo afecta el cambio de turnos a planta, logística y comercial. Tres sectores, una sola encuesta."

[Pulsa Generar.]

> "La IA crea un núcleo común para comparar a los tres sectores, y preguntas propias para cada uno. Planta habla de pausas y cuadrantes. Logística, de rutas y muelles. Comercial, de visitas.
> Pero aquí decide una persona: editamos, aprobamos… y solo entonces se publica. Un QR general y uno por sector, para el cartel de cada zona."

## Slide 3 · 1:05–1:45 · El centro de mando en directo

[Ponente 1 levanta el cartel QR de planta hacia el jurado.]

> "Escaneadlo. Es el QR de planta."

[Ponente 2 está en la Maqueta 3D. Se espera el pulso del edificio.]

> "Ese edificio que late es vuestra respuesta, llegando en directo.
> La maqueta no es decoración: cada edificio se colorea por participación. Y si pulsamos noche, filtramos el turno de noche: planta, en rojo.
> Donde hay menos de cinco respuestas, no mostramos nada. Nunca.
> Y desde aquí mismo: crear una encuesta para este sector."

## Slide 4 · 1:45–2:20 · Temas e IA medible

[Ponente 2 cambia a Resumen.]

> "Detrás, la IA lee todos los comentarios, con faltas y en dos idiomas, y los agrupa en temas. Los descansos [suben del seis al treinta y cuatro por ciento], y aparecen temas nuevos.
> Y no os pedimos que os fieis: lo hemos medido. La IA acierta el tema en el [X] por ciento de los comentarios.
> El mapa de calor compara los tres sectores con la misma pregunta. Para eso sirve el núcleo común."

## Slide 5 · 2:20–3:00 · Pregunta a tus datos e informe

[Ponente 2 pulsa la sugerencia "¿Qué sector está peor y por qué?".]

> "People pregunta en lenguaje natural. La IA responde con cifras y avisa si un dato no es representativo."

[Ponente 2 escribe: "¿Quién se queja del turno de noche?".]

> "¿Y si alguien pregunta quién se queja? La herramienta se niega. Solo trabaja con resultados agregados.
> Y para dirección, un clic: informe ejecutivo en una hoja, con acciones, responsable, plazo e indicador."

## Slide 6 · 3:00–3:30 · Cierre

[Ponente 1 al centro, mirando al jurado.]

> "Funciona donde está cada persona: QR por sector, una tablet en la zona de descanso, y la próxima parada, Teams.
> No buscábamos una encuesta más. Buscábamos esto:
> escoltar millor, actuar abans. Gràcies."

---

## Plan B

| Si falla… | Qué hacer | Frase puente |
|---|---|---|
| La IA tarda al generar | Esperar el respaldo (sale con aviso "sin IA") | "Si la IA no responde a tiempo, la plataforma sigue funcionando: así nunca se queda bloqueada." |
| Nadie del jurado escanea | Responder desde un móvil del equipo | "Os lo enseño yo mismo." |
| No late el edificio en 10 s | Pulsar Actualizar | — |
| Se cae todo | Vídeo de respaldo de 90 s y narrar encima | "Para no perder tiempo, os lo enseño en vídeo." |

## Ensayo (H22)

- 3 ensayos cronometrados. Objetivo: **3:20–3:35**. Si pasa de 3:45, recortar la frase del mapa de calor (slide 4).
- Rellenar las cifras entre corchetes con las del ensayo y el dato de precisión de UPC 1. No cambiarlas después.
- Antes de salir: cerrar terminales, `.env` y pestañas con URLs de la API.

## Respuestas para el jurado (≤ 20 s cada una)

- **¿Cómo comparáis sectores si cada uno tiene preguntas distintas?** — "Por el núcleo común: las mismas 1 a 3 preguntas para todos. Las propias sirven para profundizar en cada sector."
- **¿Y si la IA hace una pregunta inadecuada?** — "Hay temas prohibidos que la IA lee antes de escribir, un filtro después y, sobre todo, nada se publica sin aprobación humana."
- **¿Puede "Pregunta a tus datos" revelar algo de una persona?** — "No. El modelo solo recibe datos agregados, nunca comentarios individuales, y las preguntas que buscan identificar a alguien se bloquean antes de llegar al modelo."
- **¿Qué pasa sin conexión o sin IA?** — "Todo funciona con reglas de respaldo y el panel indica si el análisis es con IA o por reglas."
- **¿Por qué el umbral es 5?** — "Es el mínimo de la guía. Es configurable; con datos reales se podría subir a 10 en grupos pequeños como managers."
