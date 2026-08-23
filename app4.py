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

from PySide6.QtCore import Qt, QPoint, QRectF, QSize, Signal, QThread
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QGridLayout,
    QScrollArea
)
import pyqtgraph as pg

# -------------------------------------------------------------
# CONFIGURAÇÕES E VARIÁVEIS DO SISTEMA ESTÁTICAS (Fallback)
# -------------------------------------------------------------
CONFIG = {
    "open_alerts": "3",                 
    "resolved_today": "12",             
    "alert_time": "14:23:17",           
    "op_name": "Vinícius",              
    "op_role": "Computer Engineering Student",       
    "op_shift": "Morning (6AM - 2PM)",   
    "op_experience_val": 2,             
    "op_experience_unit": "Years",      
    "op_compliance": "67%",             
    "daily_incidents_data": [2, 3, 5, 7, 4, 3, 3],               
    "rep_avg_risk_level": "38.4%",      
    "rep_total_incidents": "27",         
    "rep_avg_compliance": "93.7%",      
    "rep_trend": "↓ 12%",               
    "sidebar_user_name": "Vinícius",               
    "sidebar_user_role": "System Manager",      
}

# -------------------------------------------------------------
# CONSTANTES DE CORES (Paleta Dark & Safety Yellow)
# -------------------------------------------------------------
COLOR_BG_MAIN = "#121318"
COLOR_BG_SIDEBAR = "#0F1015"
COLOR_BG_CARD = "#1A1C23"
COLOR_BORDER = "#2B2E3C"
COLOR_YELLOW = "#F4B400"
COLOR_RED = "#D9383A"
COLOR_GREEN = "#2D9C56"
COLOR_TEXT_MUTED = "#717686"

# -------------------------------------------------------------
# THREAD DE MACHINE LEARNING (VISÃO + XGBOOST)
# -------------------------------------------------------------
class IntegratedPipelineThread(QThread):
    frame_updated = Signal(QImage)
    metrics_updated = Signal(str, str, str, str, int) 

    def __init__(self):
        super().__init__()
        self.stop_flag = False
        
        self.model_pose = YOLO('YoloPoseEstimation.pt') 
        self.model_epi = YOLO('modelo_treino_mario.pt') 
        
        self.xgb_model = xgb.XGBClassifier()
        self.scaler = None
        self.modelos_carregados = False

        try:
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

        self.csv_file = 'historico_risco.csv'
        self.last_log_time = time.time()
        
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Data_Hora', 'Risco_Percentual', 'Status_Postura', 'Status_EPI'])

    def run(self):
        cap = None
        for i in range(4):
            temp_cap = cv2.VideoCapture(i)
            if temp_cap.isOpened():
                ret, frame = temp_cap.read()
                if ret:
                    cap = temp_cap
                    break
                temp_cap.release()
        
        if cap is None:
            print("❌ Nenhuma câmera funcional encontrada.")
            return

        while not self.stop_flag:
            ret, frame = cap.read()
            if not ret:
                continue

            results_pose = self.model_pose(frame, verbose=False, conf=0.5)
            results_epi = self.model_epi(frame, verbose=False, conf=0.5)
            
            posture_features = np.zeros(4) 
            epi_features = np.zeros(2)
            
            status_postura = "Sem dados"
            angulo_inclinacao = 0.0
            
            if results_pose[0].keypoints is not None and len(results_pose[0].keypoints.xy) > 0:
                if results_pose[0].keypoints.xy[0].numel() > 0:
                    keypoints = results_pose[0].keypoints.xy[0].cpu().numpy()
                    if len(keypoints) >= 2:
                        posture_features, angulo_inclinacao = self.calculate_body_angles(keypoints)
                        status_postura = f"Coluna: {angulo_inclinacao:.1f}°"
                        frame = results_pose[0].plot()

            if results_epi[0].boxes is not None and len(results_epi[0].boxes) > 0:
                for box in results_epi[0].boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id == 0: epi_features[0] = 1 
                    elif cls_id == 1: epi_features[1] = 1 
                frame = results_epi[0].plot(img=frame)
            
            status_epi = f"EPI: C:{int(epi_features[0])} V:{int(epi_features[1])}"

            risco_percentual = 0
            risco_score = "BAIXO"
            cor_final = COLOR_GREEN

            if self.modelos_carregados:
                try:
                    combined_vector = np.concatenate((posture_features, epi_features))
                    features_scaled = self.scaler.transform([combined_vector])
                    pred_class = int(self.xgb_model.predict(features_scaled)[0])
                    probabilidades = self.xgb_model.predict_proba(features_scaled)[0]
                    risco_percentual = int(probabilidades[pred_class] * 100)
                    
                    mapeamento_risco = {
                        0: ("BAIXO", COLOR_GREEN), 1: ("MÉDIO", COLOR_YELLOW), 
                        2: ("ALTO", COLOR_RED), 3: ("CRÍTICO", "#9C27B0")
                    }
                    risco_score, cor_final = mapeamento_risco.get(pred_class, ("ERRO", COLOR_TEXT_MUTED))
                except Exception:
                    pass
            else:
                pontos_risco = 0
                if angulo_inclinacao > 15.0: pontos_risco += min(int(angulo_inclinacao * 1.2), 40)
                if epi_features[0] == 0: pontos_risco += 35 
                if epi_features[1] == 0: pontos_risco += 25 
                
                risco_percentual = min(pontos_risco, 100)
                if risco_percentual <= 25: risco_score, cor_final = "BAIXO", COLOR_GREEN
                elif risco_percentual <= 55: risco_score, cor_final = "MÉDIO", COLOR_YELLOW
                elif risco_percentual <= 85: risco_score, cor_final = "ALTO", COLOR_RED
                else: risco_score, cor_final = "CRÍTICO", "#9C27B0"

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
            self.metrics_updated.emit(status_postura, status_epi, risco_score, cor_final, risco_percentual)

        if cap:
            cap.release()

    def calculate_body_angles(self, keypoints):
        try:
            cervical, lombar = keypoints[0], keypoints[1]
            dx, dy = cervical[0] - lombar[0], cervical[1] - lombar[1]
            angulo_graus = float(np.abs(np.degrees(np.arctan2(dx, dy))))
            features = np.array([angulo_graus, angulo_graus * 0.8, np.abs(dx), np.abs(dy)])
            return features, angulo_graus
        except Exception:
            return np.zeros(4), 0.0

    def stop(self):
        self.stop_flag = True
        self.wait()

