"""
captura_dataset.py — Captura de imágenes en la Raspberry Pi
============================================================
Ejecutar en la Raspberry Pi conectada a la cámara.
Captura frames y los guarda en una carpeta para luego
transferirlos a la laptop y etiquetarlos.

Uso:
    python captura_dataset.py

Controles:
    ESPACIO  → Capturar frame actual
    A        → Activar/desactivar captura automática (cada N segundos)
    Q        → Salir

Dependencias:
    pip install opencv-python
"""

import cv2
import os
import time
from datetime import datetime

# ─── Configuración ────────────────────────────────────────────────────────────
CARPETA_SALIDA = "dataset_crudo"
RESOLUCION = (640, 480)          # Resolución de captura
CAMARA_INDEX = 0                 # 0 = cámara por defecto, o ruta a video
INTERVALO_AUTO = 1.5             # Segundos entre capturas automáticas
PREFIJO = "pieza"                # Prefijo para los archivos


def crear_carpeta():
    """Crea la carpeta de salida si no existe."""
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    print(f"📁 Carpeta de salida: {os.path.abspath(CARPETA_SALIDA)}")


def nombre_archivo():
    """Genera un nombre único basado en timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return f"{PREFIJO}_{ts}.jpg"


def main():
    crear_carpeta()

    cap = cv2.VideoCapture(CAMARA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])

    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        return

    print("✅ Cámara abierta")
    print("─" * 50)
    print("  ESPACIO  → Capturar frame")
    print("  A        → Captura automática ON/OFF")
    print("  Q        → Salir")
    print("─" * 50)

    contador = 0
    auto_captura = False
    ultimo_auto = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error leyendo frame")
            break

        # ─── Mostrar info en pantalla ─────────────────────────────────────
        display = frame.copy()
        estado = "AUTO" if auto_captura else "MANUAL"
        color = (0, 255, 0) if auto_captura else (0, 200, 255)
        cv2.putText(display, f"Modo: {estado} | Capturas: {contador}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display, "ESPACIO=Capturar | A=Auto | Q=Salir",
                    (10, RESOLUCION[1] - 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (150, 150, 150), 1)

        cv2.imshow("Captura Dataset - Tuercas y Tornillos", display)

        # ─── Captura automática ───────────────────────────────────────────
        if auto_captura and (time.time() - ultimo_auto) >= INTERVALO_AUTO:
            archivo = nombre_archivo()
            ruta = os.path.join(CARPETA_SALIDA, archivo)
            cv2.imwrite(ruta, frame)
            contador += 1
            ultimo_auto = time.time()
            print(f"📸 [{contador}] Auto: {archivo}")

        # ─── Teclas ───────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):  # Espacio → captura manual
            archivo = nombre_archivo()
            ruta = os.path.join(CARPETA_SALIDA, archivo)
            cv2.imwrite(ruta, frame)
            contador += 1
            print(f"📸 [{contador}] Manual: {archivo}")

        elif key == ord('a') or key == ord('A'):
            auto_captura = not auto_captura
            modo = "ACTIVADA" if auto_captura else "DESACTIVADA"
            print(f"🔄 Captura automática: {modo}")
            ultimo_auto = time.time()

        elif key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Total de imágenes capturadas: {contador}")
    print(f"📁 Guardadas en: {os.path.abspath(CARPETA_SALIDA)}")
    print("\nSiguiente paso: transferir a la laptop con:")
    print(f"  scp -r pi@<IP_RASPBERRY>:{os.path.abspath(CARPETA_SALIDA)} .")


if __name__ == "__main__":
    main()
