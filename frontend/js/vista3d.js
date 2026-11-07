// Maqueta 3D como centro de mando · UPC 2 (v2.md sección 3.7)
//
//   import { iniciarVista3D } from "./js/vista3d.js";
//   const vista = iniciarVista3D(document.getElementById("vista-3d"), analisis, {
//     THREE, FBXLoader, OrbitControls,          // o window.THREE / THREE.FBXLoader / THREE.OrbitControls
//     modeloUrl: "/modelos/fabrica.fbx",        // opcional: sin modelo (o si falla) se dibujan bloques
//     onVerEnAnalisis: (colectivo) => { … },    // opcional: cambiar a Resumen y resaltar la columna
//   });
//   vista.actualizar(analisisNuevo); vista.setCapa("valoracion"); vista.setModo(true); vista.dispose();
//
// Además emite en document el evento "vista3d:ver-en-analisis" con detail = { colectivo }.

<<<<<<< HEAD
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { decimal, porcentaje, textoLegible, TIPOS_ALERTA, escapar } from '/js/ui.js';

// =========================================================================
// CONSTANTES
// =========================================================================

/**
 * Zonas de la maqueta. AJUSTA AQUÍ la posición de cada marcador:
 * fx y fz van de -0.5 a 0.5 sobre la planta del modelo (fx: izquierda → derecha,
 * fz: fondo → frente). La altura se calcula sola: el marcador se apoya en el tejado
 * que haya debajo de ese punto.
 */
