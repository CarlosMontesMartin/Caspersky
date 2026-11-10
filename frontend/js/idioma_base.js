/**
 * idioma_base.js — idioma actual y diccionarios
 *
 * Módulo sin efectos en la página: lo importan api.js (para añadir ?idioma= a las
 * llamadas y traducir códigos) e idioma.js (que pinta el selector y traduce el HTML).
 *
 * - Idiomas: solo es, ca y en.
 * - El idioma se decide al cargar la página (?lang= de la URL, sessionStorage["idioma"],
 *   idioma del navegador). Al cambiarlo se recarga la página, así todo se pide de nuevo.
 * - Diccionario = /i18n/<idioma>.json (nombres comunes con el backend: colectivo.*, turno.*,
 *   tema.*, dimension.*) + /i18n/rrhh_<idioma>.json (pantallas de RRHH).
 *   El castellano es el texto por defecto del código y del HTML.
 */

export const IDIOMAS = [
  { codigo: 'es', nombre: 'Español', corto: 'ES' },
  { codigo: 'ca', nombre: 'Català', corto: 'CA' },
  { codigo: 'en', nombre: 'English', corto: 'EN' },
];
const CODIGOS = IDIOMAS.map(i => i.codigo);
const CLAVE = 'idioma';
const LOCALES = { es: 'es-ES', ca: 'ca-ES', en: 'en-GB' };

/** ?lang= de la URL, después sessionStorage, después el idioma del navegador; por defecto, es */
export function idiomaInicial() {
  if (typeof window === 'undefined') return 'es';
  const url = new URLSearchParams(window.location.search).get('lang');
  if (CODIGOS.includes(url)) return url;
  try {
    const guardado = sessionStorage.getItem(CLAVE);
    if (CODIGOS.includes(guardado)) return guardado;
  } catch { /* nada */ }
  const nav = (navigator.language || 'es').slice(0, 2).toLowerCase();
  return CODIGOS.includes(nav) ? nav : 'es';
}

export const idioma = idiomaInicial();
export const locale = LOCALES[idioma];
export function idiomaActual() { return idioma; }

async function leer(ruta) {
  try {
    const r = await fetch(ruta);
    if (!r.ok) return {};
    const tipo = r.headers.get('content-type') || '';
    return tipo.includes('json') ? await r.json() : {};
  } catch { return {}; }
}

// Se carga antes de que nadie pinte nada (await de nivel superior)
let diccionario = {};
if (typeof window !== 'undefined') {
  const [comun, rrhh] = await Promise.all([
    leer(`/i18n/${idioma}.json`),
    idioma === 'es' ? Promise.resolve({}) : leer(`/i18n/rrhh_${idioma}.json`),
  ]);
  // Los nombres comunes mandan sobre los de RRHH
  diccionario = { ...rrhh, ...comun };
}

/**
 * Texto traducido. Si falta la clave, el texto por defecto (castellano).
 * Variables: t('x', 'Hola {nombre}', { nombre: 'Ana' })
 */
export function t(clave, porDefecto = clave, variables = {}) {
  const texto = diccionario[clave] ?? porDefecto;
  return String(texto).replace(/\{(\w+)\}/g, (m, v) => (v in variables ? variables[v] : m));
}

/** ¿Existe la clave en el diccionario del idioma actual? */
export function hayClave(clave) { return clave in diccionario; }

const mayuscula = s => (s ? s.charAt(0).toLocaleUpperCase(locale) + s.slice(1) : s);

/**
 * Nombre de un código para usarlo como etiqueta (con mayúscula inicial).
 * nombre('colectivo', 'planta', 'Planta') → "Planta" / "Planta" / "Plant"
 * Los diccionarios guardan los nombres en minúscula para poder ir dentro de una frase.
 */
export function nombre(tipo, codigo, porDefecto) {
  if (!codigo) return '—';
  return mayuscula(t(`${tipo}.${codigo}`, porDefecto ?? String(codigo).replace(/_/g, ' ')));
}

/** Nombre en minúscula, para dentro de una frase */
export function nombreEnFrase(tipo, codigo, porDefecto) {
  const texto = t(`${tipo}.${codigo}`, porDefecto ?? String(codigo).replace(/_/g, ' '));
  return texto.toLocaleLowerCase(locale);
}

// ---------- Números y fechas con Intl ----------
const esVacio = v => v === null || v === undefined || v === '' || Number.isNaN(Number(v));

/** 2.8 → "2,8" (es, ca) / "2.8" (en) */
export function numero(valor, decimales = 1) {
  if (esVacio(valor)) return '—';
  return new Intl.NumberFormat(locale, { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(Number(valor));
}

/** 1234 → "1.234" / "1,234" */
export function entero(valor) {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(valor || 0));
}

/** 0.228 → "22,8 %" / "22.8%" */
export function porcentaje(tasa, decimales = 1) {
  if (esVacio(tasa)) return '—';
  const texto = new Intl.NumberFormat(locale, { style: 'percent', minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(Number(tasa));
  return texto.replace(/\s%/, ' %'); // espacio fino en es y ca
}

/** "2026-10" → "octubre de 2026" / "October 2026" */
export function nombrePeriodo(periodo) {
  if (!periodo || !/^\d{4}-\d{2}$/.test(periodo)) return periodo || '—';
  const [a, m] = periodo.split('-').map(Number);
  return new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(new Date(a, m - 1, 1));
}

/** Hora local: "14:05:09" */
export function hora(fecha = new Date(), conSegundos = true) {
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', ...(conSegundos ? { second: '2-digit' } : {}) }).format(fecha);
}

/** Lista legible: ["Planta", "Oficina"] → "Planta y Oficina" / "Planta i Oficina" / "Planta and Oficina" */
export function lista(elementos) {
  try { return new Intl.ListFormat(locale, { style: 'long', type: 'conjunction' }).format(elementos); }
  catch { return elementos.join(', '); }
}
