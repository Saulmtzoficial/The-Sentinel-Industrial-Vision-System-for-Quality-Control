# Pipeline de Detección — Tuercas y Tornillos
## Guía completa paso a paso

---

## Arquitectura

```
┌─────────────────────┐         ┌──────────────────────┐
│   RASPBERRY PI      │         │      LAPTOP          │
│                     │  SSH/   │                      │
│  • Cámara           │  SCP    │  • Etiquetado        │
│  • Captura dataset ─┼────────►│  • Entrenamiento     │
│  • Inferencia YOLO  │◄────────┼  • Exportación NCNN  │
│  • Servidor Flask   │ modelo  │  • GPU (CUDA)        │
└─────────────────────┘         └──────────────────────┘
```

---

## FASE 1 — Captura de imágenes (Raspberry Pi)

### 1.1 Instalar dependencias en la Raspberry Pi

```bash
pip install opencv-python
```

### 1.2 Capturar imágenes

```bash
python captura_dataset.py
```

- Coloca piezas en la banda: tuercas, tornillos, objetos extraños
- Usa **ESPACIO** para captura manual o **A** para automática
- Captura al menos **100-200 imágenes por clase** (más = mejor)
- Varía posiciones, rotaciones, cantidad de piezas por frame
- Incluye frames con múltiples piezas juntas
- Incluye frames sin piezas (fondo vacío)

### 1.3 Transferir a la laptop

```bash
# Desde la laptop:
scp -r pi@<IP_RASPBERRY>:~/dataset_crudo ./dataset_crudo
```

---

## FASE 2 — Etiquetado (Laptop)

### 2.1 Opción A: LabelImg (offline, gratis)

```bash
pip install labelImg
labelImg ./dataset_crudo
```

Configuración en LabelImg:
1. Cambiar formato a **YOLO** (botón izquierdo)
2. Abrir directorio de imágenes
3. Cambiar directorio de guardado al mismo
4. Dibujar bounding boxes con solo 2 clases:
   - `tuerca` (clase 0)
   - `tornillo` (clase 1)
   - **NO etiquetar objetos extraños** — se detectan por descarte

### 2.2 Opción B: Roboflow (online, más rápido)

1. Ir a https://roboflow.com (gratis para proyectos pequeños)
2. Crear proyecto → Object Detection
3. Subir imágenes
4. Etiquetar solo con 2 clases: tuerca y tornillo
5. Exportar en formato **YOLOv8**

### 2.3 Resultado esperado

Después de etiquetar, organiza así:

```
etiquetado/
├── images/
│   ├── pieza_001.jpg
│   ├── pieza_002.jpg
│   └── ...
└── labels/
    ├── pieza_001.txt      ← mismo nombre que la imagen
    ├── pieza_002.txt
    └── ...
```

Cada `.txt` contiene una línea por objeto detectado:

```
0 0.45 0.52 0.12 0.15
1 0.70 0.30 0.08 0.20
```

Formato: `clase x_centro y_centro ancho alto` (normalizado 0-1)

---

## FASE 3 — Entrenamiento (Laptop)

### 3.1 Instalar dependencias

```bash
pip install ultralytics torch torchvision pyyaml
```

Verificar que CUDA funciona:

```python
import torch
print(torch.cuda.is_available())       # True
print(torch.cuda.get_device_name(0))   # Tu GPU
```

### 3.2 Preparar dataset

```bash
python entrenar_modelo.py preparar etiquetado
```

Esto crea la estructura:

```
dataset/
├── data.yaml
├── train/
│   ├── images/
│   └── labels/
└── val/
    ├── images/
    └── labels/
```

### 3.3 Entrenar

```bash
python entrenar_modelo.py entrenar
```

El entrenamiento tarda entre 20 min y 2 horas según tu GPU.
Resultados en `runs/entrenar/tuercas_tornillos/`.

### 3.4 Validar

```bash
python entrenar_modelo.py validar
```

Busca un mAP50 > 0.85 para buen rendimiento.

### 3.5 Exportar para Raspberry Pi

```bash
python entrenar_modelo.py exportar
```

Genera el modelo en formato NCNN (óptimo para ARM/Raspberry Pi).

---

## FASE 4 — Deploy en Raspberry Pi

### 4.1 Instalar dependencias en la Raspberry Pi

```bash
pip install ultralytics opencv-python flask flask-socketio
```

### 4.2 Copiar el modelo entrenado

```bash
# Desde la laptop:
scp -r runs/entrenar/tuercas_tornillos/weights/best_ncnn_model/ pi@<IP>:~/modelo/
```

### 4.3 Ejecutar servidor de inferencia

```bash
python inferencia_servidor.py
```

**Lógica de descarte (objeto extraño):**
El modelo solo conoce 2 clases (tuerca y tornillo). El servidor
usa dos umbrales de confianza:
- `CONFIANZA_ALTA = 0.65` → el modelo está seguro → tuerca o tornillo
- `CONFIANZA_MIN = 0.30` → el modelo ve algo pero no sabe qué es → objeto extraño

Puedes ajustar estos umbrales en `inferencia_servidor.py` según
qué tan estricto quieras que sea el filtro.

El servidor expone:
- `http://<IP_RASP>:5000/video_feed` → Stream MJPEG con bounding boxes
- `http://<IP_RASP>:5000/api/status` → Estado y contadores
- `http://<IP_RASP>:5000/api/detecciones` → Historial de detecciones
- `http://<IP_RASP>:5000/api/control/iniciar` → Iniciar detección
- `http://<IP_RASP>:5000/api/control/detener` → Detener detección

---

## FASE 5 — Conectar con la interfaz web (Laptop)

En tu `APP.PY` de la laptop, puedes consumir el stream y la API
de la Raspberry Pi. Modifica el `index.html` para apuntar el
video al stream de la Raspberry:

```html
<img src="http://<IP_RASPBERRY>:5000/video_feed" 
     style="width:100%; height:auto;" />
```

O puedes hacer fetch a la API de detecciones desde el JavaScript
para actualizar contadores en tiempo real.

---

## Tips para buen rendimiento

### Captura
- Fondo negro uniforme de la banda → fácil de separar
- Buena iluminación constante (evitar sombras variables)
- Mínimo 150 imágenes por clase, ideal 300+
- Incluir piezas parcialmente visibles (entrando/saliendo del frame)

### Entrenamiento
- YOLOv8n (nano) es el balance ideal para Raspberry Pi
- Si la precisión no es suficiente, probar YOLOv8s (small)
- Usar augmentaciones de rotación (las piezas giran en la banda)
- El fondo negro ayuda mucho al modelo

### Inferencia en Raspberry Pi
- Formato NCNN es 2-3x más rápido que ONNX en ARM
- Resolución 640x480 es buen balance velocidad/precisión
- Con YOLOv8n + NCNN espera ~5-10 FPS en RPi 4, ~15+ en RPi 5

---

## Estructura de archivos final

```
raspberry_pi/
├── captura_dataset.py          ← Fase 1: capturar imágenes
├── inferencia_servidor.py      ← Fase 4: correr modelo
├── modelo/
│   └── best_ncnn_model/        ← Modelo exportado
└── dataset_crudo/              ← Imágenes capturadas

laptop/
├── entrenar_modelo.py          ← Fases 2-3: entrenar y exportar
├── etiquetado/
│   ├── images/
│   └── labels/
├── dataset/
│   ├── data.yaml
│   ├── train/
│   └── val/
└── runs/
    └── entrenar/
        └── tuercas_tornillos/
            └── weights/
                ├── best.pt
                ├── best.onnx
                └── best_ncnn_model/
```
