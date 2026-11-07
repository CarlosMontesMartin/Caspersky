# Vista 3D del dashboard (UAB 1)

Trabaja SOLO dentro de frontend/. No toques js/api.js, crear.html, index.html, responder.html
ni la vista analítica del dashboard: ya funcionan y cumplen contratos/modulos.md.
Respeta contratos/modulos.md: HTML + CSS + JavaScript SIN compilación. Nada de React, npm,
Vite, drei ni bundlers.

## 1. Three.js sin compilación y sin depender de internet
- Descarga three (versión 0.160.0) dentro del repo: frontend/vendor/three/three.module.js,
  frontend/vendor/three/addons/loaders/FBXLoader.js y
  frontend/vendor/three/addons/controls/OrbitControls.js, más los archivos que estos
  importen (por ejemplo addons/curves/NURBSCurve.js, addons/curves/NURBSUtils.js y
  addons/libs/fflate.module.js). El demo debe funcionar sin internet.
- En dashboard.html, un import map:
  { "imports": { "three": "/vendor/three/three.module.js",
                 "three/addons/": "/vendor/three/addons/" } }
- Todo el código 3D va en un archivo nuevo: frontend/js/vista3d.js (módulo ES).
  Exporta una función: iniciarVista3D(contenedor, analisis).

## 2. Cargar el modelo
- Ruta: /public/fabrica.fbx (está en frontend/public/fabrica.fbx).
- FBXLoader. Al cargar, recorre las mallas (traverse) y sustituye cada material por un
  MeshStandardMaterial de color sólido estilo maqueta/clay: tonos blanco roto #F5F1EA y
  arena #E8DFD0, roughness 0.9, sin texturas. Activa sombras (castShadow / receiveShadow).
- Centra y escala el modelo automáticamente con su Box3 para que quepa en el contenedor.
- OrbitControls con rotación 360°, zoom con límites (minDistance / maxDistance), damping
  activado y sin poder pasar por debajo del suelo (maxPolarAngle ≈ 85°).
- Muestra "Cargando maqueta…" mientras carga. Si falla la carga, muestra un aviso
  discreto y vuelve automáticamente a la vista analítica. El dashboard nunca se rompe.

## 3. Modo día / modo noche
Interruptor "Día / Noche" encima del visor.
- Día: HemisphereLight cálida + DirectionalLight tipo sol con sombras, fondo crema #FAF7F2.
- Noche: luces azules tenues (#2B3A67), fondo azul oscuro #141B2D, y una PointLight roja
  (#B5121B) que parpadea suavemente sobre la zona de Planta SOLO si en
  analisis.participacion la fila planta / noche tiene representativo = false.
  Nada inventado: todo sale de los datos.

## 4. Zonas clicables (5 colectivos)
El modelo no tiene departamentos, así que se usan puntos de interés:
- Constante ZONAS en vista3d.js con una posición x, y, z para cada colectivo:
  planta (Planta de producción), logistica (Logística), comercial (Comercial),
  oficina (Oficina) y manager (Dirección). Pon posiciones iniciales razonables según la
  caja del modelo y deja un comentario claro para ajustarlas a mano.
- En cada zona, un marcador: esfera pequeña + etiqueta HTML (CSS2DRenderer o un div
  posicionado proyectando la posición 3D). Color del marcador según la participación
  del colectivo: oscuro si todas sus filas son representativas, rojo Damm si alguna no lo es,
  gris si el colectivo no aparece en el análisis.
- Hover: el marcador crece. Clic: panel lateral (estilo .card de css/estilos.css) con,
  solo de ese colectivo y usando los campos exactos del contrato Analisis:
  filas de participacion (turno, respuestas, personas, tasa en %, representativo),
  medias de ese colectivo y las alertas cuyo mensaje lo mencione.
- PRIVACIDAD: una fila con respuestas < 5 muestra solo su recuento, con la etiqueta
  "Oculto por privacidad (n<5)". Nunca respuestas individuales.
- Si la encuesta es de un solo colectivo, los demás marcadores van atenuados.

## 5. Integración en dashboard.html
- Selector "Vista analítica / Maqueta 3D" arriba, debajo de las alertas. Por defecto,
  la analítica.
- La maqueta solo se crea la primera vez que se elige (carga diferida) y reutiliza el
  mismo objeto analisis que ya ha cargado la página: no hagas peticiones nuevas.
- Visor de 520 px de alto en portátil y 360 px en móvil, con borde fino y radio como .card.
- Al cambiar de vista o salir, detén el bucle de animación.
- Estilos nuevos en css/estilos.css, con las variables existentes.

## 6. Comprobación
Con python frontend/servir.py, abre /dashboard.html?id=enc_000: cambia a Maqueta 3D, rota,
haz zoom, cambia a Noche (debe verse la luz roja sobre Planta porque el turno de noche no
es representativo) y haz clic en las 5 zonas. Comprueba que la vista analítica sigue igual
y que no hay errores en la consola. Commit solo con: git add frontend
