# Reglas por colectivo · contexto para la IA que genera encuestas

> Dueño: UAB 2 · Lo lee `backend/ia/generar.py` con `_extraer_reglas_colectivo(reglas, colectivo)`.
> **Formato obligatorio:** cada colectivo es una sección `## <colectivo>` con el valor cerrado exacto
> (`planta`, `logistica`, `comercial`, `oficina`, `manager`) y `## varios` para las encuestas multisector.
> La sección termina en el siguiente `## `. No uséis `## ` para otra cosa que empiece por esas palabras.
> Las reglas de privacidad y formato JSON ya están en `backend/ia/prompts/generar.md`; aquí solo va lo propio de cada colectivo.

## Reglas generales (referencia para el equipo, no se envía al modelo)

- Tiempo estimado, igual que el código: **15 s por pregunta cerrada** (`escala_1_5`, `opcion`, `si_no`) y **30 s por pregunta `texto`**.
- Tiempo efectivo de cada colectivo = `min(duracion_max_seg, tiempo máximo del colectivo)`.
- Total por colectivo: entre 3 y 6 preguntas. Como máximo 1 `texto`, opcional y la última.
- Turnos en la plataforma (`plantilla.json`): solo `planta` tiene `manana`, `tarde` y `noche`. El resto, `sin_turno`.
- Temas prohibidos siempre: salario o retribución individual, salud personal, afiliación sindical, ideología, religión, vida privada, evaluación de personas concretas.

## planta

- Quién: producción y envasado, en línea, a turnos rotativos (mañana, tarde, noche). Sin ordenador, con guantes y ruido. Responden en fichaje, comedor o pausa. El turno de noche es el que menos participa.
- Preguntas: 3–4. Tiempo máximo: 90 s.
- Tono: cercano, de tú, frases de 12 palabras como máximo. Situaciones concretas del día a día, nada abstracto.
- Tipos preferidos: `escala_1_5` (se ve con caritas), `si_no`, `opcion` con 3–4 opciones. `texto` solo si sobra tiempo.
- Canal: QR en fichaje, comedor y vestuarios; tablet en modo quiosco en la zona de descanso.
- Temas y vocabulario propios: pausas y descansos, cuadrante de turnos, relevo entre turnos, ritmo de la línea, seguridad y EPIs, información del jefe de turno.
- Ejemplos de preguntas propias:
  - "¿Te da tiempo a hacer la pausa completa en tu turno?" (`si_no`, bienestar)
  - "¿Sabes con antelación qué turno te toca?" (`escala_1_5`, condiciones)
  - "En el relevo, ¿te pasan las incidencias de la línea?" (`si_no`, entorno)
- Evitar: preguntar por línea, máquina o equipo concreto (identifica a personas), jerga de RRHH.

## logistica

- Quién: almacén y distribución, siempre en movimiento (carretilla, muelle, ruta). Sin ordenador; móvil personal solo en pausas. Si no se acaba en un minuto, se abandona. Es el colectivo que menos participa.
- Preguntas: 3–4. Tiempo máximo: 60 s.
- Tono: muy directo, de tú, 10 palabras como máximo por pregunta. Intro de dos líneas.
- Tipos preferidos: `si_no` (lo más rápido), `escala_1_5`, `opcion` con 3–4 opciones. Evitar `texto` salvo que sea la única abierta de la encuesta.
- Canal: QR en muelles, cabina de fichaje y sala de descanso; quiosco en la sala de descanso.
- Temas y vocabulario propios: rutas y cuadrante de rutas, muelles de carga, picos de carga, coordinación con planta, seguridad con carretillas, información que llega a tiempo.
- Ejemplos de preguntas propias:
  - "¿Te llega a tiempo el cuadrante de rutas?" (`escala_1_5`, condiciones)
  - "¿Puedes parar cuando hay picos de carga?" (`si_no`, bienestar)
  - "¿Cómo es la coordinación con planta en los muelles?" (`escala_1_5`, entorno)
- Evitar: preguntar por ruta, matrícula o muelle concreto (identifica a personas).

## comercial

- Quién: equipos en la calle visitando clientes (hostelería, distribución, gran consumo). Trabajan desde el móvil y el coche, con la agenda fragmentada. Sin turnos.
- Preguntas: 3–5. Tiempo máximo: 120 s.
- Tono: profesional y cercano, de tú, frases de 15 palabras como máximo.
- Tipos preferidos: `escala_1_5`, `opcion`, `si_no`.
- Canal: Teams en el móvil; QR en reuniones comerciales.
- Temas y vocabulario propios: visitas a clientes, carga de la agenda, objetivos del equipo, herramientas en el móvil, tiempo en el coche y desconexión, apoyo del responsable.
- Ejemplos de preguntas propias:
  - "¿Las herramientas del móvil te ayudan en las visitas?" (`escala_1_5`, condiciones)
  - "¿Puedes desconectar al acabar tu jornada?" (`si_no`, bienestar)
  - "¿Recibes apoyo de tu responsable cuando lo necesitas?" (`escala_1_5`, liderazgo)
