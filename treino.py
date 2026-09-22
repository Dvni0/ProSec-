from ultralytics import YOLO

def main():
    # Carrega o modelo base
    model = YOLO('yolov8n.pt') 

    # Treina o modelo apontando para o seu data.yaml baixado
    results = model.train(
        data='/home/vin0/Desktop/Yolo/Construction-Site-Safety-1/data.yaml', 
        epochs=2, 
        imgsz=640, 
        batch=16,
        plots=True # Isso gera gráficos super úteis no final para ver como o modelo aprendeu
    )

if __name__ == '__main__':
    main()