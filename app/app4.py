import cv2
import time
import json
import serial
import math
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

# Constantes de Cores
COLOR_YELLOW = "#F4B400"
COLOR_RED = "#D9383A"
COLOR_GREEN = "#2D9C56"

class SafetyPipelineThread(QThread):
    """
    Thread responsável exclusivamente pela lógica de IA, Visão Computacional,
    cálculo de risco (RULA) e comunicação de hardware (ESP32).
    """
    frame_updated = Signal(QImage)
    # status_postura, status_epi, risco_texto, cor_hex, risco_percentual
    metrics_updated = Signal(str, str, str, str, int) 

    def __init__(self, porta_serial='COM3', baudrate=115200, camera_index=0):
        super().__init__()
        self.stop_flag = False
        self.camera_index = camera_index
        
        # Carregamento dos modelos
        self.model_pose = YOLO('yolov8n-pose.pt') 
        self.model_epi = YOLO('modelo_treino_mario.pt') 
        self.active_tags = {
            "postura": True, "capacete": True, "colete": True,
            "oculos": True, "luvas": True, "botas": True
        }
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


        
    def run(self):
        # Inicializa a câmera selecionada no menu
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("❌ Nenhuma câmera funcional encontrada.")
            return

        while not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                continue

            # 1. Inferência dos Modelos (Filtrada nativamente para bloquear o .plot() de classes indesejadas)
            results_pose = self.model_pose(frame, verbose=False, conf=0.5) if self.active_tags["postura"] else None
            
            # IDs de classe assumidos: 0=Capacete, 1=Colete, 2=Óculos, 3=Luvas, 4=Botas. Ajuste se o seu modelo diferir.
            classes_permitidas = []
            if self.active_tags["capacete"]: classes_permitidas.append(0)
            if self.active_tags["colete"]: classes_permitidas.append(1)
            if self.active_tags["oculos"]: classes_permitidas.append(2)
            if self.active_tags["luvas"]: classes_permitidas.append(3)
            if self.active_tags["botas"]: classes_permitidas.append(4)
            
            if len(classes_permitidas) > 0:
                results_epi = self.model_epi(frame, verbose=False, conf=0.5, classes=classes_permitidas)
            else:
                results_epi = None
            
            # Variáveis iniciais
            postura_score = 0
            status_postura = "Postura: OK"
            angulo_tronco = 0.0
            
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
                frame = results_pose[0].plot()

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

            # 4. Cálculo do Risco Global
            risco_percentual = min(postura_score + epi_score, 100)
            
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
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

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