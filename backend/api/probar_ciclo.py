"""Recorre el ciclo completo por la API y dice OK o FALLO en cada comprobación · UPC 2.

    python -m backend.api.probar_ciclo                       # sin servidor, datos temporales
    python -m backend.api.probar_ciclo --url http://localhost:8000   # contra un servidor arrancado

Sin --url arranca la API dentro del propio script con un almacén temporal:
no hace falta tener el servidor encendido y no ensucia backend/datos/almacen/.
Con --url prueba el servidor de verdad (necesita MODO_DEMO=1 en su .env).
Sale con código 1 si algo falla. Tarda unos segundos: úsalo después de cada cambio.
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
                                        "turno", "canal", "valores", "comentario"}, sorted(guardada))
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
        seg = rec.get("seguimiento") or {}
        res.comprobar("Propone encuesta de seguimiento para planta", seg.get("colectivo") == "planta", str(seg))
        estado, _ = pedir("post", "/encuestas/generar", json=seg)
        res.comprobar("El seguimiento se puede generar (cierra el ciclo)", estado == 200, f"devolvió {estado}")

    res.seccion("7. Histórico enc_000 (escenario C)")
    estado, lista = pedir("get", "/encuestas")
    if any(e["id"] == "enc_000" for e in lista or []):
        estado, a0 = pedir("get", "/encuestas/enc_000/analisis")
        res.comprobar("Análisis de enc_000", estado == 200 and a0.get("n_respuestas", 0) > 0, f"{estado}")
    else:
        res.omitir("Análisis de enc_000", "UPC 1 aún no ha subido datos_sinteticos/enc_000.json")


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
