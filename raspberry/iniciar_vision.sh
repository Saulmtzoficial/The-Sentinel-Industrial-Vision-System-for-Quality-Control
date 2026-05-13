#!/bin/bash
# ─── iniciar_vision.sh ─────────────────────────────────────────────────────
# Inicia el hotspot WiFi y el servidor Vision automáticamente.
# ───────────────────────────────────────────────────────────────────────────

echo "════════════════════════════════════════"
echo "  Vision — Iniciando sistema..."
echo "════════════════════════════════════════"

# Activar hotspot
echo "→ Activando hotspot WiFi..."
sudo nmcli connection up Hotspot 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Hotspot activo: Vision (192.168.4.1)"
else
    echo "⚠️  Creando hotspot por primera vez..."
    sudo nmcli device wifi hotspot ssid Vision password vision2024 ifname wlan0
    sudo nmcli connection modify Hotspot connection.autoconnect yes
    sudo nmcli connection modify Hotspot ipv4.addresses 192.168.4.1/24
    sudo nmcli connection modify Hotspot ipv4.method shared
    echo "✅ Hotspot creado y activo"
fi

# Esperar que la red se estabilice
sleep 3

# Iniciar servidor
echo "→ Iniciando servidor Vision..."
cd ~/vision
source env/bin/activate
python APP.PY
