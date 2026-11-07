/**
 * ejemplos_v2.js — datos de ejemplo con el formato de la versión 2 (contratos v2, sección 1)
 * Solo se usan con USAR_EJEMPLOS = true en api.js, mientras el backend v2 no está listo.
 */

export const ENCUESTA_MULTISECTOR = {
  id: 'enc_002',
  estado: 'publicada',
  origen: 'ia',
  titulo: 'El cambio de turnos en planta, logística y comercial',
  intro: 'Queremos saber cómo te está afectando el nuevo sistema de turnos. Es anónima y dura menos de 2 minutos.',
  periodo: '2026-11',
  url: null,
  qr: null,
  colectivo: 'varios',
  colectivos: ['planta', 'logistica', 'comercial'],
  tiempo_estimado_seg: 90,
  tiempo_por_colectivo: { planta: 90, logistica: 75, comercial: 75 },
  preguntas: [
    { id: 'c1', texto: '¿Cómo valoras el nuevo sistema de turnos?', tipo: 'escala_1_5', opciones: [], dimension: 'condiciones', condicion: null },
    { id: 'c2', texto: '¿Te llega a tiempo la información de los cambios?', tipo: 'escala_1_5', opciones: [], dimension: 'liderazgo', condicion: null },
    { id: 'c3', texto: '¿Qué cambiarías?', tipo: 'texto', opciones: [], dimension: 'condiciones', condicion: null },
  ],
  preguntas_por_colectivo: {
    planta: [
      { id: 'planta_p1', texto: '¿Te da tiempo a hacer la pausa completa en tu turno?', tipo: 'si_no', opciones: [], dimension: 'bienestar', condicion: null },
      { id: 'planta_p2', texto: '¿Cómo valoras el relevo entre turnos en la línea?', tipo: 'escala_1_5', opciones: [], dimension: 'entorno', condicion: null },
    ],
    logistica: [
      { id: 'logistica_p1', texto: '¿Te llega a tiempo el cuadrante de rutas?', tipo: 'escala_1_5', opciones: [], dimension: 'condiciones', condicion: null },
    ],
    comercial: [
      { id: 'comercial_p1', texto: '¿Cómo afecta el cambio a la coordinación con almacén para tus visitas?', tipo: 'escala_1_5', opciones: [], dimension: 'entorno', condicion: null },
    ],
  },
};

