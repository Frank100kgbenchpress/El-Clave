#!/bin/bash
# setup_firewall.sh
# Ejecutar como root: sudo ./setup_firewall.sh

# -----------------------------
# Detectar WAN automáticamente
# -----------------------------
detect_wan() {
    # 1) intentar hallar interfaz con ruta default
    WAN=$(ip route | grep default | awk '{print $5}' | head -n 1)

    if [ -z "$WAN" ]; then
        echo "[!] No se pudo detectar WAN automáticamente"
        exit 1
    fi

    echo "[+] WAN detectada automáticamente: $WAN"
}

detect_wan

LAN="wlp2s0"      # interfaz del hotspot
PORTAL_IP="10.42.0.1"

echo "[+] Aplicando reglas iniciales del Portal Cautivo..."

iptables -F
iptables -t nat -F
iptables -X

sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1

iptables -t nat -A POSTROUTING -o $WAN -j MASQUERADE
iptables -P FORWARD DROP

iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

iptables -A OUTPUT -o $WAN -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT  -i $WAN -m state --state ESTABLISHED,RELATED -j ACCEPT

iptables -A INPUT -p tcp -i $LAN --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -i $LAN --dport 80   -j ACCEPT

iptables -t nat -A PREROUTING -i $LAN -p tcp --dport 80 -j REDIRECT --to-ports 8080

iptables -A INPUT -p udp -i $LAN --dport 67:68 -j ACCEPT
iptables -A INPUT -p udp -i $LAN --dport 53   -j ACCEPT

echo "[+] Reglas aplicadas. Portal cautivo activo."
