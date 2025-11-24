#!/bin/bash
# setup_firewall.sh
# Ejecutar como root: sudo ./setup_firewall.sh

WAN="enx624bd6d28fdf"   # interfaz de salida (cámbiala si hace falta)
LAN="wlp2s0"            # interfaz del hotspot
PORTAL_IP="10.42.0.1"   # IP del portal (gateway del hotspot)

echo "[+] Aplicando reglas iniciales del Portal Cautivo..."

# Limpia reglas previas con precaución
iptables -F
iptables -t nat -F
iptables -X

# Activar forwarding de IPv4 (necesario para actuar como gateway)
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || echo "[!] No se pudo habilitar ip_forward"

# NAT para que el gateway pueda salir (cuando clientes estén autorizados)
iptables -t nat -A POSTROUTING -o $WAN -j MASQUERADE

# Política por defecto: bloquear forwarding
iptables -P FORWARD DROP

# Permitir loopback y tráfico local en el equipo gateway
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Permitir al equipo gateway iniciar conexiones salientes (necesario para el servidor y updates)
iptables -A OUTPUT -o $WAN -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i $WAN -m state --state ESTABLISHED,RELATED -j ACCEPT

# Permitir acceso al servidor del portal (HTTP) desde clientes y desde WAN si quieres
# Nuestro servidor corre en el gateway en el puerto 8080 (HTTP)
iptables -A INPUT -p tcp -i $LAN --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -i $LAN --dport 80 -j ACCEPT  # si usas puerto 80

# Redirigir cualquier intento HTTP (puerto 80) de clientes al portal en 8080
# Esto hace que al navegar a cualquier sitio HTTP sin autorización aparezca el login
iptables -t nat -A PREROUTING -i $LAN -p tcp --dport 80 -j REDIRECT --to-ports 8080

# También permitir DHCP/DNS que NetworkManager provea (puede variar); ejemplo:
iptables -A INPUT -p udp -i $LAN --dport 67:68 -j ACCEPT   # DHCP (si fuese necesario)
iptables -A INPUT -p udp -i $LAN --dport 53 -j ACCEPT      # DNS (si el gateway provee DNS)

echo "[+] Reglas aplicadas. Clientes podrán conectarse al WiFi pero NO tendrán internet hasta autorizarse."
echo "[+] Tráfico HTTP (80) redirigido al portal en 8080."