export const ANALISIS_MULTISECTOR = {
  encuesta_id: 'enc_002',
  titulo: 'El cambio de turnos en planta, logística y comercial',
  n_respuestas: 312,
  n_anterior: 246,
  n_simuladas: 300,
  periodo_actual: '2026-11',
  periodo_anterior: '2026-10',
  colectivos: ['planta', 'logistica', 'comercial'],
  participacion_global: 0.236,
  participacion: [
    { colectivo: 'planta', turno: 'manana', respuestas: 82, personas: 300, tasa: 0.273, representativo: true },
    { colectivo: 'planta', turno: 'tarde', respuestas: 71, personas: 280, tasa: 0.254, representativo: true },
    { colectivo: 'planta', turno: 'noche', respuestas: 19, personas: 220, tasa: 0.086, representativo: false },
    { colectivo: 'logistica', turno: 'sin_turno', respuestas: 31, personas: 240, tasa: 0.129, representativo: false },
    { colectivo: 'comercial', turno: 'sin_turno', respuestas: 109, personas: 160, tasa: 0.681, representativo: true },
  ],
  medias: [
    { pregunta: 'c1', colectivo: 'planta', media: 2.6, n: 172 },
    { pregunta: 'c1', colectivo: 'logistica', media: 2.9, n: 31 },
    { pregunta: 'c1', colectivo: 'comercial', media: 3.6, n: 109 },
    { pregunta: 'c2', colectivo: 'planta', media: 2.2, n: 172 },
    { pregunta: 'c2', colectivo: 'logistica', media: 2.5, n: 31 },
    { pregunta: 'c2', colectivo: 'comercial', media: 3.3, n: 109 },
    { pregunta: 'planta_p2', colectivo: 'planta', media: 2.4, n: 172 },
    { pregunta: 'logistica_p1', colectivo: 'logistica', media: 2.7, n: 31 },
    { pregunta: 'comercial_p1', colectivo: 'comercial', media: 3.1, n: 109 },
  ],
  medias_anterior: [
    { pregunta: 'c1', colectivo: 'planta', media: 3.0, n: 150 },
    { pregunta: 'c1', colectivo: 'logistica', media: 3.0, n: 28 },
    { pregunta: 'c1', colectivo: 'comercial', media: 3.5, n: 68 },
    { pregunta: 'c2', colectivo: 'planta', media: 2.9, n: 150 },
    { pregunta: 'c2', colectivo: 'logistica', media: 2.6, n: 28 },
    { pregunta: 'c2', colectivo: 'comercial', media: 3.4, n: 68 },
  ],
  preguntas: [
    { id: 'c1', texto: '¿Cómo valoras el nuevo sistema de turnos?', tipo: 'escala_1_5', dimension: 'condiciones', ambito: 'comun' },
    { id: 'c2', texto: '¿Te llega a tiempo la información de los cambios?', tipo: 'escala_1_5', dimension: 'liderazgo', ambito: 'comun' },
    { id: 'c3', texto: '¿Qué cambiarías?', tipo: 'texto', dimension: 'condiciones', ambito: 'comun' },
    { id: 'planta_p1', texto: '¿Te da tiempo a hacer la pausa completa en tu turno?', tipo: 'si_no', dimension: 'bienestar', ambito: 'planta' },
    { id: 'planta_p2', texto: '¿Cómo valoras el relevo entre turnos en la línea?', tipo: 'escala_1_5', dimension: 'entorno', ambito: 'planta' },
    { id: 'logistica_p1', texto: '¿Te llega a tiempo el cuadrante de rutas?', tipo: 'escala_1_5', dimension: 'condiciones', ambito: 'logistica' },
    { id: 'comercial_p1', texto: '¿Cómo afecta el cambio a la coordinación con almacén para tus visitas?', tipo: 'escala_1_5', dimension: 'entorno', ambito: 'comercial' },
  ],
  distribuciones: [
    { pregunta: 'c1', texto: '¿Cómo valoras el nuevo sistema de turnos?', dimension: 'condiciones', conteos: [48, 66, 82, 78, 38], n: 312, media: 2.97 },
    { pregunta: 'c2', texto: '¿Te llega a tiempo la información de los cambios?', dimension: 'liderazgo', conteos: [79, 84, 70, 52, 27], n: 312, media: 2.55 },
    { pregunta: 'planta_p2', texto: '¿Cómo valoras el relevo entre turnos en la línea?', dimension: 'entorno', conteos: [42, 52, 41, 27, 10], n: 172, media: 2.4 },
    { pregunta: 'logistica_p1', texto: '¿Te llega a tiempo el cuadrante de rutas?', dimension: 'condiciones', conteos: [5, 9, 9, 6, 2], n: 31, media: 2.7 },
    { pregunta: 'comercial_p1', texto: '¿Cómo afecta el cambio a la coordinación con almacén para tus visitas?', dimension: 'entorno', conteos: [9, 22, 36, 30, 12], n: 109, media: 3.1 },
  ],
  temas: [
    { tema: 'comunicacion', n: 31, n_anterior: 0, pct: 0.21, pct_anterior: 0, resumen: 'Muchas personas dicen que se enteraron del cambio de turnos por canales informales y piden un aviso oficial con antelación.', tendencia: 'nuevo' },
    { tema: 'descansos', n: 38, n_anterior: 19, pct: 0.26, pct_anterior: 0.15, resumen: 'En planta, sobre todo de noche, se repite que la pausa no da para descansar ni comer con calma tras el cambio.', tendencia: 'sube' },
    { tema: 'turnos', n: 29, n_anterior: 17, pct: 0.2, pct_anterior: 0.13, resumen: 'Se pide estabilidad en las rotaciones y conocer el cuadrante con más tiempo.', tendencia: 'sube' },
    { tema: 'carga_trabajo', n: 22, n_anterior: 24, pct: 0.15, pct_anterior: 0.19, resumen: 'Algunas franjas concentran más trabajo tras la reorganización, sobre todo en logística.', tendencia: 'estable' },
    { tema: 'herramientas', n: 9, n_anterior: 15, pct: 0.06, pct_anterior: 0.12, resumen: 'Quejas menores sobre terminales y aplicaciones de rutas.', tendencia: 'baja' },
  ],
  alertas: [
    { tipo: 'representatividad', colectivo: 'planta', turno: 'noche', mensaje: 'El turno de noche de planta solo ha respondido un 8,6 % (19 de 220): los resultados pueden no representarle.' },
    { tipo: 'representatividad', colectivo: 'logistica', turno: 'sin_turno', mensaje: 'Logística solo ha respondido un 12,9 % (31 de 240): los resultados pueden no representarle.' },
    { tipo: 'caida', colectivo: 'planta', pregunta: 'c2', mensaje: 'La pregunta «¿Te llega a tiempo la información de los cambios?» baja de 2,9 a 2,2 en planta respecto al periodo anterior.' },
    { tipo: 'caida', colectivo: 'planta', pregunta: 'c1', mensaje: 'La pregunta «¿Cómo valoras el nuevo sistema de turnos?» baja de 3,0 a 2,6 en planta respecto al periodo anterior.' },
    { tipo: 'tema_emergente', colectivo: 'planta', mensaje: 'El tema comunicación aparece como nuevo con 31 comentarios.' },
  ],
  limites: [
    'Muestra pequeña en el turno de noche de planta (19 respuestas) y en logística (31): interpretar con cautela.',
    'Segmentos con menos de 5 respuestas ocultos.',
    'Una correlación no demuestra una causa.',
  ],
  zonas: [
    {
      colectivo: 'planta', respuestas: 172, personas: 800, tasa: 0.215, representativo: false,
      media: 2.4, media_anterior: 2.95, variacion: -0.55,
      temas: [{ tema: 'descansos', n: 30 }, { tema: 'comunicacion', n: 22 }, { tema: 'turnos', n: 18 }],
      alertas: ['El turno de noche de planta solo ha respondido un 8,6 % (19 de 220).', 'La valoración de la información de los cambios baja de 2,9 a 2,2.'],
      turnos: [
        { colectivo: 'planta', turno: 'manana', respuestas: 82, personas: 300, tasa: 0.273, representativo: true, media: 2.6 },
        { colectivo: 'planta', turno: 'tarde', respuestas: 71, personas: 280, tasa: 0.254, representativo: true, media: 2.5 },
        { colectivo: 'planta', turno: 'noche', respuestas: 19, personas: 220, tasa: 0.086, representativo: false, media: 1.9 },
      ],
    },
    {
      colectivo: 'logistica', respuestas: 31, personas: 240, tasa: 0.129, representativo: false,
      media: 2.7, media_anterior: 2.8, variacion: -0.1,
      temas: [{ tema: 'carga_trabajo', n: 9 }, { tema: 'turnos', n: 6 }],
      alertas: ['Logística solo ha respondido un 12,9 % (31 de 240).'],
      turnos: [{ colectivo: 'logistica', turno: 'sin_turno', respuestas: 31, personas: 240, tasa: 0.129, representativo: false, media: 2.7 }],
    },
    {
      colectivo: 'comercial', respuestas: 109, personas: 160, tasa: 0.681, representativo: true,
      media: 3.33, media_anterior: 3.45, variacion: -0.12,
      temas: [{ tema: 'comunicacion', n: 8 }, { tema: 'turnos', n: 5 }],
      alertas: [],
      turnos: [{ colectivo: 'comercial', turno: 'sin_turno', respuestas: 109, personas: 160, tasa: 0.681, representativo: true, media: 3.33 }],
    },
  ],
  lectura: 'La valoración del nuevo sistema de turnos baja en planta de 3,0 a 2,6, y la información sobre los cambios es el punto más débil (2,2). Comunicación aparece como tema nuevo con el 21 % de los comentarios. El turno de noche y logística responden poco (8,6 % y 12,9 %), así que sus datos deben leerse con cautela.',
  estado_ia: { llm: true, pendientes: 2, comentarios_total: 101, comentarios_ia: 75, listo: false, origen_recomendaciones: 'ia' },
};

