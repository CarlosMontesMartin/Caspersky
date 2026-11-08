/**
 * teams.js — "Publicar en Teams" y "Enviar resumen a Teams" (contratos v3, 5.4)
 *
 * Si Teams está configurado en el servidor (GET /integraciones → { teams: true }),
 * envía la tarjeta al canal. Si no, muestra una vista previa de la tarjeta adaptativa
 * dibujada en HTML con el aspecto de un mensaje de Teams.
 */
import {
  obtenerIntegraciones, vistaPreviaTeams, enviarTeamsPublicar, enviarTeamsResumen
} from '/js/api.js';
import { escapar } from '/js/ui.js';
import { t } from '/js/idioma.js';

let integraciones = null;

/** { teams: bool }, pedido una sola vez por página */
export async function integracionesDisponibles() {
  if (integraciones) return integraciones;
  try {
    integraciones = await obtenerIntegraciones();
  } catch {
    integraciones = { teams: false };
  }
  return integraciones;
}

// ---------- Dibujo de la tarjeta adaptativa (subconjunto de Adaptive Cards 1.4) ----------
function elemento(el) {
  if (!el || typeof el !== 'object') return '';
  switch (el.type) {
    case 'TextBlock': {
      const clases = ['ac-texto'];
      if (el.weight === 'Bolder') clases.push('ac-negrita');
      if (el.size === 'Large' || el.size === 'ExtraLarge') clases.push('ac-grande');
      if (el.size === 'Medium') clases.push('ac-medio');
      if (el.size === 'Small') clases.push('ac-pequeno');
      if (el.isSubtle) clases.push('ac-sutil');
      if (el.color === 'Attention') clases.push('ac-atencion');
      if (el.color === 'Good') clases.push('ac-bien');
      if (el.color === 'Warning') clases.push('ac-aviso');
      if (el.spacing === 'Medium' || el.spacing === 'Large') clases.push('ac-espacio');
      return `<div class="${clases.join(' ')}">${escapar(el.text || '')}</div>`;
    }
    case 'FactSet':
      return `<dl class="ac-datos">${(el.facts || []).map(f =>
        `<dt>${escapar(f.title)}</dt><dd>${escapar(f.value)}</dd>`).join('')}</dl>`;
    case 'Container':
      return `<div class="ac-contenedor">${(el.items || []).map(elemento).join('')}</div>`;
    case 'ColumnSet':
      return `<div class="ac-columnas">${(el.columns || []).map(c =>
        `<div class="ac-columna">${(c.items || []).map(elemento).join('')}</div>`).join('')}</div>`;
    case 'Image':
      return el.url ? `<img class="ac-imagen" src="${escapar(el.url)}" alt="${escapar(el.altText || '')}">` : '';
    default:
      return '';
  }
}

function dibujarTarjeta(tarjeta) {
  const cuerpo = (tarjeta?.body || []).map(elemento).join('');
  const acciones = (tarjeta?.actions || [])
    .filter(a => a.type === 'Action.OpenUrl')
    .map(a => `<a class="ac-boton" href="${escapar(a.url)}" target="_blank" rel="noopener">${escapar(a.title)}</a>`)
    .join('');
  return `<div class="ac-tarjeta">${cuerpo}${acciones ? `<div class="ac-acciones">${acciones}</div>` : ''}</div>`;
}

/** Ventana con la vista previa con aspecto de mensaje de Teams */
function abrirVistaPrevia(tarjeta, nota) {
  let dialogo = document.getElementById('dialogo-teams');
  if (!dialogo) {
    dialogo = document.createElement('dialog');
    dialogo.id = 'dialogo-teams';
    dialogo.className = 'dialogo dialogo-teams';
    dialogo.setAttribute('aria-labelledby', 'titulo-teams');
    document.body.appendChild(dialogo);
  }
  const hora = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  dialogo.innerHTML = `
    <h3 id="titulo-teams">${escapar(t('teams.titulo', 'Vista previa del mensaje en Teams'))}</h3>
    ${nota ? `<p class="aviso info" style="margin: var(--e3) 0;">${escapar(nota)}</p>` : ''}
    <div class="teams-canal">
      <div class="teams-cabecera"><span class="teams-canal-nombre">Damm Escucha activa – demo › Encuestas</span></div>
      <div class="teams-mensaje">
        <div class="teams-avatar" aria-hidden="true">W</div>
        <div class="teams-contenido">
          <div class="teams-autor"><strong>Workflows</strong> <span>${hora}</span></div>
          ${dibujarTarjeta(tarjeta)}
        </div>
      </div>
    </div>
    <div class="pie-acciones">
      <button type="button" class="btn btn-secundario" id="btn-cerrar-teams">${escapar(t('comun.cerrar', 'Cerrar'))}</button>
    </div>`;
  dialogo.querySelector('#btn-cerrar-teams').addEventListener('click', () => dialogo.close());
  dialogo.showModal();
}

/**
 * Acción del botón de Teams.
 * tipo: "publicar" (encuesta) o "resumen" (análisis).
 * Devuelve el texto de resultado para mostrarlo junto al botón.
 */
export async function accionTeams(encuestaId, tipo, boton) {
  const textoOriginal = boton?.textContent;
  if (boton) { boton.disabled = true; boton.textContent = t('teams.preparando', 'Preparando…'); }
  try {
    const { teams } = await integracionesDisponibles();
    if (teams) {
      if (boton) boton.textContent = t('teams.enviando', 'Enviando…');
      try {
        if (tipo === 'resumen') await enviarTeamsResumen(encuestaId);
        else await enviarTeamsPublicar(encuestaId);
        return { ok: true, mensaje: tipo === 'resumen' ? t('teams.resumen_enviado', 'Resumen enviado al canal') : t('teams.publicado', 'Publicado en el canal') };
      } catch (err) {
        // 503: el servidor dice que no está configurado → vista previa
        if (err.status !== 503) return { ok: false, mensaje: `${t('teams.error_enviar', 'No se pudo enviar a Teams')}: ${err.message}` };
      }
    }
    const tarjeta = await vistaPreviaTeams(encuestaId, tipo);
    abrirVistaPrevia(tarjeta, t('teams.no_configurado', 'Teams no está configurado en este equipo. Así se vería el mensaje en el canal.'));
    return { ok: true, mensaje: '' };
  } catch (err) {
    return { ok: false, mensaje: `${t('teams.error_preparar', 'No se pudo preparar el mensaje de Teams')}: ${err.message}` };
  } finally {
    if (boton) { boton.disabled = false; boton.textContent = textoOriginal; }
  }
}
