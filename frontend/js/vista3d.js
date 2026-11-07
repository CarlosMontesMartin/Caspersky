/**
 * vista3d.js — Vista 3D de la maqueta industrial Damm
 * Módulo ES · Three.js 0.160.0 (vendor local, sin CDN)
 * Exporta: iniciarVista3D(contenedor, analisis)
 */

import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// =========================================================================
// CONSTANTES
// =========================================================================

/** Posiciones de marcadores (ajustar a mano tras ver el modelo) */
const ZONAS = {
  planta:    { label: '🏭 Planta de producción', pos: new THREE.Vector3(-2,  1.5,  0)   },
  logistica: { label: '📦 Logística',            pos: new THREE.Vector3( 2,  1.2, -2)   },
  comercial: { label: '🚚 Comercial',            pos: new THREE.Vector3( 3,  0.8,  2.5) },
  oficina:   { label: '🏢 Oficina',              pos: new THREE.Vector3(-1,  2.8,  2)   },
  manager:   { label: '👔 Dirección',            pos: new THREE.Vector3( 0,  3.5,  0.5) },
};

const COLOR_CLAY_1  = 0xF5F1EA;
const COLOR_CLAY_2  = 0xE8DFD0;
const COLOR_BG_DAY  = 0xFAF7F2;
const COLOR_BG_NIGHT = 0x141B2D;
const COLOR_DAMM    = 0xB5121B;
const COLOR_NIGHT_BLUE = 0x2B3A67;

// =========================================================================
// UTILIDADES
// =========================================================================

/** Devuelve color del marcador según representatividad del colectivo */
function colorMarcador(colKey, analisis) {
  const filas = (analisis.participacion || []).filter(f => f.colectivo === colKey);
  if (filas.length === 0) return 0x999999; // gris: ausente
  const hayNoRep = filas.some(f => !f.representativo);
  return hayNoRep ? COLOR_DAMM : 0x2A1A1A; // rojo Damm o oscuro
}

/** Proyecta una posición 3D a coordenadas de pantalla del contenedor */
function toScreen(pos, camera, domRect) {
  const v = pos.clone().project(camera);
  return {
    x: (v.x * 0.5 + 0.5) * domRect.width,
    y: (-v.y * 0.5 + 0.5) * domRect.height,
  };
}

// =========================================================================
// FUNCIÓN PRINCIPAL
// =========================================================================

/**
 * Inicializa la escena 3D dentro de `contenedor` usando los datos de `analisis`.
 * Devuelve un objeto { dispose() } para limpiar y detener el render loop.
 */
