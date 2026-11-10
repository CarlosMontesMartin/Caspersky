# Privacidad y uso responsable

La herramienta trabaja con opiniones de personas sobre su trabajo, así que el anonimato es un requisito de diseño, no una opción. **Todos los datos del repositorio son sintéticos.**

| Principio | Cómo se aplica |
|---|---|
| Datos sintéticos | Generados en `datos_sinteticos/`. No hay ningún dato real de ninguna empresa ni persona. |
| Solo agregados | El dashboard muestra recuentos, porcentajes, medias y temas por grupo, nunca respuestas individuales. |
| Umbral de 5 | Un grupo con menos de 5 respuestas no muestra medias, temas ni comentarios. |
| Supresión complementaria | Si un turno tiene menos de 5 respuestas, también se ocultan las medias de los demás turnos de su sector, y las cifras globales excluyen los grupos pequeños. Así no se puede deducir un dato restando. |
| Anonimización | Antes de guardar un comentario se eliminan nombres, correos, teléfonos y documentos de identidad (castellano, catalán e inglés). |
| Minimización | No se guarda IP, navegador ni hora exacta: solo colectivo, turno, canal, idioma, mes y respuestas. Los identificadores de respuesta son aleatorios. |
| Sin perfiles | La herramienta no evalúa a nadie. «Pregunta a tus datos» rechaza preguntas que buscan identificar personas y el modelo solo recibe datos agregados. |
| Transparencia | Antes de empezar, quien responde ve para qué sirve la encuesta y cómo se tratan sus datos (`contenido/transparencia*.md`). |
| Explicabilidad | Tamaño de muestra, representatividad y límites del análisis siempre visibles. El «antes → después» de un compromiso avisa de que no demuestra una causa. |
| Control humano | RRHH aprueba cada encuesta y firma cada compromiso. La IA propone y la persona decide. |
| Secretos | Las claves del modelo y de Teams solo van en `.env`, excluido de git. La URL de Teams nunca se escribe en los registros y solo se aceptan dominios de Microsoft. |

## Fuera del alcance del prototipo
- **Autenticación:** la aplicación es local. En producción iría detrás del inicio de sesión corporativo (por ejemplo, Microsoft Entra ID) con roles de RRHH.
- **Retención:** no hay borrado automático de respuestas antiguas; en producción se definiría un plazo de conservación.
- **Proveedor del modelo:** en producción, el modelo debería ejecutarse en un entorno con garantías de no reutilización de datos.
