# 🔩 The Sentinel — Industrial Vision System for Quality Control

> Sistema de inspección industrial basado en visión por computadora para la detección y clasificación de tuercas y tornillos en tiempo real sobre una banda transportadora.

---

## 📋 Descripción

**The Sentinel** es un sistema embebido de visión artificial desarrollado para automatizar el control de calidad en líneas de manufactura. Utiliza un modelo **YOLOv8n** entrenado con imágenes propias para detectar y clasificar piezas (tornillos y tuercas) en movimiento. El sistema cuenta con un servidor web accesible desde cualquier dispositivo en la red local, control de motor y servo por Arduino, y exportación de registros a Excel.

---

## 🏗️ Arquitectura del sistema

```
┌─────────────────────┐         ┌──────────────────────┐
│   RASPBERRY PI 5    │  WiFi   │   Tablet / PC        │
│                     │◄───────►│                      │
│  • Cámara CSI       │         │  • Dashboard web     │
│  • YOLOv8n NCNN     │         │  • http://192.168.4.1│
│  • Flask Server     │         │    :5000             │
│  • Hotspot WiFi     │         └──────────────────────┘
└────────┬────────────┘
         │ Serial USB
┌────────▼────────────┐
│   ARDUINO UNO       │
│  • Motor NEMA 17    │
│  • Servo clasificador│
│  • Botones físicos  │
└─────────────────────┘
```

---

## ✨ Características

- **Detección en tiempo real** con YOLOv8n optimizado para ARM (formato NCNN)
- **Línea de gatillo virtual** para conteo preciso al cruzar el centro del frame
- **Tracking por IoU** para evitar doble conteo de la misma pieza
- **Lógica de descarte** — objeto extraño = confianza < umbral (sin entrenar clase adicional)
- **Control bidireccional** — botones físicos + interfaz web controlan el mismo motor
- **Servo clasificador** que separa piezas al detectarlas
- **Dashboard web** con video en vivo MJPEG, contadores, gráficas y alarmas
- **Hotspot propio** en la Raspberry Pi (red WiFi "Vision", IP fija 192.168.4.1)
- **Exportación a Excel** con detalle de cada pieza detectada en la sesión
- **Auto-inicio** como servicio systemd al encender la Raspberry Pi
- **Login multi-usuario** con contraseñas hasheadas (SHA-256)

---

## 📁 Estructura del repositorio

```
The-Sentinel/
├── README.md
├── .gitignore
│
├── raspberry/                    # Scripts para la Raspberry Pi
│   ├── App.py                    # Servidor principal (Flask + YOLO + Arduino)
│   ├── captura_rasp.py           # Captura de imágenes con cámara CSI
│   ├── iniciar_vision.sh         # Script de inicio del servidor
│   ├── instalar_servicio.sh      # Instalador del servicio systemd
│   ├── setup_raspberry.sh        # Configuración inicial de la Raspberry Pi
│   └── vision.service            # Definición del servicio systemd
│
├── laptop/                       # Scripts para la laptop (entrenamiento)
│   ├── captura_laptop.py         # Captura de imágenes con webcam
│   ├── auto_etiquetar.py         # Etiquetado automático por contornos
│   ├── convertir_labelme.py      # Convertir JSON de LabelMe a YOLO .txt
│   ├── entrenar_modelo.py        # Entrenamiento y exportación del modelo
│   └── testear_modelo.py         # Prueba del modelo con webcam en laptop
│
├── arduino/
│   └── vision_arduino.ino        # Código Arduino (motor + servo + botones)
│
├── web/                          # Interfaz web del servidor
│   ├── templates/
│   │   ├── index.html            # Dashboard principal
│   │   └── login.html            # Pantalla de login
│   └── static/
│       ├── css/
│       │   ├── styles.css        # Estilos del dashboard
│       │   └── login.css         # Estilos del login
│       └── js/
│           └── app.js            # Lógica del frontend
│
└── docs/
    └── GUIA_PIPELINE.md          # Guía completa del pipeline de entrenamiento
```

---

## 🚀 Instalación

### Raspberry Pi

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/the-sentinel.git
cd the-sentinel/raspberry

# 2. Ejecutar el script de configuración
chmod +x setup_raspberry.sh
./setup_raspberry.sh

