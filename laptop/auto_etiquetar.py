"""
auto_etiquetar.py — Etiquetado automático para dataset YOLO
=============================================================
Detecta la pieza en cada imagen usando contornos (OpenCV)
y asigna la clase según el prefijo del nombre del archivo:
  - tornillo_... → clase 0
  - tuerca_...   → clase 1

Genera archivos .txt en formato YOLO junto a cada imagen.

Uso:
    python auto_etiquetar.py --carpeta train

    Opciones:
      --carpeta    Carpeta con las imágenes (default: train)
      --revisar    Muestra cada imagen con su bbox para verificar (default: no)
      --umbral     Área mínima del contorno en pixeles (default: 500)

Dependencias:
    pip install opencv-python numpy
"""

import cv2
import numpy as np
import os
import argparse
from pathlib import Path


# ─── Mapeo de clase por prefijo del nombre ────────────────────────────────────
CLASES = {
    "tornillo": 0,
    "tuerca": 1,
}


def detectar_clase(nombre_archivo: str) -> int:
    """Detecta la clase según el prefijo del nombre del archivo."""
    nombre = nombre_archivo.lower()
    for prefijo, clase_id in CLASES.items():
        if nombre.startswith(prefijo):
            return clase_id
    return -1  # No reconocido


def detectar_bbox(imagen_path: str, area_min: int = 500):
    """
    Detecta el bounding box de la pieza usando contornos.
    Retorna (x_centro, y_centro, ancho, alto) normalizado [0-1],
    o None si no encuentra nada.
    """
    img = cv2.imread(imagen_path)
    if img is None:
        return None

    h, w = img.shape[:2]

    # Convertir a escala de grises
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aplicar blur para reducir ruido
    blur = cv2.GaussianBlur(gris, (5, 5), 0)

    # Umbral adaptativo (funciona bien con fondos oscuros irregulares)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, -10
    )

    # Operaciones morfológicas para limpiar
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    # Encontrar contornos
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contornos:
        return None

    # Filtrar por área mínima
    contornos_validos = [c for c in contornos if cv2.contourArea(c) >= area_min]

    if not contornos_validos:
        return None

    # Tomar el contorno más grande (la pieza principal)
    contorno_max = max(contornos_validos, key=cv2.contourArea)

    # Bounding box
    x, y, bw, bh = cv2.boundingRect(contorno_max)

    # Agregar un pequeño margen (5%)
    margen_x = int(bw * 0.05)
    margen_y = int(bh * 0.05)
    x = max(0, x - margen_x)
    y = max(0, y - margen_y)
    bw = min(w - x, bw + 2 * margen_x)
    bh = min(h - y, bh + 2 * margen_y)

    # Convertir a formato YOLO (normalizado, centro)
    x_centro = (x + bw / 2) / w
    y_centro = (y + bh / 2) / h
    ancho_norm = bw / w
    alto_norm = bh / h

    return (x_centro, y_centro, ancho_norm, alto_norm)


def procesar_carpeta(carpeta: str, revisar: bool = False, area_min: int = 500):
    """Procesa todas las imágenes de la carpeta y genera etiquetas YOLO."""
    extensiones = {'.jpg', '.jpeg', '.png', '.bmp'}
    archivos = [f for f in os.listdir(carpeta)
                if Path(f).suffix.lower() in extensiones]

    if not archivos:
        print(f"❌ No se encontraron imágenes en: {carpeta}")
        return

    print(f"📁 Carpeta: {carpeta}")
    print(f"📷 Imágenes encontradas: {len(archivos)}")
    print("─" * 50)

    stats = {"ok": 0, "sin_bbox": 0, "sin_clase": 0, "saltadas": 0}

    for i, archivo in enumerate(sorted(archivos)):
        ruta_img = os.path.join(carpeta, archivo)
        nombre_base = Path(archivo).stem

        # Detectar clase por nombre
        clase_id = detectar_clase(archivo)
        if clase_id == -1:
            print(f"⚠️  [{i+1}/{len(archivos)}] Clase no reconocida: {archivo}")
            stats["sin_clase"] += 1
            continue

        # Detectar bounding box
        bbox = detectar_bbox(ruta_img, area_min)
        if bbox is None:
            print(f"⚠️  [{i+1}/{len(archivos)}] No se detectó pieza: {archivo}")
            stats["sin_bbox"] += 1
            continue

        x_c, y_c, an, al = bbox

        # ─── Modo revisión ────────────────────────────────────────────────
        if revisar:
            img = cv2.imread(ruta_img)
            h, w = img.shape[:2]
            x1 = int((x_c - an/2) * w)
            y1 = int((y_c - al/2) * h)
            x2 = int((x_c + an/2) * w)
            y2 = int((y_c + al/2) * h)

            clase_nombre = [k for k, v in CLASES.items() if v == clase_id][0]
            color = (0, 255, 120) if clase_id == 1 else (255, 180, 0)

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, f"{clase_nombre} ({clase_id})",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, color, 2)

            cv2.imshow("Revision - ESPACIO=OK | S=Saltar | Q=Salir", img)
            key = cv2.waitKey(0) & 0xFF

            if key == ord('q'):
                print("🛑 Revisión cancelada")
                break
            elif key == ord('s'):
                print(f"   ⏭  Saltada: {archivo}")
                stats["saltadas"] += 1
                continue

        # ─── Guardar etiqueta YOLO ────────────────────────────────────────
        ruta_label = os.path.join(carpeta, nombre_base + ".txt")
        with open(ruta_label, "w") as f:
            f.write(f"{clase_id} {x_c:.6f} {y_c:.6f} {an:.6f} {al:.6f}\n")

        stats["ok"] += 1
        if (i + 1) % 50 == 0 or i == len(archivos) - 1:
            print(f"   ✅ [{i+1}/{len(archivos)}] Procesadas...")

    if revisar:
        cv2.destroyAllWindows()

    # ─── Resumen ──────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("  RESUMEN DE ETIQUETADO")
    print("=" * 50)
    print(f"  ✅ Etiquetadas correctamente : {stats['ok']}")
    print(f"  ⚠️  Sin bounding box detectado: {stats['sin_bbox']}")
    print(f"  ⚠️  Clase no reconocida       : {stats['sin_clase']}")
    print(f"  ⏭  Saltadas en revisión      : {stats['saltadas']}")
    print("=" * 50)

    if stats["sin_bbox"] > 0:
        print(f"\n💡 Si hay muchas sin bbox, prueba ajustar --umbral (actual: {area_min})")
        print(f"   Más bajo detecta piezas más pequeñas, más alto ignora ruido.")

    if stats["ok"] > 0:
        print(f"\n✅ Archivos .txt generados en: {carpeta}")
        print("   Siguiente paso: python entrenar_modelo.py preparar train")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-etiquetado YOLO por contornos")
    parser.add_argument("--carpeta", default="train",
                        help="Carpeta con las imágenes (default: train)")
    parser.add_argument("--revisar", action="store_true",
                        help="Mostrar cada imagen para verificar el bbox")
    parser.add_argument("--umbral", type=int, default=500,
                        help="Área mínima del contorno en px (default: 500)")

    args = parser.parse_args()
    procesar_carpeta(args.carpeta, args.revisar, args.umbral)
