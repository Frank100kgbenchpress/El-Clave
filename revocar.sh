#!/bin/bash
# revocar.sh <IP_CLIENTE> <MAC_CLIENTE>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Uso: $0 <IP_CLIENTE> <MAC_CLIENTE>"
    exit 1
fi

CLIENT_IP="$1"
CLIENT_MAC="$(echo "$2" | tr '[:upper:]' '[:lower:]')"
LAN="wlp2s0"

# -----------------------------
# Detectar WAN automáticamente
# -----------------------------
WAN=$(ip route | grep default | awk '{print $5}' | head -n 1)
echo "[+] WAN detectada automáticamente: $WAN"

iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -m mac --mac-source "$CLIENT_MAC" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true

iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -p icmp -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -p icmp -j ACCEPT 2>/dev/null || true

iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -p udp --dport 53 -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -p udp --sport 53 -j ACCEPT 2>/dev/null || true

iptables -t nat -D PREROUTING -s "$CLIENT_IP" -p tcp --dport 80 -j RETURN 2>/dev/null || true

echo "[+] Revocado: $CLIENT_IP ($CLIENT_MAC)"
