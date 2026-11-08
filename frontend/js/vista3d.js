/**
 * vista3d.js — Maqueta 3D de Damm como centro de mando · UPC 2 (v2.md sección 3.7)
 * Módulo ES · Three.js 0.160.0 (vendor local, sin CDN)
 *
 * Exporta: iniciarVista3D(contenedor, analisis, opciones?)
 *   → { actualizar(analisisNuevo), setCapa(capa), setModo(noche), dispose() }
 *
 * La carga es la misma que la versión anterior: imports 'three' / 'three/addons/…',
 * modelo en /public/fabrica.fbx, maqueta normalizada a ~6 unidades y zonas por fx/fz.
 *
 * opciones (todas opcionales):
 *   capa: "participacion" | "valoracion" | "alertas"   noche: bool
 *   onVerEnAnalisis(colectivo)   urlCrear: "crear.html"   modeloUrl: "/public/fabrica.fbx"
 * Además emite en document "vista3d:ver-en-analisis" (detail = { colectivo }) y, si el modelo
 * no carga, "vista3d-error" en el contenedor (como antes).
 */

import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
// Textos en el idioma de la pantalla (contratos v4 §4, UAB 1)
import { t, nombre as nombreCodigo, porcentaje, numero } from '/js/idioma_base.js';

// =========================================================================
// CONSTANTES
// =========================================================================

/**
 * Zonas de la maqueta (las mismas que en la versión anterior). fx y fz van de -0.5 a 0.5
 * sobre la planta del modelo (fx: izquierda → derecha, fz: fondo → frente). La altura se
 * calcula sola: la etiqueta se apoya en el tejado que haya debajo de ese punto.
 */
export const ZONAS = {
  planta:    { label: nombreCodigo('colectivo', 'planta', 'Planta'),    fx:  0.25, fz: -0.20 },
  logistica: { label: nombreCodigo('colectivo', 'logistica', 'Logística'), fx: -0.30, fz: -0.30 },
  comercial: { label: nombreCodigo('colectivo', 'comercial', 'Comercial'), fx: -0.30, fz:  0.30 },
  oficina:   { label: nombreCodigo('colectivo', 'oficina', 'Oficina'),   fx:  0.05, fz:  0.30 },
  manager:   { label: nombreCodigo('colectivo', 'manager', 'Managers'),  fx:  0.30, fz:  0.25 },
};

/** Mallas del FBX que no forman parte de las instalaciones (decoración) */
const MALLAS_OCULTAS = /^(cloud|car)/i;

const COLOR_CLAY       = 0xF5F1EA;
const COLOR_BG_DAY     = 0xFFFFFF;
const COLOR_BG_NIGHT   = 0x141B2D;
const COLOR_DAMM       = 0xB91C1C;
const COLOR_NIGHT_BLUE = 0x2B3A67;

export const COLORES = {
  rojo: '#d64545', ambar: '#e0a43a', verde: '#3f9e5a', gris: '#9aa0a6', atenuado: '#c9ccd1',
};

const NOMBRE_TEMA = Object.fromEntries(Object.entries({
  descansos: 'Descansos', turnos: 'Turnos', carga_trabajo: 'Carga de trabajo', comunicacion: 'Comunicación',
  liderazgo: 'Liderazgo', herramientas: 'Herramientas', formacion: 'Formación', reconocimiento: 'Reconocimiento',
  seguridad: 'Seguridad', ambiente: 'Ambiente', conciliacion: 'Conciliación', otros: 'Otros',
}).map(([c, texto]) => [c, nombreCodigo('tema', c, texto)]));
const DURACION_PULSO = 1200;

// =========================================================================
// UTILIDADES PURAS (exportadas para poder probarlas)
// =========================================================================

export function formatearPct(tasa) {
  return porcentaje(tasa || 0, 0);
}

export function formatearMedia(media) {
  return media == null ? '—' : numero(media, 1);
}

function flecha(variacion) {
  if (variacion == null) return '';
  if (variacion <= -0.1) return ' ↓';
  if (variacion >= 0.1) return ' ↑';
  return '';
}

