# Escucha activa · Reto Damm · UAB The Hack 2026

> **Escoltar millor, actuar abans… i demostrar-ho.**
> Plataforma de escucha activa con IA: crea microencuestas adaptadas a cada colectivo, avisa cuando un grupo no está representado, convierte los comentarios en temas y acciones, y devuelve a la plantilla lo que se ha hecho con sus respuestas ("Dijisteis → Hemos hecho").

**Todos los datos son 100 % sintéticos.** No hay ningún dato real de Damm ni de ninguna persona.

---

## 1. Qué hace

| Paso | Qué hace la plataforma |
|---|---|
| 1. Necesidad | RRHH escribe el objetivo, los sectores (planta, logística, comercial, oficina, managers), el contexto, la duración máxima y qué no se puede preguntar. También puede empezar desde uno de los 4 escenarios del reto. |
| 2. Consulta con IA | La IA propone el título, la introducción y de 3 a 6 preguntas por sector. Con varios sectores hay un **núcleo común** para comparar y **preguntas propias** de cada sector. La encuesta se escribe en el idioma de la pantalla de RRHH (castellano, catalán o inglés). |
| 3. Validación humana | RRHH edita, borra y aprueba. **La IA nunca publica sin aprobación.** Al aprobar, la encuesta se traduce a los otros dos idiomas. |
| 4. Publicación | Enlace, QR general y QR por sector, cartel imprimible, modo quiosco (tablet compartida) y tarjeta de Microsoft Teams. |
| 5. Participación | Formulario móvil en 3 idiomas, botones grandes y caritas. El panel compara las respuestas con la plantilla de cada colectivo y turno y avisa de los grupos no representativos. |
| 6. Análisis | Temas de los comentarios, tendencia frente al periodo anterior, resúmenes, medias y mapa de calor por sector, y límites del análisis. |
| 7. Visualización | Dashboard, maqueta 3D de la fábrica con capas (participación, valoración, alertas y turno de noche), "Pregunta a tus datos" e informe ejecutivo en PDF. |
| 8. Acción | Acciones propuestas con responsable, plazo e indicador. RRHH las convierte en **compromisos** que vuelven a la plantilla en el QR, en el quiosco y en Teams, y se miden con una encuesta de seguimiento. |

Todo funciona **sin IA** (modo de respaldo con reglas) y la pantalla indica cuándo un texto es "Sin IA".

## 2. Arrancar en local

Requisitos: **Python 3.10 o superior**. No hace falta nada más: el backend sirve también el frontend.

```bash
# 1. Clonar el repositorio y entrar en la carpeta
git clone <url-del-repositorio> && cd Caspersky

# 2. Crear tu .env a partir del ejemplo (nunca se sube a git)
cp .env.example .env          # Windows: copy .env.example .env

# 3. Arrancar con un solo comando: crea .venv, instala dependencias y carga los datos sintéticos
./run.sh                      # Linux y Mac (si dice "Permiso denegado": chmod +x run.sh)
run.bat                       # Windows
python run.py                 # cualquier sistema
```

Abre **http://localhost:8000**. Nunca con Live Server ni otro servidor estático, porque las llamadas a la API fallarían.

- Modo desarrollo (se reinicia solo al cambiar el código): `./run.sh --dev` o `run.bat --dev`.
- **Después de cada `git pull`, reinicia el servidor** (Ctrl+C y volver a arrancar) y recarga el navegador con Ctrl+Shift+R.
- Para empezar con los datos limpios: para el servidor, borra `backend/datos/almacen/` y vuelve a arrancar.

## 3. Variables de entorno (`.env`)

| Variable | Para qué | Ejemplo |
|---|---|---|
| `BASE_URL` | Dirección con la que se abre la app; la usan el QR y los botones de Teams | `http://localhost:8000` o `http://192.168.43.20:8000` |
| `LLM_API_KEY` | Clave del modelo de IA. Vacía = modo de respaldo sin IA | *(secreta)* |
| `LLM_BASE_URL` | URL del gateway del modelo | `https://dcc-llm-gw.uab.cat/uabthehack/v1` |
| `LLM_MODEL` | Modelo que se usa | `ornith` |
| `MODO_DEMO` | `1` activa el botón "Simular respuestas" | `1` |
| `TEAMS_WEBHOOK_URL` | URL del workflow de Teams "Post to a channel when a webhook request is received". Vacía = solo vista previa | *(secreta)* |

Comprobación rápida: `http://localhost:8000/salud` debe responder `"llm": true` si la IA está configurada.

**Secretos:** `LLM_API_KEY` y `TEAMS_WEBHOOK_URL` solo van en `.env`, que está en `.gitignore`. Nunca en el código, en capturas ni en las diapositivas.

## 4. Demo con móvil (QR)

El móvil tiene que llegar al portátil:

1. **Plan A:** portátil y móviles en la misma wifi. En `.env`, `BASE_URL=http://<IP del portátil>:8000` (`run.py` la muestra al arrancar).
2. **Plan B (recomendado en eventos):** muchas wifis aíslan a los dispositivos entre sí, y con datos móviles (4G) no se llega a una IP local. Activad el **punto de acceso del móvil** de alguien del equipo, conectad el portátil y poned en `BASE_URL` la IP que os da el hotspot.
3. **Plan C:** un túnel https temporal (por ejemplo, `cloudflared tunnel --url http://localhost:8000`) y su URL en `BASE_URL`. También hace que funcione el botón "Responder" de Teams. **Solo durante la demo:** expone la app a internet.