# -------------------------------------------------------------
# WIDGETS CUSTOMIZADOS DA INTERFACE
# -------------------------------------------------------------

class ToggleSwitch(QWidget):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.checked = checked
        self.setFixedSize(50, 26)
        
    def mousePressEvent(self, event):
        self.checked = not self.checked
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg_color = QColor(COLOR_GREEN) if self.checked else QColor(COLOR_BORDER)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        knob_color = QColor("white")
        painter.setBrush(QBrush(knob_color))
        knob_x = 28 if self.checked else 4
        painter.drawEllipse(knob_x, 3, 20, 20)

class CameraFeedWidget(QFrame):
    def __init__(self, title, location, parent=None):
        super().__init__(parent)
        self.title = title
        self.location = location
        self.init_ui()
        
    def init_ui(self):
        self.setMinimumSize(320, 240)
        self.setObjectName("cameraFeedWidget")
        self.setStyleSheet(f"QFrame#cameraFeedWidget {{ background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER}; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QWidget()
        top_bar.setFixedHeight(45)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(15, 12, 15, 0)
        
        live_badge = QLabel("● LIVE")
        live_badge.setStyleSheet(f"color: {COLOR_RED}; font-weight: bold; font-size: 11px; background-color: rgba(217, 56, 58, 0.15); border-radius: 4px; padding: 4px 8px;")
        
        self.status_badge = QLabel("NORMAL")
        self.status_badge.setStyleSheet(f"color: {COLOR_GREEN}; font-weight: bold; font-size: 11px; background-color: rgba(45, 156, 86, 0.15); border-radius: 4px; padding: 4px 8px;")
        
        top_bar_layout.addWidget(live_badge)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.status_badge)
        
        self.feed_placeholder = QLabel()
        self.feed_placeholder.setAlignment(Qt.AlignCenter)
        self.feed_placeholder.setText(f"[ Aguardando Feed de Vídeo ]")
        self.feed_placeholder.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; background-color: #121319;")
        
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(70)
        bottom_bar.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 12, 15, 12)
        bottom_layout.setSpacing(2)
        
        cam_title = QLabel(self.title)
        cam_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        cam_sub = QLabel(self.location)
        cam_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")
        
        bottom_layout.addWidget(cam_title)
        bottom_layout.addWidget(cam_sub)
        
        layout.addWidget(top_bar)
        layout.addWidget(self.feed_placeholder, 1)
        layout.addWidget(bottom_bar)

    def set_frame(self, qt_img):
        pixmap = QPixmap.fromImage(qt_img)
        self.feed_placeholder.setPixmap(pixmap.scaled(self.feed_placeholder.width(), self.feed_placeholder.height(), Qt.KeepAspectRatio))

