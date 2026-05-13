"""
inferencia_servidor.py — Inferencia YOLOv8 + Servidor en Raspberry Pi
======================================================================
Captura video, ejecuta detección de tuercas/tornillos y sirve:
  - Stream MJPEG con bounding boxes en /video_feed
  - API REST con resultados de detección en /api/detecciones
  - WebSocket para datos en tiempo real

Uso:
    python inferencia_servidor.py

Dependencias (en la Raspberry Pi):
    pip install ultralytics opencv-python flask flask-socketio
"""

from flask import Flask, Response, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from ultralytics import YOLO
import cv2
import threading
import time
import numpy as np
from collections import deque
from datetime import datetime

# ─── Configuración ────────────────────────────────────────────────────────────
MODELO_PATH    = "modelo/best_ncnn_model"   # Carpeta NCNN (o best.onnx / best.pt)
CAMARA_INDEX   = 0
RESOLUCION     = (640, 480)
CONFIANZA_MIN  = 0.30                        # Umbral bajo: detectar cualquier objeto
CONFIANZA_ALTA = 0.65                        # Umbral alto: aceptar como tuerca/tornillo
FPS_OBJETIVO   = 15
HISTORIAL_MAX  = 200                         # Máximo de detecciones en historial

# ─── Lógica de clasificación por descarte ─────────────────────────────────────
# El modelo solo conoce 2 clases: tuerca (0) y tornillo (1).
# Si detecta algo con confianza >= CONFIANZA_ALTA → es tuerca o tornillo.
# Si detecta algo con CONFIANZA_MIN <= confianza < CONFIANZA_ALTA → objeto extraño
#   (el modelo ve algo pero no está seguro de que sea tuerca o tornillo).

# Colores por clase (BGR)
COLORES = {
    0: (255, 180, 0),    # tornillo → cyan
    1: (0, 255, 120),    # tuerca → verde
    -1: (0, 0, 255),     # objeto_extrano → rojo (asignado por descarte)
}

NOMBRES_CLASE = {
    0: "Tornillo",
    1: "Tuerca",
    -1: "Obj. Extrano",
}

# ─── App Flask ────────────────────────────────────────────────────────────────
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ─── Estado global ────────────────────────────────────────────────────────────
estado = {
    "activo": False,
    "fps_actual": 0,
    "contadores": {
        "tuercas": 0,
        "tornillos": 0,
        "objetos_extranos": 0,
        "total": 0,
    },
    "ultima_deteccion": None,
    "confianza_min": CONFIANZA_MIN,
}

historial_detecciones = deque(maxlen=HISTORIAL_MAX)
frame_actual = None
frame_lock = threading.Lock()
modelo = None


# ─── Cargar modelo ────────────────────────────────────────────────────────────
def cargar_modelo():
    global modelo
    print(f"🔄 Cargando modelo: {MODELO_PATH}")
    try:
        modelo = YOLO(MODELO_PATH, task="detect")
        # Warm-up: correr una inferencia en imagen dummy
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        modelo.predict(dummy, verbose=False)
        print("✅ Modelo cargado y listo")
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        modelo = None


