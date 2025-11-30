#!/usr/bin/env python3
# portal_server.py

import os
import json
import urllib.parse
import socket
import subprocess
import threading
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")

SETUP_FIREWALL = os.path.join(BASE_DIR, "setup_firewall.sh")
AUTORIZE_SCRIPT = os.path.join(BASE_DIR, "autorizar.sh")
REVOKE_SCRIPT = os.path.join(BASE_DIR, "revocar.sh")

PORT = 8080

# Store de clientes autorizados: { ip: {"mac": str, "last_seen": float} }
authorized = {}
auth_lock = threading.Lock()
TIMEOUT_SECONDS = 120
def get_mac_for_ip(ip: str):
    try:
        with open("/proc/net/arp", "r") as f:
            lines = f.read().strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == ip:
                mac = parts[3]
                if mac and re.match(r"^[0-9a-fA-F:]{17}$", mac) and mac != "00:00:00:00:00:00":
                    return mac.lower()
    except Exception as e:
        print("[!] Error leyendo /proc/net/arp:", e)
    return None


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            return data.get("users", [])
    except Exception as e:
        print("Error cargando users.json:", e)
        return []


def run_setup_firewall():
    print("[+] Ejecutando setup_firewall.sh...")

    try:
        subprocess.run(["sudo", SETUP_FIREWALL], check=True)
        print("[+] setup_firewall.sh ejecutado correctamente.")
    except Exception as e:
        print("[!] ERROR ejecutando setup_firewall.sh:", e)
        print("[!] El portal NO funcionará correctamente sin las reglas de iptables.")


