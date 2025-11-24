#!/usr/bin/env python3
# portal_server.py
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import json
import urllib.parse
from socketserver import ThreadingMixIn
import subprocess
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
AUTORIZE_SCRIPT = os.path.join(BASE_DIR, "autorizar.sh")
REVOKE_SCRIPT = os.path.join(BASE_DIR, "revocar.sh")
PORT = 8080

# Simple store of authorized IPs (in-memory). For persistence, guarda en archivo.
authorized = set()
auth_lock = threading.Lock()

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            return data.get("users", [])
    except Exception as e:
        print("Error cargando users.json:", e)
        return []

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == "/":
            path = "/index.html"
        return os.path.join(STATIC_DIR, path.lstrip("/"))

    def do_POST(self):
        if self.path == "/login":
            self.handle_login()
        elif self.path == "/logout":
            self.handle_logout()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_login(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = urllib.parse.parse_qs(body)

        username = data.get("username", [""])[0]
        password = data.get("password", [""])[0]
        client_ip = self.client_address[0]

        print(f"[+] Login attempt from {client_ip}: {username}")

        users = load_users()
        valid = any(u["username"] == username and u["password"] == password for u in users)

        if valid:
            # Call autorizar script to open iptables for this client
            # Necesita ser ejecutado con permisos (ejecutar servidor con sudo o configurar sudoers)
            try:
                # Llamada sin mostrar output; captura errores
                res = subprocess.run(["sudo", AUTORIZE_SCRIPT, client_ip], capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    with auth_lock:
                        authorized.add(client_ip)
                    response = "OK"
                    print(f"[+] {client_ip} autorizado")
                else:
                    response = "ERROR: no se pudo autorizar (ver logs)"
                    print("[!] autorizar.sh fallo:", res.stdout, res.stderr)
            except Exception as e:
                response = "ERROR: exception al autorizar"
                print("[!] Exception al ejecutar autorizar.sh:", e)
        else:
            response = "Invalid username or password"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def handle_logout(self):
        client_ip = self.client_address[0]
        print(f"[+] Logout attempt from {client_ip}")
        # Ejecutar script de revocación
        try:
            res = subprocess.run(["sudo", REVOKE_SCRIPT, client_ip], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                with auth_lock:
                    if client_ip in authorized:
                        authorized.remove(client_ip)
                response = "LOGOUT_OK"
                print(f"[+] {client_ip} revocado")
            else:
                response = "ERROR: no se pudo revocar"
                print("[!] revocar.sh fallo:", res.stdout, res.stderr)
        except Exception as e:
            response = "ERROR: exception al revocar"
            print("[!] Exception al ejecutar revocar.sh:", e)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def do_GET(self):
        client_ip = self.client_address[0]
        # Si el cliente NO está autorizado, forzamos a entregar el portal para (casi) cualquier ruta
        # incluyendo rutas de detección adicionales que algunos sistemas usan ("fastconnect", etc.).
        with auth_lock:
            authorized_ip = client_ip in authorized
        if not authorized_ip:
            # Extensiones de recursos estáticos permitidos (para que la página de login cargue su CSS/JS/iconos)
            allowed_ext = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico")
            # Rutas explícitas de detección de conectividad de distintos sistemas
            captive_paths = {"/generate_204", "/hotspot-detect.html", "/ncsi.txt", "/connecttest.txt",
                             "/success.txt", "/redirect", "/check_network_status", "/fastconnect"}
            path_lower = self.path.lower()
            # Si es un recurso estático (para que cargue assets) lo servimos normalmente
            if path_lower.endswith(allowed_ext):
                return super().do_GET()
            # Si es el endpoint de login, dejamos que el POST se maneje aparte (GET mostrará index)
            if self.path == "/login":
                pass  # caerá a servir index
            # Para cualquier otra ruta (incluyendo detección) devolver el portal
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open(os.path.join(STATIC_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return
        # Autorizado: comportamiento normal
        return super().do_GET()

    def log_message(self, format, *args):
        return

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def run():
    print("Cargando usuarios desde:", USERS_FILE)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Servidor corriendo en http://0.0.0.0:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
