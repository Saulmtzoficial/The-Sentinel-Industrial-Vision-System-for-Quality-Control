"""
convertir_labelme.py — Convierte etiquetas de LabelMe a formato YOLO
=====================================================================
LabelMe guarda etiquetas en JSON. Este script las convierte
a archivos .txt en formato YOLO para entrenar YOLOv8.

Uso:
    python convertir_labelme.py --carpeta train

Resultado:
    Por cada archivo JSON genera un .txt YOLO en la misma carpeta.

Dependencias:
    pip install labelme2yolo  (opcional)
    Solo requiere: json, os, PIL (Pillow)
"""

import json
import os
import argparse
from pathlib import Path
from PIL import Image

# ─── Mapeo de clases ─────────────────────────────────────────────────────────
# Debe coincidir con el orden de CLASES en entrenar_modelo.py
CLASES = {
    "tornillo": 0,
    "tuerca":   1,
}


def convertir_json_a_yolo(json_path):
    """Convierte un archivo JSON de LabelMe a formato YOLO."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Obtener dimensiones de la imagen
    img_w = data.get('imageWidth')
    img_h = data.get('imageHeight')

    # Si no están en el JSON, leer de la imagen
    if not img_w or not img_h:
        img_path = json_path.replace('.json', '.jpg')
        if not os.path.exists(img_path):
            img_path = json_path.replace('.json', '.png')
        try:
            with Image.open(img_path) as img:
                img_w, img_h = img.size
        except Exception:
            return False, "No se pudo obtener dimensiones de imagen"

    shapes = data.get('shapes', [])
    if not shapes:
        return False, "Sin anotaciones"

    lineas = []
    for shape in shapes:
        label = shape.get('label', '').lower().strip()
        clase_id = CLASES.get(label)

        if clase_id is None:
            print(f"  ⚠️  Clase desconocida: '{label}' — saltando")
            continue

        shape_type = shape.get('shape_type', '')
        points = shape.get('points', [])

        if shape_type == 'rectangle' and len(points) == 2:
            # Formato rectángulo: dos puntos [[x1,y1],[x2,y2]]
            x1, y1 = points[0]
            x2, y2 = points[1]

        elif shape_type == 'polygon' and len(points) >= 3:
            # Formato polígono: extraer bounding box
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            x1, y1 = min(xs), min(ys)
            x2, y2 = max(xs), max(ys)

        else:
            print(f"  ⚠️  Tipo de forma no soportado: {shape_type} — saltando")
            continue

        # Convertir a formato YOLO (normalizado, centro)
        x_c = ((x1 + x2) / 2) / img_w
        y_c = ((y1 + y2) / 2) / img_h
        w   = abs(x2 - x1) / img_w
        h   = abs(y2 - y1) / img_h

        # Limitar a [0, 1]
        x_c = max(0.0, min(1.0, x_c))
        y_c = max(0.0, min(1.0, y_c))
        w   = max(0.0, min(1.0, w))
        h   = max(0.0, min(1.0, h))

        lineas.append(f"{clase_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")

    if not lineas:
        return False, "No se generaron etiquetas válidas"

    # Guardar .txt
    txt_path = json_path.replace('.json', '.txt')
    with open(txt_path, 'w') as f:
        f.write('\n'.join(lineas) + '\n')

    return True, f"{len(lineas)} objeto(s)"


def convertir_carpeta(carpeta):
    """Convierte todos los JSON de LabelMe en una carpeta."""
    archivos_json = list(Path(carpeta).glob('*.json'))

    if not archivos_json:
        print(f"❌ No se encontraron archivos JSON en: {carpeta}")
        return

    print(f"📁 Carpeta: {os.path.abspath(carpeta)}")
    print(f"📄 Archivos JSON encontrados: {len(archivos_json)}")
    print(f"🗂️  Clases: {CLASES}")
    print("─" * 50)

    ok = 0
    errores = 0

    for json_file in sorted(archivos_json):
        # Saltar el archivo de clases si existe
        if json_file.name == 'label_studio.json':
            continue

        exito, msg = convertir_json_a_yolo(str(json_file))

        if exito:
            ok += 1
            if ok % 100 == 0:
                print(f"   ✅ [{ok}/{len(archivos_json)}] Convertidas...")
        else:
            errores += 1
            print(f"   ❌ {json_file.name}: {msg}")

    print("\n" + "=" * 50)
    print("  RESUMEN")
    print("=" * 50)
    print(f"  ✅ Convertidas : {ok}")
    print(f"  ❌ Con errores  : {errores}")
    print(f"  📁 Archivos .txt generados en: {carpeta}")
    print("\nSiguiente paso:")
    print("  python entrenar_modelo.py preparar train")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--carpeta", default="train",
                        help="Carpeta con archivos JSON de LabelMe (default: train)")
    args = parser.parse_args()
    convertir_carpeta(args.carpeta)
