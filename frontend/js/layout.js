/**
 * layout.js — Estructura común de las pantallas de RRHH (estética "Tu Rincón")
 *
 * - Sustituye la cabecera antigua por una cabecera con imagen y título en cursiva.
 * - Convierte el contenido principal en dos columnas: menú lateral + contenido.
 * No llama a la API ni toca la lógica de cada página.
 *
 * Imagen de cabecera: pon una foto propia o de licencia libre en
 * frontend/public/cabecera.jpg. Si no existe, se usa un degradado mediterráneo.
 */

const params = new URLSearchParams(window.location.search);
const idActual = params.get('id');
const pagina = window.location.pathname.replace(/^\//, '') || 'index.html';

function idParaAnalisis() {
  // En el dashboard y en crear se usa la encuesta abierta; si no, el pulso general
  return idActual || 'enc_000';
}

const OPCIONES = [
  { texto: 'Mis encuestas', href: '/', activa: p => p === 'index.html' },
  { texto: 'Nueva necesidad', href: '/crear.html', activa: p => p === 'crear.html' && !idActual },
  // Solo aparece cuando hay una encuesta abierta
  ...(idActual ? [{ texto: 'Revisar y publicar', href: `/crear.html?id=${encodeURIComponent(idActual)}`, activa: p => p === 'crear.html' }] : []),
  { texto: 'Análisis', href: `/dashboard.html?id=${encodeURIComponent(idParaAnalisis())}`, activa: p => p === 'dashboard.html' && window.location.hash !== '#seccion-recomendaciones' },
  { texto: 'Recomendaciones', href: `/dashboard.html?id=${encodeURIComponent(idParaAnalisis())}#seccion-recomendaciones`, activa: p => p === 'dashboard.html' && window.location.hash === '#seccion-recomendaciones' },
];

function crearCabecera() {
  const cabecera = document.createElement('header');
  cabecera.className = 'hero';
  // Cada pantalla tiene su propia foto de cabecera (ver css/estilos.css)
  const fotoPorPagina = { 'index.html': 'inicio', 'crear.html': 'crear', 'dashboard.html': 'analisis' };
  cabecera.dataset.pagina = fotoPorPagina[pagina] || 'inicio';
  cabecera.innerHTML = `
    <div class="hero-barra">
      <a href="/" class="hero-marca">Damm</a>
      <span class="hero-contexto">Estás en <strong>Escucha activa</strong> · RRHH</span>
    </div>
    <a href="/" class="hero-titulo">Escucha activa</a>
  `;
  return cabecera;
}

function crearMenu() {
  const menu = document.createElement('nav');
  menu.className = 'menu-lateral';
  menu.setAttribute('aria-label', 'Secciones');
  menu.innerHTML = OPCIONES.map(o => {
    const activa = o.activa(pagina);
    return `<a href="${o.href}" class="menu-lateral-item${activa ? ' activo' : ''}"${activa ? ' aria-current="page"' : ''}>${activa ? '_' : ''}${o.texto}</a>`;
  }).join('');

  // Al cambiar el hash dentro del dashboard, actualizar el elemento activo
  window.addEventListener('hashchange', () => {
    menu.querySelectorAll('.menu-lateral-item').forEach((a, i) => {
      const activa = OPCIONES[i].activa(pagina);
      a.classList.toggle('activo', activa);
      a.textContent = (activa ? '_' : '') + OPCIONES[i].texto;
    });
  });
  return menu;
}

function montar() {
  const antigua = document.querySelector('.site-header');
  const main = document.querySelector('main.main-content');
  if (!main) return;

  document.body.insertBefore(crearCabecera(), document.body.firstChild);
  if (antigua) antigua.remove();

  const contenedor = main.querySelector(':scope > .container');
  if (!contenedor) return;

  const columna = document.createElement('div');
  columna.className = 'layout-contenido';
  while (contenedor.firstChild) columna.appendChild(contenedor.firstChild);

  contenedor.removeAttribute('style');
  contenedor.classList.add('layout');
  contenedor.appendChild(crearMenu());
  contenedor.appendChild(columna);

  // Si se llega con #seccion-recomendaciones, bajar hasta ella cuando cargue
  if (window.location.hash) {
    setTimeout(() => {
      const destino = document.querySelector(window.location.hash);
      if (destino) destino.scrollIntoView({ behavior: 'smooth' });
    }, 600);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', montar);
} else {
  montar();
}
