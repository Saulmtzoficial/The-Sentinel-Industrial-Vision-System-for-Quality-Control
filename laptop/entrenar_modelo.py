"""
entrenar_modelo.py — Entrenamiento de YOLOv8 en la Laptop
==========================================================
Entrena un modelo YOLOv8n (nano) para detectar:
  0: tuerca
  1: tornillo

Todo lo que el modelo detecte con baja confianza (no reconoce
como tuerca ni tornillo) se clasifica automáticamente como
"objeto extraño" por lógica de descarte en el código.

Umbrales:
  - CONFIANZA_MIN  (0.30): el modelo ve algo en el frame
  - CONFIANZA_ALTA (0.65): el modelo está seguro de la clase
  Si CONFIANZA_MIN <= conf < CONFIANZA_ALTA → objeto extraño

Uso:
    python entrenar_modelo.py

Requisitos:
    pip install ultralytics torch torchvision

Estructura esperada del dataset (formato YOLO):
    dataset/
    ├── data.yaml
    ├── train/
    │   ├── images/
    │   │   ├── pieza_001.jpg
    │   │   └── ...
    │   └── labels/
    │       ├── pieza_001.txt
    │       └── ...
    └── val/
        ├── images/
        │   └── ...
        └── labels/
            └── ...

Cada archivo .txt de etiquetas tiene el formato YOLO:
    <clase> <x_centro> <y_centro> <ancho> <alto>
    Ejemplo: 0 0.45 0.52 0.12 0.15
    (valores normalizados entre 0 y 1)
"""

from ultralytics import YOLO
import os
import yaml
import shutil
import random
from pathlib import Path


# ─── Configuración ────────────────────────────────────────────────────────────
DATASET_DIR       = "dataset"
MODELO_BASE       = "yolov8n.pt"      # nano: rápido para Raspberry Pi
EPOCHS            = 100
IMG_SIZE          = 640
BATCH_SIZE        = 8                  # Ajustado para 4GB VRAM
PROYECTO          = "runs/detect/runs/entrenar"
NOMBRE            = "tuercas_tornillos"

CLASES = {
    0: "tornillo",
    1: "tuerca",
}


