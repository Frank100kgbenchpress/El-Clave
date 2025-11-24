#!/bin/bash
# revocar.sh <IP_CLIENTE>

if [ -z "$1" ]; then
  echo "Uso: $0 <IP_CLIENTE>"
  exit 1
fi

CLIENT_IP="$1"
WAN="enx624bd6d28fdf"
LAN="wlp2s0"

# Borrar reglas FORWARD del cliente (varias posibles variantes/state)
iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -p icmp -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -p icmp -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -s "$CLIENT_IP" -o "$WAN" -p udp --dport 53 -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -d "$CLIENT_IP" -i "$WAN" -p udp --sport 53 -j ACCEPT 2>/dev/null || true

# Borrar regla que anulaba la redirección HTTP (RETURN)
iptables -t nat -D PREROUTING -s "$CLIENT_IP" -p tcp --dport 80 -j RETURN 2>/dev/null || true

echo "[+] Revocado: $CLIENT_IP"
