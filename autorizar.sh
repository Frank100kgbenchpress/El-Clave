#!/bin/bash
# autorizar.sh <IP_CLIENTE>
# Añade reglas para permitir que <IP_CLIENTE> salga por WAN.
# Ejecutar como root (o asegúrate que el proceso que lo llame tenga sudo sin password)

if [ -z "$1" ]; then
  echo "Uso: $0 <IP_CLIENTE>"
  exit 1
fi

CLIENT_IP="$1"
WAN="enx624bd6d28fdf"
LAN="wlp2s0"  # interfaz del hotspot (para posibles reglas adicionales)

#############################################
# Reglas para permitir tráfico del cliente  #
#############################################

# Evitar duplicados usando coincidencia con state
iptables -C FORWARD -s "$CLIENT_IP" -o "$WAN" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT >/dev/null 2>&1 && {
  echo "[*] $CLIENT_IP ya autorizado"
  exit 0
}

# Permitir tráfico saliente iniciando conexiones y retorno
iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -m state --state ESTABLISHED,RELATED -j ACCEPT

# (Opcional) permitir ICMP (ping) si lo deseas
iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -p icmp -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -p icmp -j ACCEPT

# Si usas DNS externo (no sólo el gateway), permitir UDP 53 forward
iptables -I FORWARD 1 -s "$CLIENT_IP" -o "$WAN" -p udp --dport 53 -j ACCEPT
iptables -I FORWARD 1 -d "$CLIENT_IP" -i "$WAN" -p udp --sport 53 -j ACCEPT

#############################################
# Sacar al cliente de la redirección HTTP   #
#############################################
# Insertar regla al principio de PREROUTING para que ESTE cliente ya no
# sea redirigido al portal (salta la regla REDIRECT posterior)
iptables -t nat -I PREROUTING 1 -s "$CLIENT_IP" -p tcp --dport 80 -j RETURN

# (Opcional) Añadir NAT específico por IP si no quieres el MASQUERADE global
# iptables -t nat -A POSTROUTING -s "$CLIENT_IP" -o "$WAN" -j MASQUERADE

echo "[+] Autorizado: $CLIENT_IP"