# ─── Hilo de captura + inferencia ─────────────────────────────────────────────
def hilo_captura_inferencia():
    global frame_actual, estado

    cap = cv2.VideoCapture(CAMARA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])

    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        return

    print(f"✅ Cámara abierta ({RESOLUCION[0]}x{RESOLUCION[1]})")

    intervalo = 1.0 / FPS_OBJETIVO
    fps_counter = 0
    fps_timer = time.time()

    while True:
        t_inicio = time.time()

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        # ─── Inferencia ───────────────────────────────────────────────────
        frame_procesado = frame.copy()

        if estado["activo"] and modelo is not None:
            results = modelo.predict(
                frame,
                conf=estado["confianza_min"],
                imgsz=640,
                verbose=False,
            )

            detecciones_frame = []

            for result in results:
                boxes = result.boxes
                if boxes is not None and len(boxes) > 0:
                    for box in boxes:
                        cls_id_raw = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        # ─── Lógica de descarte ──────────────────────────
                        # Confianza alta → el modelo está seguro, es tuerca o tornillo
                        # Confianza baja → el modelo ve algo pero no sabe qué es → objeto extraño
                        if conf >= CONFIANZA_ALTA:
                            cls_id = cls_id_raw   # 0=tuerca, 1=tornillo
                        else:
                            cls_id = -1            # objeto extraño (por descarte)

                        # Dibujar bounding box
                        color = COLORES.get(cls_id, (255, 255, 255))
                        nombre = NOMBRES_CLASE.get(cls_id, f"Clase {cls_id}")
                        label = f"{nombre} {conf:.0%}"

                        cv2.rectangle(frame_procesado, (x1, y1), (x2, y2), color, 2)

                        # Fondo para texto
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                        cv2.rectangle(frame_procesado, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
                        cv2.putText(frame_procesado, label, (x1 + 3, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        deteccion = {
                            "clase": nombre,
                            "clase_id": cls_id,
                            "confianza": round(conf, 3),
                            "bbox": [x1, y1, x2, y2],
                            "timestamp": datetime.now().isoformat(),
                        }
                        detecciones_frame.append(deteccion)

            # Actualizar contadores y emitir
            if detecciones_frame:
                for d in detecciones_frame:
                    if d["clase_id"] == 0:
                        estado["contadores"]["tornillos"] += 1
                    elif d["clase_id"] == 1:
                        estado["contadores"]["tuercas"] += 1
                    elif d["clase_id"] == -1:
                        estado["contadores"]["objetos_extranos"] += 1
                    estado["contadores"]["total"] += 1

                estado["ultima_deteccion"] = detecciones_frame[-1]
                historial_detecciones.extend(detecciones_frame)

                # Enviar por WebSocket
                socketio.emit("detecciones", {
                    "detecciones": detecciones_frame,
                    "contadores": estado["contadores"],
                })

        # ─── Actualizar frame para stream ─────────────────────────────────
        with frame_lock:
            frame_actual = frame_procesado

        # ─── FPS ──────────────────────────────────────────────────────────
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            estado["fps_actual"] = fps_counter
            fps_counter = 0
            fps_timer = time.time()

        # Limitar FPS
        elapsed = time.time() - t_inicio
        if elapsed < intervalo:
            time.sleep(intervalo - elapsed)

    cap.release()


# ─── Stream MJPEG ─────────────────────────────────────────────────────────────
def generar_frames():
    while True:
        with frame_lock:
            if frame_actual is None:
                time.sleep(0.05)
                continue
            _, buffer = cv2.imencode('.jpg', frame_actual, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(1.0 / FPS_OBJETIVO)


# ─── Rutas ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({
        "servicio": "Inferencia Tuercas y Tornillos",
        "estado": "activo" if estado["activo"] else "detenido",
        "modelo": MODELO_PATH,
        "endpoints": {
            "video": "/video_feed",
            "detecciones": "/api/detecciones",
            "contadores": "/api/contadores",
            "control": "/api/control/<iniciar|detener>",
        }
    })


@app.route('/video_feed')
def video_feed():
    """Stream MJPEG para mostrar en un <img> tag."""
    return Response(
        generar_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/detecciones')
def api_detecciones():
    """Últimas detecciones."""
    limite = request.args.get('limite', 50, type=int)
    return jsonify({
        "detecciones": list(historial_detecciones)[-limite:],
        "total": len(historial_detecciones),
    })


@app.route('/api/contadores')
def api_contadores():
    return jsonify(estado["contadores"])


@app.route('/api/contadores/reset', methods=['POST'])
def api_reset_contadores():
    estado["contadores"] = {
        "tuercas": 0, "tornillos": 0,
        "objetos_extranos": 0, "total": 0,
    }
    historial_detecciones.clear()
    return jsonify({"status": "ok", "msg": "Contadores reseteados"})


@app.route('/api/control/iniciar', methods=['POST'])
def api_iniciar():
    estado["activo"] = True
    socketio.emit("cambio_estado", {"estado": "en_ejecucion"})
    return jsonify({"status": "ok", "msg": "Detección iniciada"})


@app.route('/api/control/detener', methods=['POST'])
def api_detener():
    estado["activo"] = False
    socketio.emit("cambio_estado", {"estado": "detenido"})
    return jsonify({"status": "ok", "msg": "Detección detenida"})


@app.route('/api/config', methods=['POST'])
def api_config():
    data = request.get_json()
    if "confianza_min" in data:
        estado["confianza_min"] = float(data["confianza_min"])
    return jsonify({"status": "ok"})


@app.route('/api/status')
def api_status():
    return jsonify({
        "activo": estado["activo"],
        "fps": estado["fps_actual"],
        "contadores": estado["contadores"],
        "confianza_min": estado["confianza_min"],
        "ultima_deteccion": estado["ultima_deteccion"],
    })


# ─── Socket.IO ────────────────────────────────────────────────────────────────
@socketio.on('connect')
def on_connect():
    print("🌐 Cliente conectado")
    emit("status", {
        "activo": estado["activo"],
        "contadores": estado["contadores"],
    })


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    cargar_modelo()

    # Iniciar hilo de captura
    hilo = threading.Thread(target=hilo_captura_inferencia, daemon=True)
    hilo.start()

    print("\n" + "=" * 60)
    print("  Servidor de inferencia listo")
    print(f"  Video stream : http://0.0.0.0:5000/video_feed")
    print(f"  API status   : http://0.0.0.0:5000/api/status")
    print("=" * 60)

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