def crear_data_yaml():
    """Crea el archivo data.yaml para YOLO."""
    data = {
        "path": os.path.abspath(DATASET_DIR),
        "train": "train/images",
        "val": "val/images",
        "nc": len(CLASES),
        "names": list(CLASES.values())
    }

    yaml_path = os.path.join(DATASET_DIR, "data.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    print(f"✅ Creado: {yaml_path}")
    print(f"   Clases: {list(CLASES.values())}")
    return yaml_path


def preparar_dataset(carpeta_imagenes_etiquetadas, split_ratio=0.8):
    """
    Organiza imágenes etiquetadas en estructura train/val.
    
    Acepta dos estructuras:
      A) Carpeta plana: imágenes y .txt juntos (salida de auto_etiquetar.py)
      B) Subcarpetas:   images/ + labels/
    """
    img_dir = os.path.join(carpeta_imagenes_etiquetadas, "images")
    lbl_dir = os.path.join(carpeta_imagenes_etiquetadas, "labels")

    # Detectar estructura: subcarpetas o carpeta plana
    if os.path.exists(img_dir) and os.path.exists(lbl_dir):
        modo = "subcarpetas"
    else:
        # Carpeta plana: imágenes y .txt juntos
        img_dir = carpeta_imagenes_etiquetadas
        lbl_dir = carpeta_imagenes_etiquetadas
        modo = "plana"

    print(f"📂 Estructura detectada: {modo}")

    # Obtener lista de imágenes con etiqueta
    imagenes = []
    for f in os.listdir(img_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            nombre_base = os.path.splitext(f)[0]
            label_file = os.path.join(lbl_dir, nombre_base + ".txt")
            if os.path.exists(label_file):
                imagenes.append(f)

    if not imagenes:
        print("❌ No se encontraron imágenes con etiquetas (.txt)")
        print(f"   Buscando en: {img_dir}")
        return False

    print(f"📊 Total de imágenes etiquetadas: {len(imagenes)}")

    # Shuffle y split
    random.shuffle(imagenes)
    split_idx = int(len(imagenes) * split_ratio)
    train_imgs = imagenes[:split_idx]
    val_imgs = imagenes[split_idx:]

    print(f"   Train: {len(train_imgs)} | Val: {len(val_imgs)}")

    # Crear estructura
    for subset, imgs in [("train", train_imgs), ("val", val_imgs)]:
        img_dest = os.path.join(DATASET_DIR, subset, "images")
        lbl_dest = os.path.join(DATASET_DIR, subset, "labels")
        os.makedirs(img_dest, exist_ok=True)
        os.makedirs(lbl_dest, exist_ok=True)

        for img_file in imgs:
            nombre_base = os.path.splitext(img_file)[0]
            shutil.copy2(
                os.path.join(img_dir, img_file),
                os.path.join(img_dest, img_file)
            )
            shutil.copy2(
                os.path.join(lbl_dir, nombre_base + ".txt"),
                os.path.join(lbl_dest, nombre_base + ".txt")
            )

    print("✅ Dataset organizado correctamente")
    return True


def entrenar():
    """Entrena el modelo YOLOv8."""
    yaml_path = os.path.join(DATASET_DIR, "data.yaml")

    if not os.path.exists(yaml_path):
        print("❌ No se encontró data.yaml — ejecuta crear_data_yaml() primero")
        return

    print("=" * 60)
    print("  ENTRENAMIENTO YOLOv8 — Tuercas y Tornillos")
    print("=" * 60)
    print(f"  Modelo base  : {MODELO_BASE}")
    print(f"  Epochs       : {EPOCHS}")
    print(f"  Imagen       : {IMG_SIZE}x{IMG_SIZE}")
    print(f"  Batch         : {BATCH_SIZE}")
    print(f"  Clases       : {list(CLASES.values())}")
    print("=" * 60)

    # Cargar modelo preentrenado
    model = YOLO(MODELO_BASE)

    # Entrenar
    results = model.train(
        data=yaml_path,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        project=PROYECTO,
        name=NOMBRE,
        patience=20,          # Early stopping
        save=True,
        save_period=10,       # Guardar checkpoint cada 10 epochs
        device=0,             # GPU 0 (cambiar a 'cpu' si no hay GPU)
        workers=4,
        pretrained=True,
        optimizer="auto",
        lr0=0.01,
        augment=True,
        # Augmentaciones útiles para banda transportadora
        flipud=0.5,           # Flip vertical (las piezas pueden venir en cualquier orientación)
        fliplr=0.5,           # Flip horizontal
        mosaic=1.0,
        mixup=0.1,
        degrees=180,          # Rotación completa (las piezas giran)
        scale=0.3,
        hsv_h=0.01,           # Poca variación de color (fondo negro consistente)
        hsv_s=0.3,
        hsv_v=0.3,
    )

    print("\n✅ Entrenamiento completado")
    print(f"📁 Resultados en: {PROYECTO}/{NOMBRE}/")
    print(f"📦 Mejor modelo: {PROYECTO}/{NOMBRE}/weights/best.pt")

    return results


def exportar_para_raspberry(modelo_path=None):
    """
    Exporta el modelo entrenado a formato NCNN (óptimo para Raspberry Pi).
    También exporta a ONNX como respaldo.
    """
    if modelo_path is None:
        modelo_path = f"{PROYECTO}/{NOMBRE}/weights/best.pt"

    if not os.path.exists(modelo_path):
        print(f"❌ No se encontró el modelo: {modelo_path}")
        return

    print(f"\n📦 Exportando modelo: {modelo_path}")
    model = YOLO(modelo_path)

    # Exportar a NCNN (mejor rendimiento en Raspberry Pi)
    print("\n→ Exportando a NCNN...")
    model.export(format="ncnn", imgsz=640)
    print("✅ Modelo NCNN exportado")

    # Exportar a ONNX (alternativa universal)
    print("\n→ Exportando a ONNX...")
    model.export(format="onnx", imgsz=640, simplify=True)
    print("✅ Modelo ONNX exportado")

    print("\n" + "=" * 60)
    print("  Siguiente paso: copiar el modelo a la Raspberry Pi")
    print("=" * 60)
    print(f"  scp -r {PROYECTO}/{NOMBRE}/weights/best_ncnn_model/ pi@<IP>:~/modelo/")
    print(f"  scp {PROYECTO}/{NOMBRE}/weights/best.onnx pi@<IP>:~/modelo/")


def validar_modelo(modelo_path=None):
    """Ejecuta validación y muestra métricas."""
    if modelo_path is None:
        modelo_path = f"{PROYECTO}/{NOMBRE}/weights/best.pt"

    model = YOLO(modelo_path)
    yaml_path = os.path.join(DATASET_DIR, "data.yaml")

    results = model.val(data=yaml_path, imgsz=IMG_SIZE)
    print(f"\n📊 mAP50    : {results.box.map50:.4f}")
    print(f"📊 mAP50-95 : {results.box.map:.4f}")

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        comando = sys.argv[1]

        if comando == "preparar":
            # python entrenar_modelo.py preparar <carpeta_etiquetada>
            carpeta = sys.argv[2] if len(sys.argv) > 2 else "etiquetado"
            preparar_dataset(carpeta)
            crear_data_yaml()

        elif comando == "entrenar":
            entrenar()

        elif comando == "exportar":
            exportar_para_raspberry()

        elif comando == "validar":
            validar_modelo()

        else:
            print("Comandos: preparar | entrenar | exportar | validar")
    else:
        # Flujo completo
        print("=" * 60)
        print("  Pipeline completo de entrenamiento")
        print("=" * 60)
        print("\nUso por pasos:")
        print("  1. python entrenar_modelo.py preparar etiquetado")
        print("  2. python entrenar_modelo.py entrenar")
        print("  3. python entrenar_modelo.py validar")
        print("  4. python entrenar_modelo.py exportar")
        print("\n¿Desea ejecutar el entrenamiento ahora? (s/n)")

        if input().strip().lower() == 's':
            if os.path.exists(os.path.join(DATASET_DIR, "data.yaml")):
                entrenar()
            else:
                print("❌ Primero prepara el dataset con: python entrenar_modelo.py preparar <carpeta>")
