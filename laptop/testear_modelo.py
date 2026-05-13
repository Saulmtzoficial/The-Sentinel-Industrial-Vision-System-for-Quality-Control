"""
testear_modelo.py — Probar el modelo YOLOv8 en la laptop
=========================================================
Abre la cámara de la laptop y muestra las detecciones en
tiempo real con bounding boxes.

Uso:
    python testear_modelo.py

Controles:
    Q        → Salir
    S        → Capturar screenshot con detecciones
    +/-      → Subir/bajar umbral de confianza alta (objeto extraño)
    ESPACIO  → Pausar/reanudar
    R        → Resetear contadores

Dependencias:
    pip install ultralytics opencv-python
"""

import cv2
import time
import os
from datetime import datetime
from ultralytics import YOLO

# ─── Configuración ────────────────────────────────────────────────────────────
MODELO_PATH    = "runs/detect/runs/entrenar/tuercas_tornillos/weights/best.pt"
CAMARA_INDEX   = 0                     # 0 = webcam por defecto
RESOLUCION     = (640, 480)
CONFIANZA_MIN  = 0.30                  # Umbral bajo: detectar cualquier objeto
CONFIANZA_ALTA = 0.65                  # Umbral alto: aceptar como tuerca/tornillo
CARPETA_CAPTURAS = "capturas_test"

# Clases (deben coincidir con el entrenamiento)
NOMBRES_CLASE = {
    0: "Tornillo",
    1: "Tuerca",
    -1: "Obj. Extrano",
}

# Colores BGR
COLORES = {
    0: (255, 180, 0),    # tornillo → cyan
    1: (0, 255, 120),    # tuerca → verde
    -1: (0, 0, 255),     # objeto extraño → rojo
}


