from ultralytics import YOLO

# Modell laden, z. B. das vortrainierte Nano-Modell
model = YOLO('yolov8n.pt')

# Training starten
results = model.train(
    data='C:/mySciebo/_SRO/Yolo/save/yolo_duplo.yaml',
    imgsz=640,
    epochs=50,
    batch=8,
    name='yolov8_duplo_custom'
)