class CircularRiskGauge(QWidget):
    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.value = value
        self.setMinimumSize(180, 180)
        
    def set_value(self, new_value):
        self.value = new_value
        self.update()
        
    def paintEvent(self, event):
        width, height = self.width(), self.height()
        size = min(width, height) - 20
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = width / 2, height / 2
        track_rect = QRectF(cx - size/2, cy - size/2, size, size)
        
        pen_track = QPen(QColor(COLOR_BORDER), 12)
        pen_track.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_track)
        painter.drawArc(track_rect, 0, 360 * 16)
        
        span_angle = -360 * (self.value / 100)
        pen_active = QPen(QColor(COLOR_YELLOW), 12)
        if self.value > 60: pen_active.setColor(QColor(COLOR_RED))
        elif self.value < 30: pen_active.setColor(QColor(COLOR_GREEN))
            
        pen_active.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_active)
        painter.drawArc(track_rect, 90 * 16, span_angle * 16)
        
        painter.setPen(QColor("white"))
        font_val = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(font_val)
        val_rect = QRectF(cx - size/2, cy - size/4, size, size/3)
        painter.drawText(val_rect, Qt.AlignCenter, f"{self.value}%")
        
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        font_lbl = QFont("Segoe UI", 10)
        painter.setFont(font_lbl)
        lbl_rect = QRectF(cx - size/2, cy + 12, size, size/3)
        painter.drawText(lbl_rect, Qt.AlignCenter, "Current Risk")

class MetricCard(QFrame):
    def __init__(self, title, value, subtitle="", is_red=False, is_green=False, is_yellow=False, parent=None):
        super().__init__(parent)
        self.init_ui(title, value, subtitle, is_red, is_green, is_yellow)
        
    def init_ui(self, title, value, subtitle, is_red, is_green, is_yellow):
        self.setObjectName("metricCard")
        self.setStyleSheet(f"QFrame#metricCard {{ background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(6)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold;")
        
        val_color = "white"
        if is_red: val_color = COLOR_RED
        elif is_green: val_color = COLOR_GREEN
        elif is_yellow: val_color = COLOR_YELLOW
            
        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"color: {val_color}; font-size: 26px; font-weight: bold;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(self.val_lbl)
        
        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
            layout.addWidget(self.sub_lbl)

    def set_value(self, text, color_hex=None):
        self.val_lbl.setText(str(text))
        if color_hex:
            self.val_lbl.setStyleSheet(f"color: {color_hex}; font-size: 26px; font-weight: bold;")

class CustomChartWidget(QWidget):
    def __init__(self, x_labels, series, y_range=(0, 100), parent=None):
        super().__init__(parent)
        self.x_labels = x_labels
        self.series = series
        self.y_range = y_range
        self.setMinimumHeight(200)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin_left, margin_right, margin_top, margin_bottom = 50, 20, 20, 30
        plot_w, plot_h = w - margin_left - margin_right, h - margin_top - margin_bottom
        y_min, y_max = self.y_range
        steps = 4
        for i in range(steps + 1):
            val = y_min + i * (y_max - y_min) / steps
            y_pos = margin_top + plot_h - (i * plot_h / steps)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(10, y_pos + 4, str(int(val)))
            painter.setPen(QColor("#242630"))
            painter.drawLine(margin_left, y_pos, w - margin_right, y_pos)
            
        num_x = len(self.x_labels)
        for i, label in enumerate(self.x_labels):
            x_pos = margin_left + i * plot_w / (num_x - 1)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(x_pos - 18, h - 8, label)
            
        for s in self.series:
            color = QColor(s["color"])
            data = s["data"]
            painter.setPen(QPen(color, 3))
            points = []
            for i, val in enumerate(data):
                x_pos = margin_left + i * plot_w / (num_x - 1)
                val_norm = (val - y_min) / (y_max - y_min)
                y_pos = margin_top + plot_h - (val_norm * plot_h)
                points.append(QPoint(x_pos, y_pos))
                
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i+1])
            painter.setBrush(color)
            painter.setPen(QPen(QColor(COLOR_BG_CARD), 1.5))
            for pt in points:
                painter.drawEllipse(pt, 5, 5)