const ZONAS = {
  planta:    { label: 'Planta', fx:  0.25, fz: -0.20, pos: new THREE.Vector3() },
  logistica: { label: 'Logística',            fx: -0.30, fz: -0.30, pos: new THREE.Vector3() },
  comercial: { label: 'Comercial',            fx: -0.30, fz:  0.30, pos: new THREE.Vector3() },
  oficina:   { label: 'Oficina',              fx:  0.05, fz:  0.30, pos: new THREE.Vector3() },
  manager:   { label: 'Managers',            fx:  0.30, fz:  0.25, pos: new THREE.Vector3() },
=======
// Posiciones de cada zona en el plano xz (y = 0). Si el FBX usa otras coordenadas, pasad
// opciones.zonas con las mismas claves (o copiad aquí las posiciones del ZONAS anterior).
export const ZONAS = {
  planta: { nombre: "Planta", pos: [-14, 0, -6], tam: [14, 7, 10] },
  logistica: { nombre: "Logística", pos: [12, 0, -8], tam: [12, 5, 10] },
  comercial: { nombre: "Comercial", pos: [-11, 0, 12], tam: [8, 5, 7] },
  oficina: { nombre: "Oficina", pos: [10, 0, 11], tam: [8, 12, 8] },
  manager: { nombre: "Managers", pos: [0, 0, 24], tam: [6, 9, 6] },
>>>>>>> a5048f5 (UPC 2 v2: multisector, análisis completo, preguntar, simulación contextual, maqueta 3D y ejemplos)
};

export const COLORES = {
  rojo: "#d64545", ambar: "#e0a43a", verde: "#3f9e5a", gris: "#9aa0a6", atenuado: "#c9ccd1",
};

<<<<<<< HEAD
const COLOR_CLAY    = 0xF5F1EA; // color único de la maqueta (monocromática)
const COLOR_BG_DAY  = 0xFFFFFF;
const COLOR_BG_NIGHT = 0x141B2D;
const COLOR_DAMM    = 0xB91C1C; // --critico de diseno.md
const COLOR_NIGHT_BLUE = 0x2B3A67;
=======
const NOMBRE_TEMA = {
  descansos: "Descansos", turnos: "Turnos", carga_trabajo: "Carga de trabajo", comunicacion: "Comunicación",
  liderazgo: "Liderazgo", herramientas: "Herramientas", formacion: "Formación", reconocimiento: "Reconocimiento",
  seguridad: "Seguridad", ambiente: "Ambiente", conciliacion: "Conciliación", otros: "Otros",
};
const DURACION_PULSO = 1200;
>>>>>>> a5048f5 (UPC 2 v2: multisector, análisis completo, preguntar, simulación contextual, maqueta 3D y ejemplos)

// ---------- utilidades puras (exportadas para poder probarlas) ----------

<<<<<<< HEAD
/** Devuelve color del marcador según representatividad del colectivo */
function colorMarcador(colKey, analisis) {
  const filas = (analisis.participacion || []).filter(f => f.colectivo === colKey);
  if (filas.length === 0) return 0xA1A1AA; // gris: ausente
  const hayNoRep = filas.some(f => !f.representativo);
  return hayNoRep ? COLOR_DAMM : 0x15803D; // crítico o correcto (--ok)
=======
export function formatearPct(tasa) {
  return `${Math.round((tasa || 0) * 100)} %`;
>>>>>>> a5048f5 (UPC 2 v2: multisector, análisis completo, preguntar, simulación contextual, maqueta 3D y ejemplos)
}

export function formatearMedia(media) {
  return media == null ? "—" : media.toFixed(1).replace(".", ",");
}

function flecha(variacion) {
  if (variacion == null) return "";
  if (variacion <= -0.1) return " ↓";
  if (variacion >= 0.1) return " ↑";
  return "";
}

/** Color, etiqueta y estado de una zona para una capa. `zona` es un elemento de analisis.zonas (o undefined). */
export function valorCapa(zona, capa, noche = false, nombre = "") {
  nombre = nombre || (zona && ZONAS[zona.colectivo]?.nombre) || "";
  if (!zona) return { color: COLORES.atenuado, etiqueta: nombre, atenuada: true, motivo: "Fuera de esta encuesta" };

  let fila = zona;
  let alertas = zona.alertas || [];
  if (noche) {
    fila = (zona.turnos || []).find((t) => t.turno === "noche");
    if (!fila) {
      return { color: COLORES.atenuado, etiqueta: `${nombre} · Sin turno de noche`, atenuada: true,
               motivo: "Sin turno de noche" };
    }
    alertas = alertas.filter((a) => /noche/i.test(a));
  }

  if (capa === "valoracion") {
    if (fila.media == null) return { color: COLORES.gris, etiqueta: `${nombre} · Oculto (n < 5)`, atenuada: false };
    const color = fila.media < 2.5 ? COLORES.rojo : fila.media < 3.5 ? COLORES.ambar : COLORES.verde;
    return { color, etiqueta: `${nombre} · ${formatearMedia(fila.media)}${noche ? "" : flecha(zona.variacion)}`,
             atenuada: false };
  }
  if (capa === "alertas") {
    const n = alertas.length;
    const color = n === 0 ? COLORES.verde : n === 1 ? COLORES.ambar : COLORES.rojo;
    return { color, etiqueta: `${nombre} · ${n} ${n === 1 ? "alerta" : "alertas"}`, atenuada: false };
  }
  const tasa = fila.tasa || 0; // participacion
  const color = tasa < 0.1 ? COLORES.rojo : tasa < 0.2 ? COLORES.ambar : COLORES.verde;
  return { color, etiqueta: `${nombre} · ${formatearPct(tasa)}`, atenuada: false };
}

/** Necesidad para "Crear encuesta para este sector". */
export function necesidadParaZona(zona, nombre) {
  const tema = zona.temas?.[0]?.tema;
  const temaTexto = tema ? (NOMBRE_TEMA[tema] || tema).toLowerCase() : "el clima laboral";
  return {
    objetivo: `Profundizar en ${temaTexto} en ${nombre.toLowerCase()}`,
    colectivos: [zona.colectivo],
    contexto: zona.alertas?.[0] || (tema ? `Tema principal: ${temaTexto}` : "Seguimiento del último pulso"),
    duracion_max_seg: 60,
    temas_prohibidos: ["salario"],
  };
}

<<<<<<< HEAD
// =========================================================================
// FUNCIÓN PRINCIPAL
// =========================================================================

/**
 * Inicializa la escena 3D dentro de `contenedor` usando los datos de `analisis`.
 * Devuelve un objeto { dispose() } para limpiar y detener el render loop.
 */
export function iniciarVista3D(contenedor, analisis, mapaPreguntas = {}) {
  // --- Estado interno ----
  let animFrameId = null;
  let disposed = false;
  let modoNoche = false;

  // --- Renderer ---
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(COLOR_BG_DAY);

  const canvas = renderer.domElement;
  canvas.classList.add('visor-3d-canvas');
  contenedor.appendChild(canvas);

  function resizeRenderer() {
    const w = contenedor.clientWidth;
    const h = contenedor.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  // --- Cámara ---
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  camera.position.set(8, 6, 8);

  // --- Escena ---
  const scene = new THREE.Scene();

  // --- Luces (Día por defecto) ---
  const hemiLight = new THREE.HemisphereLight(0xFFF5E6, 0xD5C8B3, 1.0);
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xFFF5E6, 1.2);
  sunLight.position.set(5, 10, 7);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(1024, 1024);
  sunLight.shadow.camera.near = 0.5;
  sunLight.shadow.camera.far = 50;
  sunLight.shadow.camera.left = -10;
  sunLight.shadow.camera.right = 10;
  sunLight.shadow.camera.top = 10;
  sunLight.shadow.camera.bottom = -10;
  scene.add(sunLight);

  // Luces nocturnas (desactivadas al inicio)
  const nightAmbient = new THREE.AmbientLight(COLOR_NIGHT_BLUE, 0.7);
  nightAmbient.visible = false;
  scene.add(nightAmbient);

  const nightFill = new THREE.DirectionalLight(0x8FA3D9, 0.6);
  nightFill.position.set(-3, 8, -5);
  nightFill.visible = false;
  scene.add(nightFill);

  // Luz roja parpadeante sobre Planta (solo si planta/noche no representativo)
  const plantaNocheNoRep = (analisis.participacion || []).some(
    f => f.colectivo === 'planta' && f.turno === 'noche' && !f.representativo
  );
  const redBlink = new THREE.PointLight(COLOR_DAMM, 0, 12);
  redBlink.position.copy(ZONAS.planta.pos).add(new THREE.Vector3(0, 1.5, 0));
  redBlink.visible = false;
  scene.add(redBlink);

  // --- Suelo ---
  const groundGeo = new THREE.PlaneGeometry(60, 60);
  // Suelo invisible: solo muestra las sombras, el fondo es el color de la página
  const groundMat = new THREE.ShadowMaterial({ opacity: 0.14 });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.01;
  ground.receiveShadow = true;
  scene.add(ground);

  // --- Controles ---
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.47; // ≈ 85° — no traspasar el suelo
  controls.minDistance = 3;
  controls.maxDistance = 25;
  controls.target.set(0, 1, 0);
  controls.update();

  resizeRenderer();

  // --- Carga del modelo FBX ---
  const loaderOverlay = document.createElement('div');
  loaderOverlay.className = 'visor-3d-loader';
  loaderOverlay.textContent = 'Cargando maqueta…';
  contenedor.appendChild(loaderOverlay);

  const loader = new FBXLoader();
  loader.load(
    '/public/fabrica.fbx',
    (fbx) => {
      // Maqueta monocromática: un único material para todas las mallas,
      // ignorando texturas y colores de vértice del FBX
      const matClay = new THREE.MeshStandardMaterial({
        color: COLOR_CLAY, roughness: 0.9, metalness: 0, vertexColors: false,
      });
      fbx.traverse(child => {
        if (!child.isMesh) return;
        if (MALLAS_OCULTAS.test(child.name)) { child.visible = false; return; }
        child.material = matClay;
        child.castShadow = true;
        child.receiveShadow = true;
      });

      // Caja solo de las mallas visibles (sin nubes ni coches)
      fbx.updateMatrixWorld(true);
      const box = new THREE.Box3();
      fbx.traverse(child => { if (child.isMesh && child.visible) box.expandByObject(child); });
      const size = box.getSize(new THREE.Vector3());
      const scale = 6 / Math.max(size.x, size.z); // la planta ocupa ~6 unidades
      fbx.scale.setScalar(scale);
      // Centrado en x/z y apoyado en el suelo (y = 0)
      const center = box.getCenter(new THREE.Vector3());
      fbx.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
      scene.add(fbx);
      fbx.updateMatrixWorld(true);

      const finalBox = new THREE.Box3();
      fbx.traverse(child => { if (child.isMesh && child.visible) finalBox.expandByObject(child); });
      const fCenter = finalBox.getCenter(new THREE.Vector3());
      const fSize = finalBox.getSize(new THREE.Vector3());

      // Cada marcador se apoya en el tejado que hay debajo de su punto (raycast vertical)
      const ray = new THREE.Raycaster();
      const visibles = [];
      fbx.traverse(child => { if (child.isMesh && child.visible) visibles.push(child); });
      Object.values(ZONAS).forEach(zona => {
        const x = fCenter.x + zona.fx * fSize.x;
        const z = fCenter.z + zona.fz * fSize.z;
        ray.set(new THREE.Vector3(x, finalBox.max.y + 5, z), new THREE.Vector3(0, -1, 0));
        const hit = ray.intersectObjects(visibles, false)[0];
        const y = hit ? hit.point.y : 0;
        zona.pos.set(x, y + 0.15, z);
      });

      // Luz roja sobre Planta
      redBlink.position.copy(ZONAS.planta.pos).add(new THREE.Vector3(0, 1.2, 0));

      // Cámara en vista de maqueta (3/4 desde arriba)
      controls.target.set(fCenter.x, fSize.y * 0.25, fCenter.z);
      const dist = Math.max(fSize.x, fSize.z) * 1.15;
      camera.position.set(fCenter.x + dist * 0.75, dist * 0.8, fCenter.z + dist);
      controls.minDistance = dist * 0.35;
      controls.maxDistance = dist * 2.2;
      controls.update();

      // Crear marcadores 3D (esferas) y overlays HTML
      crearMarcadores();

      loaderOverlay.remove();
    },
    undefined,
    (err) => {
      console.error('Error cargando fabrica.fbx:', err);
      loaderOverlay.textContent = '⚠ No se pudo cargar la maqueta 3D';
      loaderOverlay.classList.add('visor-3d-loader-error');
      // Dispara el evento para que dashboard.html vuelva a vista analítica
      contenedor.dispatchEvent(new CustomEvent('vista3d-error'));
    }
  );

  // --- Marcadores (esferas 3D + overlays HTML) ---
  const marcadores3D = [];
  const overlays = [];
  const panelLateral = document.getElementById('panel-3d-detalle');

  function crearMarcadores() {
    // Determinar si la encuesta es de un solo colectivo
    const colectivos = [...new Set((analisis.participacion || []).map(f => f.colectivo))];
    const esMono = colectivos.length === 1;

    Object.entries(ZONAS).forEach(([key, zona]) => {
      // Esfera 3D
      const color = colorMarcador(key, analisis);
      const geo = new THREE.SphereGeometry(0.15, 16, 16);
      const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.4, emissive: color, emissiveIntensity: 0.15 });
      const sphere = new THREE.Mesh(geo, mat);
      sphere.position.copy(zona.pos);
      sphere.position.y += 0.05;
      scene.add(sphere);
      marcadores3D.push({ key, sphere, baseScale: 1 });

      // Overlay HTML
      const overlay = document.createElement('div');
      overlay.className = 'marcador-3d-overlay';
      overlay.dataset.colectivo = key;
      overlay.innerHTML = `<span class="marcador-3d-dot" style="background:#${color.toString(16).padStart(6,'0')}"></span><span class="marcador-3d-label">${zona.label}</span>`;
      contenedor.appendChild(overlay);
      overlays.push({ key, el: overlay });

      // Atenuar si la encuesta es de un solo colectivo distinto
      if (esMono && !colectivos.includes(key)) {
        overlay.classList.add('marcador-atenuado');
        mat.opacity = 0.3;
        mat.transparent = true;
      }

      // Eventos
      overlay.addEventListener('mouseenter', () => {
        sphere.scale.setScalar(1.4);
        overlay.classList.add('marcador-hover');
      });
      overlay.addEventListener('mouseleave', () => {
        sphere.scale.setScalar(1);
        overlay.classList.remove('marcador-hover');
      });
      overlay.addEventListener('click', () => {
        mostrarDetalle(key);
      });
    });
  }

  // --- Panel lateral de detalle ---
  function mostrarDetalle(colKey) {
    if (!panelLateral) return;
    const zona = ZONAS[colKey];
    const filas = (analisis.participacion || []).filter(f => f.colectivo === colKey);
    const respuestas = filas.reduce((a, f) => a + (f.respuestas || 0), 0);
    const personas = filas.reduce((a, f) => a + (f.personas || 0), 0);
    const tasa = personas > 0 ? respuestas / personas : 0;
    const hayNoRep = filas.some(f => !f.representativo);

    // Resaltar marcador activo
    overlays.forEach(o => o.el.classList.toggle('marcador-activo', o.key === colKey));

    let html = `<h4 class="panel-3d-titulo">${zona.label}</h4>`;

    // PRIVACIDAD: n < 5
    if (respuestas < 5) {
      html += `
        <div class="aviso-ia" style="margin:0.6rem 0">
          Oculto por privacidad (menos de 5 respuestas). Solo ${respuestas} respuestas de ${personas} personas.
        </div>`;
      panelLateral.innerHTML = html;
      panelLateral.style.display = 'block';
      return;
    }

    // Badge representatividad
    if (hayNoRep) {
      html += `<span class="badge badge-no-representativo" style="margin-bottom:0.6rem;display:inline-block">No representativo</span>`;
    } else {
      html += `<span class="badge badge-ok" style="margin-bottom:0.6rem;display:inline-block">Representativo</span>`;
    }

    // Participación global
    html += `
      <div class="panel-3d-stat">
        <span class="text-muted text-small">Tasa de participación</span>
        <strong>${porcentaje(tasa)}</strong>
        <span class="text-muted text-small">${respuestas} / ${personas}</span>
      </div>`;

    // Turnos
    if (filas.length > 0) {
      html += `<div class="panel-3d-turnos"><span class="text-muted text-small" style="font-weight:600;margin-bottom:0.3rem;display:block">Desglose por turno</span>`;
      filas.forEach(f => {
        const turnoLabel = { manana: 'Mañana', tarde: 'Tarde', noche: 'Noche', sin_turno: 'Sin turno' }[f.turno] || f.turno;
        const pct = porcentaje(f.tasa || 0);
        const noRep = !f.representativo;
        html += `
          <div class="panel-3d-turno-row">
            <span>${turnoLabel}</span>
            <span style="font-weight:700;${noRep ? 'color:var(--critico)' : ''}">${pct}</span>
            <span class="text-muted text-small">(${f.respuestas}/${f.personas})</span>
          </div>`;
      });
      html += `</div>`;
    }

    // Medias del colectivo
    const mediasCol = (analisis.medias || []).filter(m => m.colectivo === colKey);
    if (mediasCol.length > 0) {
      html += `<div class="panel-3d-medias"><span class="text-muted text-small" style="font-weight:600;margin-bottom:0.3rem;display:block">Medias</span>`;
      mediasCol.forEach(m => {
        if (m.n < 5) {
          html += `<div class="panel-3d-turno-row"><span style="flex:1">${escapar(mapaPreguntas[m.pregunta] || m.pregunta)}</span><span class="text-muted">—</span></div>`;
        } else {
          html += `<div class="panel-3d-turno-row"><span style="flex:1">${escapar(mapaPreguntas[m.pregunta] || m.pregunta)}</span><strong>${decimal(m.media)}</strong></div>`;
        }
      });
      html += `</div>`;
    }

    // Alertas
    const alertas = (analisis.alertas || []).filter(a => {
      const msg = (a.mensaje || '').toLowerCase();
      return msg.includes(colKey) ||
        (colKey === 'planta' && msg.includes('noche')) ||
        (colKey === 'logistica' && msg.includes('almacén'));
    });
    if (alertas.length > 0) {
      html += `<div style="margin-top:0.6rem">`;
      alertas.forEach(a => {
        html += `<div class="alerta" style="margin-bottom:0.4rem;padding:0.5rem 0.7rem"><div><div class="alerta-tipo">${escapar(TIPOS_ALERTA[a.tipo] || a.tipo)}</div><div class="alerta-mensaje">${escapar(textoLegible(a.mensaje, mapaPreguntas))}</div></div></div>`;
      });
      html += `</div>`;
    }

    panelLateral.innerHTML = html;
    panelLateral.style.display = 'block';
  }

  // --- Modo Día/Noche ---
  function setModo(noche) {
    modoNoche = noche;
    if (noche) {
      renderer.setClearColor(COLOR_BG_NIGHT);
      hemiLight.visible = false;
      sunLight.visible = false;
      nightAmbient.visible = true;
      nightFill.visible = true;
      if (plantaNocheNoRep) {
        redBlink.visible = true;
      }
    } else {
      renderer.setClearColor(COLOR_BG_DAY);
      hemiLight.visible = true;
      sunLight.visible = true;
      nightAmbient.visible = false;
      nightFill.visible = false;
      redBlink.visible = false;
    }
  }

  // Exponer para el toggle externo
  contenedor.__vista3d_setModo = setModo;

  // --- Actualizar overlays (proyectar 3D → 2D cada frame) ---
  function actualizarOverlays() {
    const rect = canvas.getBoundingClientRect();
    const contRect = contenedor.getBoundingClientRect();

    overlays.forEach(({ key, el }) => {
      const zona = ZONAS[key];
      const screen = toScreen(zona.pos, camera, rect);
      el.style.left = `${screen.x}px`;
      el.style.top = `${screen.y}px`;

      // Ocultar si está detrás de la cámara
      const v = zona.pos.clone().project(camera);
      el.style.display = (v.z > 1) ? 'none' : '';
    });
  }

  // --- Loop de animación ---
  const clock = new THREE.Clock();
  function animate() {
    if (disposed) return;
    animFrameId = requestAnimationFrame(animate);

    controls.update();

    // Parpadeo de luz roja en modo noche
    if (modoNoche && redBlink.visible) {
      const t = clock.getElapsedTime();
      redBlink.intensity = 1.5 + Math.sin(t * 2.5) * 1.5; // 0 ↔ 3
    }

    renderer.render(scene, camera);
    actualizarOverlays();
  }
  animate();

  // --- Resize ---
  const resizeObs = new ResizeObserver(() => {
    if (!disposed) resizeRenderer();
  });
  resizeObs.observe(contenedor);

  // --- Cleanup ---
  function dispose() {
    disposed = true;
    if (animFrameId != null) cancelAnimationFrame(animFrameId);
    resizeObs.disconnect();
    controls.dispose();
    renderer.dispose();
    // Eliminar overlays
    overlays.forEach(o => o.el.remove());
    overlays.length = 0;
    // Eliminar canvas
    canvas.remove();
    loaderOverlay.remove?.();
  }

  return { dispose, setModo };
=======
function el(tag, props = {}, hijos = []) {
  const nodo = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "style") Object.assign(nodo.style, v);
    else if (k.startsWith("on")) nodo.addEventListener(k.slice(2), v);
    else if (k === "texto") nodo.textContent = v;
    else nodo.setAttribute(k, v);
  }
  for (const h of [].concat(hijos)) if (h != null) nodo.append(h);
  return nodo;
