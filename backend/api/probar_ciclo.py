"""Recorre el ciclo completo por la API y dice OK o FALLO en cada comprobación · UPC 2 (v2 3.6, v3 3.5, v4 P1).

    python -m backend.api.probar_ciclo                       # sin servidor, datos temporales
    python -m backend.api.probar_ciclo --url http://localhost:8000   # contra un servidor arrancado

Sin --url arranca la API dentro del propio script con un almacén temporal:
no hace falta tener el servidor encendido y no ensucia backend/datos/almacen/.
Con --url prueba el servidor de verdad (necesita MODO_DEMO=1 en su .env).
Sale con código 1 si algo falla. Tarda unos segundos: úsalo después de cada cambio.

Siempre se ejecuta SIN clave de IA (LLM_API_KEY vacío) para no gastar ni saturar
la API del evento: todo tiene que pasar con el modo de respaldo. Los caminos con
IA se prueban a mano, una vez por función.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

PLANTILLA_PRUEBA = [
    {"colectivo": "planta", "turno": "manana", "personas": 60},
    {"colectivo": "planta", "turno": "tarde", "personas": 60},
    {"colectivo": "planta", "turno": "noche", "personas": 120},
    {"colectivo": "logistica", "turno": "sin_turno", "personas": 90},
    {"colectivo": "comercial", "turno": "sin_turno", "personas": 40},
    {"colectivo": "oficina", "turno": "sin_turno", "personas": 50},
    {"colectivo": "manager", "turno": "sin_turno", "personas": 15},
]
NECESIDAD_A = {"objetivo": "Saber cómo afecta el nuevo sistema de turnos", "colectivo": "planta",
               "contexto": "Cambio de turnos desde octubre", "duracion_max_seg": 120,
               "temas_prohibidos": ["salario"]}
DATO_PERSONAL = "Soy Ramón, llamadme al 612345678"
TENDENCIAS = {"nuevo", "sube", "estable", "baja"}
NECESIDAD_MULTI = {"objetivo": "Saber cómo afecta el cambio de turnos a la coordinación entre áreas",
                   "colectivos": ["planta", "logistica"], "contexto": "Cambio de turnos desde octubre",
                   "duracion_max_seg": 120, "temas_prohibidos": ["salario"]}
CAMPOS_ANALISIS_V2 = {"encuesta_id", "titulo", "n_respuestas", "periodo_actual", "periodo_anterior", "participacion",
                      "medias", "alertas", "limites", "temas", "n_anterior", "n_simuladas", "colectivos",
                      "participacion_global", "medias_anterior", "preguntas", "distribuciones", "zonas",
                      "lectura", "estado_ia"}
CAMPOS_ESTADO_IA = {"llm", "pendientes", "comentarios_total", "comentarios_ia", "listo", "origen_recomendaciones",
                    "resumenes_listos", "recomendaciones_listas"}
NOMBRES_INVENTADOS = ("Ramón", "Ramon", "Jordi", "Montse", "Pepe", "pepe")


class Resultado:
    def __init__(self):
        self.ok = self.fallos = self.omitidos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> bool:
        if condicion:
            self.ok += 1
            print(f"  OK      {nombre}")
        else:
            self.fallos += 1
            print(f"  FALLO   {nombre}" + (f"  → {detalle}" if detalle else ""))
        return condicion

    def omitir(self, nombre: str, motivo: str) -> None:
        self.omitidos += 1
        print(f"  OMITIDO {nombre}  ({motivo})")

    def seccion(self, titulo: str) -> None:
        print(f"\n{titulo}")


def recorrer(c, res: Resultado, almacen=None, local: bool = False) -> None:
    def pedir(metodo, ruta, **kw):
        r = getattr(c, metodo)(ruta, **kw)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    res.seccion("1. Arranque")
    estado, salud = pedir("get", "/salud")
    res.comprobar("GET /salud responde ok", estado == 200 and salud.get("ok") is True, f"{estado} {salud}")
    if not res.comprobar("MODO_DEMO activo", bool(salud and salud.get("modo_demo")),
                         "pon MODO_DEMO=1 en el .env del servidor"):
        return
    print(f"          (IA real: {'sí' if salud.get('llm') else 'no, modo de respaldo'})")
    estado, escenarios = pedir("get", "/escenarios")
    res.comprobar("GET /escenarios devuelve los escenarios", estado == 200 and len(escenarios or []) >= 1)
    necesidad = next((e["necesidad"] for e in escenarios or [] if e.get("id") == "A" and e.get("necesidad")),
                     NECESIDAD_A)

    res.seccion("2. Crear, editar, aprobar y publicar (escenario A)")
    estado, enc = pedir("post", "/encuestas/generar", json=necesidad)
    if not res.comprobar("Generar encuesta", estado == 200 and enc.get("estado") == "borrador", f"{estado} {enc}"):
        return
    eid = enc["id"]
    res.comprobar("Tiene entre 1 y 6 preguntas", 1 <= len(enc.get("preguntas", [])) <= 6)
    res.comprobar("Colectivo planta", enc.get("colectivo") == "planta")
    estado, _ = pedir("post", "/encuestas/generar", json={"colectivo": "inventado"})
    res.comprobar("Necesidad no válida → 422", estado == 422, f"devolvió {estado}")
    estado, _ = pedir("post", f"/encuestas/{eid}/publicar")
    res.comprobar("Publicar sin aprobar → 409 (control humano)", estado == 409, f"devolvió {estado}")

    enc["preguntas"][0]["texto"] = enc["preguntas"][0]["texto"] + " (editada por RRHH)"
    estado, editada = pedir("put", f"/encuestas/{eid}", json=enc)
    res.comprobar("Editar en borrador", estado == 200 and "(editada por RRHH)" in editada["preguntas"][0]["texto"])
    estado, aprobada = pedir("post", f"/encuestas/{eid}/aprobar")
    res.comprobar("Aprobar", estado == 200 and aprobada.get("estado") == "aprobada", f"{estado} {aprobada}")
    estado, pub = pedir("post", f"/encuestas/{eid}/publicar")
    res.comprobar("Publicar", estado == 200 and pub.get("estado") == "publicada", f"{estado} {pub}")
    res.comprobar("URL apunta a /responder/", f"/responder/{eid}" in (pub.get("url") or ""), pub.get("url"))
    res.comprobar("QR como imagen PNG", str(pub.get("qr", "")).startswith("data:image/png;base64,"))
    estado, _ = pedir("put", f"/encuestas/{eid}", json=enc)
    res.comprobar("Editar publicada → 409", estado == 409, f"devolvió {estado}")

    res.seccion("3. Responder")
    estado, publica = pedir("get", f"/publico/encuestas/{eid}")
    res.comprobar("Encuesta pública con turnos de planta", estado == 200 and
                  publica.get("turnos") == ["manana", "tarde", "noche"], f"{estado} {publica and publica.get('turnos')}")
    res.comprobar("La encuesta pública no expone datos internos",
                  estado == 200 and not {"estado", "url", "qr"} & set(publica))
    preguntas = publica.get("preguntas", []) if publica else []
    escala = next((p["id"] for p in preguntas if p["tipo"] == "escala_1_5"), None)
    texto = next((p["id"] for p in preguntas if p["tipo"] == "texto"), None)

    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas", json={"turno": "noche", "valores": {}})
    res.comprobar("Respuesta vacía → 422", estado == 422, f"devolvió {estado}")
    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas", json={"turno": "sin_turno", "valores": {}})
    res.comprobar("Turno no válido para planta → 422", estado == 422, f"devolvió {estado}")
    if escala:
        estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas", json={"turno": "noche", "valores": {escala: 9}})
        res.comprobar("Valor de escala fuera de 1–5 → 422", estado == 422, f"devolvió {estado}")

    entrada = {"turno": "noche", "canal": "quiosco", "valores": {}, "comentario": DATO_PERSONAL}
    if escala:
        entrada["valores"][escala] = 2
    if texto:
        entrada["valores"][texto] = "el descanso es corto, escribid a pepe@gmail.com"
    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas", json=entrada)
    res.comprobar("Respuesta válida guardada", estado == 200, f"devolvió {estado}")
    if local and almacen is not None:
        guardada = almacen.leer_respuestas(eid)[-1]
        res.comprobar("Comentario anonimizado al guardar",
                      "612345678" not in guardada["comentario"] and "[telefono]" in guardada["comentario"],
                      guardada["comentario"])
        res.comprobar("Texto libre guardado solo en comentario",
                      not texto or (texto not in guardada["valores"] and "[correo]" in guardada["comentario"]),
                      json.dumps(guardada, ensure_ascii=False))
        res.comprobar("No se guarda nada fuera del contrato",
                      set(guardada) <= {"id", "encuesta_id", "fecha", "periodo", "colectivo", "centro_tipo",
                                        "turno", "canal", "idioma", "valores", "comentario"}, sorted(guardada))
    else:
        res.omitir("Comentario anonimizado al guardar", "solo sin --url")

    res.seccion("4. Simular respuestas (modo demo)")
    estado, sim = pedir("post", f"/encuestas/{eid}/simular", json={"n": 40, "semilla": 7})
    res.comprobar("Simular 40 respuestas por periodo", estado == 200 and sim.get("simuladas") == 80, f"{estado} {sim}")
    if local:
        os.environ["MODO_DEMO"] = "0"
        estado, _ = pedir("post", f"/encuestas/{eid}/simular", json={"n": 5})
        res.comprobar("Simular sin MODO_DEMO → 403", estado == 403, f"devolvió {estado}")
        os.environ["MODO_DEMO"] = "1"

    res.seccion("5. Análisis")
    estado, a = pedir("get", f"/encuestas/{eid}/analisis")
    if not res.comprobar("GET analisis", estado == 200, f"{estado} {a}"):
        return
    faltan = CAMPOS_ANALISIS_V2 - set(a)
    res.comprobar("El análisis trae todos los campos v2", not faltan, f"faltan {sorted(faltan)}")
    res.comprobar("Cuenta las respuestas del periodo actual", a["n_respuestas"] >= 40, f"n={a['n_respuestas']}")
    res.comprobar("Hay periodo anterior para comparar", a.get("periodo_anterior") is not None)
    noche = next((f for f in a["participacion"] if f["colectivo"] == "planta" and f["turno"] == "noche"), None)
    if res.comprobar("Participación por turno frente a plantilla", noche is not None,
                     "participación vacía: falta contenido/plantilla.json"):
        res.comprobar("Turno de noche marcado como no representativo", noche["representativo"] is False, str(noche))
    alertas = a.get("alertas", [])
    res.comprobar("Alerta de representatividad del turno de noche",
                  any(x["tipo"] == "representatividad" and "noche" in x["mensaje"] for x in alertas),
                  json.dumps(alertas, ensure_ascii=False))
    condiciones = [p["id"] for p in preguntas if p["tipo"] == "escala_1_5" and p.get("dimension") == "condiciones"]
    if condiciones:
        res.comprobar("Alerta de caída en condiciones", any(x["tipo"] == "caida" for x in alertas),
                      json.dumps(a.get("medias"), ensure_ascii=False))
    else:
        res.omitir("Alerta de caída en condiciones", "la encuesta no tiene escala de condiciones")
    res.comprobar("Ninguna media con menos de 5 respuestas", all(m["n"] >= 5 for m in a.get("medias", [])))
    res.comprobar("Hay límites del análisis", len(a.get("limites", [])) > 0)
    temas = a.get("temas", [])
    if temas:
        res.comprobar("Ningún tema con menos de 5 comentarios", all(t["n"] >= 5 for t in temas))
        res.comprobar("Tendencias válidas", all(t.get("tendencia") in TENDENCIAS for t in temas))
        nombres = {t["tema"] for t in temas}
        res.comprobar("Aparecen descansos o turnos", bool({"descansos", "turnos"} & nombres), str(sorted(nombres)))
    else:
        res.omitir("Temas", "vacíos: backend/ia/ aún no está o falla (modo de respaldo)")
    texto_analisis = json.dumps(a, ensure_ascii=False)
    res.comprobar("El análisis no expone datos personales",
                  "612345678" not in texto_analisis and "Ramón" not in texto_analisis)

    res.seccion("6. Recomendaciones y seguimiento")
    estado, rec = pedir("get", f"/encuestas/{eid}/recomendaciones")
    if res.comprobar("GET recomendaciones", estado == 200, f"{estado} {rec}"):
        acciones = rec.get("acciones", [])
        res.comprobar("Tiene acciones con título y motivo",
                      len(acciones) >= 1 and all(x.get("titulo") and x.get("motivo") for x in acciones))
        res.comprobar("Acciones con responsable, plazo e indicador",
                      all(x.get("responsable") and x.get("plazo") and x.get("indicador") for x in acciones))
        res.comprobar("Origen de las recomendaciones (ia | reglas)", rec.get("origen") in ("ia", "reglas"))
        seg = rec.get("seguimiento") or {}
        res.comprobar("Propone encuesta de seguimiento para planta",
                      "planta" in (seg.get("colectivos") or [seg.get("colectivo")]), str(seg))
        estado, _ = pedir("post", "/encuestas/generar", json=seg)
        res.comprobar("El seguimiento se puede generar (cierra el ciclo)", estado == 200, f"devolvió {estado}")

    recorrer_multisector(c, res, pedir)
    recorrer_v3(c, res, pedir, almacen, local)
    recorrer_v4(c, res, pedir, eid, local)

    res.seccion("13. Histórico enc_000 (escenario C)")
    estado, lista = pedir("get", "/encuestas")
    if any(e["id"] == "enc_000" for e in lista or []):
        estado, a0 = pedir("get", "/encuestas/enc_000/analisis")
        res.comprobar("Análisis de enc_000", estado == 200 and a0.get("n_respuestas", 0) > 0, f"{estado}")
    else:
        res.omitir("Análisis de enc_000", "UPC 1 aún no ha subido datos_sinteticos/enc_000.json")


def recorrer_multisector(c, res: Resultado, pedir) -> None:
    res.seccion("7. Encuesta multisector (planta + logística)")
    estado, enc = pedir("post", "/encuestas/generar", json=NECESIDAD_MULTI)
    if not res.comprobar("Generar con colectivos [planta, logistica]", estado == 200, f"{estado} {enc}"):
        return
    eid, nucleo, propias = enc["id"], enc.get("preguntas", []), enc.get("preguntas_por_colectivo") or {}
    res.comprobar("colectivo == \"varios\" y colectivos en orden",
                  enc.get("colectivo") == "varios" and enc.get("colectivos") == ["planta", "logistica"],
                  f"{enc.get('colectivo')} {enc.get('colectivos')}")
    res.comprobar("origen ia | respaldo", enc.get("origen") in ("ia", "respaldo"), str(enc.get("origen")))
    res.comprobar("Núcleo común de 1–3 preguntas", 1 <= len(nucleo) <= 3, f"{len(nucleo)}")
    res.comprobar("Cada sector con 1–3 preguntas propias",
                  set(propias) == {"planta", "logistica"} and all(1 <= len(v) <= 3 for v in propias.values()),
                  json.dumps({k: len(v) for k, v in propias.items()}))
    res.comprobar("Ninguna pregunta propia es de texto",
                  all(p["tipo"] != "texto" for v in propias.values() for p in v))
    ids = [p["id"] for p in nucleo] + [p["id"] for v in propias.values() for p in v]
    res.comprobar("Ids únicos en toda la encuesta", len(ids) == len(set(ids)), str(ids))
    res.comprobar("3–6 preguntas por sector", all(3 <= len(nucleo) + len(v) <= 6 for v in propias.values()))
    res.comprobar("tiempo_por_colectivo de cada sector",
                  set(enc.get("tiempo_por_colectivo") or {}) == {"planta", "logistica"})

    estado, _ = pedir("post", f"/encuestas/{eid}/aprobar")
    estado, pub = pedir("post", f"/encuestas/{eid}/publicar")
    res.comprobar("Aprobar y publicar", estado == 200 and pub.get("estado") == "publicada", f"{estado}")
    estado, publica = pedir("get", f"/publico/encuestas/{eid}")
    res.comprobar("Encuesta pública con turnos por colectivo",
                  estado == 200 and publica.get("turnos_por_colectivo") == {"planta": ["manana", "tarde", "noche"],
                                                                             "logistica": ["sin_turno"]},
                  str(publica and publica.get("turnos_por_colectivo")))
    res.comprobar("Encuesta pública con preguntas_por_colectivo",
                  estado == 200 and set(publica.get("preguntas_por_colectivo", {})) == {"planta", "logistica"})

    escala = next((p["id"] for p in nucleo if p["tipo"] == "escala_1_5"), None)
    de_logistica = propias.get("logistica", [{}])[0].get("id")
    ruta = f"/publico/encuestas/{eid}/respuestas"
    estado, _ = pedir("post", ruta, json={"turno": "noche", "valores": {escala: 3}})
    res.comprobar("Responder sin colectivo → 422", estado == 422, f"devolvió {estado}")
    estado, _ = pedir("post", ruta, json={"colectivo": "comercial", "turno": "sin_turno", "valores": {escala: 3}})
    res.comprobar("Responder con un colectivo que no es de la encuesta → 422", estado == 422, f"devolvió {estado}")
    estado, _ = pedir("post", ruta, json={"colectivo": "planta", "turno": "noche",
                                          "valores": {escala: 3, de_logistica: 3 if propias["logistica"][0]["tipo"] == "escala_1_5" else "si"}})
    res.comprobar("Planta respondiendo una pregunta de logística → 422", estado == 422, f"devolvió {estado}")
    estado, _ = pedir("post", ruta, json={"colectivo": "logistica", "turno": "sin_turno", "valores": {escala: 4}})
    res.comprobar("Respuesta válida de logística", estado == 200, f"devolvió {estado}")

    estado, sim = pedir("post", f"/encuestas/{eid}/simular", json={"n": 40, "semilla": 3})
    res.comprobar("Simular respuestas multisector", estado == 200 and sim.get("simuladas") == 80, f"{estado} {sim}")

    res.seccion("8. Análisis multisector, maqueta y pregunta a tus datos")
    estado, a = pedir("get", f"/encuestas/{eid}/analisis")
    if not res.comprobar("GET analisis", estado == 200, f"{estado}"):
        return
    faltan = CAMPOS_ANALISIS_V2 - set(a)
    res.comprobar("El análisis trae todos los campos v2", not faltan, f"faltan {sorted(faltan)}")
    zonas = a.get("zonas", [])
    res.comprobar("Una zona por sector (2)", [z["colectivo"] for z in zonas] == ["planta", "logistica"],
                  str([z.get("colectivo") for z in zonas]))
    res.comprobar("Hay respuestas de los dos sectores", all(z["respuestas"] > 0 for z in zonas),
                  str([(z["colectivo"], z["respuestas"]) for z in zonas]))
    res.comprobar("Zonas con < 5 respuestas: media null y sin temas",
                  all(z["media"] is None and z["temas"] == [] for z in zonas if z["respuestas"] < 5))
    res.comprobar("Turnos con < 5 respuestas: media null",
                  all(t["media"] is None for z in zonas for t in z.get("turnos", []) if t["respuestas"] < 5))
    res.comprobar("Distribuciones sin n < 5", all(d["n"] >= 5 and len(d["conteos"]) == 5 for d in a["distribuciones"]))
    res.comprobar("Hay distribuciones de escalas", len(a["distribuciones"]) >= 1)
    res.comprobar("Preguntas con ámbito común y por sector",
                  {p["ambito"] for p in a["preguntas"]} >= {"comun", "planta", "logistica"})
    res.comprobar("estado_ia completo", CAMPOS_ESTADO_IA <= set(a.get("estado_ia", {})), str(a.get("estado_ia")))
    res.comprobar("Lectura ejecutiva no vacía", bool(str(a.get("lectura", "")).strip()))
    res.comprobar("Alertas con colectivo", all(x.get("colectivo") for x in a["alertas"]))
    res.comprobar("Temas con n_anterior, pct y pct_anterior",
                  all({"n_anterior", "pct", "pct_anterior"} <= set(t) for t in a["temas"]))
    res.comprobar("El análisis no expone datos personales",
                  not any(nombre in json.dumps(a, ensure_ascii=False) for nombre in NOMBRES_INVENTADOS))

    estado, r = pedir("post", f"/encuestas/{eid}/preguntar", json={"pregunta": "¿Quién se queja más del turno de noche?"})
    res.comprobar("Preguntar «¿quién…?» → origen reglas", estado == 200 and r.get("origen") == "reglas", f"{estado} {r}")
    res.comprobar("La respuesta no menciona a nadie",
                  estado == 200 and not any(nombre in r.get("respuesta", "") for nombre in NOMBRES_INVENTADOS))
    estado, r = pedir("post", f"/encuestas/{eid}/preguntar", json={"pregunta": "¿Qué sector está peor y por qué?"})
    res.comprobar("Preguntar devuelve respuesta, cifras, confianza y origen",
                  estado == 200 and {"respuesta", "cifras", "confianza", "origen"} <= set(r)
                  and r["confianza"] in ("alta", "media", "baja"), f"{estado} {r}")
    estado, rec = pedir("get", f"/encuestas/{eid}/recomendaciones")
    seg = (rec or {}).get("seguimiento") or {}
    res.comprobar("Recomendaciones con lectura y seguimiento con colectivos",
                  estado == 200 and bool(rec.get("lectura")) and isinstance(seg.get("colectivos"), list), f"{estado}")


def recorrer_v3(c, res: Resultado, pedir, almacen=None, local: bool = False) -> None:
    res.seccion("9. Volver atrás: necesidad, regenerar y duplicar")
    estado, enc = pedir("post", "/encuestas/generar", json=NECESIDAD_A)
    if not res.comprobar("Generar guarda la necesidad", estado == 200 and
                         (enc.get("necesidad") or {}).get("objetivo") == NECESIDAD_A["objetivo"], f"{estado}"):
        return
    eid = enc["id"]
    res.comprobar("Encuesta nueva con traducciones pendientes", enc.get("estado_traduccion") == "pendiente"
                  and enc.get("traducciones") == {}, str(enc.get("estado_traduccion")))
    otra = dict(NECESIDAD_A, objetivo="Saber si las pausas del nuevo turno son suficientes")
    estado, reg = pedir("post", f"/encuestas/{eid}/regenerar", json=otra)
    res.comprobar("Regenerar conserva el id", estado == 200 and reg.get("id") == eid, f"{estado} {reg.get('id') if reg else ''}")
    res.comprobar("Regenerar cambia la necesidad y vuelve a borrador",
                  estado == 200 and reg["necesidad"]["objetivo"] == otra["objetivo"] and reg["estado"] == "borrador")
    res.comprobar("Regenerar conserva el periodo", estado == 200 and reg.get("periodo") == enc.get("periodo"))
    estado, _ = pedir("post", f"/encuestas/{eid}/regenerar", json={"colectivos": ["inventado"]})
    res.comprobar("Regenerar con necesidad no válida → 422", estado == 422, f"devolvió {estado}")
    sin_necesidad = {k: v for k, v in reg.items() if k != "necesidad"}
    estado, editada = pedir("put", f"/encuestas/{eid}", json=sin_necesidad)
    res.comprobar("Editar (PUT) conserva la necesidad",
                  estado == 200 and (editada.get("necesidad") or {}).get("objetivo") == otra["objetivo"], f"{estado}")

    pedir("post", f"/encuestas/{eid}/aprobar")
    estado, aprobada = pedir("get", f"/encuestas/{eid}")
    res.comprobar("Aprobar deja estado_traduccion válido",
                  aprobada.get("estado_traduccion") in ("pendiente", "lista", "error"), str(aprobada.get("estado_traduccion")))
    pedir("post", f"/encuestas/{eid}/publicar")
    estado, _ = pedir("post", f"/encuestas/{eid}/regenerar", json=otra)
    res.comprobar("Regenerar una encuesta publicada → 409", estado == 409, f"devolvió {estado}")

    escala = next((p["id"] for p in reg["preguntas"] if p["tipo"] == "escala_1_5"), None)
    pedir("post", f"/publico/encuestas/{eid}/respuestas", json={"turno": "manana", "valores": {escala: 3}})
    estado, copia = pedir("post", f"/encuestas/{eid}/duplicar")
    res.comprobar("Duplicar da un id nuevo en borrador",
                  estado == 200 and copia.get("id") != eid and copia.get("estado") == "borrador", f"{estado}")
    res.comprobar("Duplicar copia preguntas y necesidad, sin url ni QR",
                  estado == 200 and copia.get("preguntas") == reg.get("preguntas") and copia.get("necesidad") == reg.get("necesidad")
                  and copia.get("url") is None and copia.get("qr") is None and copia.get("traducciones") == {})
    estado, lista = pedir("get", "/encuestas")
    fila = next((e for e in lista or [] if e["id"] == copia.get("id")), {})
    res.comprobar("La copia no tiene respuestas", fila.get("n_respuestas") == 0, str(fila))
    estado, _ = pedir("post", "/encuestas/enc_999/duplicar")
    res.comprobar("Duplicar una que no existe → 404", estado == 404, f"devolvió {estado}")

    res.seccion("10. Idiomas y sugerencias")
    estado, es = pedir("get", f"/publico/encuestas/{eid}")
    estado, ca = pedir("get", f"/publico/encuestas/{eid}?idioma=ca")
    res.comprobar("?idioma=ca devuelve idioma e idiomas_disponibles",
                  estado == 200 and ca.get("idioma") == "ca" and "es" in ca.get("idiomas_disponibles", []), f"{estado}")
    if "ca" not in ca.get("idiomas_disponibles", []):
        res.comprobar("Sin traducción, los textos salen en castellano",
                      ca.get("titulo") == es.get("titulo") and ca.get("preguntas") == es.get("preguntas"))
    estado, xx = pedir("get", f"/publico/encuestas/{eid}?idioma=fr")
    res.comprobar("Idioma desconocido → castellano", estado == 200 and xx.get("idioma") == "es")
    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas",
                      json={"turno": "noche", "idioma": "ca", "valores": {escala: 2}})
    res.comprobar("Respuesta con idioma ca se acepta", estado == 200, f"devolvió {estado}")
    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas",
                      json={"turno": "noche", "idioma": "fr", "valores": {escala: 2}})
    res.comprobar("Respuesta con idioma no válido → 422", estado == 422, f"devolvió {estado}")
    if local and almacen is not None:
        res.comprobar("Se guarda el idioma de la respuesta", almacen.leer_respuestas(eid)[-1].get("idioma") == "ca")
        _comprobar_traduccion_local(res, pedir, almacen)
    else:
        res.omitir("Traducción aplicada y opciones en castellano", "solo sin --url")

    estado, sug = pedir("get", f"/encuestas/{eid}/sugerencias")
    res.comprobar("GET sugerencias responde", estado == 200 and isinstance(sug.get("preguntas"), list)
                  and sug.get("origen") in ("ia", "pendiente", "ninguno"), f"{estado} {sug}")
    if local:
        res.comprobar("Sugerencias sin IA → origen ninguno y lista vacía",
                      sug.get("origen") == "ninguno" and sug.get("preguntas") == [], str(sug))
    estado, a = pedir("get", f"/encuestas/{eid}/analisis")
    res.comprobar("estado_ia con resumenes_listos y recomendaciones_listas",
                  {"resumenes_listos", "recomendaciones_listas"} <= set(a.get("estado_ia", {})))
    res.comprobar("Cada tema con resumen_origen", all(t.get("resumen_origen") in ("ia", "pendiente", "reglas")
                                                      for t in a.get("temas", [])))
    estado, _ = pedir("get", "/encuestas/enc_999/sugerencias")
    res.comprobar("Sugerencias de una que no existe → 404", estado == 404, f"devolvió {estado}")


def recorrer_v4(c, res: Resultado, pedir, eid: str, local: bool = False) -> None:
    import random
    res.seccion("11. Estabilidad (v4): reglas, rutas e idiomas")
    corta = dict(NECESIDAD_MULTI, duracion_max_seg=30)
    estado, err = pedir("post", "/encuestas/generar", json=corta)
    res.comprobar("30 s con 2 sectores → 422 con mensaje claro",
                  estado == 422 and "60" in str((err or {}).get("detail", "")), f"{estado} {err}")
    estado, err = pedir("post", "/esta/ruta/no/existe", json={})
    res.comprobar("POST a una ruta inexistente → 404 con «¿Has reiniciado…?»",
                  estado == 404 and "reiniciado" in str((err or {}).get("detail", "")), f"{estado} {err}")

    estado, a_ca = pedir("get", f"/encuestas/{eid}/analisis?idioma=ca")
    textos_ca = " ".join([x["mensaje"] for x in a_ca.get("alertas", [])] + a_ca.get("limites", []))
    res.comprobar("?idioma=ca → alertas y límites en catalán",
                  estado == 200 and ("ha respost" in textos_ca or "resultats" in textos_ca)
                  and "ha respondido" not in textos_ca, textos_ca[:160])
    estado, a_en = pedir("get", f"/encuestas/{eid}/analisis?idioma=en")
    textos_en = " ".join([x["mensaje"] for x in a_en.get("alertas", [])] + a_en.get("limites", []))
    res.comprobar("?idioma=en → alertas y límites en inglés",
                  estado == 200 and "responded" in textos_en and "respondido" not in textos_en, textos_en[:160])
    res.comprobar("Las alertas conservan los campos estructurados",
                  all("colectivo" in x and ("tasa" in x or "antes" in x) for x in a_ca.get("alertas", [])))
    estado, a_raro = pedir("get", f"/encuestas/{eid}/analisis?idioma=pt")
    res.comprobar("Idioma no soportado (pt) → castellano", estado == 200 and a_raro.get("idioma") == "es")

    estado, es = pedir("get", "/escenarios?idioma=es")
    estado, en = pedir("get", "/escenarios?idioma=en")
    res.comprobar("GET /escenarios?idioma=en responde", estado == 200 and len(en) == len(es) and len(en) > 0)
    res.comprobar("Escenarios con nombre en texto (no objeto)", all(not isinstance(e.get("nombre", e.get("titulo")), dict) for e in en))
    if any(e.get("nombre") != f.get("nombre") for e, f in zip(es, en)):
        res.comprobar("Escenarios: los nombres cambian con el idioma", True)
    else:
        res.omitir("Escenarios en inglés", "contenido/escenarios.json aún no tiene {es, ca, en} (UAB 2)")

    estado, pub = pedir("get", f"/encuestas/{eid}")
    res.comprobar("La encuesta guarda estado_traduccion", pub.get("estado_traduccion") in ("pendiente", "lista", "error"))

    res.seccion("12. Teams sin conexión (vista previa)")
    estado, integ = pedir("get", "/integraciones")
    res.comprobar("GET /integraciones → teams false", estado == 200 and integ.get("teams") is False, str(integ))
    estado, tarjeta = pedir("get", f"/encuestas/{eid}/teams/vista_previa?tipo=publicar&idioma=ca")
    botones = [x.get("title") for x in (tarjeta or {}).get("actions", [])]
    res.comprobar("Vista previa de publicar con el botón «Respondre» (ca)",
                  estado == 200 and tarjeta.get("type") == "AdaptiveCard" and "Respondre" in botones, str(botones))
    res.comprobar("El enlace de la tarjeta lleva canal=teams",
                  "canal=teams" in ((tarjeta or {}).get("actions") or [{}])[0].get("url", ""))
    estado, resumen = pedir("get", f"/encuestas/{eid}/teams/vista_previa?tipo=resumen&idioma=en")
    res.comprobar("Vista previa del resumen sin comentarios ni datos personales",
                  estado == 200 and not any(n in json.dumps(resumen, ensure_ascii=False) for n in NOMBRES_INVENTADOS)
                  and "View analysis" in json.dumps(resumen))
    estado, _ = pedir("post", f"/encuestas/{eid}/teams/publicar")
    res.comprobar("POST teams/publicar → 503 (N/A)", estado == 503, f"devolvió {estado}")
    estado, _ = pedir("post", f"/encuestas/{eid}/teams/resumen")
    res.comprobar("POST teams/resumen → 503 (N/A)", estado == 503, f"devolvió {estado}")
    estado, _ = pedir("post", f"/publico/encuestas/{eid}/respuestas",
                      json={"turno": "manana", "canal": "teams", "valores": {next(iter(_escalas(c, eid, pedir)), "p1"): 4}})
    res.comprobar("Respuesta con canal teams se acepta", estado == 200, f"devolvió {estado}")

    res.seccion("12b. Generaciones al azar (sectores y duraciones válidas)")
    sectores = ["planta", "logistica", "comercial", "oficina", "manager"]
    azar = random.Random(4)
    fallos = []
    for _ in range(10):
        elegidos = azar.sample(sectores, azar.randint(1, 5))
        duracion = azar.choice([45 if len(elegidos) == 1 else 60, 90, 120, 300])
        necesidad = {"objetivo": "Saber cómo afecta el nuevo sistema de turnos", "colectivos": elegidos,
                     "contexto": "x", "duracion_max_seg": duracion, "temas_prohibidos": ["salario"]}
        estado, enc = pedir("post", "/encuestas/generar", json=necesidad)
        if estado != 200:
            fallos.append(f"generar {elegidos} {duracion}s → {estado} {enc}")
            continue
        estado, err = pedir("post", f"/encuestas/{enc['id']}/aprobar")
        if estado != 200:
            fallos.append(f"aprobar {elegidos} {duracion}s → {estado} {(err or {}).get('detail')}")
    res.comprobar("10 encuestas generadas se pueden aprobar", not fallos, " | ".join(fallos)[:400])


def _escalas(c, eid, pedir):
    estado, enc = pedir("get", f"/encuestas/{eid}")
    return [p["id"] for p in (enc or {}).get("preguntas", []) if p["tipo"] == "escala_1_5"]


def _comprobar_traduccion_local(res: Resultado, pedir, almacen) -> None:
    """Inyecta una traducción a mano (sin IA) para probar cómo se aplica."""
    base = {"id": "enc_prueba_idiomas", "titulo": "Turnos", "intro": "Hola", "periodo": "2026-11",
            "colectivo": "planta", "colectivos": ["planta"], "origen": "ia", "url": None, "qr": None,
            "preguntas": [{"id": "p1", "texto": "¿Qué tal?", "tipo": "escala_1_5", "opciones": [],
                           "dimension": "condiciones", "condicion": None},
                          {"id": "p2", "texto": "¿Qué cuesta más?", "tipo": "opcion", "opciones": ["Pausas", "Horario"],
                           "dimension": "condiciones", "condicion": None},
                          {"id": "p3", "texto": "¿Qué cambiarías?", "tipo": "texto", "opciones": [],
                           "dimension": "condiciones", "condicion": None}],
            "preguntas_por_colectivo": {}, "estado": "publicada", "estado_traduccion": "lista",
            "traducciones": {"ca": {"titulo": "Torns", "intro": "Hola!", "preguntas": [
                {"id": "p1", "texto": "Què tal?", "opciones": []},
                {"id": "p2", "texto": "Què costa més?", "opciones": ["Pauses", "Horari"]}]}}}
    almacen.guardar_encuesta(base)
    estado, ca = pedir("get", "/publico/encuestas/enc_prueba_idiomas?idioma=ca")
    res.comprobar("Con traducción: textos en catalán",
                  estado == 200 and ca["titulo"] == "Torns" and ca["preguntas"][1]["opciones"] == ["Pauses", "Horari"])
    res.comprobar("idiomas_disponibles incluye ca", ca.get("idiomas_disponibles") == ["es", "ca"], str(ca.get("idiomas_disponibles")))
    estado, en = pedir("get", "/publico/encuestas/enc_prueba_idiomas?idioma=en")
    res.comprobar("Idioma sin traducción → castellano", en.get("titulo") == "Turnos")
    estado, _ = pedir("post", "/publico/encuestas/enc_prueba_idiomas/respuestas",
                      json={"turno": "noche", "idioma": "ca", "valores": {"p1": 3, "p2": "Horari"}})
    guardada = almacen.leer_respuestas("enc_prueba_idiomas")[-1] if estado == 200 else {}
    res.comprobar("Opción traducida se guarda en castellano", guardada.get("valores", {}).get("p2") == "Horario",
                  f"{estado} {guardada.get('valores')}")
    borrador = dict(base, id="enc_prueba_editar", estado="aprobada")
    almacen.guardar_encuesta(borrador)
    cambiada = dict(borrador, titulo="Turnos (editado)")
    estado, ed = pedir("put", "/encuestas/enc_prueba_editar", json=cambiada)
    res.comprobar("Editar textos borra las traducciones",
                  estado == 200 and ed.get("traducciones") == {} and ed.get("estado_traduccion") == "pendiente", f"{estado}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba el ciclo completo por la API")
    parser.add_argument("--url", help="servidor ya arrancado, p. ej. http://localhost:8000")
    args = parser.parse_args()
    res, inicio = Resultado(), time.time()

    if args.url:
        import httpx
        print(f"Probando el servidor {args.url}")
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=60) as c:
            recorrer(c, res)
    else:
        os.environ["MODO_DEMO"] = "1"
        os.environ["LLM_API_KEY"] = ""  # siempre sin IA (v2.md 3.6.7); load_dotenv no lo sobrescribe
        from backend.datos import almacen
        temporal = Path(tempfile.mkdtemp(prefix="probar_ciclo_"))
        almacen.BASE = temporal / "almacen"
        if not (almacen.CONTENIDO / "plantilla.json").exists():
            print("Aviso: no existe contenido/plantilla.json; uso una plantilla de prueba.")
            contenido = temporal / "contenido"
            contenido.mkdir()
            (contenido / "plantilla.json").write_text(json.dumps(PLANTILLA_PRUEBA), encoding="utf-8")
            for nombre in ("reglas_colectivos.md", "transparencia.md"):
                if (almacen.CONTENIDO / nombre).exists():
                    (contenido / nombre).write_text((almacen.CONTENIDO / nombre).read_text(encoding="utf-8"),
                                                    encoding="utf-8")
            almacen.CONTENIDO = contenido
        from fastapi.testclient import TestClient
        from backend.api.main import app
        print(f"Probando la API en local (datos temporales en {temporal})")
        with TestClient(app) as c:
            recorrer(c, res, almacen, local=True)

    total = time.time() - inicio
    print(f"\n{res.ok} OK · {res.fallos} FALLO · {res.omitidos} OMITIDO · {total:.1f} s")
    print("TODO BIEN ✔" if res.fallos == 0 else "HAY FALLOS ✘")
    return 1 if res.fallos else 0


if __name__ == "__main__":
    sys.exit(main())
