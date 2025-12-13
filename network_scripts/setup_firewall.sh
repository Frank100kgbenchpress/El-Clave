#!/bin/bash
# setup_firewall.sh (portal cautivo)
# Ejecutar como root

# Detectar WAN
WAN=$(ip route | grep default | awk '{print $5}' | head -n 1)
[ -z "$WAN" ] && echo "[!] No se detecta WAN" && exit 1

echo "[+] WAN: $WAN"
LAN="wlp2s0"
PORTAL_IP="10.42.0.1"

echo "[+] Limpiando reglas previas"
iptables -F
iptables -t nat -F
iptables -X

sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || echo "[!] No se pudo habilitar ip_forward"

# NAT saliente
iptables -t nat -A POSTROUTING -o $WAN -j MASQUERADE
iptables -P FORWARD DROP

# Básico local
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Tráfico del propio host hacia WAN
iptables -A OUTPUT -o $WAN -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT  -i $WAN -m state --state ESTABLISHED,RELATED -j ACCEPT

# Acceso al portal
iptables -A INPUT -p tcp -i $LAN --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -i $LAN --dport 80   -j ACCEPT
iptables -A INPUT -p tcp -i $LAN --dport 443  -j ACCEPT

# Redirección HTTP hacia portal (no tocar 443/HSTS)
iptables -t nat -A PREROUTING -i $LAN -p tcp --dport 80 -j REDIRECT --to-ports 8080

# DHCP/DNS si el host los provee
iptables -A INPUT -p udp -i $LAN --dport 67:68 -j ACCEPT
iptables -A INPUT -p udp -i $LAN --dport 53   -j ACCEPT

echo "[+] Reglas aplicadas. Portal activo."