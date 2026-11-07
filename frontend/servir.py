#!/usr/bin/env python3
"""Servidor de desarrollo local para el frontend (Damm · Escucha Activa).

Usa únicamente la biblioteca estándar de Python (sin pip ni dependencias).
- Puerto por defecto: 5500
- "/" sirve los archivos de frontend/ (index.html por defecto)
- "/ejemplos/" sirve los archivos de contratos/ejemplos/
- "/responder/<id>" sirve frontend/responder.html
"""
import http.server
import mimetypes
import os
import re
import socketserver
import sys
import urllib.parse
from pathlib import Path

# Configurar tipos MIME correctos (previene bug común de Windows donde .js se sirve como text/plain)
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/svg+xml", ".svg")

PUERTO = int(os.environ.get("PUERTO", 5500))
CARPETA_FRONTEND = Path(__file__).resolve().parent
CARPETA_RAIZ = CARPETA_FRONTEND.parent
CARPETA_EJEMPLOS = CARPETA_RAIZ / "contratos" / "ejemplos"


class ServidorDevHandler(http.server.SimpleHTTPRequestHandler):
    """Manejador HTTP adaptado para rutas SPA y estáticos cruzados."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        ruta = parsed.path

        # Si coincide con /responder/<id> (con o sin barra final), sirve responder.html
        if re.match(r"^/responder/[^/]+/?$", ruta):
            # Mantiene el query string original (?canal=quiosco, etc.)
            query = f"?{parsed.query}" if parsed.query else ""
            self.path = f"/responder.html{query}"

        return super().do_GET()

    def translate_path(self, path):
        """Traduce la ruta solicitada al sistema de archivos."""
        parsed = urllib.parse.urlparse(path)
        ruta_limpia = urllib.parse.unquote(parsed.path)

        # 1. Peticiones a /ejemplos/ -> contratos/ejemplos/
        if ruta_limpia.startswith("/ejemplos/"):
            relativa = ruta_limpia[len("/ejemplos/"):]
            return str((CARPETA_EJEMPLOS / relativa).resolve())
        elif ruta_limpia == "/ejemplos":
            return str(CARPETA_EJEMPLOS.resolve())

        # 2. Peticiones generales -> frontend/
        if ruta_limpia.startswith("/"):
            ruta_limpia = ruta_limpia.lstrip("/")

        archivo_destino = CARPETA_FRONTEND / ruta_limpia

        # Si es un directorio y no termina en barra, la redirección es automática,
        # pero si apunta a raíz o directorio existente, SimpleHTTPRequestHandler buscará index.html
        return str(archivo_destino.resolve())

    def end_headers(self):
        """Añade cabeceras para facilitar el desarrollo local sin problemas de caché ni CORS."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        # Formato de log más limpio y conciso
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def iniciar():
    # Permitir reutilización rápida del puerto tras parar el servidor
    socketserver.TCPServer.allow_reuse_address = True

    try:
        # Usamos ThreadingHTTPServer de la biblioteca estándar para soportar múltiples
        # peticiones concurrentes del navegador (HTML, CSS, JS, etc.)
        servidor_clase = getattr(http.server, "ThreadingHTTPServer", socketserver.TCPServer)
        with servidor_clase(("", PUERTO), ServidorDevHandler) as httpd:
            print("=" * 65)
            print("  Damm · Escucha Activa · Servidor de Pruebas (Frontend)")
            print("=" * 65)
            print(f"  > Raíz:            http://localhost:{PUERTO}/")
            print(f"  > Crear encuesta:  http://localhost:{PUERTO}/crear.html")
            print(f"  > Dashboard demo:  http://localhost:{PUERTO}/dashboard.html?id=enc_001")
            print(f"  > Responder móvil: http://localhost:{PUERTO}/responder/enc_001?canal=qr")
            print(f"  > Responder quiosco: http://localhost:{PUERTO}/responder/enc_001?canal=quiosco")
            print(f"  > Ejemplos JSON:   http://localhost:{PUERTO}/ejemplos/")
            print("=" * 65)
            print("  Pulsa Ctrl+C para detener el servidor.\n")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    except OSError as e:
        print(f"\n[ERROR] No se pudo abrir el puerto {PUERTO}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    iniciar()