# -------------------------------------------------------------
# PÁGINAS DO SISTEMA
# -------------------------------------------------------------

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)
        
        header = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Real-time safety monitoring overview")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13px;")
        header.addWidget(title)
        header.addWidget(subtitle)
        main_layout.addLayout(header)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        
        camera_grid = QGridLayout()
        camera_grid.setSpacing(15)
        
        self.cam1 = CameraFeedWidget("Camera 1", "Assembly Line A")
        self.cam2 = CameraFeedWidget("Camera 2", "Warehouse Zone B")
        self.cam3 = CameraFeedWidget("Camera 3", "Loading Dock C")
        self.cam4 = CameraFeedWidget("Camera 4", "Quality Control")
        
        camera_grid.addWidget(self.cam1, 0, 0)
        camera_grid.addWidget(self.cam2, 0, 1)
        camera_grid.addWidget(self.cam3, 1, 0)
        camera_grid.addWidget(self.cam4, 1, 1)
        
        left_col.addLayout(camera_grid)
        
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)
        
        self.card_posture = MetricCard("Posture Status", "Aguardando", is_yellow=True)
        self.card_epi = MetricCard("EPI Status", "Aguardando", is_green=True)
        self.card_alerts = MetricCard("Open Alerts", CONFIG["open_alerts"], is_red=True)
        self.card_compliance = MetricCard("Global Compliance", "98.5%")
        
        metrics_layout.addWidget(self.card_posture)
        metrics_layout.addWidget(self.card_epi)
        metrics_layout.addWidget(self.card_alerts)
        metrics_layout.addWidget(self.card_compliance)
        
        left_col.addLayout(metrics_layout)
        content_layout.addLayout(left_col, 3)
        
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(f"QFrame#rightPanel {{ background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER}; }}")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(20, 20, 20, 20)
        
        risk_title = QLabel("⚡ Risk Level")
        risk_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        right_panel_layout.addWidget(risk_title)
        
        self.gauge = CircularRiskGauge(0)
        right_panel_layout.addWidget(self.gauge, 0, Qt.AlignCenter)
        
        indicators = QVBoxLayout()
        indicators.setSpacing(10)
        
        low_bar = QLabel("Low   0-30")
        low_bar.setAlignment(Qt.AlignCenter)
        low_bar.setStyleSheet(f"color: {COLOR_GREEN}; background-color: rgba(45,156,86,0.1); border: 1px solid {COLOR_GREEN}; border-radius: 6px; padding: 10px; font-weight: bold;")
        
        med_bar = QLabel("Medium   31-60")
        med_bar.setAlignment(Qt.AlignCenter)
        med_bar.setStyleSheet(f"color: {COLOR_YELLOW}; background-color: rgba(244,180,0,0.1); border: 1px solid {COLOR_YELLOW}; border-radius: 6px; padding: 10px; font-weight: bold;")
        
        high_bar = QLabel("High   61-100")
        high_bar.setAlignment(Qt.AlignCenter)
        high_bar.setStyleSheet(f"color: {COLOR_RED}; background-color: rgba(217,56,58,0.1); border: 1px solid {COLOR_RED}; border-radius: 6px; padding: 10px; font-weight: bold;")
        
        indicators.addWidget(low_bar)
        indicators.addWidget(med_bar)
        indicators.addWidget(high_bar)
        right_panel_layout.addLayout(indicators)
        right_panel_layout.addStretch()
        
        content_layout.addWidget(right_panel, 1)
        main_layout.addLayout(content_layout)

class AlertsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(25)
        
        critical_box = QFrame()
        critical_box.setStyleSheet(f"background-color: #1F1517; border: 2px solid {COLOR_RED}; border-radius: 12px;")
        critical_layout = QVBoxLayout(critical_box)
        critical_layout.setContentsMargins(25, 25, 25, 25)
        
        title_row = QHBoxLayout()
        bell_icon = QLabel("⚠️")
        bell_icon.setStyleSheet("font-size: 26px; border: none;")
        text_title = QLabel("CRITICAL ALERT")
        text_title.setStyleSheet(f"color: {COLOR_RED}; font-size: 24px; font-weight: bold; border: none;")
        title_row.addWidget(bell_icon)
        title_row.addWidget(text_title)
        title_row.addStretch()
        critical_layout.addLayout(title_row)
        
        sub_title = QLabel("Safety Protocol Violation Detected")
        sub_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: none;")
        critical_layout.addWidget(sub_title)
        
        meta_row = QHBoxLayout()
        for index, (k, v, c) in enumerate([("Location", "Assembly Line A", "white"), ("Time", CONFIG["alert_time"], "white"), ("Severity", "CRITICAL", COLOR_RED)]):
            card = QFrame()
            card.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.03); border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
            card_lay = QVBoxLayout(card)
            lbl = QLabel(k)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; border: none;")
            val = QLabel(v)
            val.setStyleSheet(f"color: {c}; font-size: 14px; font-weight: bold; border: none;")
            card_lay.addWidget(lbl)
            card_lay.addWidget(val)
            meta_row.addWidget(card, 1)
            
        critical_layout.addLayout(meta_row)
        
        details = QFrame()
        details.setStyleSheet("background-color: rgba(217, 56, 58, 0.05); border: 1px solid rgba(217, 56, 58, 0.2); border-radius: 8px;")
        details_layout = QVBoxLayout(details)
        for txt in ["• Operator detected without required hard hat", "• Multiple safety violations in past 15 mins", "• Immediate supervisor notification required"]:
            p = QLabel(txt)
            p.setStyleSheet("color: #FFC0C1; font-size: 13px; border: none;")
            details_layout.addWidget(p)
            
        critical_layout.addWidget(details)
        
        self.trigger_btn = QPushButton("🚨 TRIGGER ALARM")
        self.trigger_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_RED}; color: white; font-size: 16px; font-weight: bold; border: none; border-radius: 8px; padding: 14px; }}")
        self.trigger_btn.clicked.connect(self.on_trigger_clicked)
        critical_layout.addWidget(self.trigger_btn)
        
        self.notification_lbl = QLabel("Emergency response team has been notified")
        self.notification_lbl.setAlignment(Qt.AlignCenter)
        self.notification_lbl.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 12px; font-weight: bold; border: none;")
        self.notification_lbl.setVisible(False)
        critical_layout.addWidget(self.notification_lbl)
        
        layout.addWidget(critical_box)
        
        recent_title = QLabel("Recent Alerts")
        recent_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(recent_title)
        
        list_container = QVBoxLayout()
        alerts_data = [
            ("HIGH", "Missing PPE Equipment - Zone B", "12 minutes ago", "Active", COLOR_RED),
            ("MEDIUM", "Unauthorized Access Attempt", "45 minutes ago", "Investigating", COLOR_YELLOW),
            ("LOW", "Safety Check Overdue", "4 hours ago", "Resolved", COLOR_GREEN),
        ]
        for sev, name, time_ago, status, col in alerts_data:
            row = QFrame()
            row.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            badge = QLabel(sev)
            badge.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 11px; background-color: rgba(255,255,255,0.04); border-radius: 4px; padding: 4px 10px; border: none;")
            
            info = QVBoxLayout()
            lbl_n = QLabel(name)
            lbl_n.setStyleSheet("color: white; font-weight: bold; font-size: 13px; border: none;")
            lbl_t = QLabel(time_ago)
            lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; border: none;")
            info.addWidget(lbl_n)
            info.addWidget(lbl_t)
            
            stat = QLabel(status)
            stat.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 11px; background-color: rgba(255,255,255,0.04); border-radius: 4px; padding: 6px 12px; border: none;")
            
            row_layout.addWidget(badge)
            row_layout.addLayout(info, 1)
            row_layout.addWidget(stat)
            list_container.addWidget(row)
            
        layout.addLayout(list_container)
        layout.addStretch()

    def on_trigger_clicked(self):
        self.trigger_btn.setText("🔔 ALARM TRIGGERED!")
        self.trigger_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_YELLOW}; color: #121319; font-size: 16px; font-weight: bold; border: none; border-radius: 8px; padding: 14px; }}")
        self.notification_lbl.setVisible(True)

class OpsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Operator Profile")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        header_text.addWidget(title)
        header.addLayout(header_text)
        layout.addLayout(header)
        
        panel_layout = QHBoxLayout()
        profile_card = QFrame()
        profile_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;")
        prof_layout = QVBoxLayout(profile_card)
        
        initials = "".join([part[0] for part in CONFIG["op_name"].split() if part])[:2]
        avatar = QLabel(initials)
        avatar.setFixedSize(90, 90)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background-color: {COLOR_YELLOW}; color: #121319; font-size: 28px; font-weight: bold; border-radius: 45px;")
        
        name = QLabel(CONFIG["op_name"])
        name.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        role = QLabel(CONFIG["op_role"])
        role.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px;")
        
        prof_layout.addWidget(avatar, 0, Qt.AlignCenter)
        prof_layout.addWidget(name, 0, Qt.AlignCenter)
        prof_layout.addWidget(role, 0, Qt.AlignCenter)
        
        panel_layout.addWidget(profile_card, 1)
        layout.addLayout(panel_layout)
        layout.addStretch()

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Risk Evolution")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Live risk progression based on YOLO inference")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13px;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        layout.addLayout(header)
        
        # --- Integração do PyQtGraph (Gráfico 1) ---
        chart1_card = QFrame()
        chart1_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;")
        chart1_lay = QVBoxLayout(chart1_card)
        chart1_lay.setContentsMargins(20, 15, 20, 15)
        
        chart1_title = QLabel("📈 Real-time Risk Level Trend (%)")
        chart1_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        chart1_lay.addWidget(chart1_title)
        
        pg.setConfigOption('background', COLOR_BG_CARD)
        pg.setConfigOption('foreground', COLOR_TEXT_MUTED)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.getAxis('left').setPen(COLOR_BORDER)
        self.plot_widget.getAxis('bottom').setPen(COLOR_BORDER)
        chart1_lay.addWidget(self.plot_widget)
        layout.addWidget(chart1_card)

        self.time_data = list(range(60))
        self.risk_data = [0] * 60
        self.pen = pg.mkPen(color=COLOR_RED, width=3)
        self.data_line = self.plot_widget.plot(self.time_data, self.risk_data, pen=self.pen)
        
        # --- Gráfico 2 Mantido (Estático Base) ---
        chart2_card = QFrame()
        chart2_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;")
        chart2_lay = QVBoxLayout(chart2_card)
        chart2_lay.setContentsMargins(20, 15, 20, 15)
        chart2_title = QLabel("📊 Daily Incident Count")
        chart2_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        chart2_lay.addWidget(chart2_title)
        x_lbls = ["Jun 10", "Jun 11", "Jun 12", "Jun 13", "Jun 14", "Jun 15", "Jun 16"]
        series2 = [{"name": "Incidents", "color": COLOR_YELLOW, "data": CONFIG["daily_incidents_data"]}]
        chart2 = CustomChartWidget(x_lbls, series2, (0, 8))
        chart2_lay.addWidget(chart2)
        layout.addWidget(chart2_card)
        
        metrics = QHBoxLayout()
        metrics.setSpacing(15)
        metrics.addWidget(MetricCard("Average Risk Level", CONFIG["rep_avg_risk_level"], "Past 7 days", is_red=True))
        metrics.addWidget(MetricCard("Total Incidents", CONFIG["rep_total_incidents"], "Past 7 days", is_yellow=True))
        layout.addLayout(metrics)

    def update_chart(self, risk_val):
        self.risk_data = self.risk_data[1:]
        self.risk_data.append(risk_val)
        self.data_line.setData(self.time_data, self.risk_data)

