"""Plantillas de respaldo para generar encuestas sin modelo, en castellano, catalán e inglés.

Una encuesta se escribe en su idioma original (el de la pantalla de RRHH al generarla): sin IA,
una encuesta en catalán sale en catalán.
"""

from __future__ import annotations

# claves: raíces sin tildes (en cualquier idioma) que, al principio de una palabra del objetivo o
# del contexto, eligen la plantilla. preguntas: 3 escalas y 1 texto final, con su dimensión.
TEMAS_RESPALDO: list[dict] = [
    {
        "claves": ["turno", "horario", "cuadrante", "rotacion", "jornada",
                   "torn", "horari", "quadrant", "rotacio",
                   "shift", "rota", "schedule", "roster"],
        "textos": {
            "es": {"titulo": "Tu opinión sobre los nuevos turnos", "sobre": "el cambio de turnos",
                   "preguntas": [("¿Cómo valoras el nuevo sistema de turnos?", "condiciones"),
                                 ("¿Te explicaron bien cómo funciona el cambio?", "liderazgo"),
                                 ("¿Puedes descansar bien con los turnos actuales?", "bienestar"),
                                 ("¿Qué cambiarías o reforzarías de los turnos?", "condiciones")]},
            "ca": {"titulo": "La teva opinió sobre els nous torns", "sobre": "el canvi de torns",
                   "preguntas": [("Com valores el nou sistema de torns?", "condiciones"),
                                 ("T'han explicat bé com funciona el canvi?", "liderazgo"),
                                 ("Pots descansar bé amb els torns actuals?", "bienestar"),
                                 ("Què canviaries o reforçaries dels torns?", "condiciones")]},
            "en": {"titulo": "Your view on the new shifts", "sobre": "the shift change",
                   "preguntas": [("How do you rate the new shift system?", "condiciones"),
                                 ("Was the change explained clearly to you?", "liderazgo"),
                                 ("Can you rest properly with the current shifts?", "bienestar"),
                                 ("What would you change or improve about the shifts?", "condiciones")]},
        },
    },
    {
        "claves": ["herramienta", "software", "aplicacion", "app", "sistema nuevo", "programa",
                   "maquina", "tablet", "plataforma", "digital",
                   "eina", "aplicacio", "nou sistema",
                   "tool", "application", "machine", "platform", "new system"],
        "textos": {
            "es": {"titulo": "Tu opinión sobre la nueva herramienta", "sobre": "la nueva herramienta",
                   "preguntas": [("¿Cómo valoras la nueva herramienta?", "condiciones"),
                                 ("¿Has recibido formación suficiente para usarla?", "desarrollo"),
                                 ("¿Te ayuda a hacer mejor tu trabajo?", "entorno"),
                                 ("¿Qué mejorarías de la herramienta?", "condiciones")]},
            "ca": {"titulo": "La teva opinió sobre la nova eina", "sobre": "la nova eina",
                   "preguntas": [("Com valores la nova eina?", "condiciones"),
                                 ("Has rebut prou formació per fer-la servir?", "desarrollo"),
                                 ("T'ajuda a fer millor la teva feina?", "entorno"),
                                 ("Què milloraries de l'eina?", "condiciones")]},
            "en": {"titulo": "Your view on the new tool", "sobre": "the new tool",
                   "preguntas": [("How do you rate the new tool?", "condiciones"),
                                 ("Have you had enough training to use it?", "desarrollo"),
                                 ("Does it help you do your job better?", "entorno"),
                                 ("What would you improve about the tool?", "condiciones")]},
        },
    },
    {
        "claves": ["carga", "ritmo", "volumen", "pico", "estres", "presion",
                   "carrega", "ritme", "volum", "pic", "pressio",
                   "workload", "pace", "volume", "peak", "stress", "pressure"],
        "textos": {
            "es": {"titulo": "Tu opinión sobre la carga de trabajo", "sobre": "la carga de trabajo",
                   "preguntas": [("¿Cómo valoras tu carga de trabajo actual?", "condiciones"),
                                 ("¿Puedes hacer pausas cuando lo necesitas?", "bienestar"),
                                 ("¿Tienes apoyo cuando hay picos de trabajo?", "liderazgo"),
                                 ("¿Qué ayudaría a repartir mejor el trabajo?", "condiciones")]},
            "ca": {"titulo": "La teva opinió sobre la càrrega de feina", "sobre": "la càrrega de feina",
                   "preguntas": [("Com valores la teva càrrega de feina actual?", "condiciones"),
                                 ("Pots fer pauses quan ho necessites?", "bienestar"),
                                 ("Tens suport quan hi ha pics de feina?", "liderazgo"),
                                 ("Què ajudaria a repartir millor la feina?", "condiciones")]},
            "en": {"titulo": "Your view on workload", "sobre": "your workload",
                   "preguntas": [("How do you rate your current workload?", "condiciones"),
                                 ("Can you take breaks when you need them?", "bienestar"),
                                 ("Do you get support during workload peaks?", "liderazgo"),
                                 ("What would help share the work better?", "condiciones")]},
        },
    },
    {
        "claves": ["comunica", "informa", "aviso", "transparen", "avis", "notice"],
        "textos": {
            "es": {"titulo": "Tu opinión sobre la comunicación", "sobre": "cómo te llega la información",
                   "preguntas": [("¿Te llega a tiempo la información importante?", "cultura"),
                                 ("¿Entiendes por qué se toman las decisiones?", "liderazgo"),
                                 ("¿Sabes a quién acudir si tienes dudas?", "liderazgo"),
                                 ("¿Cómo te gustaría recibir la información?", "cultura")]},
            "ca": {"titulo": "La teva opinió sobre la comunicació", "sobre": "com t'arriba la informació",
                   "preguntas": [("T'arriba a temps la informació important?", "cultura"),
                                 ("Entens per què es prenen les decisions?", "liderazgo"),
                                 ("Saps a qui adreçar-te si tens dubtes?", "liderazgo"),
                                 ("Com t'agradaria rebre la informació?", "cultura")]},
            "en": {"titulo": "Your view on communication", "sobre": "how information reaches you",
                   "preguntas": [("Does important information reach you in time?", "cultura"),
                                 ("Do you understand why decisions are made?", "liderazgo"),
                                 ("Do you know who to ask if you have questions?", "liderazgo"),
                                 ("How would you like to receive information?", "cultura")]},
        },
    },
    {
        "claves": ["formacion", "curso", "aprend", "desarrollo", "carrera", "crecer",
                   "formacio", "curs", "desenvolupament", "creixe",
                   "training", "course", "learn", "development", "career", "grow"],
        "textos": {
            "es": {"titulo": "Tu opinión sobre formación y desarrollo", "sobre": "tu formación y desarrollo",
                   "preguntas": [("¿Tienes oportunidades para aprender cosas nuevas?", "desarrollo"),
                                 ("¿La formación te sirve en tu día a día?", "desarrollo"),
                                 ("¿Sabes cómo puedes crecer en la empresa?", "desarrollo"),
                                 ("¿Qué te gustaría aprender?", "desarrollo")]},
            "ca": {"titulo": "La teva opinió sobre formació i desenvolupament",
                   "sobre": "la teva formació i desenvolupament",
                   "preguntas": [("Tens oportunitats per aprendre coses noves?", "desarrollo"),
                                 ("La formació et serveix en el dia a dia?", "desarrollo"),
                                 ("Saps com pots créixer a l'empresa?", "desarrollo"),
                                 ("Què t'agradaria aprendre?", "desarrollo")]},
            "en": {"titulo": "Your view on training and development", "sobre": "your training and development",
                   "preguntas": [("Do you have opportunities to learn new things?", "desarrollo"),
                                 ("Is training useful in your daily work?", "desarrollo"),
                                 ("Do you know how you can grow in the company?", "desarrollo"),
                                 ("What would you like to learn?", "desarrollo")]},
        },
    },
]

