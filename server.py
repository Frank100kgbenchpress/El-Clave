from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import json
import urllib.parse
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, ".", "static")
USERS_FILE = os.path.join(BASE_DIR, ".", "data/users.json")


# ============================
# Cargar usuarios desde JSON
# ============================
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            return data.get("users", [])
    except Exception as e:
        print("Error cargando users.json:", e)
        return []


class Handler(SimpleHTTPRequestHandler):
    # Servir archivos estáticos
    def translate_path(self, path):
        if path == "/":
            path = "/index.html"
        return os.path.join(STATIC_DIR, path.lstrip("/"))

    # Manejo POST
    def do_POST(self):
        if self.path == "/login":
            # thread = threading.Thread(target=self.handle_login)
            # thread.daemon = True
            # thread.start()
            self.handle_login
        else:
            self.send_error(404, "Endpoint not found")

    def handle_login(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = urllib.parse.parse_qs(body)

        username = data.get("username", [""])[0]
        password = data.get("password", [""])[0]

        print(f"Login attempt: {username}")

        # Obtener usuarios
        users = load_users()

        # Buscar si coincide usuario y contraseña
        valid = any(
            u["username"] == username and u["password"] == password for u in users
        )

        if valid:
            response = "OK"
        else:
            response = "Invalid username or password"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def log_message(self, format, *args):
        return


def run():
    print("Cargando usuarios desde:", USERS_FILE)
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("Servidor corriendo en http://0.0.0.0:8080")
    server.serve_forever()


if __name__ == "__main__":
    run()