export const RECOMENDACIONES_MULTISECTOR = {
  origen: 'ia',
  lectura: ANALISIS_MULTISECTOR.lectura,
  acciones: [
    {
      titulo: 'Avisar de los cambios de turno por un canal oficial y con antelación',
      motivo: 'Comunicación aparece como tema nuevo (21 % de los comentarios) y la información de los cambios baja a 2,2 en planta.',
      tema: 'comunicacion', responsable: 'RRHH y jefes de turno', plazo: '2 semanas',
      indicador: 'Información de los cambios ≥ 3,0 en el seguimiento',
    },
    {
      titulo: 'Revisar la duración y el momento de la pausa en el turno de noche',
      motivo: 'Descansos pasa del 15 % al 26 % de los comentarios y la media del turno de noche es 1,9.',
      tema: 'descansos', responsable: 'Dirección de planta', plazo: '1 mes',
      indicador: 'Pausa completa en noche ≥ 70 % de síes',
    },
    {
      titulo: 'Reforzar la participación de noche y de logística con QR y quiosco',
      motivo: 'El turno de noche responde un 8,6 % y logística un 12,9 %: sus resultados no son representativos.',
      tema: 'otros', responsable: 'RRHH', plazo: '1 semana',
      indicador: 'Participación ≥ 20 % en ambos segmentos',
    },
  ],
  seguimiento: {
    objetivo: 'Comprobar si el aviso oficial de los cambios y el ajuste de la pausa mejoran la percepción del nuevo sistema de turnos',
    colectivos: ['planta', 'logistica'],
    contexto: 'En noviembre la información de los cambios bajó a 2,2 en planta y el tema comunicación apareció como nuevo.',
    duracion_max_seg: 60,
    temas_prohibidos: ['salario'],
  },
};

/** Respuesta de ejemplo de "Pregunta a tus datos" */
export function respuestaPreguntaEjemplo(pregunta) {
  const p = String(pregunta || '').toLowerCase();
  if (/\b(qui[eé]n|nombre|dni|correo|despedir|sancionar)\b/.test(p)) {
    return {
      respuesta: 'Esta herramienta solo trabaja con resultados agregados de grupos de 5 personas o más. No puede identificar a nadie ni decir qué ha respondido una persona concreta.',
      cifras: [], confianza: 'alta', origen: 'reglas',
    };
  }
  return {
    respuesta: 'Planta es el sector peor valorado: su media baja de 2,95 a 2,4 y el punto más débil es la información sobre los cambios (2,2). Los comentarios apuntan a la comunicación del cambio y a los descansos. El dato del turno de noche se basa en solo 19 respuestas, así que no es representativo.',
    cifras: ['Planta: 2,4 de media (antes 2,95)', 'Información de los cambios en planta: 2,2', 'Comunicación: 21 % de los comentarios (nuevo)', 'Turno de noche: 19 de 220 respuestas (8,6 %)'],
    confianza: 'media', origen: 'ia',
  };
}