# 3. Copiar el modelo entrenado
cp -r /ruta/al/modelo/best_ncnn_model ~/vision/modelo/

# 4. Instalar el servicio de auto-inicio
chmod +x instalar_servicio.sh
./instalar_servicio.sh
```

### Laptop (entrenamiento)

```bash
pip install ultralytics torch torchvision opencv-python labelme openpyxl Pillow
```

---

## 🧠 Pipeline de entrenamiento

```
1. Captura      →  2. Etiquetado  →  3. Conversión  →  4. Entrenamiento
captura_laptop.py   LabelMe           convertir_          entrenar_modelo.py
                    (Rectangle)       labelme.py          YOLOv8n + GPU

5. Validación   →  6. Exportación →  7. Deploy
entrenar_modelo     entrenar_modelo   Raspberry Pi
  validar           exportar          best_ncnn_model
                    .pt → NCNN
```

Comandos:

```bash
python captura_laptop.py                          # 1. Capturar imágenes
labelme ./train                                   # 2. Etiquetar
python convertir_labelme.py --carpeta train       # 3. Convertir a YOLO
python entrenar_modelo.py preparar train          # 4a. Preparar dataset
python entrenar_modelo.py entrenar                # 4b. Entrenar
python entrenar_modelo.py validar                 # 5. Validar
python entrenar_modelo.py exportar                # 6. Exportar a NCNN
```

---

## ⚙️ Hardware utilizado

| Componente | Especificación |
|---|---|
| SBC | Raspberry Pi 5 — 8GB RAM |
| Cámara | OV5647 (CSI, 5MP) |
| Laptop | Intel i5-12450H, NVIDIA RTX 2050 4GB |
| Microcontrolador | Arduino UNO |
| Motor | NEMA 17 + Driver A4988 |
| Servo | SG90 / MG996R — Pin D9 |
| Botón Inicio | D5 — Pull-Up 1KΩ a 3.3V |
| Botón Detener | D6 — Pull-Up 1KΩ a 3.3V |

---

## 📊 Resultados del modelo

| Métrica | Valor |
|---|---|
| mAP50 | **0.995** |
| Precision | **1.00** |
| Recall | **1.00** |
| F1 Score | **0.99** |
| Dataset | 1,148 imágenes (918 train / 230 val) |
| Clases | Tornillo (0) — Tuerca (1) |
| Modelo base | YOLOv8n |
| Formato deploy | NCNN (ARM optimizado) |

---

## 🖥️ Acceso al dashboard

1. Conecta tu dispositivo al WiFi **"Vision"** (contraseña: `vision2024`)
2. Abre el navegador en `http://192.168.4.1:5000`
3. Inicia sesión con tus credenciales

| Usuario | Contraseña |
|---|---|
| admin | Adm!n#9x2K |
| eduardo | Ed$7mQpR!3 |
| diego | Di#4kWnZ@8 |
| cesar_gael | CG!6vTxL#2 |
| saul | Sa@9jBqM!5 |

---

## 🔌 Conexiones Arduino

```
NEMA 17 + A4988:
  STEP → D3
  DIR  → D2
  MS1, MS2, MS3 → 5V (microstepping 1/16)

Servo clasificador:
  Señal → D9
  VCC   → 5V externo
  GND   → GND Arduino

Botones (Pull-Up externo 1KΩ):
  INICIAR: D5 ─── 1KΩ ─── 3.3V  |  D5 ─── Botón ─── GND
  DETENER: D6 ─── 1KΩ ─── 3.3V  |  D6 ─── Botón ─── GND
```

---

## 🛠️ Tecnologías utilizadas

| Área | Tecnología |
|---|---|
| Modelo IA | YOLOv8n (Ultralytics) |
| Backend | Flask + Flask-SocketIO |
| Frontend | HTML5 + CSS3 + Chart.js + Socket.IO |
| Cámara RPi | Picamera2 + libcamera |
| Visión | OpenCV |
| Inferencia ARM | NCNN |
| Arduino | C++ + Servo.h |
| Exportación | openpyxl |

---

## 👥 Equipo

Proyecto desarrollado como trabajo terminal de ingeniería.

---

## 📄 Licencia

MIT License — libre para uso educativo e industrial.