RESPALDO_GENERAL = {
    "es": {"titulo": "¿Cómo estás?", "sobre": "tu día a día en el trabajo",
           "preguntas": [("¿Cómo te sientes en tu trabajo últimamente?", "bienestar"),
                         ("¿Te sientes escuchado/a por tu responsable?", "liderazgo"),
                         ("¿Tienes lo necesario para hacer bien tu trabajo?", "condiciones"),
                         ("¿Qué cambiarías para estar mejor?", "condiciones")]},
    "ca": {"titulo": "Com estàs?", "sobre": "el teu dia a dia a la feina",
           "preguntas": [("Com et sents a la feina últimament?", "bienestar"),
                         ("Et sents escoltat/da pel teu responsable?", "liderazgo"),
                         ("Tens el necessari per fer bé la teva feina?", "condiciones"),
                         ("Què canviaries per estar millor?", "condiciones")]},
    "en": {"titulo": "How are you?", "sobre": "your day-to-day at work",
           "preguntas": [("How have you been feeling at work lately?", "bienestar"),
                         ("Do you feel listened to by your manager?", "liderazgo"),
                         ("Do you have what you need to do your job well?", "condiciones"),
                         ("What would you change to feel better at work?", "condiciones")]},
}

INTRO = {
    "es": "Queremos saber qué opinas sobre {sobre} para mejorarlo. Es anónima: solo se ven resultados agregados.",
    "ca": "Volem saber la teva opinió sobre {sobre} per millorar-ho. És anònima: només es veuen resultats agregats.",
    "en": "We want to know what you think about {sobre} so we can improve it. It is anonymous: only aggregated results are shown.",
}

QUE_CAMBIARIAS = {"es": "¿Qué cambiarías?", "ca": "Què canviaries?", "en": "What would you change?"}

