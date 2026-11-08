# Guion del pitch · v6 · 3:15 min · palabra por palabra

> Dueño: UAB 2 · Slides en `pitch/estructura_slides.md`.
> Unas 400 palabras habladas; el resto del tiempo son las pausas del demo. Margen de 15 s hasta los 3:30 y de 45 s hasta los 4 min.
> **Ponente 1** narra (UAB 2). **Ponente 2** maneja el demo (UAB 1). Lo que va entre [corchetes] son acotaciones o cifras que se rellenan en el ensayo.
> Antes de empezar: almacén limpio; escenario D generado, aprobado (traducciones listas) y publicado; un compromiso preparado en `enc_000` con su encuesta de seguimiento publicada y su QR en pantalla; dashboard abierto en Resumen; Teams abierto en el canal si está conectado.

---

## Slide 1 · 0:00–0:20 · El problema

> "[Siete coma cinco] por ciento. Es lo que responde el turno de noche de planta en nuestro demo, con datos sintéticos.
> Responden siempre los mismos. ¿Por qué? Porque nunca ven qué pasa después.
> Escuchamos, pero no lo demostramos."

## Slide 2 · 0:20–0:50 · La IA propone, RRHH decide

[Ponente 2: Nueva necesidad → escenario D → Generar.]

> "People escribe qué quiere entender, para planta, logística y comercial. La IA crea preguntas comunes para comparar, preguntas propias de cada sector y una pregunta que solo aparece si alguien puntúa mal.
> Reordenamos, editamos… y solo cuando una persona aprueba, se publica."

## Slide 3 · 0:50–1:10 · En tu idioma, donde estás

[Ponente 2 proyecta el móvil del equipo con el formulario.]

> "Quien responde lo hace desde un QR, una tablet en la sala de descanso o Teams. En castellano, catalán o inglés, y ampliable a más idiomas. Treinta segundos."

## Slide 4 · 1:10–1:35 · Centro de mando en directo

[Ponente 2: Maqueta 3D → Simular respuestas.]

> "Cada edificio es un sector, coloreado por participación. Llegan respuestas: late. Pulsamos noche: planta, en rojo.
> Y donde hay menos de cinco, no mostramos nada, ni siquiera a sus vecinos: no se puede deducir restando."

## Slide 5 · 1:35–2:05 · Entender

[Ponente 2: Resumen → temas → una pregunta sugerida → Informe ejecutivo.]

> "La IA lee todos los comentarios y detecta lo que crece. Lo hemos medido: acierta el tema en el [X] por ciento.
> RRHH pregunta en lenguaje natural, y dirección tiene su informe en un clic."

## Slide 6 · 2:05–2:45 · Dijisteis → Hemos hecho

[Ponente 2: Acción "Asegurar las pausas en planta" → Comprometer.]

> "Y aquí es donde casi todas las encuestas se quedan. Nosotros no.
> La IA redacta lo que nos dijisteis, con la cifra. RRHH escribe lo que va a hacer, quién y cuándo, y lo firma."

[Ponente 1 levanta el QR del seguimiento hacia el jurado.]

> "Escaneadlo. Lo primero que veis no es una pregunta: es lo que la empresa ha hecho con vuestra voz. En vuestro idioma."

[Ponente 2: Maqueta → Simular respuestas → el banderín pasa de ámbar a verde.]

> "Y lo medimos con la misma pregunta: antes [dos coma cuatro], ahora [tres coma seis]. Sin prometer que sea la causa."

## Slide 7 · 2:45–3:15 · Teams y cierre

[Ponente 2: tarjeta del compromiso en Teams o su vista previa.]

> "El compromiso llega también a Teams, con un botón: ¿ha funcionado? Responde en treinta segundos.
> Las encuestas no fallan por las preguntas: fallan por el silencio de después.
> Escoltar millor, actuar abans… i demostrar-ho. Gràcies."

---

## Plan B

| Si falla… | Qué hacer | Frase puente |
|---|---|---|
| La IA tarda al generar o al redactar el "Dijisteis" | Esperar el respaldo (sale con la etiqueta "Sin IA") | "Si la IA no responde, la plataforma sigue funcionando y lo dice." |
| El jurado no llega al QR (wifi o 4G) | Hotspot del equipo; si no, el móvil del equipo proyectado | "Os lo enseño en este móvil." |
| El "después" no tiene 5 respuestas | Simular otra vez con mejora | "Con menos de cinco, no lo enseñamos: también aquí manda el umbral." |
| Teams no está conectado | Vista previa de la tarjeta y el JSON en el Adaptive Cards Designer | "Esta es la tarjeta exacta que Teams acepta." |
| Se cae todo | Vídeo de respaldo de 90 s y narrar encima | "Para no perder tiempo, os lo enseño en vídeo." |

## Ensayo

- 3 ensayos cronometrados. Objetivo: **3:05–3:20**. Si pasa de 3:30, recortar primero la frase del informe (slide 5).
- Rellenar las cifras entre corchetes con las del ensayo y el dato de precisión de UPC 1. No prometer porcentajes de participación reales.
- Antes de salir: cerrar terminales, `.env` y cualquier pestaña con la URL del webhook de Teams. Recargar el navegador con Ctrl+Shift+R.

## Respuestas para el jurado (≤ 20 s cada una)

- **¿Por qué no Typeform?** — "Publicar es una pieza intercambiable: hoy usamos nuestro formulario porque necesitamos idioma original con traducciones, el canal, el umbral de cinco y que no se guarde nada de quien responde. Con un token, el mismo flujo crearía el formulario en Typeform por su API."
- **¿Se puede saltar el umbral restando?** — "No. Si un turno tiene menos de cinco, también ocultamos a sus vecinos, y las cifras globales excluyen los grupos pequeños: no se puede deducir restando."
- **¿Quién puede entrar al panel?** — "En Damm iría detrás de Entra ID, el inicio de sesión de Microsoft 365; aquí es local."
- **¿El compromiso no promete demasiado?** — "Lo firma una persona, con responsable y fecha, y el antes y después solo se enseña con cinco respuestas o más y avisando de que no demuestra la causa."
- **¿Cómo comparáis sectores con preguntas distintas?** — "Por el núcleo común: las mismas preguntas para todos."
- **¿Qué pasa sin IA?** — "Todo funciona con reglas y la pantalla lo indica con la etiqueta 'Sin IA'."
