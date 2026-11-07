# Formatos (solo los cambia el Tech Lead)

Valores cerrados:
- colectivo: planta | logistica | comercial | oficina | manager
- turno: manana | tarde | noche | sin_turno
- canal: qr | quiosco | teams
- dimension: bienestar | liderazgo | desarrollo | cultura | entorno | condiciones
- tipo de pregunta: escala_1_5 | opcion | si_no | texto
- estado de encuesta: borrador | aprobada | publicada
- tendencia de tema: nuevo | sube | estable | baja
- tipo de alerta: representatividad | caida | tema_emergente

Formatos (un ejemplo de cada uno en contratos/ejemplos/):
- Necesidad: la escribe RRHH (pantalla 1)
- Encuesta: la genera UPC 1, la edita RRHH y la publica UPC 2
- Respuesta: las sintéticas las crea UPC 1 y las de Typeform UPC 2. tema_real solo en sintéticas
- Plantilla: UAB 2, en contenido/plantilla.json
- Analisis: UPC 2 junta sus métricas con los temas de UPC 1
- Recomendaciones: UPC 1. "seguimiento" es una Necesidad ya rellenada
