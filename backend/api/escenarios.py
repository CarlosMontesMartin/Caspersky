"""Escenarios de la demo.

Los tres escenarios de la guía de Damm, listos para que el frontend rellene
la pantalla de crear con un clic y para que probar_ciclo.py los use.
El texto para ensayar está en docs/presentacion/escenarios_demo.md: si cambia
allí una necesidad, hay que cambiarla también aquí.
"""
ESCENARIOS = [
    {
        "id": "A",
        "titulo": "Cambio organizativo: nuevo sistema de turnos",
        "descripcion": "RRHH quiere saber si el cambio de turnos en planta se ha entendido, "
                       "qué dificultades genera y qué hay que reforzar, en menos de 2 minutos.",
        "necesidad": {
            "objetivo": "Saber cómo afecta el nuevo sistema de turnos",
            "colectivo": "planta",
            "contexto": "Cambio de turnos desde octubre",
            "duracion_max_seg": 120,
            "temas_prohibidos": ["salario"],
        },
        "encuesta_id": None,
        "que_mirar": ["La IA propone preguntas cortas y un tono cercano",
                      "RRHH edita una pregunta y aprueba",
                      "Se publica con QR",
                      "Alerta: el turno de noche responde poco",
                      "Temas descansos y comunicación; 2 acciones y una encuesta de seguimiento"],
    },
    {
        "id": "B",
        "titulo": "Colectivo de logística sin ordenador",
        "descripcion": "Personas con poco tiempo y sin correo corporativo: encuesta muy breve "
                       "por QR o quiosco y aviso si la muestra no es representativa.",
        "necesidad": {
            "objetivo": "Saber cómo se vive el día a día en el almacén y si llega la información",
            "colectivo": "logistica",
            "contexto": "Personas sin ordenador ni correo corporativo; responden por QR o en quiosco",
            "duracion_max_seg": 60,
            "temas_prohibidos": ["salario"],
        },
        "encuesta_id": None,
        "que_mirar": ["Encuesta de 3 preguntas como máximo",
                      "Respuesta desde el móvil y en modo quiosco",
                      "Alerta de representatividad si responde menos del 20 %"],
    },
    {
        "id": "C",
        "titulo": "Gran volumen de comentarios",
        "descripcion": "Unos 600 comentarios de 5 colectivos y 2 periodos: agruparlos, resumirlos, "
                       "detectar temas emergentes y explicar los límites del análisis.",
        "necesidad": None,
        "encuesta_id": "enc_000",
        "que_mirar": ["Temas con su tendencia: descansos y turnos suben, comunicación es nuevo",
                      "Caída de la pregunta de condiciones en planta",
                      "Límites del análisis y segmentos ocultos por tener menos de 5 respuestas"],
    },
]
