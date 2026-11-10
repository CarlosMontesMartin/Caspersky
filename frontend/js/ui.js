/**
 * ui.js — utilidades de presentación comunes
 * Números con coma decimal, porcentajes con espacio fino, nombres legibles
 * e iconos SVG de línea (sin emojis).
 */

import {
  numero, porcentaje as pct, entero as ent, nombrePeriodo as periodo, t, nombre
} from '/js/idioma_base.js';

const ESPACIO_FINO = '\u202F';

/** Escapa texto para insertarlo en HTML */
export function escapar(texto) {
  return String(texto ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Números y fechas en el idioma de la pantalla (Intl)
/** 2.8 → "2,8" / "2.8" */
export const decimal = (valor, decimales = 1) => numero(valor, decimales);
/** 0.228 → "22,8 %" / "22.8%" */
export const porcentaje = (tasa, decimales = 1) => pct(tasa, decimales);
/** 1234 → "1.234" / "1,234" */
export const entero = valor => ent(valor);
/** "2026-10" → "octubre de 2026" / "October 2026" */
export const nombrePeriodo = p => periodo(p);

export const TIPOS_PREGUNTA = {
  escala_1_5: t('tipo.escala_1_5', 'Escala 1–5'),
  opcion: t('tipo.opcion', 'Opción'),
  si_no: t('tipo.si_no', 'Sí / No'),
  texto: t('tipo.texto', 'Texto libre'),
};

export const DIMENSIONES = Object.fromEntries(Object.entries({
  bienestar: 'Bienestar',
  liderazgo: 'Liderazgo',
  desarrollo: 'Desarrollo',
  cultura: 'Cultura',
  entorno: 'Entorno',
  condiciones: 'Condiciones',
}).map(([c, texto]) => [c, nombre('dimension', c, texto)]));

export const TIPOS_ALERTA = {
  representatividad: t('alerta_tipo.representatividad', 'Representatividad'),
  caida: t('alerta_tipo.caida', 'Caída'),
  tema_emergente: t('alerta_tipo.tema_emergente', 'Tema emergente'),
};

/**
 * Hace legible un mensaje del servidor: "p4" → texto de la pregunta,
 * decimales con coma, valores internos con su nombre.
 */
export function textoLegible(mensaje, mapaPreguntas = {}, formatearColectivo = c => c) {
  let texto = String(mensaje || '');
  // "pregunta p4" / "pregunta c1" → «texto de la pregunta» (el backend ya escribe en el idioma pedido)
  texto = texto.replace(/\b(?:pregunta|question) ([pc]\d+|[a-z]+_\d+)\b/gi, (m, id) => (
    mapaPreguntas[id] ? m.replace(id, `«${mapaPreguntas[id]}»`) : m
  ));
  texto = texto.replace(/\b([pc]\d+)\b/g, (m, id) => (mapaPreguntas[id] ? `«${mapaPreguntas[id]}»` : m));
  // Decimales con el separador del idioma: "2.8" → "2,8" en es/ca; en inglés se quedan con punto
  if (numero(1.5, 1).includes(',')) texto = texto.replace(/(\d+)\.(\d+)/g, '$1,$2');
  texto = texto.replace(/(\d) ?%/g, numero(1, 0) && porcentaje(0.5, 0).includes('\u202F') ? `$1${ESPACIO_FINO}%` : '$1%');
  texto = texto.replace(/\b(planta|logistica|comercial|oficina|manager)\b/g, c => formatearColectivo(c).toLowerCase());
  texto = texto.replace(/\b(manana|tarde|noche|sin_turno)\b/g, c => nombre('turno', c).toLowerCase());
  texto = texto.replace(/'([a-z_]+)'/g, (m, c) => `«${c.replace(/_/g, ' ')}»`);
  return texto;
}

/** Iconos de línea de 16 px (trazos tipo Lucide) */
const svg = cuerpo => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${cuerpo}</svg>`;

export const ICONOS = {
  lista: svg('<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>'),
  mas: svg('<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'),
  actualizar: svg('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><polyline points="21 3 21 8 16 8"/>'),
  compartir: svg('<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/><line x1="15.4" y1="6.5" x2="8.6" y2="10.5"/>'),
  chevron: svg('<polyline points="9 18 15 12 9 6"/>'),
  copiar: svg('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  imprimir: svg('<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>'),
  externo: svg('<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>'),
  grafico: svg('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>'),
};

/**
 * Color de celda para la tabla de calor: 1 (rojo) → 3 (ámbar) → 5 (verde).
 * Tonos suaves para que el texto siga siendo legible.
 */
export function colorCalor(media) {
  const v = Math.max(1, Math.min(5, Number(media)));
  const t = (v - 1) / 4; // 0..1
  const tramos = [
    [0, [254, 202, 202]],   // rojo claro
    [0.5, [254, 240, 199]], // ámbar claro
    [1, [187, 247, 208]],   // verde claro
  ];
  let a = tramos[0], b = tramos[1];
  if (t > 0.5) { a = tramos[1]; b = tramos[2]; }
  const f = (t - a[0]) / (b[0] - a[0]);
  const c = a[1].map((x, i) => Math.round(x + (b[1][i] - x) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}
