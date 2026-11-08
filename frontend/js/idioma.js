/**
 * idioma.js — idioma de las pantallas de RRHH (contratos v3, 5.5)
 *
 * - Selector de idioma arriba a la derecha (menú desplegable): español, català,
 *   English, português y 中文.
 * - Traduce los textos fijos: elementos con data-i18n (texto), data-i18n-placeholder,
 *   data-i18n-title y data-i18n-aria-label, y los que pide el código con t().
 * - Los datos y los textos que genera la IA siguen en castellano.
 *
 * Diccionarios: /i18n/rrhh_<código>.json (el castellano es el texto por defecto del HTML).
 * El idioma se guarda en sessionStorage["idioma"], la misma clave que usa responder.html.
 */
import { IDIOMAS } from '/js/api.js';

const CLAVE = 'idioma';
const CODIGOS = IDIOMAS.map(i => i.codigo);
let actual = 'es';
let diccionario = {};
const avisos = [];
const originales = new WeakMap(); // texto en castellano de cada elemento, para volver a él

/** ?lang= de la URL, después sessionStorage, después el idioma del navegador; por defecto, es */
export function idiomaInicial() {
  const url = new URLSearchParams(window.location.search).get('lang');
  if (CODIGOS.includes(url)) return url;
  try {
    const guardado = sessionStorage.getItem(CLAVE);
    if (CODIGOS.includes(guardado)) return guardado;
  } catch { /* nada */ }
  const nav = (navigator.language || 'es').slice(0, 2).toLowerCase();
  return CODIGOS.includes(nav) ? nav : 'es';
}

export function idiomaActual() { return actual; }

/**
 * Texto traducido. Si falta la clave, el texto por defecto (castellano).
 * Variables: t('x', 'Hola {nombre}', { nombre: 'Ana' })
 */
export function t(clave, porDefecto = clave, variables = {}) {
  const texto = diccionario[clave] ?? porDefecto;
  return String(texto).replace(/\{(\w+)\}/g, (m, v) => (v in variables ? variables[v] : m));
}

/** Registra una función que se llama cada vez que cambia el idioma */
export function alCambiarIdioma(fn) { avisos.push(fn); }

function aplicar(raiz = document) {
  const pares = [
    ['data-i18n', el => el.textContent, (el, v) => { el.textContent = v; }],
    ['data-i18n-placeholder', el => el.getAttribute('placeholder'), (el, v) => el.setAttribute('placeholder', v)],
    ['data-i18n-title', el => el.getAttribute('title'), (el, v) => el.setAttribute('title', v)],
    ['data-i18n-aria-label', el => el.getAttribute('aria-label'), (el, v) => el.setAttribute('aria-label', v)],
  ];
  pares.forEach(([atributo, leer, escribir]) => {
    raiz.querySelectorAll(`[${atributo}]`).forEach(el => {
      let guardados = originales.get(el);
      if (!guardados) { guardados = {}; originales.set(el, guardados); }
      if (!(atributo in guardados)) guardados[atributo] = (leer(el) || '').trim();
      escribir(el, t(el.getAttribute(atributo), guardados[atributo]));
    });
  });
}

export async function cambiarIdioma(codigo) {
  if (!CODIGOS.includes(codigo)) codigo = 'es';
  let nuevo = {};
  if (codigo !== 'es') {
    try {
      const r = await fetch(`/i18n/rrhh_${codigo}.json`);
      if (r.ok) nuevo = await r.json();
    } catch { /* sin diccionario: castellano */ }
  }
  actual = codigo;
  diccionario = nuevo;
  try { sessionStorage.setItem(CLAVE, codigo); } catch { /* nada */ }
  document.documentElement.lang = codigo === 'zh' ? 'zh-Hans' : codigo;
  aplicar();
  pintarSelector();
  avisos.forEach(fn => { try { fn(codigo); } catch (e) { console.error(e); } });
}

// ---------- Selector arriba a la derecha ----------
function pintarSelector() {
  let caja = document.getElementById('selector-idioma');
  if (!caja) {
    caja = document.createElement('div');
    caja.id = 'selector-idioma';
    caja.className = 'selector-idioma';
    document.body.appendChild(caja);
    // Cerrar al pulsar fuera o con Escape
    document.addEventListener('click', e => { if (!caja.contains(e.target)) cerrarMenu(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrarMenu(); });
  }
  const info = IDIOMAS.find(i => i.codigo === actual) || IDIOMAS[0];
  caja.innerHTML = `
    <button type="button" class="selector-idioma-boton" aria-haspopup="true" aria-expanded="false"
            aria-label="${t('idioma.cambiar', 'Cambiar idioma')}: ${info.nombre}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      <span>${info.corto}</span>
      <svg class="selector-idioma-flecha" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
    </button>
    <ul class="selector-idioma-menu oculto" role="menu">
      ${IDIOMAS.map(i => `
        <li role="none"><button type="button" role="menuitemradio" aria-checked="${i.codigo === actual}" data-idioma="${i.codigo}" lang="${i.codigo}">
          <span class="selector-idioma-corto">${i.corto}</span><span>${i.nombre}</span>
        </button></li>`).join('')}
    </ul>`;
  const boton = caja.querySelector('.selector-idioma-boton');
  const menu = caja.querySelector('.selector-idioma-menu');
  boton.addEventListener('click', () => {
    const abrir = menu.classList.contains('oculto');
    menu.classList.toggle('oculto', !abrir);
    boton.setAttribute('aria-expanded', String(abrir));
  });
  menu.querySelectorAll('[data-idioma]').forEach(b => b.addEventListener('click', () => {
    cerrarMenu();
    cambiarIdioma(b.dataset.idioma);
  }));
}

function cerrarMenu() {
  const caja = document.getElementById('selector-idioma');
  if (!caja) return;
  caja.querySelector('.selector-idioma-menu')?.classList.add('oculto');
  caja.querySelector('.selector-idioma-boton')?.setAttribute('aria-expanded', 'false');
}

/** Vuelve a traducir una zona que el código acaba de pintar con data-i18n */
export function traducirZona(raiz) { aplicar(raiz); }

// Arranque: el idioma inicial se aplica en cuanto carga la página
const inicio = () => cambiarIdioma(idiomaInicial());
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', inicio);
else inicio();
