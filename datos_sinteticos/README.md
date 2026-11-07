# Datos sintéticos

Respuestas de encuesta **100 % ficticias** para desarrollo y demo.
No contienen nombres, correos, teléfonos ni ningún dato real.

## Cómo generar

```bash
python3 datos_sinteticos/generar.py            # seed=42, salida por defecto
python3 datos_sinteticos/generar.py --seed 99  # otra semilla
python3 datos_sinteticos/generar.py --salida /tmp/test.json
```

Solo usa la librería estándar de Python 3 (sin dependencias).

## Qué genera

- `respuestas.json`: array de ~600 objetos `Respuesta` para la encuesta `enc_001`.
- Dos periodos: `2026-10` y `2026-11`.
- 9 segmentos (colectivo × turno) con plantilla y tasas de participación distintas.

## Sesgos introducidos a propósito

| Sesgo | Descripción |
|-------|-------------|
| **Participación desigual** | Planta/noche responde ~6 %, oficina ~40 %, manager ~50 %. |
| **Temas por periodo** | En nov, `descansos` sube (×2 en planta/noche y planta/tarde), `comunicacion_cambio` aparece como nuevo y `herramientas` baja. |
| **Notas sesgadas** | Cada colectivo tiene media base distinta (planta 3.0, manager 3.8…). Se resta 0.8 si el tema es descansos o carga_trabajo, y 0.5 más a planta/noche en noviembre. |
| **Canal** | Planta y logística: 60 % QR / 40 % quiosco. El resto: 80 % Teams / 20 % QR. |
| **Ruido en comentarios** | 60 % con faltas de ortografía, abreviaturas y emojis. ~20 % en catalán. |
| **Comentarios vacíos** | 15 % de respuestas sin comentario (simulan gente que no escribe nada). |
| **Datos ficticios** | ~3 % incluyen un nombre inventado, correo `@example.com` o teléfono falso para probar `anonimizar()`. |
| **Seguridad** | En noviembre, el tema `seguridad` casi solo aparece en planta y logística. |
