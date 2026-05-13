"""
captura_laptop.py — Captura de imágenes (interfaz minimalista)
================================================================
Uso:
    python captura_laptop.py

Controles:
    1        → Clase: TORNILLO
    2        → Clase: TUERCA
    ESPACIO  → Capturar
    A        → Auto captura ON/OFF
    R        → Resetear contadores
    Q        → Salir
"""

import cv2
import numpy as np
import os
import time
from datetime import datetime

# ─── Configuración ────────────────────────────────────────────────────────────
CARPETA_SALIDA = "train"
RESOLUCION = (640, 480)
CAMARA_INDEX = 0
INTERVALO_AUTO = 1.0

CLASES = {1: "tornillo", 2: "tuerca"}
COLORES = {1: (210, 160, 40), 2: (80, 200, 100)}


def overlay_rect(img, x, y, w, h, color, alpha=0.7):
    """Rectángulo semitransparente."""
    y1, y2 = max(0, y), min(img.shape[0], y + h)
    x1, x2 = max(0, x), min(img.shape[1], x + w)
    sub = img[y1:y2, x1:x2]
    rect = np.full_like(sub, color, dtype=np.uint8)
    cv2.addWeighted(rect, 1 - alpha, sub, alpha, 0, sub)


def draw_hud(display, w, h, nombre, color, modo_auto, contadores):
    """Interfaz minimalista sobre el frame."""
    total = contadores["tornillo"] + contadores["tuerca"]

    # Barra superior
    overlay_rect(display, 0, 0, w, 44, (12, 14, 18), alpha=0.15)
    cv2.line(display, (0, 44), (w, 44), (40, 40, 45), 1)

    # Dot + titulo
    cv2.circle(display, (18, 22), 4, color, -1)
    cv2.putText(display, "CAPTURA", (30, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 225), 1, cv2.LINE_AA)

    # Pill de clase activa
    label = nombre.upper()
    (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    px = 110
    pill_w = tw + 20
    overlay_rect(display, px, 10, pill_w, 24, color, alpha=0.75)
    cv2.putText(display, label, (px + 10, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    # Indicador auto
    if modo_auto:
        ax = px + pill_w + 14
        cv2.circle(display, (ax + 4, 22), 4, (80, 200, 100), -1)
        cv2.putText(display, "AUTO", (ax + 14, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 200, 100), 1, cv2.LINE_AA)

    # Contadores a la derecha
    stats = f"T:{contadores['tornillo']}  N:{contadores['tuerca']}  [{total}]"
    (sw, _), _ = cv2.getTextSize(stats, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    cv2.putText(display, stats, (w - sw - 14, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (130, 130, 140), 1, cv2.LINE_AA)

    # Barra inferior
    overlay_rect(display, 0, h - 28, w, 28, (12, 14, 18), alpha=0.15)
    cv2.line(display, (0, h - 28), (w, h - 28), (40, 40, 45), 1)
    cv2.putText(display, "1 Tornillo   2 Tuerca   ESPACIO Capturar   A Auto   R Reset   Q Salir",
                (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (85, 85, 95), 1, cv2.LINE_AA)

    # Acento lateral izquierdo
    cv2.rectangle(display, (0, 44), (2, h - 28), color, -1)


def flash_effect(display, w, h):
    """Flash blanco breve al capturar."""
    overlay = display.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (255, 255, 255), -1)
    cv2.addWeighted(overlay, 0.1, display, 0.9, 0, display)


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    cap = cv2.VideoCapture(CAMARA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])

    if not cap.isOpened():
        print("Error: no se pudo abrir la camara")
        return

    contadores = {"tornillo": 0, "tuerca": 0}
    for f in os.listdir(CARPETA_SALIDA):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            if f.startswith("tornillo"): contadores["tornillo"] += 1
            elif f.startswith("tuerca"): contadores["tuerca"] += 1

    print(f"Carpeta: {os.path.abspath(CARPETA_SALIDA)}")
    print(f"Tornillos: {contadores['tornillo']}  Tuercas: {contadores['tuerca']}")

    clase_actual = 1
    auto_captura = False
    ultimo_auto = time.time()
    flash_hasta = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        h, w = display.shape[:2]
        nombre = CLASES[clase_actual]
        color = COLORES[clase_actual]

        draw_hud(display, w, h, nombre, color, auto_captura, contadores)

        if time.time() < flash_hasta:
            flash_effect(display, w, h)

        # Auto captura
        if auto_captura and (time.time() - ultimo_auto) >= INTERVALO_AUTO:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            cv2.imwrite(os.path.join(CARPETA_SALIDA, f"{nombre}_{ts}.jpg"), frame)
            contadores[nombre] += 1
            ultimo_auto = time.time()
            flash_hasta = time.time() + 0.12

        cv2.imshow("Captura", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('1'):
            clase_actual = 1
        elif key == ord('2'):
            clase_actual = 2
        elif key == ord(' '):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            cv2.imwrite(os.path.join(CARPETA_SALIDA, f"{nombre}_{ts}.jpg"), frame)
            contadores[nombre] += 1
            flash_hasta = time.time() + 0.12
        elif key == ord('a') or key == ord('A'):
            auto_captura = not auto_captura
            ultimo_auto = time.time()
        elif key == ord('r') or key == ord('R'):
            contadores = {"tornillo": 0, "tuerca": 0}
        elif key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTornillos: {contadores['tornillo']}  Tuercas: {contadores['tuerca']}  Total: {contadores['tornillo'] + contadores['tuerca']}")


if __name__ == "__main__":
    main()
