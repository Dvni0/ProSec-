import cv2
import time
import json
import serial
import math
import numpy as np
import warnings
import joblib
import xgboost as xgb
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

# Constantes de Cores
COLOR_YELLOW = "#F4B400"
COLOR_RED = "#D9383A"
COLOR_GREEN = "#2D9C56"

class OperationalRiskPredictor:
    """Aplica o modelo histórico treinado com as features preservadas no scaler."""

    RISK_BY_CLASS = {0: 100, 1: 75, 2: 45, 3: 15}

    def __init__(self, model_path, scaler_path):
        self.model = None
        self.scaler = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.scaler = joblib.load(scaler_path)
            self.model = xgb.XGBClassifier()
            self.model.load_model(model_path)
            if self.scaler.n_features_in_ != 6 or self.model.n_features_in_ != 6:
                raise ValueError("O modelo de risco deve receber exatamente 6 features")
            print("✓ Modelo histórico de risco carregado")
        except Exception as error:
            print(f"⚠ Modelo histórico indisponível: {error}")

    def predict(self, features):
        if self.model is None or self.scaler is None:
            return None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scaled_features = self.scaler.transform(np.asarray([features], dtype=float))
                probabilities = self.model.predict_proba(scaled_features)[0]
            predicted_class = int(self.model.classes_[int(np.argmax(probabilities))])
            risk_score = round(sum(
                probability * self.RISK_BY_CLASS.get(int(class_id), 50)
                for probability, class_id in zip(probabilities, self.model.classes_)
            ))
            return min(max(risk_score, 0), 100), predicted_class
        except Exception as error:
            print(f"⚠ Falha na previsão histórica: {error}")
            return None