Después de cambiar `BASE_URL`, reinicia el servidor y vuelve a publicar la encuesta para que el QR se regenere.

## 5. Pruebas

| Comando | Qué comprueba |
|---|---|
| `python -m backend.api.probar_ciclo` (con el servidor arrancado) | El ciclo completo por la API: generar, validar, publicar, responder, analizar, idiomas, Teams… Debe acabar en **TODO BIEN**. Se ejecuta sin clave de IA. |
| `python -m pytest -q backend/datos` | Almacén, métricas y anonimización. |
| `python scripts/comprobar_i18n.py` | Que todas las claves de traducción del frontend existen en `frontend/i18n/` (castellano, catalán e inglés). Debe decir **OK**. |
| `python -m backend.ia.probar_generar` y `python -m backend.ia.probar_analizar` | Robustez de la generación y precisión de la clasificación de comentarios sin IA. |

## 6. Privacidad y uso responsable

| Principio | Cómo se cumple |
|---|---|
| Solo datos sintéticos | Generados en `datos_sinteticos/`. |
| Siempre agregado | El dashboard solo muestra recuentos, porcentajes, medias y temas por grupo. |
| Umbral de 5 | Un grupo con menos de 5 respuestas no muestra medias, temas ni comentarios. |
| Supresión complementaria | Si un turno tiene menos de 5 respuestas, también se ocultan las medias de los otros turnos de su sector, y las cifras globales excluyen los grupos pequeños. Así no se puede deducir restando. |
| Anonimización | Antes de guardar cualquier comentario se borran nombres, correos y teléfonos. |
| Minimización | No se guarda IP, navegador ni hora: solo el colectivo, el turno, el canal, el idioma, la fecha y las respuestas. Los identificadores de respuesta son aleatorios. |
| Sin perfiles | La herramienta no sirve para evaluar a nadie. "Pregunta a tus datos" se niega a identificar personas y solo recibe datos agregados. |
| Transparencia | Quien responde ve antes de empezar para qué sirve y cómo se tratan sus datos (`contenido/transparencia*.md`). |
| Explicabilidad | Tamaño de muestra, representatividad y límites del análisis siempre visibles. El "antes → después" de un compromiso avisa de que no demuestra la causa. |
| Control humano | RRHH aprueba cada encuesta y firma cada compromiso. La IA propone y la persona decide. |
| Acceso | En la demo, la app es local. En Damm iría detrás de Entra ID (inicio de sesión de Microsoft 365). |

## 7. Por qué no Typeform

El reto propone publicar en Typeform. Hemos decidido usar **nuestro propio formulario** porque necesitábamos cosas que el plan gratuito de Typeform no da (10 respuestas al mes) o que nos obligarían a guardar datos en otro sitio: idioma original con traducciones, el canal de respuesta (QR, quiosco o Teams), el control del umbral de 5, la primera pantalla de "Dijisteis → Hemos hecho" y no guardar nada de quien responde.

Publicar es una pieza intercambiable. Con un token, el mismo flujo crearía el formulario en Typeform a través de su API, convirtiendo cada tipo de pregunta en el equivalente de Typeform.

## 8. Estructura del repositorio

```
/
├── README.md                 este documento
├── CONTEXT.md                contexto común del equipo
├── .env.example              variables de entorno sin valores
├── run.py · run.sh · run.bat arranque con un solo comando
├── contratos/                formatos JSON, API, diseño y ejemplos (Tech Lead)
├── backend/
│   ├── reglas.py             límites de las encuestas e idiomas (único sitio)
│   ├── textos.py             frases del backend en castellano, catalán e inglés
│   ├── api/                  FastAPI: rutas, validación, traducciones, Teams, QR y simulación
│   ├── datos/                almacén JSON, métricas, anonimización y tests
│   └── ia/                   generar, analizar, recomendar, traducir, informe y prompts
├── datos_sinteticos/         generador y respuestas sintéticas (2 periodos)
├── frontend/
│   ├── index.html · crear.html · dashboard.html · informe.html   pantallas de RRHH
│   ├── responder.html        formulario para quien responde (móvil y quiosco)
│   ├── js/                   api.js, idioma.js, i18n.js, layout.js, vista3d.js, teams.js…
│   ├── i18n/                 textos en es/ca/en (rrhh_*.json para RRHH; es/ca/en.json para responder)
│   └── vendor/ · public/     Three.js, Chart.js y la maqueta 3D (sin depender de internet)
├── contenido/                reglas por colectivo, plantilla, transparencia y escenarios
├── scripts/                  comprobar_i18n.py
└── pitch/                    guion y estructura de las diapositivas
```

## 9. Checklist de entrega (guía del reto)

- [ ] El flujo funciona de la necesidad a la recomendación (y al compromiso).
- [ ] Hay validación humana antes de publicar.
- [ ] Los datos son 100 % sintéticos.
- [ ] Hay umbral mínimo (n ≥ 5, también frente a restas) y solo resultados agregados.
- [ ] No hay ningún token en el código, el historial ni las diapositivas.
- [ ] Están el README y el `.env.example`.
- [ ] Hay vídeo o capturas de respaldo de la demo.
