/**
 * teams.js — "Publicar en Teams" y "Enviar resumen a Teams" (contratos v3, 5.4)
 *
 * Si Teams está configurado en el servidor (GET /integraciones → { teams: true }),
 * envía la tarjeta al canal. Si no, muestra una vista previa de la tarjeta adaptativa
 * dibujada en HTML con el aspecto de un mensaje de Teams.
 */
import {
  obtenerIntegraciones, vistaPreviaTeams, enviarTeamsPublicar, enviarTeamsResumen,
  obtenerEncuesta, obtenerAnalisis, obtenerRecomendaciones, colectivosDe, formatearColectivo, formatearPct
} from '/js/api.js';
import { escapar } from '/js/ui.js';
import { t } from '/js/idioma.js';
import { hora as horaLocal } from '/js/idioma_base.js';

let integraciones = null;

/** { teams: bool }, pedido una sola vez por página */
export async function integracionesDisponibles() {
  if (integraciones) return integraciones;
  // FastAPI publica sus rutas en /openapi.json: si /integraciones no está, ni se llama
  // (así no aparecen errores 404 en la consola con un servidor sin Teams)
  let rutas = null;
  try {
    const r = await fetch('/openapi.json');
    if (r.ok) rutas = Object.keys((await r.json()).paths || {});
  } catch { /* sin openapi: se prueba directamente */ }
  const tieneRuta = ruta => !rutas || rutas.some(x => x.replace(/\{[^}]+\}/g, '*') === ruta);
  const conVistaPrevia = tieneRuta('/encuestas/*/teams/vista_previa');
  if (rutas && !tieneRuta('/integraciones')) {
    integraciones = { teams: false, vista_previa: conVistaPrevia };
    return integraciones;
  }
  try {
    integraciones = { vista_previa: conVistaPrevia, ...(await obtenerIntegraciones()) };
  } catch {
    integraciones = { teams: false, vista_previa: conVistaPrevia };
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

/**
 * Tarjeta hecha en el navegador con los datos que ya da la API, para cuando el servidor
 * todavía no tiene /teams/vista_previa (así el botón nunca termina en un error).
 */
async function tarjetaLocal(encuestaId, tipo) {
  const texto = (text, extra = {}) => ({ type: 'TextBlock', text, wrap: true, ...extra });
  if (tipo === 'publicar') {
    const e = await obtenerEncuesta(encuestaId);
    const sectores = colectivosDe(e).map(formatearColectivo).join(', ');
    return {
      body: [
        texto(t('teams.t_nueva', 'Nueva encuesta: {titulo}', { titulo: e.titulo || '' }), { size: 'Large', weight: 'Bolder' }),
        e.intro ? texto(e.intro) : null,
        { type: 'FactSet', facts: [
          { title: t('teams.t_sectores', 'Sectores'), value: sectores || '—' },
          { title: t('teams.t_duracion', 'Duración'), value: t('teams.t_menos_min', 'menos de {min} min', { min: Math.max(1, Math.ceil((e.duracion_max_seg || e.necesidad?.duracion_max_seg || 120) / 60)) }) },
          { title: t('teams.t_anonima', 'Anónima'), value: t('teams.t_anonima_valor', 'Sí, resultados agregados (mínimo 5 personas)') },
        ] },
      ].filter(Boolean),
      actions: e.url ? [{ type: 'Action.OpenUrl', title: t('teams.t_responder', 'Responder'), url: e.url }] : [],
    };
  }
  const [a, r] = await Promise.all([obtenerAnalisis(encuestaId), obtenerRecomendaciones(encuestaId).catch(() => null)]);
  const noRep = (a.participacion || []).filter(f => !f.representativo).length;
  const lectura = a.lectura || r?.lectura;
  const alertas = (a.alertas || []).slice(0, 3).map(x => texto(`• ${x.mensaje || x}`));
  const acciones = (r?.acciones || []).slice(0, 2).map(x => texto(`• ${x.titulo || x}`));
  return {
    body: [
      texto(t('teams.t_resumen', 'Resumen · {titulo}', { titulo: a.titulo || '' }), { size: 'Large', weight: 'Bolder' }),
      lectura ? texto(lectura) : null,
      { type: 'FactSet', facts: [
        { title: t('teams.t_respuestas', 'Respuestas'), value: String(a.n_respuestas ?? '—') },
        { title: t('teams.t_participacion', 'Participación'), value: formatearPct(a.participacion_global) },
        { title: t('teams.t_no_rep', 'No representativos'), value: `${noRep} / ${(a.participacion || []).length}` },
      ] },
      alertas.length ? texto(t('teams.t_alertas', 'Alertas'), { weight: 'Bolder', spacing: 'Medium' }) : null,
      ...alertas,
      acciones.length ? texto(t('teams.t_acciones', 'Acciones propuestas'), { weight: 'Bolder', spacing: 'Medium' }) : null,
      ...acciones,
    ].filter(Boolean),
    actions: [{ type: 'Action.OpenUrl', title: t('teams.t_ver', 'Ver análisis'),
                url: `${window.location.origin}/dashboard.html?id=${encodeURIComponent(encuestaId)}` }],
  };
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
  const hora = horaLocal(new Date(), false);
  dialogo.innerHTML = `
    <h3 id="titulo-teams">${escapar(t('teams.titulo', 'Vista previa del mensaje en Teams'))}</h3>
    ${nota ? `<p class="aviso info" style="margin: var(--e3) 0;">${escapar(nota)}</p>` : ''}
    <div class="teams-canal">
      <div class="teams-cabecera"><span class="teams-canal-nombre">${escapar(t('teams.canal', 'Damm Escucha activa – demo › Encuestas'))}</span></div>
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
    const { teams, vista_previa: conVistaPrevia } = await integracionesDisponibles();
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
    let tarjeta;
    try {
      tarjeta = conVistaPrevia === false ? await tarjetaLocal(encuestaId, tipo) : await vistaPreviaTeams(encuestaId, tipo);
    } catch (err) {
      // El servidor aún no tiene la ruta (404/405/501): se dibuja con los datos de la API
      if (err.status && err.status < 500 && err.status !== 409) tarjeta = await tarjetaLocal(encuestaId, tipo);
      else throw err;
    }
    abrirVistaPrevia(tarjeta, t('teams.no_configurado', 'Teams no está configurado en este equipo. Así se vería el mensaje en el canal.'));
    return { ok: true, mensaje: '' };
  } catch (err) {
    return { ok: false, mensaje: `${t('teams.error_preparar', 'No se pudo preparar el mensaje de Teams')}: ${err.message}` };
  } finally {
    if (boton) { boton.disabled = false; boton.textContent = textoOriginal; }
  }
}