>>>>>>> a5048f5 (UPC 2 v2: multisector, análisis completo, preguntar, simulación contextual, maqueta 3D y ejemplos)
}

// ---------- vista ----------

export function iniciarVista3D(contenedor, analisis, opciones = {}) {
  const THREE = opciones.THREE || window.THREE;
  if (!THREE) throw new Error("vista3d: falta THREE (pásalo en opciones.THREE o cárgalo en window.THREE)");
  const FBXLoader = opciones.FBXLoader || THREE.FBXLoader || window.FBXLoader;
  const OrbitControls = opciones.OrbitControls || THREE.OrbitControls || window.OrbitControls;
  const definicion = opciones.zonas || ZONAS;
  const radioZona = opciones.radioZona ?? 14;
  const urlCrear = opciones.urlCrear || "crear.html";

  let datos = analisis || { zonas: [] };
  let capa = opciones.capa || "participacion";
  let noche = !!opciones.noche;
  let seleccionada = null;
  let cuadro = 0;
  const pulsos = [];
  const limpiezas = [];

  if (getComputedStyle(contenedor).position === "static") contenedor.style.position = "relative";

  // Escena
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  contenedor.append(renderer.domElement);
  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
  camara.position.set(38, 42, 52);
  camara.lookAt(0, 0, 4);
  const luzCielo = new THREE.HemisphereLight(0xffffff, 0x8a8f99, 0.9);
  const luzSol = new THREE.DirectionalLight(0xffffff, 0.8);
  luzSol.position.set(30, 60, 20);
  escena.add(luzCielo, luzSol);
  const suelo = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ color: 0xe9ebee }));
  suelo.rotation.x = -Math.PI / 2;
  escena.add(suelo);

  let controles = null;
  if (OrbitControls) {
    controles = new OrbitControls(camara, renderer.domElement);
    controles.target.set(0, 0, 4);
    controles.enableDamping = true;
    controles.maxPolarAngle = Math.PI / 2.2;
  }

  // Capa HTML: etiquetas, aviso y (si no existe) panel
  const capaHtml = el("div", { style: { position: "absolute", inset: "0", pointerEvents: "none", overflow: "hidden",
                                        font: "13px system-ui, sans-serif" } });
  contenedor.append(capaHtml);
  const aviso = el("div", { style: { position: "absolute", top: "12px", left: "50%", transform: "translateX(-50%)",
    background: "rgba(20,24,31,.85)", color: "#fff", padding: "6px 12px", borderRadius: "16px",
    opacity: "0", transition: "opacity .3s" } });
  capaHtml.append(aviso);
  let panel = typeof opciones.panel === "string" ? document.querySelector(opciones.panel)
    : opciones.panel || document.getElementById("panel-3d-detalle");
  let panelPropio = false;
  if (!panel) {
    panel = el("div", { id: "panel-3d-detalle", style: { position: "absolute", top: "12px", right: "12px",
      width: "280px", background: "#fff", borderRadius: "10px", padding: "14px", pointerEvents: "auto",
      boxShadow: "0 4px 16px rgba(0,0,0,.15)", display: "none" } });
    capaHtml.append(panel);
    panelPropio = true;
  }

  // Zonas
  const zonas = {}; // colectivo -> { def, material, mallas: [], etiqueta, anillo }
  for (const [colectivo, def] of Object.entries(definicion)) {
    const material = new THREE.MeshStandardMaterial({ color: COLORES.atenuado, transparent: true, opacity: 1 });
    const etiqueta = el("div", { style: { position: "absolute", transform: "translate(-50%, -100%)",
      background: "rgba(255,255,255,.92)", padding: "3px 8px", borderRadius: "6px", whiteSpace: "nowrap",
      boxShadow: "0 1px 4px rgba(0,0,0,.15)", fontWeight: "600" } });
    capaHtml.append(etiqueta);
    zonas[colectivo] = { colectivo, def, material, mallas: [], etiqueta, altura: def.tam?.[1] ?? 6 };
  }

  function construirBloques() {
    for (const z of Object.values(zonas)) {
      const [ancho, alto, fondo] = z.def.tam || [8, 6, 8];
      const malla = new THREE.Mesh(new THREE.BoxGeometry(ancho, alto, fondo), z.material);
      malla.position.set(z.def.pos[0], alto / 2, z.def.pos[2]);
      malla.userData.colectivo = z.colectivo;
      malla.userData.escalaBase = malla.scale.clone();
      escena.add(malla);
      z.mallas.push(malla);
    }
  }

  function asignarMallasDelModelo(modelo) {
    modelo.updateMatrixWorld(true);
    const caja = new THREE.Box3();
    const centro = new THREE.Vector3();
    modelo.traverse((objeto) => {
      if (!objeto.isMesh) return;
      caja.setFromObject(objeto).getCenter(centro);
      let mejor = null;
      let distancia = Infinity;
      for (const z of Object.values(zonas)) {
        const d = Math.hypot(centro.x - z.def.pos[0], centro.z - z.def.pos[2]);
        if (d < distancia) [mejor, distancia] = [z, d];
      }
      if (!mejor || distancia > radioZona) return; // sin zona: se queda con su material
      objeto.material = mejor.material;
      objeto.userData.colectivo = mejor.colectivo;
      objeto.userData.escalaBase = objeto.scale.clone();
      mejor.mallas.push(objeto);
      mejor.altura = Math.max(mejor.altura, caja.max.y);
    });
  }

  if (FBXLoader && opciones.modeloUrl) {
    new FBXLoader().load(opciones.modeloUrl, (modelo) => {
      if (opciones.escalaModelo) modelo.scale.setScalar(opciones.escalaModelo);
      escena.add(modelo);
      asignarMallasDelModelo(modelo);
      if (!Object.values(zonas).some((z) => z.mallas.length)) construirBloques();
      pintar();
    }, undefined, (error) => {
      console.warn("vista3d: no se pudo cargar el modelo, uso bloques", error);
      construirBloques();
      pintar();
    });
  } else {
    construirBloques();
  }

  // Pintar
  const zonaDe = (colectivo) => (datos.zonas || []).find((z) => z.colectivo === colectivo);
  function pintar() {
    escena.background = new THREE.Color(noche ? 0x1d2433 : 0xf4f5f7);
    luzCielo.intensity = noche ? 0.45 : 0.9;
    luzSol.intensity = noche ? 0.25 : 0.8;
    suelo.material.color.set(noche ? 0x2a3242 : 0xe9ebee);
    for (const z of Object.values(zonas)) {
      const v = valorCapa(zonaDe(z.colectivo), capa, noche, z.def.nombre);
      z.estado = v;
      z.material.color.set(v.atenuada ? COLORES.atenuado : v.color);
      z.material.opacity = v.atenuada ? 0.35 : 1;
      z.etiqueta.textContent = v.etiqueta;
      z.etiqueta.style.opacity = v.atenuada ? "0.55" : "1";
      z.etiqueta.style.outline = seleccionada === z.colectivo ? "2px solid #1d2433" : "none";
    }
    if (seleccionada) mostrarPanel(seleccionada);
  }

  // Panel de zona
  function mostrarPanel(colectivo) {
    const zona = zonaDe(colectivo);
    const def = zonas[colectivo].def;
    if (!zona) return;
    seleccionada = colectivo;
    const variacion = zona.variacion == null ? "" :
      ` (${zona.variacion > 0 ? "+" : ""}${zona.variacion.toFixed(2).replace(".", ",")} vs. periodo anterior)`;
    const temas = (zona.temas || []).length
      ? el("ul", {}, zona.temas.map((t) => el("li", { texto: `${NOMBRE_TEMA[t.tema] || t.tema} · ${t.n}` })))
      : el("p", { texto: "Sin temas con 5 comentarios o más." });
    const alertas = (zona.alertas || []).length
      ? el("ul", {}, zona.alertas.map((a) => el("li", { texto: a })))
      : el("p", { texto: "Sin alertas." });
    panel.replaceChildren(
      el("h3", { texto: def.nombre, style: { margin: "0 0 6px" } }),
      el("p", { texto: `Participación: ${formatearPct(zona.tasa)} (${zona.respuestas} de ${zona.personas})` +
                       (zona.representativo ? "" : " · no representativa") }),
      el("p", { texto: zona.media == null ? "Valoración: oculta (n < 5)"
                                          : `Valoración: ${formatearMedia(zona.media)} / 5${variacion}` }),
      el("h4", { texto: "Temas principales", style: { margin: "10px 0 4px" } }), temas,
      el("h4", { texto: "Alertas", style: { margin: "10px 0 4px" } }), alertas,
      el("div", { style: { display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" } }, [
        el("button", { type: "button", texto: "Crear encuesta para este sector", onclick: () => {
          sessionStorage.setItem("necesidad_prefill", JSON.stringify(necesidadParaZona(zona, def.nombre)));
          window.location.href = urlCrear;
        } }),
        el("button", { type: "button", texto: "Ver en el análisis", onclick: () => {
          opciones.onVerEnAnalisis?.(colectivo);
          document.dispatchEvent(new CustomEvent("vista3d:ver-en-analisis", { detail: { colectivo } }));
        } }),
      ]),
    );
    panel.style.display = "";
  }

  // Interacción
  const raycaster = new THREE.Raycaster();
  const puntero = new THREE.Vector2();
  function zonaBajoPuntero(evento) {
    const r = renderer.domElement.getBoundingClientRect();
    puntero.set(((evento.clientX - r.left) / r.width) * 2 - 1, -((evento.clientY - r.top) / r.height) * 2 + 1);
    escena.updateMatrixWorld();
    raycaster.setFromCamera(puntero, camara);
    const activas = Object.values(zonas).filter((z) => z.estado && !z.estado.motivo?.startsWith("Fuera"))
      .flatMap((z) => z.mallas);
    const golpe = raycaster.intersectObjects(activas, false)[0];
    return golpe?.object.userData.colectivo || null;
  }
  const alPulsar = (e) => {
    const c = zonaBajoPuntero(e);
    if (c) { seleccionada = c; pintar(); }
  };
  const alMover = (e) => { renderer.domElement.style.cursor = zonaBajoPuntero(e) ? "pointer" : ""; };
  renderer.domElement.addEventListener("click", alPulsar);
  renderer.domElement.addEventListener("pointermove", alMover);
  limpiezas.push(() => {
    renderer.domElement.removeEventListener("click", alPulsar);
    renderer.domElement.removeEventListener("pointermove", alMover);
  });

  // Pulso en directo
  function pulsar(colectivo, nuevas) {
    const z = zonas[colectivo];
    if (!z) return;
    const radio = Math.max(...(z.def.tam || [8, 6, 8])) * 0.7;
    const anillo = new THREE.Mesh(new THREE.RingGeometry(radio, radio + 0.6, 48),
      new THREE.MeshBasicMaterial({ color: COLORES.verde, transparent: true, opacity: 0.9, side: THREE.DoubleSide }));
    anillo.rotation.x = -Math.PI / 2;
    anillo.position.set(z.def.pos[0], 0.15, z.def.pos[2]);
    escena.add(anillo);
    pulsos.push({ z, anillo, inicio: performance.now() });
    aviso.textContent = `+${nuevas} ${nuevas === 1 ? "respuesta" : "respuestas"} en ${z.def.nombre}`;
    aviso.style.opacity = "1";
    clearTimeout(pulsar.temporizador);
    pulsar.temporizador = setTimeout(() => { aviso.style.opacity = "0"; }, 3000);
  }

  function animarPulsos(ahora) {
    for (let i = pulsos.length - 1; i >= 0; i--) {
      const p = pulsos[i];
      const k = Math.min(1, (ahora - p.inicio) / DURACION_PULSO);
      const escala = 1 + 0.06 * Math.sin(Math.PI * k);
      for (const m of p.z.mallas) m.scale.copy(m.userData.escalaBase).multiplyScalar(escala);
      p.anillo.scale.setScalar(1 + 1.5 * k);
      p.anillo.material.opacity = 0.9 * (1 - k);
      if (k >= 1) {
        for (const m of p.z.mallas) m.scale.copy(m.userData.escalaBase);
        escena.remove(p.anillo);
        p.anillo.geometry.dispose();
        p.anillo.material.dispose();
        pulsos.splice(i, 1);
      }
    }
  }

  // Bucle
  const vector = new THREE.Vector3();
  function colocarEtiquetas() {
    const ancho = contenedor.clientWidth;
    const alto = contenedor.clientHeight;
    for (const z of Object.values(zonas)) {
      vector.set(z.def.pos[0], z.altura + 1.5, z.def.pos[2]).project(camara);
      const visible = vector.z < 1;
      z.etiqueta.style.display = visible ? "" : "none";
      z.etiqueta.style.left = `${((vector.x + 1) / 2) * ancho}px`;
      z.etiqueta.style.top = `${((1 - vector.y) / 2) * alto}px`;
    }
  }
  function bucle(ahora) {
    cuadro = requestAnimationFrame(bucle);
    animarPulsos(ahora);
    controles?.update();
    renderer.render(escena, camara);
    colocarEtiquetas();
  }

  function redimensionar() {
    const ancho = Math.max(1, contenedor.clientWidth);
    const alto = Math.max(1, contenedor.clientHeight || 420);
    renderer.setSize(ancho, alto);
    camara.aspect = ancho / alto;
    camara.updateProjectionMatrix();
  }
  const observador = new ResizeObserver(redimensionar);
  observador.observe(contenedor);
  redimensionar();
  pintar();
  cuadro = requestAnimationFrame(bucle);

  return {
    actualizar(analisisNuevo) {
      const antes = Object.fromEntries((datos.zonas || []).map((z) => [z.colectivo, z.respuestas]));
      datos = analisisNuevo || datos;
      for (const z of datos.zonas || []) {
        const previas = antes[z.colectivo];
        if (previas != null && z.respuestas > previas) pulsar(z.colectivo, z.respuestas - previas);
      }
      pintar();
    },
    setCapa(nueva) {
      capa = ["participacion", "valoracion", "alertas"].includes(nueva) ? nueva : "participacion";
      pintar();
    },
    setModo(esNoche) {
      noche = !!esNoche;
      pintar();
    },
    dispose() {
      cancelAnimationFrame(cuadro);
      clearTimeout(pulsar.temporizador);
      observador.disconnect();
      limpiezas.forEach((f) => f());
      controles?.dispose?.();
      escena.traverse((o) => {
        o.geometry?.dispose?.();
        [].concat(o.material || []).forEach((m) => m.dispose?.());
      });
      renderer.dispose();
      renderer.domElement.remove();
      capaHtml.remove();
      if (!panelPropio) panel.replaceChildren();
    },
  };
}
