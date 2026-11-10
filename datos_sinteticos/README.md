# Datos sintéticos

Datos **100 % ficticios** para desarrollo y demo. Ninguna persona ni dato real de Damm.

## Cómo generar

```bash
python3 datos_sinteticos/generar.py            # busca sola una semilla que cuente la historia del demo
python3 datos_sinteticos/generar.py --seed 42  # semilla fija
```

Solo usa la librería estándar de Python 3. Lee `contenido/plantilla.json` si existe; si no, usa una plantilla por defecto.

## Qué escribe

- `enc_000.json`: encuesta "Pulso de clima general" (colectivo `todos`, `publicada`, periodo `2026-10`). p1–p5 son `escala_1_5` (bienestar, liderazgo, desarrollo, condiciones, entorno) y p6 es `texto` ("¿Qué cambiarías?").
- `respuestas.json`: unas 600–700 `Respuesta` de `enc_000` en los periodos `2026-09` y `2026-10`, con `tema_real`. La respuesta a p6 va en `comentario`, no en `valores`.

## La historia que cuentan

| Qué | Cómo |
|---|---|
| Participación desigual | manager ~60 %, oficina ~45 %, comercial ~30 %, planta mañana/tarde ~25 %, logística ~10 %, **planta noche ~7 %** |
| Condiciones en planta | La media de p4 en planta baja ≥ 0,8 puntos de 2026-09 a 2026-10 |
| Temas | En 2026-10 **descansos** y **turnos** suben y **comunicacion** aparece como tema nuevo; el resto se mantiene estable (regla ±30 % de `calcular_tendencia`) |
| Coherencia | Oficina, comercial y manager nunca hablan de turnos, planta ni almacén |
| Ruido | Faltas, abreviaturas, emojis, muletillas, ~20 % en catalán y 15 % sin comentario |
| Privacidad | ~5 % de comentarios con nombres, correos `@example.com` y teléfonos inventados para demostrar `anonimizar()` |

Los temas de los comentarios se reparten con proporciones exactas por periodo y grupo (planta / resto), así que la historia no depende del azar. El script comprueba la historia al final e imprime un resumen.