export function iniciarVista3D(contenedor, analisis) {
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
  const nightAmbient = new THREE.AmbientLight(COLOR_NIGHT_BLUE, 0.3);
  nightAmbient.visible = false;
  scene.add(nightAmbient);

  const nightFill = new THREE.DirectionalLight(COLOR_NIGHT_BLUE, 0.4);
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
  const groundGeo = new THREE.PlaneGeometry(30, 30);
  const groundMat = new THREE.MeshStandardMaterial({
    color: COLOR_CLAY_1,
    roughness: 1,
    metalness: 0,
  });
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
      // Materiales clay / maqueta
      const matA = new THREE.MeshStandardMaterial({ color: COLOR_CLAY_1, roughness: 0.9, metalness: 0 });
      const matB = new THREE.MeshStandardMaterial({ color: COLOR_CLAY_2, roughness: 0.9, metalness: 0 });
      let idx = 0;
      fbx.traverse(child => {
        if (child.isMesh) {
          child.material = idx % 2 === 0 ? matA : matB;
          child.castShadow = true;
          child.receiveShadow = true;
          idx++;
        }
      });

      // Centrar y escalar para que quepa en el visor
      const box = new THREE.Box3().setFromObject(fbx);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 6 / maxDim; // normalizar a ~6 unidades
      fbx.scale.setScalar(scale);
      fbx.position.sub(center.multiplyScalar(scale));

      scene.add(fbx);

      // Recalcular posiciones de marcadores relativas a la caja
      const finalBox = new THREE.Box3().setFromObject(fbx);
      const fCenter = finalBox.getCenter(new THREE.Vector3());
      const fSize = finalBox.getSize(new THREE.Vector3());
      // Distribuir los 5 marcadores alrededor del modelo
      ZONAS.planta.pos.set(    fCenter.x - fSize.x * 0.35, finalBox.max.y + 0.3, fCenter.z - fSize.z * 0.15);
      ZONAS.logistica.pos.set( fCenter.x + fSize.x * 0.35, finalBox.max.y + 0.3, fCenter.z - fSize.z * 0.3);
      ZONAS.comercial.pos.set( fCenter.x + fSize.x * 0.3,  finalBox.max.y + 0.3, fCenter.z + fSize.z * 0.35);
      ZONAS.oficina.pos.set(   fCenter.x - fSize.x * 0.1,  finalBox.max.y + 0.3, fCenter.z + fSize.z * 0.3);
      ZONAS.manager.pos.set(   fCenter.x,                   finalBox.max.y + 0.6, fCenter.z);

      // Actualizar luz roja sobre planta
      redBlink.position.copy(ZONAS.planta.pos).add(new THREE.Vector3(0, 0.8, 0));

      // Ajustar cámara al modelo
      controls.target.copy(fCenter);
      const dist = maxDim * scale * 1.8;
      camera.position.set(fCenter.x + dist, fCenter.y + dist * 0.7, fCenter.z + dist);
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
  const panelLateral = contenedor.querySelector('.panel-3d-detalle');

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
          🔒 Oculto por privacidad (n&lt;5). Solo ${respuestas} respuestas de ${personas} personas.
        </div>`;
      panelLateral.innerHTML = html;
      panelLateral.style.display = 'block';
      return;
    }

    // Badge representatividad
    if (hayNoRep) {
      html += `<span class="badge badge-no-representativo" style="margin-bottom:0.6rem;display:inline-block">No representativo</span>`;
    } else {
      html += `<span class="badge badge-aprobada" style="margin-bottom:0.6rem;display:inline-block">Representativo</span>`;
    }

    // Participación global
    html += `
      <div class="panel-3d-stat">
        <span class="text-muted text-small">Tasa de participación</span>
        <strong>${(tasa * 100).toFixed(1)} %</strong>
        <span class="text-muted text-small">${respuestas} / ${personas}</span>
      </div>`;

    // Turnos
    if (filas.length > 0) {
      html += `<div class="panel-3d-turnos"><span class="text-muted text-small" style="font-weight:600;margin-bottom:0.3rem;display:block">Desglose por turno</span>`;
      filas.forEach(f => {
        const turnoLabel = { manana: 'Mañana', tarde: 'Tarde', noche: 'Noche', sin_turno: 'Jornada continua' }[f.turno] || f.turno;
        const pct = ((f.tasa || 0) * 100).toFixed(1);
        const noRep = !f.representativo;
        html += `
          <div class="panel-3d-turno-row">
            <span>${turnoLabel}</span>
            <span style="font-weight:700;${noRep ? 'color:var(--color-damm)' : ''}">${pct} %</span>
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
          html += `<div class="panel-3d-turno-row"><span>${m.pregunta}</span><span class="badge badge-no-representativo" style="font-size:0.7rem">n&lt;5</span></div>`;
        } else {
          html += `<div class="panel-3d-turno-row"><span>${m.pregunta}</span><strong>${m.media.toFixed(1)} / 5</strong><span class="text-muted text-small">n=${m.n}</span></div>`;
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
        html += `<div class="alerta" style="margin-bottom:0.4rem;padding:0.5rem 0.7rem"><div><div class="alerta-tipo" style="font-size:0.65rem">${a.tipo}</div><div class="alerta-mensaje" style="font-size:0.8rem">${a.mensaje}</div></div></div>`;
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
}

