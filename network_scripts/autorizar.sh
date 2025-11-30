#!/bin/bash
# autorizar.sh <IP_CLIENTE> <MAC_CLIENTE>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Uso: $0 <IP_CLIENTE> <MAC_CLIENTE>"
    exit 1
fi

CLIENT_IP="$1"
CLIENT_MAC="$(echo "$2" | tr '[:upper:]' '[:lower:]')"
LAN="wlp2s0"

# Detectar WAN automáticamente
WAN=$(ip route | grep default | awk '{print $5}' | head -n 1)
[ -z "$WAN" ] && echo "[!] No se detecta WAN" && exit 1

echo "[+] WAN: $WAN"
echo "[+] Autorizando IP $CLIENT_IP MAC $CLIENT_MAC"

# Evitar duplicados
iptables -C FORWARD -s "$CLIENT_IP" -o "$WAN" -m mac --mac-source "$CLIENT_MAC" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT >/dev/null 2>&1 && { echo "[*] Ya autorizado"; exit 0; }

# Reglas principales
iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -m mac --mac-source "$CLIENT_MAC" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -I FORWARD 2 -d "$CLIENT_IP" -i "$WAN" -m state --state ESTABLISHED,RELATED -j ACCEPT

# ICMP opcional
iptables -I FORWARD 3 -s "$CLIENT_IP" -o "$WAN" -p icmp -j ACCEPT
iptables -I FORWARD 4 -d "$CLIENT_IP" -i "$WAN" -p icmp -j ACCEPT

# DNS
iptables -I FORWARD 5 -s "$CLIENT_IP" -o "$WAN" -p udp --dport 53 -j ACCEPT
iptables -I FORWARD 6 -d "$CLIENT_IP" -i "$WAN" -p udp --sport 53 -j ACCEPT

# Saltar redirección HTTP
iptables -t nat -I PREROUTING 1 -s "$CLIENT_IP" -p tcp --dport 80 -j RETURN

echo "[+] Autorizado: $CLIENT_IP ($CLIENT_MAC)"