import cv2
from ultralytics import YOLO

# 1. Carregar exclusivamente o modelo de Pose
# Certifique-se de que o arquivo .pt está no mesmo diretório do script
caminho_modelo = 'YoloPoseEstimation.pt'
model_pose = YOLO(caminho_modelo)

# 2. Iniciar a captura da webcam padrão
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Erro: Não foi possível acessar a webcam.")
    exit()

print(f"Modelo '{caminho_modelo}' carregado com sucesso.")
print("Pressione a tecla 'q' na janela do vídeo para encerrar o teste.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Falha ao capturar imagem da câmera.")
        break

    # 3. Rodar a inferência do YOLO
    # conf=0.5 ajuda a filtrar falsos positivos e ruídos do fundo
    results = model_pose(frame, conf=0.5, verbose=False)

    # 4. Extrair e validar os Keypoints no terminal (Opcional, para debug matemático)
    if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
        if results[0].keypoints.xy[0].numel() > 0:
            # Pega as coordenadas X e Y dos pontos encontrados
            pontos = results[0].keypoints.xy[0].cpu().numpy()
            quantidade_pontos = len(pontos)
            
            # Imprime no terminal apenas para confirmar que os dados numéricos existem
            # print(f"Pessoa detectada! {quantidade_pontos} keypoints extraídos.")

    # 5. Renderizar visualmente o esqueleto gerado pelo YOLO na imagem
    frame_anotado = results[0].plot()

    # 6. Exibir a janela do OpenCV
    cv2.imshow('Teste Isolado - YOLO Pose Estimation', frame_anotado)

    # 7. Condição de saída: aguarda 1 milissegundo e verifica se 'q' foi pressionado
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Teste encerrado pelo usuário.")
        break

# 8. Limpar recursos da memória
cap.release()
cv2.destroyAllWindows()