/** Color, etiqueta y estado de una zona para una capa. `zona` es un elemento de analisis.zonas (o undefined). */
export function valorCapa(zona, capa, noche = false, nombre = '') {
  nombre = nombre || (zona && ZONAS[zona.colectivo]?.label) || '';
  if (!zona) return { color: COLORES.atenuado, etiqueta: nombre, atenuada: true, fuera: true };

  let fila = zona;
  let alertas = zona.alertas || [];
  if (noche) {
    fila = (zona.turnos || []).find((t) => t.turno === 'noche');
    if (!fila) return { color: COLORES.atenuado, etiqueta: `${nombre} · ${t('maqueta.sin_noche', 'Sin turno de noche')}`, atenuada: true };
    alertas = alertas.filter((a) => /noche|\bnit\b|night/i.test(a));
  }

  if (capa === 'valoracion') {
    if (fila.media == null) return { color: COLORES.gris, etiqueta: `${nombre} · ${t('maqueta.oculto', 'Oculto (n < 5)')}`, atenuada: false };
    const color = fila.media < 2.5 ? COLORES.rojo : fila.media < 3.5 ? COLORES.ambar : COLORES.verde;
    return { color, etiqueta: `${nombre} · ${formatearMedia(fila.media)}${noche ? '' : flecha(zona.variacion)}`,
             atenuada: false };
  }
  if (capa === 'alertas') {
    const n = alertas.length;
    const color = n === 0 ? COLORES.verde : n === 1 ? COLORES.ambar : COLORES.rojo;
    return { color, etiqueta: `${nombre} · ${n === 1 ? t('maqueta.una_alerta', '1 alerta') : t('maqueta.n_alertas', '{n} alertas', { n })}`, atenuada: false };
  }
  const tasa = fila.tasa || 0; // participacion
  const color = tasa < 0.1 ? COLORES.rojo : tasa < 0.2 ? COLORES.ambar : COLORES.verde;
  return { color, etiqueta: `${nombre} · ${formatearPct(tasa)}`, atenuada: false };
}

/** Necesidad para "Crear encuesta para este sector". */
export function necesidadParaZona(zona, nombre) {
  const tema = zona.temas?.[0]?.tema;
  const temaTexto = tema ? (NOMBRE_TEMA[tema] || tema).toLowerCase() : t('maqueta.clima', 'el clima laboral');
  return {
    objetivo: t('maqueta.objetivo', 'Profundizar en {tema} en {sector}', { tema: temaTexto, sector: nombre.toLowerCase() }),
    colectivos: [zona.colectivo],
    contexto: zona.alertas?.[0] || (tema ? t('maqueta.tema_principal', 'Tema principal: {tema}', { tema: temaTexto }) : t('maqueta.seguimiento', 'Seguimiento del último pulso')),
    duracion_max_seg: 60,
    temas_prohibidos: ['salario'],
  };
}

function el(tag, props = {}, hijos = []) {
  const nodo = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'style') Object.assign(nodo.style, v);
    else if (k.startsWith('on')) nodo.addEventListener(k.slice(2), v);
    else if (k === 'texto') nodo.textContent = v;
    else if (k === 'className') nodo.className = v;
    else nodo.setAttribute(k, v);
  }
  for (const h of [].concat(hijos)) if (h != null) nodo.append(h);
  return nodo;
}

// =========================================================================
// FUNCIÓN PRINCIPAL
// =========================================================================

