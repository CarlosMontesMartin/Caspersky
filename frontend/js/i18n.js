/**
 * i18n.js — textos fijos en castellano, catalán e inglés (contratos v3 6.1 y v4) · UAB 2
 *
 *   await cargarIdioma('ca');          // carga /i18n/ca.json (y es.json como respaldo)
 *   t('responder.enviar');             // "Envia"
 *   t('responder.n_preguntas', { n: 4, min: 2 });
 *   idiomaInicial();                   // ?lang= → sessionStorage → navegador → "es"
 *
 * Si falta una clave en el idioma elegido se usa el castellano y, si tampoco está, la propia clave.
 * Solo traduce textos fijos de la interfaz: las preguntas las traduce la IA en el servidor.
 * Los nombres (colectivo.*, turno.*, tema.*, dimension.*) van en minúscula para poder ir dentro
 * de una frase: el backend también los lee de aquí. Para un botón o un título, usad mayuscula().
 */

/** "planta" → "Planta" */
export function mayuscula(texto) {
  const s = String(texto ?? '');
  return s.charAt(0).toLocaleUpperCase() + s.slice(1);
}

export const IDIOMAS = ['es', 'ca', 'en'];   // v4: solo estos tres (los mismos que backend/reglas.py)
/** Etiqueta del selector de cada idioma */
export const ETIQUETAS_IDIOMA = { es: 'ES', ca: 'CA', en: 'EN' };
const POR_DEFECTO = 'es';
const CLAVE_SESION = 'idioma';

const diccionarios = {};   // { es: {...}, ca: {...} }
let actual = POR_DEFECTO;

async function descargar(codigo) {
  if (diccionarios[codigo]) return diccionarios[codigo];
  try {
    const r = await fetch(`/i18n/${codigo}.json`, { headers: { Accept: 'application/json' } });
    diccionarios[codigo] = r.ok ? await r.json() : {};
  } catch {
    diccionarios[codigo] = {};
  }
  return diccionarios[codigo];
}

/** Carga el idioma (y el castellano como respaldo) y lo deja como actual. */
export async function cargarIdioma(codigo) {
  const idioma = IDIOMAS.includes(codigo) ? codigo : POR_DEFECTO;
  await Promise.all([descargar(POR_DEFECTO), descargar(idioma)]);
  actual = idioma;
  try { sessionStorage.setItem(CLAVE_SESION, idioma); } catch { /* sin almacenamiento: no pasa nada */ }
  if (typeof document !== 'undefined') document.documentElement.lang = idioma;
  return idioma;
}

export function idiomaActual() {
  return actual;
}

/** ?lang= de la URL, después sessionStorage, después el idioma del navegador; por defecto "es". */
export function idiomaInicial() {
  const deUrl = new URLSearchParams(window.location.search).get('lang');
  if (IDIOMAS.includes(deUrl)) return deUrl;
  try {
    const guardado = sessionStorage.getItem(CLAVE_SESION);
    if (IDIOMAS.includes(guardado)) return guardado;
  } catch { /* nada */ }
  const navegador = (navigator.languages && navigator.languages[0]) || navigator.language || '';
  const base = navegador.toLowerCase().slice(0, 2);
  return IDIOMAS.includes(base) ? base : POR_DEFECTO;
}

/** Texto de una clave con variables {n}. Respaldo: castellano y, si no, la clave. */
export function t(clave, variables = {}) {
  const texto = diccionarios[actual]?.[clave] ?? diccionarios[POR_DEFECTO]?.[clave] ?? clave;
  return String(texto).replace(/\{(\w+)\}/g, (m, nombre) => (nombre in variables ? String(variables[nombre]) : m));
}