def main():
    global CONFIANZA_ALTA

    os.makedirs(CARPETA_CAPTURAS, exist_ok=True)

    # ─── Cargar modelo ────────────────────────────────────────────────
    print(f"🔄 Cargando modelo: {MODELO_PATH}")
    if not os.path.exists(MODELO_PATH):
        print(f"❌ No se encontró el modelo en: {MODELO_PATH}")
        print("   Verifica la ruta o cambia MODELO_PATH en el script.")
        return

    model = YOLO(MODELO_PATH)
    print("✅ Modelo cargado")

    # ─── Abrir cámara ─────────────────────────────────────────────────
    cap = cv2.VideoCapture(CAMARA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])

    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        return

    print("✅ Cámara abierta")
    print("─" * 50)
    print("  Q        → Salir")
    print("  S        → Capturar screenshot")
    print("  +/-      → Ajustar umbral de confianza")
    print("  ESPACIO  → Pausar / Reanudar")
    print("  R        → Resetear contadores")
    print("─" * 50)

    contadores = {"tornillos": 0, "tuercas": 0, "objetos_extranos": 0}
    pausado = False
    fps_timer = time.time()
    fps_counter = 0
    fps_display = 0
    num_capturas = 0

    while True:
        if not pausado:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error leyendo frame")
                break

            display = frame.copy()
            h, w = frame.shape[:2]

            # ─── Inferencia ───────────────────────────────────────────
            results = model.predict(
                frame,
                conf=CONFIANZA_MIN,
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

                        # Lógica de descarte
                        if conf >= CONFIANZA_ALTA:
                            cls_id = cls_id_raw
                        else:
                            cls_id = -1  # objeto extraño

                        nombre = NOMBRES_CLASE.get(cls_id, f"Clase {cls_id}")
                        color = COLORES.get(cls_id, (255, 255, 255))
                        label = f"{nombre} {conf:.0%}"

                        # Bounding box
                        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

                        # Fondo para texto
                        (tw, th), _ = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                        )
                        cv2.rectangle(
                            display,
                            (x1, y1 - th - 10),
                            (x1 + tw + 6, y1),
                            color, -1,
                        )
                        cv2.putText(
                            display, label, (x1 + 3, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
                        )

                        detecciones_frame.append({
                            "clase": nombre,
                            "clase_id": cls_id,
                            "confianza": conf,
                        })

            # ─── Contadores ───────────────────────────────────────────
            for d in detecciones_frame:
                if d["clase_id"] == 0:
                    contadores["tornillos"] += 1
                elif d["clase_id"] == 1:
                    contadores["tuercas"] += 1
                elif d["clase_id"] == -1:
                    contadores["objetos_extranos"] += 1

            # ─── FPS ─────────────────────────────────────────────────
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                fps_display = fps_counter
                fps_counter = 0
                fps_timer = time.time()

            # ─── HUD ─────────────────────────────────────────────────
            # Panel superior oscuro
            overlay = display.copy()
            cv2.rectangle(overlay, (0, 0), (w, 95), (10, 14, 26), -1)
            cv2.addWeighted(overlay, 0.85, display, 0.15, 0, display)
            cv2.line(display, (0, 95), (w, 95), (13, 110, 253), 1)

            # Título
            cv2.putText(
                display, "INSPECCION - TEST EN VIVO",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 198, 255), 2,
            )

            # FPS
            fps_color = (0, 255, 120) if fps_display >= 15 else (0, 198, 255)
            cv2.putText(
                display, f"FPS: {fps_display}",
                (w - 120, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2,
            )

            # Contadores con colores
            cv2.putText(
                display, f"Tornillos: {contadores['tornillos']}",
                (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 180, 0), 1,
            )
            cv2.putText(
                display, f"Tuercas: {contadores['tuercas']}",
                (200, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 120), 1,
            )
            cv2.putText(
                display, f"Extranos: {contadores['objetos_extranos']}",
                (370, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1,
            )

            # Umbral
            cv2.putText(
                display,
                f"Umbral: {CONFIANZA_ALTA:.0%}  (+/- ajustar)  R=Reset  S=Captura",
                (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (122, 156, 199), 1,
            )

            # Indicador de detecciones
            n_det = len(detecciones_frame)
            if n_det > 0:
                det_text = f"{n_det} objeto{'s' if n_det > 1 else ''}"
                cv2.putText(
                    display, det_text,
                    (w - 140, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 120), 1,
                )

        else:
            # Pantalla de pausa
            overlay = display.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, display, 0.5, 0, display)
            cv2.putText(
                display, "PAUSADO",
                (w // 2 - 90, h // 2), cv2.FONT_HERSHEY_SIMPLEX,
                1.5, (0, 198, 255), 3,
            )
            cv2.putText(
                display, "ESPACIO para reanudar",
                (w // 2 - 130, h // 2 + 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (150, 150, 150), 1,
            )

        # ─── Mostrar ventana ──────────────────────────────────────────
        cv2.imshow("Test Modelo - Tuercas y Tornillos", display)

        # ─── Teclas ──────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            break

        elif key == ord('s') or key == ord('S'):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = os.path.join(CARPETA_CAPTURAS, f"test_{ts}.jpg")
            cv2.imwrite(archivo, display)
            num_capturas += 1
            print(f"📸 [{num_capturas}] Guardada: {archivo}")

        elif key == ord('+') or key == ord('='):
            CONFIANZA_ALTA = min(0.95, CONFIANZA_ALTA + 0.05)
            print(f"🔼 Umbral: {CONFIANZA_ALTA:.0%}")

        elif key == ord('-') or key == ord('_'):
            CONFIANZA_ALTA = max(0.20, CONFIANZA_ALTA - 0.05)
            print(f"🔽 Umbral: {CONFIANZA_ALTA:.0%}")

        elif key == ord(' '):
            pausado = not pausado
            print(f"{'⏸ Pausado' if pausado else '▶ Reanudado'}")

        elif key == ord('r') or key == ord('R'):
            contadores = {"tornillos": 0, "tuercas": 0, "objetos_extranos": 0}
            print("🔄 Contadores reseteados")

    # ─── Fin ──────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()

    print("\n" + "=" * 50)
    print("  RESUMEN DE PRUEBA")
    print("=" * 50)
    print(f"  Tornillos detectados  : {contadores['tornillos']}")
    print(f"  Tuercas detectadas    : {contadores['tuercas']}")
    print(f"  Objetos extraños      : {contadores['objetos_extranos']}")
    print(f"  Capturas guardadas    : {num_capturas}")
    print(f"  Umbral final          : {CONFIANZA_ALTA:.0%}")
    print("=" * 50)


if __name__ == "__main__":
    main()
