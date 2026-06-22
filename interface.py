import sys
import os
import cv2
import csv
import time
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime
from ultralytics import YOLO

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
import pyqtgraph as pg

class IntegratedPipelineThread(QThread):
    frame_updated = Signal(QImage)
    # Envia (Texto Postura, Texto EPI, Nível de Risco, Cor Hex, Risco Percentual)
    metrics_updated = Signal(str, str, str, str, int) 

    def __init__(self):
        super().__init__()
        
        # ATRIBUTO DE STOP (Inicia como False)
        self.stop_flag = False
        
        # 1. Carrega os modelos YOLO
        self.model_pose = YOLO('YoloPoseEstimation.pt') 
        self.model_epi = YOLO('modelo_treino_mario.pt') 
        
        # 2. Inicializa os objetos de Machine Learning
        self.xgb_model = xgb.XGBClassifier()
        self.scaler = None
        self.modelos_carregados = False

        # Tenta carregar a inteligência preditiva real
        try:
            # Certifique-se de que a pasta 'modelos' existe junto ao script
            caminho_xgb = os.path.join('modelos', 'xgboost_risco_operacional.json')
            caminho_scaler = os.path.join('modelos', 'scaler_integrado.pkl')
            
            if os.path.exists(caminho_xgb) and os.path.exists(caminho_scaler):
                self.xgb_model.load_model(caminho_xgb)
                self.scaler = joblib.load(caminho_scaler)
                self.modelos_carregados = True
                print("✓ Modelos XGBoost e Scaler carregados com sucesso.")
            else:
                print("⚠ Ficheiros de modelo não encontrados. Ativando Modo Heurístico de Segurança.")
        except Exception as e:
            print(f"❌ Erro crítico ao carregar os modelos de ML: {e}")
            print("Ativando Modo Heurístico de Segurança para execução do Dashboard.")

        # 3. Configuração do histórico em CSV
        self.csv_file = 'historico_risco.csv'
        self.last_log_time = time.time()
        
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Data_Hora', 'Risco_Percentual', 'Status_Postura', 'Status_EPI'])

    def run(self):
        # 1. Busca Automática de Câmera
        cap = None
        for i in range(4): # Testa os índices de 0 a 3
            print(f"Testando câmera no índice {i}...")
            temp_cap = cv2.VideoCapture(i)
            if temp_cap.isOpened():
                ret, frame = temp_cap.read()
                if ret:
                    print(f"✓ Câmera conectada com sucesso no índice {i}!")
                    cap = temp_cap
                    break
                temp_cap.release()
        
        if cap is None:
            print("❌ Nenhuma câmera funcional encontrada. Verifique as conexões físicas.")
            return # Encerra a thread se não achar nada para não gerar erro na UI

        # 2. Laço de repetição condicionado ao stop_flag
        while not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                continue

            # Filtro de confiança para evitar falsas deteções de keypoints ou EPIs
            results_pose = self.model_pose(frame, verbose=False, conf=0.5)
            results_epi = self.model_epi(frame, verbose=False, conf=0.5)
            
            posture_features = np.zeros(4) 
            epi_features = np.zeros(2)     # [Capacete, Colete]
            
            status_postura = "Sem dados de postura"
            angulo_inclinacao = 0.0
            
            # Processa a Postura (Keypoints reais do dataset)
            if results_pose[0].keypoints is not None and len(results_pose[0].keypoints.xy) > 0:
                if results_pose[0].keypoints.xy[0].numel() > 0:
                    keypoints = results_pose[0].keypoints.xy[0].cpu().numpy()
                    
                    if len(keypoints) >= 2:
                        posture_features, angulo_inclinacao = self.calculate_body_angles(keypoints)
                        status_postura = f"Coluna: {angulo_inclinacao:.1f}°"
                        frame = results_pose[0].plot()

            # Processa os EPIs (Bounding boxes do modelo)
            if results_epi[0].boxes is not None and len(results_epi[0].boxes) > 0:
                for box in results_epi[0].boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id == 0:
                        epi_features[0] = 1 
                    elif cls_id == 1:
                        epi_features[1] = 1 
                
                frame = results_epi[0].plot(img=frame)
            
            status_epi = f"EPI: C:{int(epi_features[0])} V:{int(epi_features[1])}"

            # Cálculo de Risco (ML Real vs Modo Heurístico)
            risco_percentual = 0
            risco_score = "BAIXO"
            cor_final = "#4CAF50"

            if self.modelos_carregados:
                try:
                    combined_vector = np.concatenate((posture_features, epi_features))
                    features_scaled = self.scaler.transform([combined_vector])
                    
                    pred_class = int(self.xgb_model.predict(features_scaled)[0])
                    probabilidades = self.xgb_model.predict_proba(features_scaled)[0]
                    
                    risco_percentual = int(probabilidades[pred_class] * 100)
                    
                    mapeamento_risco = {
                        0: ("BAIXO", "#4CAF50"), 
                        1: ("MÉDIO", "#FF9800"), 
                        2: ("ALTO", "#F44336"), 
                        3: ("CRÍTICO", "#9C27B0")
                    }
                    risco_score, cor_final = mapeamento_risco.get(pred_class, ("ERRO", "#888888"))
                except Exception as inference_error:
                    print(f"Erro em tempo de inferência: {inference_error}")
            else:
                pontos_risco = 0
                
                if angulo_inclinacao > 15.0:
                    pontos_risco += min(int(angulo_inclinacao * 1.2), 40)
                
                if epi_features[0] == 0: pontos_risco += 35 
                if epi_features[1] == 0: pontos_risco += 25 
                
                risco_percentual = min(pontos_risco, 100)
                
                if risco_percentual <= 25:
                    risco_score, cor_final = "BAIXO (H)", "#4CAF50"
                elif risco_percentual <= 55:
                    risco_score, cor_final = "MÉDIO (H)", "#FF9800"
                elif risco_percentual <= 85:
                    risco_score, cor_final = "ALTO (H)", "#F44336"
                else:
                    risco_score, cor_final = "CRÍTICO (H)", "#9C27B0"

            current_time = time.time()
            if current_time - self.last_log_time >= 1.0:
                with open(self.csv_file, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow([data_hora, risco_percentual, status_postura, status_epi])
                self.last_log_time = current_time

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

            self.frame_updated.emit(qt_img)
            self.metrics_updated.emit(status_postura, status_epi, f"{risco_score} ({risco_percentual}%)", cor_final, risco_percentual)

        cap.release()

    def calculate_body_angles(self, keypoints):
        """
        Calcula a inclinação real da coluna com base nos pontos do dataset.
        Retorna o vetor de características para o modelo e o ângulo absoluto em graus.
        """
        try:
            # Ponto 0: Cervical (Pescoço), Ponto 1: Lombar (Base das costas)
            cervical = keypoints[0]
            lombar = keypoints[1]
            
            # Cálculo do ângulo em relação ao eixo vertical ideal
            dx = cervical[0] - lombar[0]
            dy = cervical[1] - lombar[1]
            
            # Ângulo absoluto em graus
            angulo_graus = float(np.abs(np.degrees(np.arctan2(dx, dy))))
            
            # Constrói o vetor de 4 dimensões esperado pelo scaler/XGBoost
            features = np.array([angulo_graus, angulo_graus * 0.8, np.abs(dx), np.abs(dy)])
            return features, angulo_graus
        except Exception:
            return np.zeros(4), 0.0

    def stop(self):
        """Método seguro de parada que altera a flag"""
        self.stop_flag = True
        self.wait()


class PostureEpiDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Segurança e Ergonomia Integrada")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #121212; color: #ffffff;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout Principal Horizontal (Vídeo e Status na esquerda, Gráfico na direita)
        self.main_h_layout = QHBoxLayout(self.central_widget)

        # ---- COLUNA ESQUERDA (Vídeo e Status) ----
        self.left_panel = QWidget()
        self.layout_left = QVBoxLayout(self.left_panel)

        self.title_label = QLabel("Análise de Risco Operacional em Tempo Real")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; padding: 10px; color: #deff9a;")
        self.layout_left.addWidget(self.title_label)

        self.video_label = QLabel("Carregando pipelines de Visão Computacional...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000; border: 2px solid #222; border-radius: 8px;")
        self.video_label.setMinimumSize(640, 480)
        self.layout_left.addWidget(self.video_label, stretch=1)

        self.panel_layout = QHBoxLayout()
        
        self.posture_widget = QLabel("Postura: Aguardando")
        self.posture_widget.setStyleSheet("background-color: #1c1c1c; padding: 15px; font-size: 16px; border-radius: 6px; text-align: center;")
        self.posture_widget.setAlignment(Qt.AlignCenter)
        
        self.epi_widget = QLabel("EPIs: Aguardando")
        self.epi_widget.setStyleSheet("background-color: #1c1c1c; padding: 15px; font-size: 16px; border-radius: 6px; text-align: center;")
        self.epi_widget.setAlignment(Qt.AlignCenter)

        self.risco_widget = QLabel("MATRIZ DE RISCO")
        self.risco_widget.setStyleSheet("padding: 15px; font-size: 20px; font-weight: bold; border-radius: 6px; text-align: center;")
        self.risco_widget.setAlignment(Qt.AlignCenter)

        self.panel_layout.addWidget(self.posture_widget)
        self.panel_layout.addWidget(self.epi_widget)
        self.panel_layout.addWidget(self.risco_widget, stretch=2)
        
        self.layout_left.addLayout(self.panel_layout)
        
        # ---- COLUNA DIREITA (Gráfico Visual) ----
        self.right_panel = QWidget()
        self.layout_right = QVBoxLayout(self.right_panel)
        
        self.graph_title = QLabel("Evolução do Risco Percentual (%)")
        self.graph_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #deff9a;")
        self.graph_title.setAlignment(Qt.AlignCenter)
        self.layout_right.addWidget(self.graph_title)

        # Configuração do pyqtgraph
        pg.setConfigOption('background', '#1c1c1c')
        pg.setConfigOption('foreground', '#ffffff')
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setYRange(0, 100)
        self.graph_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout_right.addWidget(self.graph_widget, stretch=1)

        # Estruturas de dados para armazenar o histórico na UI
        self.time_data = list(range(60)) # Mostra os últimos 60 segundos
        self.risk_data = [0] * 60
        
        self.pen = pg.mkPen(color='#E53935', width=3)
        self.data_line = self.graph_widget.plot(self.time_data, self.risk_data, pen=self.pen)

        # Adiciona as colunas ao layout principal
        self.main_h_layout.addWidget(self.left_panel, stretch=2)
        self.main_h_layout.addWidget(self.right_panel, stretch=1)

        # ---- INICIALIZAÇÃO DA THREAD ----
        self.pipeline_thread = IntegratedPipelineThread()
        self.pipeline_thread.frame_updated.connect(self.update_video_feed)
        self.pipeline_thread.metrics_updated.connect(self.update_metrics_ui)
        self.pipeline_thread.start()

    def update_video_feed(self, qt_img):
        pixmap = QPixmap.fromImage(qt_img)
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
        ))

    def update_metrics_ui(self, postura, epi, risco_texto, cor, risco_percentual):
        # Atualiza Status de Texto
        self.posture_widget.setText(f"Status Corporal:\n{postura}")
        self.epi_widget.setText(f"Detecção de EPI:\n{epi}")
        self.risco_widget.setText(f"RISCO: {risco_texto}")
        self.risco_widget.setStyleSheet(f"background-color: {cor}; color: #ffffff; font-size: 22px; font-weight: bold; padding: 15px; border-radius: 6px;")

        # Atualiza o Gráfico dinamicamente
        self.risk_data = self.risk_data[1:]  # Remove o dado mais antigo
        self.risk_data.append(risco_percentual) # Adiciona a nova predição percentual
        self.data_line.setData(self.time_data, self.risk_data) # Renderiza a linha

    def closeEvent(self, event):
        self.pipeline_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PostureEpiDashboard()
    window.show()
    sys.exit(app.exec())