class CustomHTTPServer:
    def __init__(self, host, port, handler_class):
        self.host = host
        self.port = port
        self.handler_class = handler_class
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

    def serve_forever(self):
        print(f"Servidor corriendo en http://{self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            handler = self.handler_class(client_socket, client_address)
            handler.handle()


class CustomHandler:
    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address

    def handle(self):
        method, path, headers, body = self.read_request()

        if method == "GET":
            self.do_GET(path)
        elif method == "POST":
            self.do_POST(path, headers, body)
        else:
            self.send_response(405, "Method Not Allowed")

    def read_request(self):
        # Leer hasta el fin de headers (\r\n\r\n)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.client_socket.recv(1024)
            if not chunk:
                break
            data += chunk

        header_end = data.find(b"\r\n\r\n")
        headers_raw = data[:header_end].decode("utf-8", errors="replace")
        body = data[header_end + 4:]

        lines = headers_raw.split("\r\n")
        request_line = lines[0]
        method, path, _ = request_line.split()

        headers = {}
        for line in lines[1:]:
            if not line:
                continue
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value

        content_length = int(headers.get("Content-Length", 0))
        # Si falta parte del cuerpo, leer el resto
        remaining = content_length - len(body)
        while remaining > 0:
            chunk = self.client_socket.recv(remaining)
            if not chunk:
                break
            body += chunk
            remaining -= len(chunk)

        return method, path, headers, body

    def do_GET(self, path):
        client_ip = self.client_address[0]

        if path == "/":
            path = "/index.html"

        # Heartbeat de cliente autorizado
        if path == "/heartbeat":
            with auth_lock:
                if client_ip in authorized:
                    authorized[client_ip]["last_seen"] = time.time()
                    return self.send_response(200, "OK", b"OK", "text/plain")
            return self.send_response(401, "Unauthorized", b"UNAUTHORIZED", "text/plain")

        # Lista de endpoints típicos de detección de portal cautivo
        detection_paths = {
            "/hotspot-detect.html",
            "/generate_204",
            "/gen_204",
            "/ncsi.txt",
            "/connecttest.txt",
            "/check_network_status.txt",
        }

        # Permitir assets necesarios para el login cuando no esté autorizado
        allow_unauth_prefixes = ("/icons/",)
        allow_unauth_exact = {"/index.html", "/script.js", "/styles.css", "/favicon.ico"}

        with auth_lock:
            is_auth = client_ip in authorized

        # Si NO está autorizado y no es un asset permitido, forzar redirección al login
        if not is_auth:
            if path in detection_paths or (
                path not in allow_unauth_exact and not any(path.startswith(p) for p in allow_unauth_prefixes)
            ):
                return self.send_redirect("/index.html")

        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))

        if os.path.exists(file_path):
            content_type = "text/html"
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif file_path.endswith(".gif"):
                content_type = "image/gif"
            elif file_path.endswith(".svg"):
                content_type = "image/svg+xml"

            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200, "OK", content, content_type)
        else:
            # Si el recurso no existe, para no mostrar 404 en CNA, redirigir al login si no autorizado
            if not is_auth:
                return self.send_redirect("/index.html")
            self.send_response(404, "Not Found")

    def do_POST(self, path, headers, body):
        if path == "/login":
            self.handle_login(headers, body)
        elif path == "/logout":
            self.handle_logout()
        else:
            self.send_response(404, "Not Found")

    def handle_login(self, headers, body):
        # body viene como bytes; decodificar y parsear
        body_text = body.decode("utf-8", errors="replace")
        data = urllib.parse.parse_qs(body_text)

        username = data.get("username", [""])[0]
        password = data.get("password", [""])[0]
        client_ip = self.client_address[0]
        client_mac = get_mac_for_ip(client_ip)

        print(f"[+] Login attempt from {client_ip}: {username}")

        if not client_mac:
            print(f"[!] MAC no disponible para {client_ip}. Pide recargar o generar tráfico.")
            return self.send_response(401, "Unauthorized", b"MAC no detectada, reintenta", "text/plain")

        users = load_users()
        valid = any(u["username"] == username and u["password"] == password for u in users)

        if valid:
            print(f"[+] Usuario {username} autenticado. Autorizando IP {client_ip} MAC {client_mac}...")

            try:
                subprocess.run(["sudo", AUTORIZE_SCRIPT, client_ip, client_mac], check=True)
                with auth_lock:
                    authorized[client_ip] = {"mac": client_mac, "last_seen": time.time()}
                self.send_response(200, "OK", b"OK", "text/plain")
            except Exception as e:
                print("[!] Error ejecutando autorizar.sh:", e)
                self.send_response(500, "Internal Server Error", b"Error autorizando", "text/plain")
        else:
            print(f"[!] Login fallido para {client_ip}")
            self.send_response(401, "Unauthorized", b"Credenciales invalidas", "text/plain")

    def handle_logout(self):
        client_ip = self.client_address[0]
        with auth_lock:
            client_mac = authorized.get(client_ip, {}).get("mac")
        if not client_mac:
            client_mac = get_mac_for_ip(client_ip) or "00:00:00:00:00:00"
        print(f"[+] Logout desde {client_ip} (MAC {client_mac})")

        try:
            subprocess.run(["sudo", REVOKE_SCRIPT, client_ip, client_mac], check=True)
            with auth_lock:
                authorized.pop(client_ip, None)

            self.send_response(200, "OK", b"LOGOUT_OK", "text/plain")
        except Exception as e:
            print("[!] Error ejecutando revocar.sh:", e)
            self.send_response(500, "Internal Server Error", b"Error revocando", "text/plain")

    def send_response(self, status_code, status_message, content=b"", content_type="text/plain", headers=None):
        response = f"HTTP/1.1 {status_code} {status_message}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        if headers:
            for k, v in headers.items():
                response += f"{k}: {v}\r\n"
        response += "\r\n"
        self.client_socket.sendall(response.encode() + content)
        self.client_socket.close()

    def send_redirect(self, location="/index.html"):
        headers = {
            "Location": location,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        self.send_response(302, "Found", b"", "text/plain", headers)


def run():
    print("Cargando usuarios desde:", USERS_FILE)

    # 🔥 Ejecutar automáticamente las reglas del firewall
    run_setup_firewall()

    server = CustomHTTPServer("0.0.0.0", PORT, CustomHandler)

    # Hilo reaper que revoca por inactividad
    def reaper_loop():
        while True:
            now = time.time()
            expired = []
            with auth_lock:
                for ip, data in list(authorized.items()):
                    if now - data["last_seen"] > TIMEOUT_SECONDS:
                        expired.append((ip, data["mac"]))
            for ip, mac in expired:
                try:
                    print(f"[!] Inactividad > {TIMEOUT_SECONDS}s para {ip} ({mac}). Revocando...")
                    subprocess.run(["sudo", REVOKE_SCRIPT, ip, mac], check=True)
                except Exception as e:
                    print(f"[!] Error revocando {ip}/{mac} por inactividad:", e)
                finally:
                    with auth_lock:
                        authorized.pop(ip, None)
            time.sleep(15)

    threading.Thread(target=reaper_loop, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    run()
