/**
 * idioma.js — selector de idioma y traducción del HTML de las pantallas de RRHH
 * (contratos v3 §5.5 y v4 §4)
 *
 * - Selector arriba a la derecha: ES · CA · EN.
 * - Traduce los elementos con data-i18n (texto), data-i18n-placeholder, data-i18n-title
 *   y data-i18n-aria-label; el código usa t() para el resto.
 * - Al cambiar de idioma se recarga la página: así api.js vuelve a pedir todo con
 *   ?idioma= y el backend devuelve sus frases (alertas, lectura, acciones…) en ese idioma.
 *
 * El idioma y los diccionarios están en idioma_base.js (sin efectos en la página).
 */
import { IDIOMAS, idioma, t as traducir, idiomaInicial } from '/js/idioma_base.js';

export { idiomaInicial };
export const t = traducir;
export function idiomaActual() { return idioma; }

const CLAVE = 'idioma';
const antes = [];

/** Compatibilidad: con la recarga ya no hace falta repintar, pero se mantiene la función */
export function alCambiarIdioma() { /* la página se recarga al cambiar de idioma */ }

/**
 * Función que se ejecuta antes de recargar por un cambio de idioma
 * (por ejemplo, guardar el borrador en crear.html). Puede ser async.
 */
export function antesDeCambiarIdioma(fn) { antes.push(fn); }

function aplicar(raiz = document) {
  const pares = [
    ['data-i18n', (el, v) => { el.textContent = v; }, el => el.textContent],
    ['data-i18n-placeholder', (el, v) => el.setAttribute('placeholder', v), el => el.getAttribute('placeholder')],
    ['data-i18n-title', (el, v) => el.setAttribute('title', v), el => el.getAttribute('title')],
    ['data-i18n-aria-label', (el, v) => el.setAttribute('aria-label', v), el => el.getAttribute('aria-label')],
  ];
  pares.forEach(([atributo, escribir, leer]) => {
    raiz.querySelectorAll(`[${atributo}]`).forEach(el => {
      escribir(el, traducir(el.getAttribute(atributo), (leer(el) || '').trim()));
    });
  });
}

/** Vuelve a traducir una zona que el código acaba de pintar con data-i18n */
export function traducirZona(raiz) { aplicar(raiz); }

export async function cambiarIdioma(codigo) {
  if (!IDIOMAS.some(i => i.codigo === codigo) || codigo === idioma) return;
  for (const fn of antes) {
    try { await fn(codigo); } catch (e) { console.warn(e); }
  }
  try { sessionStorage.setItem(CLAVE, codigo); } catch { /* nada */ }
  // ?lang= de la URL manda sobre sessionStorage: se cambia para que la recarga use el nuevo
  const url = new URL(window.location.href);
  if (url.searchParams.has('lang')) url.searchParams.set('lang', codigo);
  window.location.replace(url.toString());
}

// ---------- Selector arriba a la derecha ----------
function pintarSelector() {
  let caja = document.getElementById('selector-idioma');
  if (!caja) {
    caja = document.createElement('div');
    caja.id = 'selector-idioma';
    caja.className = 'selector-idioma';
    document.body.appendChild(caja);
    document.addEventListener('click', e => { if (!caja.contains(e.target)) cerrarMenu(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrarMenu(); });
  }
  const info = IDIOMAS.find(i => i.codigo === idioma) || IDIOMAS[0];
  caja.innerHTML = `
    <button type="button" class="selector-idioma-boton" aria-haspopup="true" aria-expanded="false"
            aria-label="${traducir('idioma.cambiar', 'Cambiar idioma')}: ${info.nombre}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      <span>${info.corto}</span>
      <svg class="selector-idioma-flecha" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
    </button>
    <ul class="selector-idioma-menu oculto" role="menu">
      ${IDIOMAS.map(i => `
        <li role="none"><button type="button" role="menuitemradio" aria-checked="${i.codigo === idioma}" data-idioma="${i.codigo}" lang="${i.codigo}">
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

function iniciar() {
  try { sessionStorage.setItem(CLAVE, idioma); } catch { /* nada */ }
  document.documentElement.lang = idioma;
  aplicar();
  pintarSelector();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
else iniciar();