- Evitar: resultados de ventas, objetivos individuales o comisiones (cuentan como retribución individual).

## oficina

- Quién: equipos corporativos con ordenador, Microsoft 365 y Teams. Sin turnos, con teletrabajo parcial. Es el colectivo que más responde y el que más se satura de encuestas.
- Preguntas: 3–6. Tiempo máximo: 180 s.
- Tono: profesional, de tú, claro. Preguntas de 20 palabras como máximo.
- Tipos preferidos: `escala_1_5`, `opcion` y 1 `texto` opcional al final (aquí el comentario abierto aporta más).
- Canal: Teams en el ordenador; QR en pantallas de oficina.
- Temas y vocabulario propios: reuniones, herramientas digitales, carga de trabajo, conciliación y flexibilidad, oportunidades de desarrollo, coordinación con otras áreas.
- Ejemplos de preguntas propias:
  - "¿El número de reuniones te deja tiempo para tu trabajo?" (`escala_1_5`, condiciones)
  - "¿Tienes oportunidades para aprender cosas nuevas?" (`escala_1_5`, desarrollo)
  - "¿Qué te ayudaría más a conciliar?" (`opcion`, bienestar)
- Evitar: encuestas largas; no superar 5 preguntas si no hace falta.

## manager

- Quién: mandos de fábrica, logística, comercial y oficinas, y dirección. Agenda llena. También reciben los resultados agregados. Colectivo pequeño: riesgo alto de grupos con menos de 5 respuestas. Sin turnos.
- Preguntas: 3–5. Tiempo máximo: 120 s.
- Tono: directo y ejecutivo, de tú. Pregunta por lo que necesitan para liderar, no por su desempeño.
- Tipos preferidos: `escala_1_5`, `opcion` y 1 `texto` opcional al final.
- Canal: Teams; QR en comités.
- Temas y vocabulario propios: información para decidir, apoyo de People, comunicación de cambios al equipo, carga del equipo, tiempo para acompañar a las personas.
- Ejemplos de preguntas propias:
  - "¿Recibes a tiempo la información para explicar los cambios a tu equipo?" (`escala_1_5`, liderazgo)
  - "¿Tienes tiempo para acompañar a las personas de tu equipo?" (`escala_1_5`, liderazgo)
  - "¿Qué apoyo de People te sería más útil?" (`opcion`, cultura)
- Evitar: pedir que evalúen a personas de su equipo o que señalen "quién se queja".

## varios

Encuesta para varios colectivos: un **núcleo común** (para comparar) y **preguntas propias** de cada colectivo.

- Núcleo común (`preguntas`, ids `c1`, `c2`, `c3`):
  - 1–3 preguntas válidas para todos los colectivos de la encuesta. Al menos 1 `escala_1_5`.
  - Como máximo 1 `texto`, siempre la última del núcleo: "¿Qué cambiarías o reforzarías?". Así los comentarios se comparan entre colectivos.
  - Sin vocabulario de un solo colectivo: nada de "línea", "relevo", "muelle", "ruta", "visita" ni "reunión". Habla del objetivo de la necesidad con palabras que entienda cualquiera.
  - La primera pregunta mide directamente el objetivo: "¿Cómo valoras el nuevo sistema de turnos?" (`escala_1_5`).
- Preguntas propias (`preguntas_por_colectivo`, ids `<colectivo>_p1`, `<colectivo>_p2`…):
  - 1–3 por colectivo, solo `escala_1_5`, `opcion` o `si_no`. Nunca `texto`.
  - Usan los temas, el vocabulario y los ejemplos de la sección de ese colectivo.
  - No repiten ni reformulan ninguna pregunta del núcleo.
- Presupuesto por colectivo con el núcleo típico (`c1` escala + `c2` texto = 45 s):

| Colectivo | Tiempo máx. | Propias | Total | Tiempo |
|---|---|---|---|---|
| planta | 90 s | hasta 2 | 4 | 75 s |
| logistica | 60 s | 1 | 3 | 60 s |
| comercial | 120 s | hasta 3 | 5 | 90 s |
| oficina | 180 s | hasta 3 | 5 | 90 s |
| manager | 120 s | hasta 3 | 5 | 90 s |

- Con un núcleo de 1 sola pregunta cerrada (15 s), cada colectivo puede tener 1 propia más, sin pasar de su máximo de preguntas ni de su tiempo.
- La `intro` es común: una frase sobre para qué sirve y otra que diga que es anónima y que solo se ven grupos de 5 personas o más.

## frecuencia y seguimiento

- Planta, logística y comercial: 1 microconsulta cada 4 semanas como máximo y 1 recordatorio.
- Oficina y manager: 1 cada 3 semanas como máximo y 1 recordatorio.
- La encuesta de seguimiento es más corta que la original: 3 preguntas y 60 s como máximo, centrada en las acciones tomadas.
