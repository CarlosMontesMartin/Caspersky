# Guía de diseño · herramienta profesional

Documento del Tech Lead para `frontend/`. Pegadlo junto a `CONTEXT.md` en cada prompt de diseño.
Objetivo: que parezca una herramienta de People Analytics que una empresa usaría, no una web de presentación.

## 1. Principios
1. **Sobriedad.** Fondo claro, un solo color de acento, nada decorativo.
2. **Primero el dato.** Cada pantalla responde a una pregunta y lo importante está arriba.
3. **Menos es más.** Si algo no ayuda a decidir, se quita o se pliega.
4. **Consistencia.** Mismos componentes, tamaños y espaciados en todas las páginas.

## 2. Qué eliminar ya
- Tipografías serif y cursivas (Playfair Display) y la importación de Google Fonts.
- Botones y títulos en MAYÚSCULAS con espaciado entre letras.
- Emojis en las pantallas de RRHH (pestañas, botones, títulos).
- Imágenes de cabecera (`public/cabecera-*.jpg`, casi 5 MB).
- Cajas de alerta grandes y rojas, una debajo de otra.
- Textos con exclamaciones o tono de anuncio ("¡La encuesta ya está activa!").

## 3. Tokens (`css/estilos.css`, en `:root`)

```css
:root {
  /* Tipografía del sistema: profesional y sin depender de internet */
  --fuente: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --t-xs: 12px; --t-sm: 13px; --t-md: 14px; --t-lg: 16px; --t-xl: 20px; --t-2xl: 24px;
  --peso-normal: 400; --peso-medio: 500; --peso-fuerte: 600;

  /* Color */
  --fondo: #F7F7F8;  --superficie: #FFFFFF;  --borde: #E4E4E7;
  --texto: #18181B;  --texto-2: #52525B;     --texto-3: #A1A1AA;
  --acento: #B4121B; --acento-hover: #961017; /* rojo Damm: solo botón principal y marca */
  --ok: #15803D;     --ok-fondo: #F0FDF4;
  --aviso: #B45309;  --aviso-fondo: #FFFBEB;
  --critico: #B91C1C; --critico-fondo: #FEF2F2;

  /* Espaciado (múltiplos de 4) y forma */
  --e1: 4px; --e2: 8px; --e3: 12px; --e4: 16px; --e5: 24px; --e6: 32px;
  --radio: 6px;
  --sombra: 0 1px 2px rgba(0,0,0,.04);
}
body { font-family: var(--fuente); font-size: var(--t-md); color: var(--texto); background: var(--fondo); }
.num { font-variant-numeric: tabular-nums; }
```

Reglas: títulos de página en 24 px y peso 600; títulos de tarjeta en 16 px y peso 600; texto en 14 px;
etiquetas y notas en 12–13 px con `--texto-2`. Todo en minúsculas normales (solo la primera letra en mayúscula).

## 4. Componentes
| Componente | Especificación |
|---|---|
| Botón principal | Fondo `--acento`, texto blanco, 36 px de alto, radio 6 px, peso 500. Uno por pantalla como máximo. |
| Botón secundario | Fondo blanco, borde `--borde`, texto `--texto`. |
| Botón de texto | Sin borde, color `--texto-2`; para acciones menores ("Borrar", "Cancelar"). |
| Tarjeta | Fondo `--superficie`, borde 1 px `--borde`, radio 6 px, padding 16–24 px, `--sombra`. |
| KPI | Etiqueta 13 px `--texto-2` encima, número 24 px peso 600 `.num`, nota 12 px debajo. |
| Badge | 12 px, padding 2×8 px, radio 4 px, fondo tintado: borrador gris, aprobada ámbar, publicada verde, no representativo rojo. |
| Tabla | Filas de 40 px, cabecera 12 px `--texto-2` sin mayúsculas, separadores de 1 px, números alineados a la derecha. |
| Alertas | **Una sola tarjeta** "Alertas (5)" con una línea por alerta: punto de color (rojo representatividad, ámbar caída) + texto. Máximo 5 visibles y "Ver todas". |
| Iconos | SVG de línea de 16 px (por ejemplo, Lucide copiados en línea) o ninguno. Nunca emojis. |
| Estados vacíos | Una frase gris y, si aplica, la acción para salir de ese estado. |
| Carga | Texto "Cargando…" o un esqueleto gris; nunca la pantalla en blanco. |

