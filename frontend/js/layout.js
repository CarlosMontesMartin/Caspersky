/**
 * layout.js — barra lateral común (contratos v2, 4.2; diseño en contratos/diseno.md §5)
 *
 * Va en index, crear, dashboard e informe (nunca en responder). Cada página tiene
 * <aside class="barra-lateral" id="barra-lateral"></aside> y este módulo la rellena:
 *   - "Mis encuestas", con una flecha que despliega las encuestas publicadas
 *     (título corto y nº de respuestas; la abierta, resaltada).
 *   - "Nueva necesidad".
 *   - Abajo, el estado del servidor (IA conectada o respaldo, modo demo).
 */
import { obtenerSalud, listarEncuestasActivas } from '/js/api.js';
import { ICONOS, escapar, entero } from '/js/ui.js';

const pagina = window.location.pathname.replace(/^\//, '') || 'index.html';
const idAbierto = new URLSearchParams(window.location.search).get('id');
const CLAVE_CACHE = 'encuestas_activas';
const CACHE_MS = 30000;
const CLAVE_DESPLEGADO = 'menu_encuestas_abierto';

function recortar(texto, max = 32) {
  const t = String(texto || 'Sin título').trim();
  return t.length > max ? `${t.slice(0, max - 1).trimEnd()}…` : t;
}

/** Encuestas publicadas, guardadas 30 s en sessionStorage */
async function encuestasActivas(forzar = false) {
  if (!forzar) {
    try {
      const guardado = JSON.parse(sessionStorage.getItem(CLAVE_CACHE) || 'null');
      if (guardado && Date.now() - guardado.hora < CACHE_MS) return guardado.lista;
    } catch { /* caché no disponible */ }
  }
  const lista = await listarEncuestasActivas();
  try {
    sessionStorage.setItem(CLAVE_CACHE, JSON.stringify({ hora: Date.now(), lista }));
  } catch { /* sin almacenamiento: no pasa nada */ }
  return lista;
}

/** Permite a otras páginas pedir que se recargue la lista (por ejemplo, tras publicar o simular) */
export function refrescarMisEncuestas() {
  try { sessionStorage.removeItem(CLAVE_CACHE); } catch { /* nada */ }
  pintarLista(true);
}

function estaDesplegado() {
  try {
    const v = sessionStorage.getItem(CLAVE_DESPLEGADO);
    if (v !== null) return v === '1';
  } catch { /* nada */ }
  return pagina === 'dashboard.html'; // abierto por defecto en el dashboard
}

async function pintarLista(forzar = false) {
  const ul = document.getElementById('mis-encuestas');
  if (!ul) return;
  try {
    const lista = await encuestasActivas(forzar);
    if (!lista.length) {
      ul.innerHTML = '<li class="submenu-vacio">Sin encuestas publicadas</li>';
      return;
    }
    ul.innerHTML = lista.map(e => {
      const activa = e.id === idAbierto && (pagina === 'dashboard.html' || pagina === 'informe.html');
      return `
        <li>
          <a href="/dashboard.html?id=${encodeURIComponent(e.id)}" class="${activa ? 'activo' : ''}"
             ${activa ? 'aria-current="page"' : ''} title="${escapar(e.titulo || '')}">
            <span class="submenu-titulo">${escapar(recortar(e.titulo))}</span>
            <span class="submenu-n num">${entero(e.n_respuestas)}</span>
          </a>
        </li>`;
    }).join('');
  } catch {
    ul.innerHTML = '<li class="submenu-vacio">No se pudo cargar la lista</li>';
  }
}

function montar() {
  const barra = document.getElementById('barra-lateral');
  if (!barra) return;
  const desplegado = estaDesplegado();
  const enListado = pagina === 'index.html';

  barra.innerHTML = `
    <a href="/" class="marca" aria-label="Damm · Escucha activa, ir a Mis encuestas">
      <span class="marca-damm">Damm</span>
      <span class="marca-producto">Escucha activa</span>
    </a>
    <nav class="menu" aria-label="Secciones">
      <div class="menu-grupo">
        <div class="menu-fila ${enListado ? 'activo' : ''}">
          <a href="/" ${enListado ? 'aria-current="page"' : ''}>${ICONOS.lista}<span>Mis encuestas</span></a>
          <button type="button" class="menu-flecha ${desplegado ? 'abierto' : ''}" id="btn-mis-encuestas"
                  aria-expanded="${desplegado}" aria-controls="mis-encuestas" aria-label="Mostrar encuestas publicadas">
            ${ICONOS.chevron}
          </button>
        </div>
        <ul class="submenu ${desplegado ? '' : 'oculto'}" id="mis-encuestas">
          <li class="submenu-vacio">Cargando…</li>
        </ul>
      </div>
      <a href="/crear.html" class="${pagina === 'crear.html' ? 'activo' : ''}" ${pagina === 'crear.html' ? 'aria-current="page"' : ''}>
        ${ICONOS.mas}<span>Nueva necesidad</span>
      </a>
    </nav>
    <div class="estado-servidor" id="estado-servidor"></div>
  `;

  const boton = document.getElementById('btn-mis-encuestas');
  boton.addEventListener('click', () => {
    const abrir = boton.getAttribute('aria-expanded') !== 'true';
    boton.setAttribute('aria-expanded', String(abrir));
    boton.classList.toggle('abierto', abrir);
    document.getElementById('mis-encuestas').classList.toggle('oculto', !abrir);
    try { sessionStorage.setItem(CLAVE_DESPLEGADO, abrir ? '1' : '0'); } catch { /* nada */ }
  });

  pintarLista();

  // Estado del servidor: IA conectada o modo de respaldo
  obtenerSalud()
    .then(salud => {
      const el = document.getElementById('estado-servidor');
      if (!el || !salud) return;
      const ia = salud.llm ? 'IA conectada' : 'IA en modo de respaldo';
      const demo = salud.modo_demo ? ' · Modo demo' : '';
      el.innerHTML = `<span class="punto ${salud.llm ? 'punto-ok' : 'punto-aviso'}"></span><span>${ia}${demo}</span>`;
    })
    .catch(() => {
      const el = document.getElementById('estado-servidor');
      if (el) el.innerHTML = '<span class="punto punto-critico"></span><span>Sin conexión con el servidor</span>';
    });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', montar);
} else {
  montar();
}
