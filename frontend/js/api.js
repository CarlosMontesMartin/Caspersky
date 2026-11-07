/**
 * Damm · Escucha activa
 * Cliente API del Frontend (UAB 1)
 *
 * Contrato estricto: contratos/modulos.md sección 6 y contratos/api.md.
 * Ninguna página llama a fetch directamente: todo pasa por este módulo.
 */

export const USAR_EJEMPLOS = false;

/**
 * Generador SVG de código QR estético para modo mock
 */
function generarQrDataUrl(texto) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
    <rect width="200" height="200" fill="#FFFFFF"/>
    <!-- Patrones de esquina (position marks) -->
    <rect x="20" y="20" width="46" height="46" fill="#2A1A1A"/>
    <rect x="26" y="26" width="34" height="34" fill="#FFFFFF"/>
    <rect x="33" y="33" width="20" height="20" fill="#2A1A1A"/>

    <rect x="134" y="20" width="46" height="46" fill="#2A1A1A"/>
    <rect x="140" y="26" width="34" height="34" fill="#FFFFFF"/>
    <rect x="147" y="33" width="20" height="20" fill="#2A1A1A"/>

    <rect x="20" y="134" width="46" height="46" fill="#2A1A1A"/>
    <rect x="26" y="140" width="34" height="34" fill="#FFFFFF"/>
    <rect x="33" y="147" width="20" height="20" fill="#2A1A1A"/>

    <!-- Puntos de datos simulados -->
    <rect x="76" y="24" width="8" height="8" fill="#2A1A1A"/>
    <rect x="92" y="24" width="16" height="8" fill="#2A1A1A"/>
    <rect x="116" y="24" width="8" height="8" fill="#2A1A1A"/>

    <rect x="76" y="40" width="16" height="8" fill="#2A1A1A"/>
    <rect x="100" y="40" width="8" height="8" fill="#2A1A1A"/>
    <rect x="116" y="40" width="10" height="8" fill="#2A1A1A"/>

    <rect x="24" y="76" width="8" height="16" fill="#2A1A1A"/>
    <rect x="40" y="84" width="16" height="8" fill="#2A1A1A"/>
    <rect x="64" y="76" width="8" height="8" fill="#2A1A1A"/>
    <rect x="80" y="76" width="24" height="8" fill="#2A1A1A"/>
    <rect x="112" y="84" width="16" height="16" fill="#2A1A1A"/>
    <rect x="136" y="76" width="8" height="8" fill="#2A1A1A"/>
    <rect x="152" y="84" width="24" height="8" fill="#2A1A1A"/>

    <rect x="24" y="100" width="16" height="8" fill="#2A1A1A"/>
    <rect x="48" y="108" width="8" height="16" fill="#2A1A1A"/>
    <rect x="64" y="100" width="16" height="8" fill="#2A1A1A"/>
    <rect x="88" y="92" width="8" height="24" fill="#2A1A1A"/>
    <rect x="104" y="108" width="16" height="8" fill="#2A1A1A"/>
    <rect x="128" y="100" width="24" height="8" fill="#2A1A1A"/>
    <rect x="160" y="100" width="16" height="16" fill="#2A1A1A"/>

    <rect x="76" y="134" width="16" height="8" fill="#2A1A1A"/>
    <rect x="100" y="142" width="8" height="16" fill="#2A1A1A"/>
    <rect x="116" y="134" width="24" height="8" fill="#2A1A1A"/>
    <rect x="148" y="142" width="16" height="8" fill="#2A1A1A"/>
    <rect x="172" y="134" width="8" height="16" fill="#2A1A1A"/>

    <rect x="76" y="160" width="24" height="8" fill="#2A1A1A"/>
    <rect x="108" y="168" width="16" height="8" fill="#2A1A1A"/>
    <rect x="132" y="160" width="12" height="16" fill="#2A1A1A"/>
    <rect x="152" y="168" width="28" height="8" fill="#2A1A1A"/>
  </svg>`;
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

// Estructura inicial para simular el ciclo cuando USAR_EJEMPLOS = true
const _almacenInicial = {
  encuestas: {
    "enc_000": {
      id: "enc_000",
      estado: "publicada",
      titulo: "Pulso de clima general",
      intro: "Evaluación periódica de clima laboral en todos los colectivos de Damm.",
      colectivo: "todos",
      periodo: "2026-10",
      tiempo_estimado_seg: 90,
      url: (typeof window !== "undefined" ? window.location.origin : "http://localhost:5500") + "/responder/enc_000?canal=qr",
      qr: generarQrDataUrl((typeof window !== "undefined" ? window.location.origin : "http://localhost:5500") + "/responder/enc_000?canal=qr"),
      preguntas: [
        { id: "p1", texto: "¿Cómo valoras tu bienestar general en el trabajo?", tipo: "escala_1_5", opciones: [], dimension: "bienestar", condicion: null },
        { id: "p2", texto: "¿Sientes cercanía y apoyo por parte de tu responsable directo?", tipo: "escala_1_5", opciones: [], dimension: "liderazgo", condicion: null },
        { id: "p3", texto: "¿Tienes oportunidades de aprendizaje y desarrollo?", tipo: "escala_1_5", opciones: [], dimension: "desarrollo", condicion: null },
        { id: "p4", texto: "¿Cómo valoras las condiciones y turnos actuales?", tipo: "escala_1_5", opciones: [], dimension: "condiciones", condicion: null },
        { id: "p5", texto: "¿El ambiente y entorno de trabajo te resultan cómodos?", tipo: "escala_1_5", opciones: [], dimension: "entorno", condicion: null },
        { id: "p6", texto: "¿Qué mejorarías en tu día a día?", tipo: "texto", opciones: [], dimension: "cultura", condicion: null }
      ]
    },
    "enc_001": {
      id: "enc_001",
      estado: "borrador",
      titulo: "¿Qué tal con los nuevos turnos?",
      intro: "Queremos saber cómo te está yendo con el nuevo sistema de turnos. Es anónima y dura menos de 1 minuto.",
      colectivo: "planta",
      periodo: "2026-11",
      tiempo_estimado_seg: 59,
      url: null,
      qr: null,
      preguntas: [
        {
          id: "p1",
          texto: "¿Cómo valoras el nuevo sistema de turnos en general?",
          tipo: "escala_1_5",
          opciones: [],
          dimension: "condiciones",
          condicion: null
        },
        {
          id: "p2",
          texto: "¿Qué es lo que más te cuesta del cambio de turnos?",
          tipo: "opcion",
          opciones: [
            "Los descansos entre turnos",
            "La comunicación de los cambios",
            "La conciliación con mi vida personal",
            "No me cuesta nada en especial"
          ],
          dimension: "entorno",
          condicion: null
        },
        {
          id: "p3",
          texto: "¿Te avisaron con tiempo suficiente antes del cambio de turnos?",
          tipo: "si_no",
          opciones: [],
          dimension: "cultura",
          condicion: null
        },
        {
          id: "p4",
          texto: "¿Cómo valoras el tiempo de descanso que tienes ahora entre turnos?",
          tipo: "escala_1_5",
          opciones: [],
          dimension: "bienestar",
          condicion: {
            pregunta: "p1",
            valor_max: 2
          }
        },
        {
          id: "p5",
          texto: "¿Quieres contarnos algo más sobre los turnos?",
          tipo: "texto",
          opciones: [],
          dimension: "condiciones",
          condicion: null
        }
      ]
    }
  },
  respuestas: {
    "enc_000": 612,
    "enc_001": 312
  }
};

/**
 * Carga el almacén simulado desde sessionStorage (clave "almacen_simulado")
 * para persistir cambios de estado entre páginas
 */
function _obtenerAlmacen() {
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      const guardado = window.sessionStorage.getItem("almacen_simulado");
      if (guardado) {
        return JSON.parse(guardado);
      }
    } catch (e) {
      console.warn("No se pudo leer almacen_simulado de sessionStorage:", e);
    }
  }
  const inicial = JSON.parse(JSON.stringify(_almacenInicial));
  _guardarAlmacen(inicial);
  return inicial;
}

/**
 * Guarda el almacén simulado en sessionStorage (clave "almacen_simulado")
 */
function _guardarAlmacen(almacen) {
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      window.sessionStorage.setItem("almacen_simulado", JSON.stringify(almacen));
    } catch (e) {
      console.warn("No se pudo guardar almacen_simulado en sessionStorage:", e);
    }
  }
}

// Inicialización inmediata en sessionStorage
let _almacenSimulado = _obtenerAlmacen();

/**
 * Petición HTTP centralizada al backend con manejo de errores FastAPI
 */
async function peticion(ruta, opciones = {}) {
  const cabeceras = {
    "Accept": "application/json",
    ...(opciones.headers || {})
  };

  if (opciones.body && typeof opciones.body === "object") {
    cabeceras["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(opciones.body);
  }

  const respuesta = await fetch(ruta, {
    ...opciones,
    headers: cabeceras
  });

  if (!respuesta.ok) {
    let detalle = respuesta.statusText;
    try {
      const errorJson = await respuesta.json();
      if (typeof errorJson.detail === "string") {
        detalle = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        detalle = errorJson.detail.map(d => d.msg || JSON.stringify(d)).join(", ");
      } else if (errorJson.detail) {
        detalle = JSON.stringify(errorJson.detail);
      }
    } catch (_) {
      // Ignora error de parseo si no es JSON
    }
    throw new Error(detalle || `Error HTTP ${respuesta.status}`);
  }

  return respuesta.json();
}

/**
 * GET /encuestas
 * Devuelve lista de ResumenEncuesta:
 * [{ id, titulo, colectivo, estado, periodo, n_respuestas }]
 */
export async function listarEncuestas() {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    return Object.values(almacen.encuestas).map(e => ({
      id: e.id,
      titulo: e.titulo,
      colectivo: e.colectivo,
      estado: e.estado,
      periodo: e.periodo,
      n_respuestas: almacen.respuestas[e.id] ?? 0
    }));
  }
  return peticion("/encuestas");
}

/**
 * POST /encuestas/generar
 * Recibe Necesidad: { objetivo, colectivo, contexto, duracion_max_seg, temas_prohibidos }
 * Devuelve Encuesta en borrador
 */
export async function generarEncuesta(necesidad) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const ids = Object.keys(almacen.encuestas)
      .map(k => parseInt(k.replace("enc_", ""), 10))
      .filter(n => !isNaN(n));
    const siguienteNum = (ids.length ? Math.max(...ids) : 0) + 1;
    const nuevoId = `enc_${String(siguienteNum).padStart(3, "0")}`;

    const nuevaEncuesta = {
      id: nuevoId,
      estado: "borrador",
      titulo: necesidad.objetivo || "¿Qué tal con los turnos?",
      intro: necesidad.contexto || "Tu opinión es clave para adaptar el ritmo de trabajo. Es 100% anónima.",
      colectivo: necesidad.colectivo || "planta",
      periodo: new Date().toISOString().slice(0, 7),
      tiempo_estimado_seg: Math.min(necesidad.duracion_max_seg || 60, 90),
      url: null,
      qr: null,
      preguntas: [
        {
          id: "p1",
          texto: `¿Cómo valoras el impacto de ${necesidad.objetivo.toLowerCase()}?`,
          tipo: "escala_1_5",
          opciones: [],
          dimension: "condiciones",
          condicion: null
        },
        {
          id: "p2",
          texto: "¿Cuál consideras que es el punto principal a mejorar?",
          tipo: "opcion",
          opciones: [
            "La comunicación del equipo",
            "Los descansos y pausas",
            "La distribución de tareas",
            "Ninguno en especial"
          ],
          dimension: "entorno",
          condicion: null
        },
        {
          id: "p3",
          texto: "¿Consideras suficiente la antelación con la que se avisan los cambios?",
          tipo: "si_no",
          opciones: [],
          dimension: "cultura",
          condicion: null
        },
        {
          id: "p4",
          texto: "¿Quieres dejarnos algún comentario o sugerencia adicional?",
          tipo: "texto",
          opciones: [],
          dimension: "bienestar",
          condicion: null
        }
      ]
    };

    almacen.encuestas[nuevoId] = nuevaEncuesta;
    almacen.respuestas[nuevoId] = 0;
    _guardarAlmacen(almacen);
    return JSON.parse(JSON.stringify(nuevaEncuesta));
  }
  return peticion("/encuestas/generar", {
    method: "POST",
    body: necesidad
  });
}

/**
 * GET /encuestas/{id}
 * Devuelve Encuesta completa
 */
export async function obtenerEncuesta(id) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const enc = almacen.encuestas[id];
    if (!enc) {
      throw new Error(`No existe la encuesta ${id}`);
    }
    return JSON.parse(JSON.stringify(enc));
  }
  return peticion(`/encuestas/${encodeURIComponent(id)}`);
}

/**
 * PUT /encuestas/{id}
 * Recibe Encuesta editada (solo permitida si está en borrador o aprobada -> vuelve a borrador)
 * Devuelve Encuesta actualizada
 */
export async function guardarEncuesta(encuesta) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const actual = almacen.encuestas[encuesta.id];
    if (!actual) {
      throw new Error(`No existe la encuesta ${encuesta.id}`);
    }
    if (actual.estado === "publicada") {
      throw new Error("No se puede editar: la encuesta ya está publicada");
    }

    const actualizada = {
      ...encuesta,
      id: actual.id,
      estado: "borrador", // si estaba aprobada, vuelve a borrador según modulos.md
      url: actual.url,
      qr: actual.qr
    };
    almacen.encuestas[encuesta.id] = actualizada;
    _guardarAlmacen(almacen);
    return JSON.parse(JSON.stringify(actualizada));
  }
  return peticion(`/encuestas/${encodeURIComponent(encuesta.id)}`, {
    method: "PUT",
    body: encuesta
  });
}

/**
 * POST /encuestas/{id}/aprobar
 * Cambia estado a 'aprobada' (solo desde borrador)
 */
export async function aprobarEncuesta(id) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const actual = almacen.encuestas[id];
    if (!actual) {
      throw new Error(`No existe la encuesta ${id}`);
    }
    if (actual.estado !== "borrador") {
      throw new Error(`No se puede aprobar: la encuesta está '${actual.estado}', debe estar 'borrador'`);
    }
    if (!actual.preguntas || actual.preguntas.length < 1 || actual.preguntas.length > 6) {
      throw new Error("La encuesta debe tener entre 1 y 6 preguntas válidas");
    }

    actual.estado = "aprobada";
    _guardarAlmacen(almacen);
    return JSON.parse(JSON.stringify(actual));
  }
  return peticion(`/encuestas/${encodeURIComponent(id)}/aprobar`, {
    method: "POST"
  });
}

/**
 * POST /encuestas/{id}/publicar
 * Genera url y qr, cambia estado a 'publicada' (solo si está aprobada)
 */
export async function publicarEncuesta(id) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const actual = almacen.encuestas[id];
    if (!actual) {
      throw new Error(`No existe la encuesta ${id}`);
    }
    if (actual.estado !== "aprobada") {
      throw new Error(`No se puede publicar: la encuesta está '${actual.estado}', debe estar 'aprobada'`);
    }

    const url = `${window.location.origin}/responder/${id}?canal=qr`;
    actual.estado = "publicada";
    actual.url = url;
    actual.qr = generarQrDataUrl(url);

    _guardarAlmacen(almacen);
    return JSON.parse(JSON.stringify(actual));
  }
  return peticion(`/encuestas/${encodeURIComponent(id)}/publicar`, {
    method: "POST"
  });
}

/**
 * GET /encuestas/{id}/analisis
 * Devuelve Analisis (métricas, participación, temas con tendencia, alertas, límites)
 */
export async function obtenerAnalisis(id) {
  if (USAR_EJEMPLOS) {
    return {
      encuesta_id: id,
      periodo_actual: "2026-10",
      periodo_anterior: "2026-09",
      n_respuestas: 312,
      participacion: [
        { colectivo: "planta", turno: "manana", respuestas: 38, personas: 150, tasa: 0.253, representativo: true },
        { colectivo: "planta", turno: "tarde", respuestas: 32, personas: 130, tasa: 0.246, representativo: true },
        { colectivo: "planta", turno: "noche", respuestas: 9, personas: 120, tasa: 0.075, representativo: false },
        { colectivo: "logistica", turno: "sin_turno", respuestas: 9, personas: 90, tasa: 0.10, representativo: false },
        { colectivo: "comercial", turno: "sin_turno", respuestas: 18, personas: 60, tasa: 0.30, representativo: true },
        { colectivo: "oficina", turno: "sin_turno", respuestas: 36, personas: 80, tasa: 0.45, representativo: true },
        { colectivo: "manager", turno: "sin_turno", respuestas: 15, personas: 25, tasa: 0.60, representativo: true }
      ],
      medias: [
        { pregunta: "p1", colectivo: "planta", media: 2.8, n: 79 },
        { pregunta: "p3", colectivo: "planta", media: 3.4, n: 79 },
        { pregunta: "p4", colectivo: "planta", media: 2.1, n: 24 }
      ],
      temas: [
        { tema: "descansos", n: 57, resumen: "Quejas reiteradas por falta de pausas adecuadas en el turno de noche.", tendencia: "sube" },
        { tema: "comunicacion", n: 34, resumen: "Petición de aviso con mayor antelación sobre cambios de cuadrante.", tendencia: "nuevo" },
        { tema: "turnos", n: 28, resumen: "Preferencia por rotaciones estables frente a cambios imprevistos.", tendencia: "sube" },
        { tema: "herramientas", n: 12, resumen: "Solicitud de renovación de terminales portátiles de planta.", tendencia: "estable" },
        { tema: "ambiente", n: 8, resumen: "Valoración positiva del compañerismo en las líneas de envasado.", tendencia: "baja" }
      ],
      alertas: [
        { tipo: "representatividad", mensaje: "El turno de noche de planta solo ha respondido un 7,5 %: los resultados pueden no representarle." },
        { tipo: "tema_emergente", mensaje: "El tema 'comunicacion' aparece como nuevo con 34 respuestas tras la modificación de cuadrantes." }
      ],
      limites: [
        "Muestra pequeña en turno de noche de planta (n=9).",
        "Segmentos con menos de 5 respuestas ocultos por regla de privacidad.",
        "Una correlación no demuestra una causa directa."
      ]
    };
  }
  return peticion(`/encuestas/${encodeURIComponent(id)}/analisis`);
}

/**
 * GET /encuestas/{id}/recomendaciones
 * Devuelve Recomendaciones: { acciones, seguimiento }
 */
export async function obtenerRecomendaciones(id) {
  if (USAR_EJEMPLOS) {
    return {
      acciones: [
        {
          titulo: "Revisar la duración de las pausas en el turno de noche",
          motivo: "El tema descansos agrupa 57 respuestas y su tendencia sube respecto a octubre. Se propone a RRHH valorar una redistribución o ampliación de las pausas nocturnas.",
          tema: "descansos"
        },
        {
          titulo: "Establecer un canal oficial para comunicar cambios de turno",
          motivo: "El tema comunicacion aparece como nuevo con 34 respuestas (tendencia nuevo). Se sugiere que RRHH evalúe implantar un canal formal de preaviso.",
          tema: "comunicacion"
        }
      ],
      seguimiento: {
        objetivo: "Evaluar si el personal de noche nota mejora en los descansos tras los posibles ajustes",
        colectivo: "planta",
        contexto: "En noviembre se detectó que los descansos entre turnos de noche son el principal punto de mejora. Esta encuesta de seguimiento mide si las medidas adoptadas han tenido efecto.",
        duracion_max_seg: 90,
        temas_prohibidos: ["salario"]
      }
    };
  }
  return peticion(`/encuestas/${encodeURIComponent(id)}/recomendaciones`);
}

/**
 * GET /publico/encuestas/{id}
 * Devuelve EncuestaPublica:
 * { id, titulo, intro, colectivo, tiempo_estimado_seg, preguntas, turnos, transparencia }
 */
export async function obtenerEncuestaPublica(id) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const enc = almacen.encuestas[id];
    if (!enc || enc.estado !== "publicada") {
      throw new Error(`La encuesta ${id} no existe o no está publicada`);
    }

    const turnos = enc.colectivo === "planta"
      ? ["manana", "tarde", "noche"]
      : ["sin_turno"];

    return {
      id: enc.id,
      titulo: enc.titulo,
      intro: enc.intro,
      colectivo: enc.colectivo,
      tiempo_estimado_seg: enc.tiempo_estimado_seg,
      preguntas: enc.preguntas,
      turnos: turnos,
      transparencia: "Esta microencuesta ayuda a mejorar tu día a día en Damm. Tus respuestas son 100 % anónimas: no se guarda quién eres ni desde dónde respondes. RRHH solo ve resultados agregados (mínimo 5 respuestas por grupo)."
    };
  }
  return peticion(`/publico/encuestas/${encodeURIComponent(id)}`);
}

/**
 * POST /publico/encuestas/{id}/respuestas
 * Recibe RespuestaEntrada: { turno, canal, valores, comentario }
 * Devuelve { ok: true }
 */
export async function enviarRespuesta(id, respuestaEntrada) {
  if (USAR_EJEMPLOS) {
    const almacen = _obtenerAlmacen();
    const enc = almacen.encuestas[id];
    if (!enc || enc.estado !== "publicada") {
      throw new Error(`La encuesta ${id} no está publicada para recibir respuestas`);
    }
    almacen.respuestas[id] = (almacen.respuestas[id] || 0) + 1;
    _guardarAlmacen(almacen);
    return { ok: true };
  }
  return peticion(`/publico/encuestas/${encodeURIComponent(id)}/respuestas`, {
    method: "POST",
    body: respuestaEntrada
  });
}

// ============================================================================
// Diccionarios y formateadores para etiquetas legibles (contratos/modulos.md)
// ============================================================================

export const ETIQUETAS_COLECTIVOS = {
  planta: "Planta",
  logistica: "Logística",
  comercial: "Comercial",
  oficina: "Oficina",
  manager: "Managers",
  todos: "Todos los colectivos"
};

export const ETIQUETAS_TEMAS = {
  descansos: "Descansos",
  turnos: "Turnos",
  carga_trabajo: "Carga de trabajo",
  comunicacion: "Comunicación",
  comunicacion_cambio: "Comunicación de cambios",
  liderazgo: "Liderazgo",
  herramientas: "Herramientas",
  formacion: "Formación",
  reconocimiento: "Reconocimiento",
  seguridad: "Seguridad",
  ambiente: "Ambiente laboral",
  conciliacion: "Conciliación",
  otros: "Otros"
};

export const ETIQUETAS_TURNOS = {
  manana: "Mañana",
  tarde: "Tarde",
  noche: "Noche",
  sin_turno: "Sin turno"
};

export const ETIQUETAS_ESTADOS = {
  borrador: "Borrador",
  aprobada: "Aprobada",
  publicada: "Publicada"
};

export function formatearColectivo(colectivo) {
  if (!colectivo) return "-";
  return ETIQUETAS_COLECTIVOS[colectivo] || colectivo.charAt(0).toUpperCase() + colectivo.slice(1);
}

export function formatearTema(tema) {
  if (!tema) return "-";
  return ETIQUETAS_TEMAS[tema] || tema.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase());
}

export function formatearTurno(turno) {
  if (!turno) return "-";
  return ETIQUETAS_TURNOS[turno] || turno;
}

export function formatearEstado(estado) {
  if (!estado) return "-";
  return ETIQUETAS_ESTADOS[estado] || estado;
}

// Vinculación al objeto global window para uso tanto de módulos ES6 como scripts clásicos
if (typeof window !== "undefined") {
  window.api = {
    USAR_EJEMPLOS,
    listarEncuestas,
    generarEncuesta,
    obtenerEncuesta,
    guardarEncuesta,
    aprobarEncuesta,
    publicarEncuesta,
    obtenerAnalisis,
    obtenerRecomendaciones,
    obtenerEncuestaPublica,
    enviarRespuesta,
    ETIQUETAS_COLECTIVOS,
    ETIQUETAS_TEMAS,
    ETIQUETAS_TURNOS,
    ETIQUETAS_ESTADOS,
    formatearColectivo,
    formatearTema,
    formatearTurno,
    formatearEstado
  };
}