class SafetyPipelineThread(QThread):
    """
    Thread responsável exclusivamente pela lógica de IA, Visão Computacional,
    cálculo de risco (RULA) e comunicação de hardware (ESP32).
    """
    frame_updated = Signal(QImage)
    camera_error = Signal(str)
    # status_postura, status_epi, risco_texto, cor_hex, risco_percentual
    metrics_updated = Signal(str, str, str, str, int) 

    def __init__(self, porta_serial='COM3', baudrate=115200, camera_index=0):
        super().__init__()
        self.stop_flag = False
        self.camera_index = camera_index
        source_root = Path(__file__).resolve().parents[1]
        
        # Carregamento dos modelos
        self.model_pose = YOLO(source_root / 'models' / 'yolo26n-pose.pt')
        self.model_epi = YOLO(source_root / 'models' / 'modelo_treino_mario.pt')
        project_root = Path(__file__).resolve().parents[2]
        self.risk_predictor = OperationalRiskPredictor(
            project_root / 'modelos' / 'xgboost_risco_operacional.json',
            project_root / 'modelos' / 'scaler_integrado.pkl'
        )
        self.active_tags = {
            "postura": True, "capacete": True, "colete": True,
            "oculos": True, "luvas": True, "botas": True
        }
        # Pontos normalizados (0.0 a 1.0), independentes da resolução da câmera.
        self.dead_zones = []
        # Configuração da comunicação USB com ESP32
        self.esp32_conn = None
        try:
            self.esp32_conn = serial.Serial(porta_serial, baudrate, timeout=1)
            print(f"✓ Conectado ao ESP32 na porta {porta_serial}")
        except Exception as e:
            print(f"⚠ Aviso: ESP32 não conectado em {porta_serial}. Erro: {e}")

    def set_tags(self, tags_dict):
        """Atualiza quais validações a IA deve processar no próximo frame"""
        self.active_tags.update(tags_dict)

    def set_dead_zones(self, zones):
        """Atualiza os polígonos nos quais a IA não deve procurar ocorrências."""
        self.dead_zones = [
            [(max(0.0, min(1.0, float(x))), max(0.0, min(1.0, float(y)))) for x, y in zone]
            for zone in zones
            if len(zone) >= 3
        ]

    def _apply_dead_zones(self, frame):
        if not self.dead_zones:
            return frame

        masked_frame = frame.copy()
        height, width = frame.shape[:2]
        for zone in self.dead_zones:
            polygon = np.array(
                [[round(x * width), round(y * height)] for x, y in zone],
                dtype=np.int32
            )
            cv2.fillPoly(masked_frame, [polygon], (0, 0, 0))
        return masked_frame

    def _draw_dead_zones(self, frame):
        if not self.dead_zones:
            return frame

        overlay = frame.copy()
        height, width = frame.shape[:2]
        for zone in self.dead_zones:
            polygon = np.array(
                [[round(x * width), round(y * height)] for x, y in zone],
                dtype=np.int32
            )
            cv2.fillPoly(overlay, [polygon], (80, 80, 80))
            cv2.polylines(frame, [polygon], True, (180, 180, 180), 2)
        return cv2.addWeighted(overlay, 0.28, frame, 0.72, 0)


        
    def run(self):
        # Inicializa a câmera selecionada no menu
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.camera_error.emit(f"Não foi possível abrir a câmera: {self.camera_index}")
            print("❌ Nenhuma câmera funcional encontrada.")
            return

        while not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                continue

            # A máscara impede que pixels de zonas mortas influenciem as detecções.
            detection_frame = self._apply_dead_zones(frame)

            # 1. Inferência dos Modelos (Filtrada nativamente para bloquear o .plot() de classes indesejadas)
            results_pose = self.model_pose(detection_frame, verbose=False, conf=0.5) if self.active_tags["postura"] else None
            
            # IDs de classe assumidos: 0=Capacete, 1=Colete, 2=Óculos, 3=Luvas, 4=Botas. Ajuste se o seu modelo diferir.
            classes_permitidas = []
            if self.active_tags["capacete"]: classes_permitidas.append(0)
            if self.active_tags["colete"]: classes_permitidas.append(1)
            if self.active_tags["oculos"]: classes_permitidas.append(2)
            if self.active_tags["luvas"]: classes_permitidas.append(3)
            if self.active_tags["botas"]: classes_permitidas.append(4)
            
            if len(classes_permitidas) > 0:
                results_epi = self.model_epi(detection_frame, verbose=False, conf=0.5, classes=classes_permitidas)
            else:
                results_epi = None
            
            # Variáveis iniciais
            postura_score = 0
            status_postura = "Postura: OK"
            angulo_tronco = 0.0
            angulo_secundario = 0.0
            dx = 0.0
            dy = 0.0
            
            # EPI (0: Sem Capacete, 1: Sem Colete) - Supondo ID das classes
            epi_score = 0
            epi_ausentes = []
            
            # 2. Lógica de Postura (Baseado no RULA - Tronco e Pescoço)
            if self.active_tags["postura"] and results_pose and results_pose[0].keypoints is not None and len(results_pose[0].keypoints.xy) > 0:
                keypoints = results_pose[0].keypoints.xy[0].cpu().numpy()
                if len(keypoints) > 12: # Verifica se há pontos suficientes mapeados
                    # Pega ombro (ID 5 ou 6) e quadril (ID 11 ou 12) para calcular a inclinação do tronco
                    ombro_y = (keypoints[5][1] + keypoints[6][1]) / 2
                    ombro_x = (keypoints[5][0] + keypoints[6][0]) / 2
                    quadril_y = (keypoints[11][1] + keypoints[12][1]) / 2
                    quadril_x = (keypoints[11][0] + keypoints[12][0]) / 2
                    
                    if quadril_y > 0 and ombro_y > 0:
                        dx = ombro_x - quadril_x
                        dy = quadril_y - ombro_y
                        angulo_tronco = math.degrees(math.atan2(abs(dx), dy))

                    nariz_x, nariz_y = keypoints[0]
                    if ombro_y > 0 and nariz_y > 0:
                        angulo_secundario = math.degrees(math.atan2(abs(nariz_x - ombro_x), abs(ombro_y - nariz_y)))
                        
                        # Tabela simplificada RULA para Tronco:
                        if angulo_tronco < 10:
                            postura_score = 10
                            status_postura = f"Normal ({int(angulo_tronco)}°)"
                        elif 10 <= angulo_tronco <= 20:
                            postura_score = 30
                            status_postura = f"Atenção ({int(angulo_tronco)}°)"
                        elif 20 < angulo_tronco <= 60:
                            postura_score = 60
                            status_postura = f"Risco ({int(angulo_tronco)}°)"
                        else:
                            postura_score = 90
                            status_postura = f"Perigo ({int(angulo_tronco)}°)"

                # Plota esqueleto no frame
                frame = results_pose[0].plot(img=frame)

            # 3. Lógica de EPI
            # Inverte a lógica base: Se a tag está desativada, assume-se que está 'True' para não gerar multa indevida
            tem_capacete = not self.active_tags["capacete"] 
            tem_colete = not self.active_tags["colete"]
            if results_epi and results_epi[0].boxes is not None:
                for box in results_epi[0].boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id == 0 and self.active_tags["capacete"]: tem_capacete = True
                    elif cls_id == 1 and self.active_tags["colete"]: tem_colete = True
                frame = results_epi[0].plot(img=frame)
            
            if not tem_capacete: 
                epi_score += 40
                epi_ausentes.append("Capacete")
            if not tem_colete: 
                epi_score += 30
                epi_ausentes.append("Colete")
                
            status_epi = "EPI: OK" if epi_score == 0 else f"Falta: {', '.join(epi_ausentes)}"

            # 4. Previsão histórica e cálculo do risco global
            risco_imediato = min(postura_score + epi_score, 100)
            risco_predictivo = self.risk_predictor.predict([
                angulo_tronco,
                angulo_secundario,
                dx,
                dy,
                float(tem_capacete),
                float(tem_colete)
            ])
            risco_modelo = risco_predictivo[0] if risco_predictivo else 0
            risco_percentual = max(risco_imediato, risco_modelo)
            
            if risco_percentual <= 30:
                risco_score, cor_final = "BAIXO", COLOR_GREEN
                violacao = False
            elif risco_percentual <= 60:
                risco_score, cor_final = "MÉDIO", COLOR_YELLOW
                violacao = False
            else:
                risco_score, cor_final = "ALTO", COLOR_RED
                violacao = True

            # 5. Comunicação com ESP32 via JSON (Trigger do alarme/luz)
            if violacao:
                self.send_alert_to_esp32(risco_percentual, epi_ausentes, status_postura)

            # 6. Preparar imagem e emitir Sinais para a Interface
            frame = self._draw_dead_zones(frame)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

            self.frame_updated.emit(qt_img)
            self.metrics_updated.emit(status_postura, status_epi, risco_score, cor_final, risco_percentual)

        cap.release()
        if self.esp32_conn and self.esp32_conn.is_open:
            self.esp32_conn.close()

    def send_alert_to_esp32(self, risco, epis_faltantes, postura):
        """Envia um payload JSON pela porta serial para o ESP32."""
        if self.esp32_conn and self.esp32_conn.is_open:
            payload = {
                "alarm_trigger": True,
                "risk_level": risco,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": {
                    "missing_ppe": epis_faltantes,
                    "posture_issue": postura
                }
            }
            try:
                json_data = json.dumps(payload) + "\n"
                self.esp32_conn.write(json_data.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar dados para ESP32: {e}")

    def stop(self):
        self.stop_flag = True
        self.wait()