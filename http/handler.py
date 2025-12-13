import os
import time
import subprocess
import urllib.parse

from http.context import HTTPContext
from http.responder import HTTPResponder


class CustomHandler:
    def __init__(self, client_socket, client_address, deps):
        self.client_socket = client_socket
        self.client_address = client_address
        self.deps = deps

    def handle(self):
        ctx = HTTPContext.parse(self.client_socket)
        responder = HTTPResponder(self.client_socket)
        if ctx is None:
            try:
                responder.send_response(400, "Bad Request", b"", "text/plain")
            except Exception:
                pass
            return
        if ctx.method == "GET":
            self.do_GET(ctx, responder)
        elif ctx.method == "POST":
            self.do_POST(ctx, responder)
        else:
            responder.send_response(405, "Method Not Allowed")

    def do_GET(self, ctx, responder):
        client_ip = self.client_address[0]
        path = ctx.path if ctx.path != "/" else "/index.html"
        authorized = self.deps["authorized"]
        auth_lock = self.deps["auth_lock"]
        STATIC_DIR = self.deps["STATIC_DIR"]
        if path == "/heartbeat":
            with auth_lock:
                if client_ip in authorized:
                    authorized[client_ip]["last_seen"] = time.time()
                    return responder.send_response(200, "OK", b"OK", "text/plain")
            return responder.send_response(
                401, "Unauthorized", b"UNAUTHORIZED", "text/plain"
            )
        detection_paths = {
            "/hotspot-detect.html",
            "/generate_204",
            "/gen_204",
            "/ncsi.txt",
            "/connecttest.txt",
            "/check_network_status.txt",
        }
        allow_unauth_prefixes = ("/icons/",)
        allow_unauth_exact = {
            "/index.html",
            "/script.js",
            "/styles.css",
            "/favicon.ico",
        }
        with auth_lock:
            is_auth = client_ip in authorized
        if not is_auth:
            if path in detection_paths:
                # Responder directamente con el portal para las rutas de detección
                index_path = os.path.join(STATIC_DIR, "index.html")
                if os.path.exists(index_path):
                    with open(index_path, "rb") as f:
                        content = f.read()
                    return responder.send_response(200, "OK", content, "text/html")
                else:
                    return responder.send_response(200, "OK", b"", "text/html")
            if (
                path not in allow_unauth_exact
                and not any(path.startswith(p) for p in allow_unauth_prefixes)
            ):
                return responder.send_redirect("/index.html")
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
            responder.send_response(200, "OK", content, content_type)
        else:
            if not is_auth:
                return responder.send_redirect("/index.html")
            responder.send_response(404, "Not Found")

    def do_POST(self, ctx, responder):
        path = ctx.path
        if path == "/login":
            self.handle_login(ctx, responder)
        elif path == "/logout":
            self.handle_logout(responder)
        else:
            responder.send_response(404, "Not Found")

    def handle_login(self, ctx, responder):
        body_text = ctx.body.decode("utf-8", errors="replace")
        data = urllib.parse.parse_qs(body_text)
        username = data.get("username", [""])[0]
        password = data.get("password", [""])[0]
        client_ip = self.client_address[0]
        get_mac_for_ip = self.deps["get_mac_for_ip"]
        load_users = self.deps["load_users"]
        AUTORIZE_SCRIPT = self.deps["AUTORIZE_SCRIPT"]
        authorized = self.deps["authorized"]
        auth_lock = self.deps["auth_lock"]
        client_mac = get_mac_for_ip(client_ip)
        print(f"[+] Login attempt from {client_ip}: {username}")
        if not client_mac:
            print(
                f"[!] MAC no disponible para {client_ip}. Pide recargar o generar tráfico."
            )
            return responder.send_response(
                401, "Unauthorized", b"MAC no detectada, reintenta", "text/plain"
            )
        users = load_users()
        valid = any(
            u["username"] == username and u["password"] == password for u in users
        )
        if valid:
            print(
                f"[+] Usuario {username} autenticado. Autorizando IP {client_ip} MAC {client_mac}..."
            )
            try:
                subprocess.run(
                    ["sudo", AUTORIZE_SCRIPT, client_ip, client_mac], check=True
                )
                with auth_lock:
                    authorized[client_ip] = {
                        "mac": client_mac,
                        "last_seen": time.time(),
                    }
                # Responder OK; el frontend hará la navegación a /welcome.html
                return responder.send_response(200, "OK", b"OK", "text/plain")
            except Exception as e:
                print("[!] Error ejecutando autorizar.sh:", e)
                responder.send_response(
                    500, "Internal Server Error", b"Error autorizando", "text/plain"
                )
        else:
            print(f"[!] Login fallido para {client_ip}")
            responder.send_response(
                401, "Unauthorized", b"Credenciales invalidas", "text/plain"
            )

    def handle_logout(self, responder):
        client_ip = self.client_address[0]
        REVOKE_SCRIPT = self.deps["REVOKE_SCRIPT"]
        authorized = self.deps["authorized"]
        auth_lock = self.deps["auth_lock"]
        get_mac_for_ip = self.deps["get_mac_for_ip"]
        with auth_lock:
            client_mac = authorized.get(client_ip, {}).get("mac")
        if not client_mac:
            client_mac = get_mac_for_ip(client_ip) or "00:00:00:00:00:00"
        print(f"[+] Logout desde {client_ip} (MAC {client_mac})")
        try:
            subprocess.run(["sudo", REVOKE_SCRIPT, client_ip, client_mac], check=True)
            with auth_lock:
                authorized.pop(client_ip, None)
            responder.send_response(200, "OK", b"LOGOUT_OK", "text/plain")
        except Exception as e:
            print("[!] Error ejecutando revocar.sh:", e)
            responder.send_response(
                500, "Internal Server Error", b"Error revocando", "text/plain"
            )
