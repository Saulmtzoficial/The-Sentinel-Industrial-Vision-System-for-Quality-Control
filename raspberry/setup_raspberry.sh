#!/bin/bash
# ─── setup_raspberry.sh ────────────────────────────────────────────────────
# Script de instalación para Raspberry Pi 5
# Ejecutar con: chmod +x setup_raspberry.sh && ./setup_raspberry.sh
# ───────────────────────────────────────────────────────────────────────────

set -e
echo "════════════════════════════════════════════════════"
echo "  Instalación — Sistema Vision (Raspberry Pi)"
echo "════════════════════════════════════════════════════"

# Actualizar sistema
echo ""
echo "→ Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
echo ""
echo "→ Instalando dependencias del sistema..."
sudo apt install -y python3-pip python3-venv python3-opencv libatlas-base-dev \
    libhdf5-dev libharfbuzz-dev libwebp-dev libjasper-dev libilmbase-dev \
    libopenexr-dev libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev

# Crear entorno virtual
echo ""
echo "→ Creando entorno virtual..."
python3 -m venv env
source env/bin/activate

# Instalar paquetes Python
echo ""
echo "→ Instalando paquetes Python..."
pip install --upgrade pip
pip install flask flask-socketio pyserial openpyxl
pip install ultralytics
pip install opencv-python-headless

# Crear estructura de carpetas
echo ""
echo "→ Creando estructura de carpetas..."
mkdir -p templates static/css static/js modelo

echo ""
echo "════════════════════════════════════════════════════"
echo "  ✅ Instalación completada"
echo "════════════════════════════════════════════════════"
echo ""
echo "  Siguiente paso: copiar archivos desde la laptop."
echo "  Ejecuta estos comandos DESDE TU LAPTOP:"
echo ""
echo "  IP=\$(hostname -I | awk '{print \$1}')"
echo "  echo \"IP de la Raspberry: \$IP\""
echo ""
echo "  Desde la laptop:"
echo "    scp APP.PY pi@<IP>:~/vision/"
echo "    scp templates/index.html templates/login.html pi@<IP>:~/vision/templates/"
echo "    scp static/css/styles.css static/css/login.css pi@<IP>:~/vision/static/css/"
echo "    scp static/js/app.js pi@<IP>:~/vision/static/js/"
echo "    scp -r runs/detect/runs/entrenar/tuercas_tornillos/weights/best_ncnn_model/ pi@<IP>:~/vision/modelo/"
echo ""
echo "  Después en la Raspberry:"
echo "    cd ~/vision"
echo "    source env/bin/activate"
echo "    python APP.PY"
echo ""
