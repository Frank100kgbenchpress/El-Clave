#!/bin/bash
# autorizar.sh <IP_CLIENTE>

if [ -z "$1" ]; then
    echo "Uso: $0 <IP_CLIENTE>"
    exit 1
fi

CLIENT_IP="$1"
LAN="wlp2s0"

# -----------------------------
# Detectar WAN automáticamente
# -----------------------------
WAN=$(ip route | grep default | awk '{print $5}' | head -n 1)
echo "[+] WAN detectada automáticamente: $WAN"

#############################################
# Reglas para permitir al cliente navegar   #
#############################################

iptables -C FORWARD -s "$CLIENT_IP" -o "$WAN" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT >/dev/null 2>&1 && {
    echo "[*] $CLIENT_IP ya autorizado"
    exit 0
}

iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -m state --state ESTABLISHED,RELATED -j ACCEPT

iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -p icmp -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -p icmp -j ACCEPT

iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -p udp --dport 53 -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -p udp --sport 53 -j ACCEPT

iptables -t nat -I PREROUTING 1 -s "$CLIENT_IP" -p tcp --dport 80 -j RETURN

echo "[+] Autorizado: $CLIENT_IP"