# -------------------------------------------------------------
# JANELA PRINCIPAL DO APLICATIVO (MAIN WINDOW)
# -------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProSec - Industrial Safety System")
        self.resize(1300, 850)
        self.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")
        self.init_ui()
        
        # INICIALIZAÇÃO DA INTELIGÊNCIA ARTIFICIAL
        self.pipeline_thread = IntegratedPipelineThread()
        self.pipeline_thread.frame_updated.connect(self.page_dashboard.cam1.set_frame)
        self.pipeline_thread.metrics_updated.connect(self.update_live_metrics)
        self.pipeline_thread.start()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {COLOR_BG_SIDEBAR}; border-right: 1px solid {COLOR_BORDER};")
        sidebar_layout = QVBoxLayout(sidebar)
        
        logo_lay = QVBoxLayout()
        logo_lay.setSpacing(2)
        logo = QLabel("ProSec")
        logo.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 22px; font-weight: bold; font-family: 'Segoe UI';")
        logo_sub = QLabel("Industrial Safety System")
        logo_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        logo_lay.addWidget(logo)
        logo_lay.addWidget(logo_sub)
        sidebar_layout.addLayout(logo_lay)
        sidebar_layout.addSpacing(30)
        
        self.btn_dashboard = QPushButton("📊  Dashboard")
        self.btn_alerts = QPushButton("⚠️  Alerts")
        self.btn_ops = QPushButton("👤  Ops")
        self.btn_reports = QPushButton("📋  Reports")
        
        self.nav_buttons = [self.btn_dashboard, self.btn_alerts, self.btn_ops, self.btn_reports]
        for btn in self.nav_buttons:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {COLOR_TEXT_MUTED}; border: none; font-weight: bold; font-size: 13px; text-align: left; padding: 12px 15px; border-radius: 8px;
                }}
                QPushButton:hover {{ background-color: #20222B; color: white; }}
                QPushButton:checked {{ background-color: {COLOR_YELLOW}; color: #121319; }}
            """)
            sidebar_layout.addWidget(btn)
            
        self.btn_dashboard.setChecked(True)
        sidebar_layout.addStretch()
        
        profile_box = QFrame()
        profile_box.setStyleSheet(f"background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px;")
        prof_lay = QHBoxLayout(profile_box)
        sidebar_initials = "".join([part[0] for part in CONFIG["sidebar_user_name"].split() if part])[:2]
        avatar = QLabel(sidebar_initials)
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background-color: {COLOR_YELLOW}; color: #121319; font-weight: bold; border-radius: 18px; border: none;")
        
        u_info = QVBoxLayout()
        u_name = QLabel(CONFIG["sidebar_user_name"])
        u_name.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none;")
        u_role = QLabel(CONFIG["sidebar_user_role"])
        u_role.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; border: none;")
        u_info.addWidget(u_name)
        u_info.addWidget(u_role)
        prof_lay.addWidget(avatar)
        prof_lay.addLayout(u_info)
        sidebar_layout.addWidget(profile_box)
        main_layout.addWidget(sidebar)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {COLOR_BG_MAIN}; }}")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        
        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_alerts = AlertsPage()
        self.page_ops = OpsPage()
        self.page_reports = ReportsPage()
        
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_alerts)
        self.stack.addWidget(self.page_ops)
        self.stack.addWidget(self.page_reports)
        
        container_layout.addWidget(self.stack)
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area, 1)
        
        self.btn_dashboard.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_alerts.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_ops.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.btn_reports.clicked.connect(lambda: self.stack.setCurrentIndex(3))

    def update_live_metrics(self, postura, epi, risco_texto, cor, risco_percentual):
        # Atualiza a UI do Dashboard
        self.page_dashboard.gauge.set_value(risco_percentual)
        self.page_dashboard.card_posture.set_value(postura.replace("Coluna:", "").strip(), cor)
        self.page_dashboard.card_epi.set_value(epi.replace("EPI:", "").strip(), cor)
        self.page_dashboard.cam1.status_badge.setText(risco_texto)
        self.page_dashboard.cam1.status_badge.setStyleSheet(f"color: {cor}; font-weight: bold; font-size: 11px; background-color: {cor}25; border-radius: 4px; padding: 4px 8px;")
        
        # Atualiza a UI de Relatórios (Gráfico via pyqtgraph)
        self.page_reports.update_chart(risco_percentual)

    def closeEvent(self, event):
        self.pipeline_thread.stop()
        event.accept()

# -------------------------------------------------------------
# INICIALIZAÇÃO
# -------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())