# Respaldo multisector: dos preguntas propias por colectivo, con el vocabulario de cada uno
PREGUNTAS_SECTOR: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "es": {
        "planta": [("¿Te da tiempo a hacer la pausa completa en tu turno?", "si_no", "bienestar"),
                   ("¿Recibes el cuadrante con antelación suficiente?", "escala_1_5", "condiciones")],
        "logistica": [("¿El relevo te da tiempo a pasar la información?", "si_no", "condiciones"),
                      ("¿Cómo valoras la coordinación en el muelle?", "escala_1_5", "entorno")],
        "comercial": [("¿Tienes el apoyo que necesitas para tus visitas?", "escala_1_5", "liderazgo"),
                      ("¿Puedes desconectar al acabar la jornada en ruta?", "si_no", "bienestar")],
        "oficina": [("¿Las reuniones te dejan tiempo para tu trabajo?", "escala_1_5", "condiciones"),
                    ("¿Las herramientas digitales te facilitan el día a día?", "escala_1_5", "entorno")],
        "manager": [("¿Tienes la información necesaria para decidir con tu equipo?", "escala_1_5", "liderazgo"),
                    ("¿Recibes apoyo de People para gestionar los cambios?", "escala_1_5", "cultura")],
    },
    "ca": {
        "planta": [("Et dóna temps de fer la pausa completa al teu torn?", "si_no", "bienestar"),
                   ("Reps el quadrant amb prou antelació?", "escala_1_5", "condiciones")],
        "logistica": [("El relleu et dóna temps per passar la informació?", "si_no", "condiciones"),
                      ("Com valores la coordinació al moll?", "escala_1_5", "entorno")],
        "comercial": [("Tens el suport que necessites per a les teves visites?", "escala_1_5", "liderazgo"),
                      ("Pots desconnectar en acabar la jornada de ruta?", "si_no", "bienestar")],
        "oficina": [("Les reunions et deixen temps per a la teva feina?", "escala_1_5", "condiciones"),
                    ("Les eines digitals et faciliten el dia a dia?", "escala_1_5", "entorno")],
        "manager": [("Tens la informació necessària per decidir amb el teu equip?", "escala_1_5", "liderazgo"),
                    ("Reps suport de People per gestionar els canvis?", "escala_1_5", "cultura")],
    },
    "en": {
        "planta": [("Do you have time to take your full break during your shift?", "si_no", "bienestar"),
                   ("Do you get the rota early enough?", "escala_1_5", "condiciones")],
        "logistica": [("Does the handover give you time to pass on information?", "si_no", "condiciones"),
                      ("How do you rate coordination at the loading dock?", "escala_1_5", "entorno")],
        "comercial": [("Do you have the support you need for your visits?", "escala_1_5", "liderazgo"),
                      ("Can you switch off after your day on the road?", "si_no", "bienestar")],
        "oficina": [("Do meetings leave you time for your own work?", "escala_1_5", "condiciones"),
                    ("Do digital tools make your day-to-day easier?", "escala_1_5", "entorno")],
        "manager": [("Do you have the information you need to decide with your team?", "escala_1_5", "liderazgo"),
                    ("Do you get support from People to manage changes?", "escala_1_5", "cultura")],
    },
}

# Temas prohibidos en cualquier idioma. Si un tema prohibido empieza por alguna de las "claves",
# se bloquean todas las "raices" (expresiones regulares al principio de palabra, texto sin tildes).
GRUPOS_PROHIBIDOS = [
    {
        "claves": ["salari", "sueld", "nomina", "diner", "retribu", "remunera", "sou", "sous",
                   "salary", "wage", "pay", "money", "compensation"],
        "raices": [
            # castellano
            "salari", "sueld", "nomina", "dinero", "retribu", "remunera", "paga", "pagan", "pagar",
            "cobr", "plus\\b", "incentivo", "bonus",
            # catalán
            "sou\\b", "sous\\b", "diners", "pagues",
            # inglés
            "salar", "wage", "pay\\b", "pays\\b", "paid\\b", "payroll", "payment", "money",
            "compensation", "earning", "bonuses",
        ],
    },
]

ERRORES = {
    "es": {"duracion": "La duración máxima debe ser de al menos {minimo} s con {n} {sectores}",
           "sector": "sector", "sectores": "sectores",
           "no_caben": "Con {segundos} s no caben {total} preguntas para {colectivo}: aumenta la duración máxima"},
    "ca": {"duracion": "La durada màxima ha de ser d'almenys {minimo} s amb {n} {sectores}",
           "sector": "sector", "sectores": "sectors",
           "no_caben": "Amb {segundos} s no hi caben {total} preguntes per a {colectivo}: augmenta la durada màxima"},
    "en": {"duracion": "The maximum duration must be at least {minimo} s with {n} {sectores}",
           "sector": "sector", "sectores": "sectors",
           "no_caben": "With {segundos} s, {total} questions do not fit for {colectivo}: increase the maximum duration"},
}
