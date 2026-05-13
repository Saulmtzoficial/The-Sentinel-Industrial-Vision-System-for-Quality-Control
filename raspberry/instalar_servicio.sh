#!/bin/bash
# ─── instalar_servicio.sh ──────────────────────────────────────────────────
# Instala el servicio para que Vision arranque automáticamente
# al encender la Raspberry Pi.
#
# Uso: chmod +x instalar_servicio.sh && ./instalar_servicio.sh
# ───────────────────────────────────────────────────────────────────────────

echo "════════════════════════════════════════"
echo "  Instalando servicio Vision..."
echo "════════════════════════════════════════"

# Dar permisos al script de inicio
chmod +x ~/vision/iniciar_vision.sh
echo "✅ Permisos asignados"

# Copiar servicio a systemd
sudo cp ~/vision/vision.service /etc/systemd/system/
echo "✅ Servicio copiado"

# Habilitar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable vision.service
echo "✅ Servicio habilitado (arranca al encender)"

echo ""
echo "════════════════════════════════════════"
echo "  Listo. Comandos útiles:"
echo "════════════════════════════════════════"
echo ""
echo "  Iniciar ahora:"
echo "    sudo systemctl start vision"
echo ""
echo "  Detener:"
echo "    sudo systemctl stop vision"
echo ""
echo "  Ver estado:"
echo "    sudo systemctl status vision"
echo ""
echo "  Ver logs en vivo:"
echo "    journalctl -u vision -f"
echo ""
echo "  Desactivar auto-inicio:"
echo "    sudo systemctl disable vision"
echo ""
echo "  Al encender la Raspberry, conecta"
echo "  tu tablet al WiFi 'Vision' (pass: vision2024)"
echo "  y abre: http://192.168.4.1:5000"
echo ""