## 5. Estructura común
- **Barra lateral fija** de 220 px: "Damm · Escucha activa" arriba; enlaces "Encuestas" y "Nueva encuesta".
- **Contenido** con ancho máximo de 1200 px y padding de 32 px.
- **Cabecera de página:** título a la izquierda y acciones a la derecha. Nada más.

## 6. Páginas

### `index.html` · Encuestas
Título "Encuestas" y botón principal "Nueva encuesta". Tabla: Título (con el id debajo en gris),
Colectivo, Estado (badge), Respuestas, Periodo y la acción "Abrir" a la derecha. Sin textos explicativos.

### `crear.html` · Nueva encuesta
- Indicador de pasos arriba: **1 Necesidad · 2 Revisión · 3 Publicación**. Se muestra **un paso cada vez**, no los tres apilados.
- Paso 1: selector "Empezar desde un escenario" arriba; formulario a 2 columnas; botón "Generar propuesta".
- Paso 2: una fila por pregunta (número, texto editable, tipo como badge, botón de texto "Borrar"); arriba,
  título e introducción editables y una nota discreta: "Propuesta generada por IA. Revísala antes de aprobar".
  Acciones: "Guardar borrador" (secundario) y "Aprobar" (principal).
- Paso 3: QR a la izquierda; a la derecha, el enlace con "Copiar", "Imprimir cartel", "Abrir modo quiosco" e "Ir al análisis".

### `dashboard.html` · Análisis
Pestañas **Resumen** (por defecto) e **Instalaciones** (las vistas 3D actuales). En Resumen, en este orden:
1. Cabecera: título, badges de colectivo y estado; a la derecha "Actualizar", "Compartir" (enlace y QR)
   y, si `modo_demo`, "Simular respuestas".
2. Fila de 4 KPIs: Respuestas · Participación global (%) · Segmentos no representativos · Periodo actual frente al anterior.
3. Tarjeta de alertas (formato del punto 4).
4. Dos columnas: **Participación** (tabla compacta con una barra fina por fila) y **Temas** (ranking: nombre,
   nº de comentarios, flecha ↑ si sube, etiqueta "Nuevo"; al pulsar se despliega el resumen).
5. **Valoraciones:** tabla de calor con las preguntas (por su texto, no "p1") en filas, los colectivos en columnas
   y la media en cada celda, coloreada de rojo (1) a verde (5). Celda vacía con "—" si n < 5.
6. **Recomendaciones:** tarjetas con título, motivo y la etiqueta "Propuesta", y el botón "Crear encuesta de seguimiento".
7. **Límites del análisis:** texto de 12 px al pie, sin caja.
Se actualiza solo cada 10 s mientras la página está abierta.

### `responder.html` · Móvil y quiosco
- Fondo blanco, una columna, "Damm" en texto arriba, barra de progreso "Pregunta 2 de 5".
- Transparencia en 2 líneas y un enlace "Más información" que despliega el resto.
- Escala 1–5: cinco botones grandes numerados, con "Muy mal" y "Muy bien" en los extremos (en quiosco pueden llevar caritas SVG monocromas).
- Botón principal "Enviar", desactivado hasta contestar las preguntas obligatorias.
- Pantalla final: "Gracias. Tu respuesta se ha registrado de forma anónima."

## 7. Textos
- Tono profesional y directo, sin exclamaciones.
- Números con coma decimal y % pegado con espacio fino: "22,8 %".
- Nombres legibles siempre: "Turno de noche", "Logística", "Carga de trabajo". Nunca `p4`, `sin_turno` ni `carga_trabajo`.