export function iniciarVista3D(contenedor, analisis, opciones = {}) {
  opciones = opciones && typeof opciones === 'object' ? opciones : {};
  const urlCrear = opciones.urlCrear || 'crear.html';

  let datos = analisis || { zonas: [] };
  let capa = ['participacion', 'valoracion', 'alertas'].includes(opciones.capa) ? opciones.capa : 'participacion';
  let modoNoche = !!opciones.noche;
  let seleccionada = null;
  let animFrameId = null;
  let disposed = false;
  let temporizadorAviso = null;
  const pulsos = [];

  // Estado de cada zona (copia propia: no se toca el ZONAS del módulo)
  const zonas = {};
  for (const [key, def] of Object.entries(ZONAS)) {
    zonas[key] = { key, label: def.label, fx: def.fx, fz: def.fz, pos: new THREE.Vector3(),
                   grupo: null, material: null, mallas: [], overlay: null, estado: null };
  }
  let tamMaqueta = 6;

  // --- Renderer (igual que antes) ---
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(COLOR_BG_DAY);
  const canvas = renderer.domElement;
  canvas.classList.add('visor-3d-canvas');
  contenedor.appendChild(canvas);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  camera.position.set(8, 6, 8);
  const scene = new THREE.Scene();

  function resizeRenderer() {
    const w = contenedor.clientWidth || 1;
    const h = contenedor.clientHeight || 1;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  // --- Luces ---
  const hemiLight = new THREE.HemisphereLight(0xFFF5E6, 0xD5C8B3, 1.0);
  scene.add(hemiLight);
  const sunLight = new THREE.DirectionalLight(0xFFF5E6, 1.2);
  sunLight.position.set(5, 10, 7);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(1024, 1024);
  Object.assign(sunLight.shadow.camera, { near: 0.5, far: 50, left: -10, right: 10, top: 10, bottom: -10 });
  scene.add(sunLight);
  const nightAmbient = new THREE.AmbientLight(COLOR_NIGHT_BLUE, 0.7);
  nightAmbient.visible = false;
  scene.add(nightAmbient);
  const nightFill = new THREE.DirectionalLight(0x8FA3D9, 0.6);
  nightFill.position.set(-3, 8, -5);
  nightFill.visible = false;
  scene.add(nightFill);
  const redBlink = new THREE.PointLight(COLOR_DAMM, 0, 12);
  redBlink.visible = false;
  scene.add(redBlink);

  // --- Suelo (solo sombras) ---
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.ShadowMaterial({ opacity: 0.14 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.01;
  ground.receiveShadow = true;
  scene.add(ground);

  // --- Controles ---
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.47;
  controls.minDistance = 3;
  controls.maxDistance = 25;
  controls.target.set(0, 1, 0);
  controls.update();
  resizeRenderer();

  // --- Aviso en directo y panel ---
  const aviso = el('div', { style: { position: 'absolute', top: '12px', left: '50%', transform: 'translateX(-50%)',
    background: 'rgba(20,24,31,.85)', color: '#fff', padding: '6px 12px', borderRadius: '16px', zIndex: '5',
    opacity: '0', transition: 'opacity .3s', pointerEvents: 'none', font: '13px system-ui, sans-serif' } });
  contenedor.appendChild(aviso);
  let panel = document.getElementById('panel-3d-detalle');
  let panelPropio = false;
  if (!panel) {
    panel = el('div', { id: 'panel-3d-detalle', style: { position: 'absolute', top: '12px', right: '12px',
      width: '280px', background: '#fff', borderRadius: '10px', padding: '14px', zIndex: '5',
      boxShadow: '0 4px 16px rgba(0,0,0,.15)', display: 'none' } });
    contenedor.appendChild(panel);
    panelPropio = true;
  }

  // --- Carga del modelo FBX (igual que antes) ---
  const loaderOverlay = document.createElement('div');
  loaderOverlay.className = 'visor-3d-loader';
  loaderOverlay.textContent = t('maqueta.cargando', 'Cargando maqueta…');
  contenedor.appendChild(loaderOverlay);

  new FBXLoader().load(
    opciones.modeloUrl || '/public/fabrica.fbx',
    (fbx) => {
      if (disposed) return;
      const matClay = new THREE.MeshStandardMaterial({
        color: COLOR_CLAY, roughness: 0.9, metalness: 0, vertexColors: false,
      });
      fbx.traverse((child) => {
        if (!child.isMesh) return;
        if (MALLAS_OCULTAS.test(child.name)) { child.visible = false; return; }
        child.material = matClay;
        child.castShadow = true;
        child.receiveShadow = true;
      });

      // Escala y centrado (sin nubes ni coches)
      fbx.updateMatrixWorld(true);
      const box = new THREE.Box3();
      fbx.traverse((child) => { if (child.isMesh && child.visible) box.expandByObject(child); });
      const size = box.getSize(new THREE.Vector3());
      const scale = 6 / Math.max(size.x, size.z);
      fbx.scale.setScalar(scale);
      const center = box.getCenter(new THREE.Vector3());
      fbx.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
      scene.add(fbx);
      fbx.updateMatrixWorld(true);

      const finalBox = new THREE.Box3();
      const visibles = [];
      fbx.traverse((child) => {
        if (child.isMesh && child.visible) { finalBox.expandByObject(child); visibles.push(child); }
      });
      const fCenter = finalBox.getCenter(new THREE.Vector3());
      const fSize = finalBox.getSize(new THREE.Vector3());
      tamMaqueta = Math.max(fSize.x, fSize.z);

      // Posición de cada zona sobre el tejado (raycast vertical, como antes)
      const ray = new THREE.Raycaster();
      for (const zona of Object.values(zonas)) {
        const x = fCenter.x + zona.fx * fSize.x;
        const z = fCenter.z + zona.fz * fSize.z;
        ray.set(new THREE.Vector3(x, finalBox.max.y + 5, z), new THREE.Vector3(0, -1, 0));
        const hit = ray.intersectObjects(visibles, false)[0];
        zona.pos.set(x, (hit ? hit.point.y : 0) + 0.15, z);
      }

      // Edificios coloreados: cada malla va a la zona más cercana (plano xz) si está dentro del radio
      const radio = opciones.radioZona ?? tamMaqueta * 0.2;
      const cajaMalla = new THREE.Box3();
      const centroMalla = new THREE.Vector3();
      const tamMalla = new THREE.Vector3();
      for (const zona of Object.values(zonas)) {
        zona.material = new THREE.MeshStandardMaterial({ color: COLOR_CLAY, roughness: 0.9, metalness: 0,
                                                          transparent: true });
        zona.grupo = new THREE.Group();
        zona.grupo.position.set(zona.pos.x, 0, zona.pos.z);
        scene.add(zona.grupo);
      }
      scene.updateMatrixWorld(true);
      for (const malla of visibles) {
        cajaMalla.setFromObject(malla);
        cajaMalla.getCenter(centroMalla);
        cajaMalla.getSize(tamMalla);
        if (Math.max(tamMalla.x, tamMalla.z) > tamMaqueta * 0.45) continue; // terreno o base: no es un edificio
        let mejor = null;
        let distancia = Infinity;
        for (const zona of Object.values(zonas)) {
          const d = Math.hypot(centroMalla.x - zona.pos.x, centroMalla.z - zona.pos.z);
          if (d < distancia) [mejor, distancia] = [zona, d];
        }
        if (!mejor || distancia > radio) continue;
        malla.material = mejor.material;
        malla.userData.colectivo = mejor.key;
        mejor.grupo.attach(malla); // conserva su posición; el grupo permite el pulso alrededor de la zona
        mejor.mallas.push(malla);
      }

      redBlink.position.copy(zonas.planta.pos).add(new THREE.Vector3(0, 1.2, 0));

      // Cámara en vista de maqueta (3/4 desde arriba), igual que antes
      controls.target.set(fCenter.x, fSize.y * 0.25, fCenter.z);
      const dist = tamMaqueta * 1.15;
      camera.position.set(fCenter.x + dist * 0.75, dist * 0.8, fCenter.z + dist);
      controls.minDistance = dist * 0.35;
      controls.maxDistance = dist * 2.2;
      controls.update();

      crearEtiquetas();
      setModo(modoNoche);
      loaderOverlay.remove();
    },
    undefined,
    (err) => {
      console.error('Error cargando fabrica.fbx:', err);
      loaderOverlay.textContent = `⚠ ${t('maqueta.error', 'No se pudo cargar la maqueta 3D')}`;
      loaderOverlay.classList.add('visor-3d-loader-error');
      contenedor.dispatchEvent(new CustomEvent('vista3d-error'));
    },
  );

  // --- Etiquetas (mismas clases CSS que antes) ---
  function crearEtiquetas() {
    for (const zona of Object.values(zonas)) {
      const punto = el('span', { className: 'marcador-3d-dot' });
      const texto = el('span', { className: 'marcador-3d-label', texto: zona.label });
      const overlay = el('div', { className: 'marcador-3d-overlay', 'data-colectivo': zona.key }, [punto, texto]);
      overlay.addEventListener('mouseenter', () => { if (!zona.estado?.fuera) overlay.classList.add('marcador-hover'); });
      overlay.addEventListener('mouseleave', () => overlay.classList.remove('marcador-hover'));
      overlay.addEventListener('click', () => { if (!zona.estado?.fuera) seleccionar(zona.key); });
      contenedor.appendChild(overlay);
      zona.overlay = { el: overlay, punto, texto };
    }
  }

  // --- Pintar según capa y modo ---
  const zonaDatos = (key) => (datos.zonas || []).find((z) => z.colectivo === key);
  const colorClay = new THREE.Color(COLOR_CLAY);

  function pintar() {
    for (const zona of Object.values(zonas)) {
      const v = valorCapa(zonaDatos(zona.key), capa, modoNoche, zona.label);
      zona.estado = v;
      if (zona.material) {
        zona.material.color.copy(colorClay).lerp(new THREE.Color(v.atenuada ? COLORES.atenuado : v.color),
                                                 v.atenuada ? 0.3 : 0.8);
        zona.material.opacity = v.atenuada ? 0.45 : 1;
      }
      if (zona.overlay) {
        zona.overlay.texto.textContent = v.etiqueta;
        zona.overlay.punto.style.background = v.color;
        zona.overlay.el.classList.toggle('marcador-atenuado', !!v.atenuada);
        zona.overlay.el.classList.toggle('marcador-activo', seleccionada === zona.key);
      }
    }
    if (seleccionada) mostrarPanel(seleccionada);
  }

  // --- Panel de zona ---
  function seleccionar(key) {
    seleccionada = key;
    pintar();
  }

  function mostrarPanel(key) {
    const zona = zonaDatos(key);
    if (!zona || !panel) return;
    const nombre = zonas[key].label;
    const variacion = zona.variacion == null ? '' :
      ` (${zona.variacion > 0 ? '+' : ''}${numero(zona.variacion, 2)} ${t('maqueta.vs_anterior', 'vs. periodo anterior')})`;
    const temas = (zona.temas || []).length
      ? el('ul', {}, zona.temas.map((t) => el('li', { texto: `${NOMBRE_TEMA[t.tema] || t.tema} · ${t.n}` })))
      : el('p', { texto: t('maqueta.sin_temas', 'Sin temas con 5 comentarios o más.') });
    const alertas = (zona.alertas || []).length
      ? el('ul', {}, zona.alertas.map((a) => el('li', { texto: a })))
      : el('p', { texto: t('maqueta.sin_alertas', 'Sin alertas.') });
    panel.replaceChildren(
      el('h3', { texto: nombre }),
      el('p', { texto: t('maqueta.participacion', 'Participación: {pct} ({n} de {total})', { pct: formatearPct(zona.tasa), n: zona.respuestas, total: zona.personas }) +
                       (zona.representativo ? '' : ` · ${t('maqueta.no_representativa', 'no representativa')}`) }),
      el('p', { texto: zona.media == null ? t('maqueta.valoracion_oculta', 'Valoración: oculta (n < 5)')
                                          : `${t('maqueta.valoracion', 'Valoración: {media} / 5', { media: formatearMedia(zona.media) })}${variacion}` }),
      el('h4', { texto: t('maqueta.temas', 'Temas principales') }), temas,
      el('h4', { texto: t('maqueta.alertas', 'Alertas') }), alertas,
      el('div', { style: { display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' } }, [
        el('button', { type: 'button', className: 'btn', texto: t('maqueta.crear', 'Crear encuesta para este sector'), onclick: () => {
          sessionStorage.setItem('necesidad_prefill', JSON.stringify(necesidadParaZona(zona, nombre)));
          window.location.href = urlCrear;
        } }),
        el('button', { type: 'button', className: 'btn', texto: t('maqueta.ver_analisis', 'Ver en el análisis'), onclick: () => {
          opciones.onVerEnAnalisis?.(key);
          document.dispatchEvent(new CustomEvent('vista3d:ver-en-analisis', { detail: { colectivo: key } }));
        } }),
      ]),
    );
    panel.style.display = 'block';
  }

  // --- Clic sobre los edificios ---
  const raycaster = new THREE.Raycaster();
  const puntero = new THREE.Vector2();
  function zonaBajoPuntero(evento) {
    const r = canvas.getBoundingClientRect();
    puntero.set(((evento.clientX - r.left) / r.width) * 2 - 1, -((evento.clientY - r.top) / r.height) * 2 + 1);
    scene.updateMatrixWorld();
    raycaster.setFromCamera(puntero, camera);
    const activas = Object.values(zonas).filter((z) => z.estado && !z.estado.fuera).flatMap((z) => z.mallas);
    return raycaster.intersectObjects(activas, false)[0]?.object.userData.colectivo || null;
  }
  const alPulsar = (e) => { const k = zonaBajoPuntero(e); if (k) seleccionar(k); };
  const alMover = (e) => { canvas.style.cursor = zonaBajoPuntero(e) ? 'pointer' : ''; };
  canvas.addEventListener('click', alPulsar);
  canvas.addEventListener('pointermove', alMover);

  // --- Pulso en directo ---
  function pulsar(key, nuevas) {
    const zona = zonas[key];
    if (!zona) return;
    const r = tamMaqueta * 0.06;
    const anillo = new THREE.Mesh(new THREE.RingGeometry(r, r * 1.25, 48),
      new THREE.MeshBasicMaterial({ color: COLORES.verde, transparent: true, opacity: 0.9, side: THREE.DoubleSide }));
    anillo.rotation.x = -Math.PI / 2;
    anillo.position.set(zona.pos.x, 0.02, zona.pos.z);
    scene.add(anillo);
    pulsos.push({ zona, anillo, inicio: performance.now() });
    aviso.textContent = `+${nuevas} ${nuevas === 1 ? 'respuesta' : 'respuestas'} en ${zona.label}`;
    aviso.style.opacity = '1';
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(() => { aviso.style.opacity = '0'; }, 3000);
  }

  function animarPulsos(ahora) {
    for (let i = pulsos.length - 1; i >= 0; i--) {
      const p = pulsos[i];
      const k = Math.min(1, (ahora - p.inicio) / DURACION_PULSO);
      p.zona.grupo?.scale.setScalar(1 + 0.06 * Math.sin(Math.PI * k));
      p.anillo.scale.setScalar(1 + 2 * k);
      p.anillo.material.opacity = 0.9 * (1 - k);
      if (k >= 1) {
        p.zona.grupo?.scale.setScalar(1);
        scene.remove(p.anillo);
        p.anillo.geometry.dispose();
        p.anillo.material.dispose();
        pulsos.splice(i, 1);
      }
    }
  }

  // --- Modo Día/Noche (= filtro del turno de noche) ---
  function setModo(noche) {
    modoNoche = !!noche;
    renderer.setClearColor(modoNoche ? COLOR_BG_NIGHT : COLOR_BG_DAY);
    hemiLight.visible = !modoNoche;
    sunLight.visible = !modoNoche;
    nightAmbient.visible = modoNoche;
    nightFill.visible = modoNoche;
    const nocheNoRep = (datos.zonas || []).some((z) =>
      (z.turnos || []).some((t) => t.turno === 'noche' && !t.representativo));
    redBlink.visible = modoNoche && nocheNoRep;
    pintar();
  }
  contenedor.__vista3d_setModo = setModo; // compatibilidad con el toggle externo anterior

  // --- Etiquetas: proyectar 3D → 2D cada frame ---
  function actualizarOverlays() {
    const rect = canvas.getBoundingClientRect();
    for (const zona of Object.values(zonas)) {
      if (!zona.overlay) continue;
      const v = zona.pos.clone().project(camera);
      zona.overlay.el.style.left = `${(v.x * 0.5 + 0.5) * rect.width}px`;
      zona.overlay.el.style.top = `${(-v.y * 0.5 + 0.5) * rect.height}px`;
      zona.overlay.el.style.display = v.z > 1 ? 'none' : '';
    }
  }

  // --- Bucle ---
  const clock = new THREE.Clock();
  function animate(ahora) {
    if (disposed) return;
    animFrameId = requestAnimationFrame(animate);
    controls.update();
    animarPulsos(ahora ?? performance.now());
    if (modoNoche && redBlink.visible) redBlink.intensity = 1.5 + Math.sin(clock.getElapsedTime() * 2.5) * 1.5;
    renderer.render(scene, camera);
    actualizarOverlays();
  }
  animate();

  const resizeObs = new ResizeObserver(() => { if (!disposed) resizeRenderer(); });
  resizeObs.observe(contenedor);

  // --- API ---
  return {
    actualizar(analisisNuevo) {
      const antes = Object.fromEntries((datos.zonas || []).map((z) => [z.colectivo, z.respuestas]));
      datos = analisisNuevo || datos;
      for (const z of datos.zonas || []) {
        const previas = antes[z.colectivo];
        if (previas != null && z.respuestas > previas) pulsar(z.colectivo, z.respuestas - previas);
      }
      setModo(modoNoche); // repinta y recalcula la luz del turno de noche
    },
    setCapa(nueva) {
      capa = ['participacion', 'valoracion', 'alertas'].includes(nueva) ? nueva : 'participacion';
      pintar();
    },
    setModo,
    dispose() {
      disposed = true;
      if (animFrameId != null) cancelAnimationFrame(animFrameId);
      clearTimeout(temporizadorAviso);
      resizeObs.disconnect();
      canvas.removeEventListener('click', alPulsar);
      canvas.removeEventListener('pointermove', alMover);
      controls.dispose();
      scene.traverse((o) => {
        o.geometry?.dispose?.();
        [].concat(o.material || []).forEach((m) => m.dispose?.());
      });
      renderer.dispose();
      Object.values(zonas).forEach((z) => z.overlay?.el.remove());
      canvas.remove();
      aviso.remove();
      loaderOverlay.remove?.();
      if (panelPropio) panel.remove();
      delete contenedor.__vista3d_setModo;
    },
  };
}
