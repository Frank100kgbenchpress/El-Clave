#!/usr/bin/env python3
# portal_server.py

import os
import json
import subprocess
import threading
import time
import re
from http.http_server import CustomHTTPServer
from http.handler import CustomHandler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")

SCRIPTS_DIR = os.path.join(BASE_DIR, "network_scripts")
SETUP_FIREWALL = os.path.join(SCRIPTS_DIR, "setup_firewall.sh")
AUTORIZE_SCRIPT = os.path.join(SCRIPTS_DIR, "autorizar.sh")
REVOKE_SCRIPT = os.path.join(SCRIPTS_DIR, "revocar.sh")

PORT = 8080

# Store de clientes autorizados: { ip: {"mac": str, "last_seen": float} }
authorized = {}
auth_lock = threading.Lock()
TIMEOUT_SECONDS = 120


def get_mac_for_ip(ip: str):
    """Obtiene la MAC asociada a una IP desde /proc/net/arp."""
    try:
        with open("/proc/net/arp", "r") as f:
            lines = f.read().strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == ip:
                mac = parts[3]
                if mac and mac != "00:00:00:00:00:00" and re.match(r"^[0-9a-fA-F:]{17}$", mac):
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


def run():
    print("Cargando usuarios desde:", USERS_FILE)

    # 🔥 Ejecutar automáticamente las reglas del firewall
    run_setup_firewall()

    deps = {
        'authorized': authorized,
        'auth_lock': auth_lock,
        'STATIC_DIR': STATIC_DIR,
        'AUTORIZE_SCRIPT': AUTORIZE_SCRIPT,
        'REVOKE_SCRIPT': REVOKE_SCRIPT,
        'get_mac_for_ip': get_mac_for_ip,
        'load_users': load_users,
        'TIMEOUT_SECONDS': TIMEOUT_SECONDS,
    }
    server = CustomHTTPServer("0.0.0.0", PORT, CustomHandler, deps)

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
