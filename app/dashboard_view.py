# dashboard_view.py
from PySide6.QtCore import Qt, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QStackedWidget
)
from config import (
    COLOR_BG_MAIN, COLOR_BG_SIDEBAR, COLOR_BG_CARD, COLOR_BORDER,
    COLOR_YELLOW, COLOR_RED, COLOR_GREEN, COLOR_TEXT_MUTED, CONFIG
)

# Importa a Thread de IA com o back-end (Lógica de Negócio)
from app4 import SafetyPipelineThread

# ==============================================================================
# 🛠️ COMPONENTES VISUAIS PERSONALIZADOS
# ==============================================================================

class ToggleSwitch(QWidget):
    """Um interruptor liga/desliga estilizado."""
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
    """Widget de Câmera individual."""
    def __init__(self, title, location, parent=None):
        super().__init__(parent)
        self.title = title
        self.location = location
        self.init_ui()
        
    def init_ui(self):
        self.setMinimumSize(320, 240)
        self.setObjectName("cameraFeedWidget")
        self.setStyleSheet(f"""
            QFrame#cameraFeedWidget {{
                background-color: {COLOR_BG_CARD};
                border-radius: 12px;
                border: 1px solid {COLOR_BORDER};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QWidget()
        top_bar.setFixedHeight(45)
        top_bar.setStyleSheet("background: transparent; border: none;")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(15, 12, 15, 0)
        
        live_badge = QLabel("● LIVE")
        live_badge.setStyleSheet(f"""
            color: {COLOR_RED};
            font-weight: bold;
            font-size: 11px;
            background-color: rgba(217, 56, 58, 0.15);
            border-radius: 4px;
            padding: 4px 8px;
            border: none;
            background: transparent;
        """)
        
        self.status_badge = QLabel("NORMAL")
        self.status_badge.setStyleSheet(f"""
            color: {COLOR_GREEN};
            font-weight: bold;
            font-size: 11px;
            background-color: rgba(45, 156, 86, 0.15);
            border-radius: 4px;
            padding: 4px 8px;
            border: none;
            background: transparent;
        """)
        
        top_bar_layout.addWidget(live_badge)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.status_badge)
        
        self.feed_placeholder = QLabel()
        self.feed_placeholder.setAlignment(Qt.AlignCenter)
        self.feed_placeholder.setText(f"[ Área do Feed da Câmera ]")
        self.feed_placeholder.setStyleSheet(f"""
            color: {COLOR_TEXT_MUTED};
            font-size: 12px;
            background-color: #121319;
            border: none;
        """)
        
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(70)
        bottom_bar.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: none; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 12, 15, 12)
        bottom_layout.setSpacing(2)
        
        cam_title = QLabel(self.title)
        cam_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        cam_sub = QLabel(self.location)
        cam_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; border: none; background: transparent;")
        
        bottom_layout.addWidget(cam_title)
        bottom_layout.addWidget(cam_sub)
        
        layout.addWidget(top_bar)
        layout.addWidget(self.feed_placeholder, 1)
        layout.addWidget(bottom_bar)

    def set_frame(self, qt_img):
        """Recebe o frame atualizado do back-end e o renderiza"""
        from PySide6.QtGui import QPixmap
        pixmap = QPixmap.fromImage(qt_img)
        self.feed_placeholder.setPixmap(pixmap.scaled(self.feed_placeholder.width(), self.feed_placeholder.height(), Qt.KeepAspectRatio))


class CircularRiskGauge(QWidget):
    """Mostrador de risco circular que se atualiza automaticamente."""
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
        elif self.value <= 30: pen_active.setColor(QColor(COLOR_GREEN))
            
        pen_active.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_active)
        painter.drawArc(track_rect, int(90 * 16), int(span_angle * 16))
        
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
    """Cartão informativo de estatísticas."""
    def __init__(self, title, value, subtitle="", is_red=False, is_green=False, is_yellow=False, parent=None):
        super().__init__(parent)
        self.init_ui(title, value, subtitle, is_red, is_green, is_yellow)
        
    def init_ui(self, title, value, subtitle, is_red, is_green, is_yellow):
        self.setObjectName("metricCard")
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {COLOR_BG_CARD};
                border-radius: 12px;
                border: 1px solid {COLOR_BORDER};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(6)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        
        val_color = "white"
        if is_red: val_color = COLOR_RED
        elif is_green: val_color = COLOR_GREEN
        elif is_yellow: val_color = COLOR_YELLOW
            
        self.val_lbl = QLabel(str(value))
        self.val_lbl.setStyleSheet(f"color: {val_color}; font-size: 26px; font-weight: bold; border: none; background: transparent;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(self.val_lbl)
        
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; border: none; background: transparent;")
            layout.addWidget(sub_lbl)

    def set_value(self, text, color_hex=None):
        """Permite a atualização dinâmica dos valores."""
        self.val_lbl.setText(str(text))
        if color_hex:
            self.val_lbl.setStyleSheet(f"color: {color_hex}; font-size: 26px; font-weight: bold; border: none; background: transparent;")


class CustomChartWidget(QWidget):
    """Graficador personalizado usando o QPainter."""
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
        margin_left, margin_right = 50, 20
        margin_top, margin_bottom = 20, 30
        
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom
        
        y_min, y_max = self.y_range
        steps = 4
        for i in range(steps + 1):
            val = y_min + i * (y_max - y_min) / steps
            y_pos = margin_top + plot_h - (i * plot_h / steps)
            
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(10, int(y_pos + 4), str(int(val)))
            
            painter.setPen(QColor("#242630"))
            painter.drawLine(margin_left, int(y_pos), w - margin_right, int(y_pos))
            
        num_x = len(self.x_labels)
        for i, label in enumerate(self.x_labels):
            x_pos = margin_left + i * plot_w / (num_x - 1)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(int(x_pos - 18), h - 8, label)
            
        for s in self.series:
            color = QColor(s["color"])
            data = s["data"]
            
            pen = QPen(color, 3)
            painter.setPen(pen)
            
            points = []
            for i, val in enumerate(data):
                x_pos = margin_left + i * plot_w / (num_x - 1)
                val_norm = (val - y_min) / (y_max - y_min)
                y_pos = margin_top + plot_h - (val_norm * plot_h)
                points.append(QPoint(int(x_pos), int(y_pos)))
                
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i+1])
                
            painter.setBrush(color)
            painter.setPen(QPen(QColor(COLOR_BG_CARD), 1.5))
            for pt in points:
                painter.drawEllipse(pt, 5, 5)

# ==============================================================================
# 📄 ESTRUTURA DE PÁGINAS INTERNAS DO DASHBOARD
# ==============================================================================

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
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent;")
        subtitle = QLabel("Real-time safety monitoring overview")
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 13px; background: transparent;")
        header.addWidget(title)
        header.addWidget(subtitle)
        main_layout.addLayout(header)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        
        camera_grid = QGridLayout()
        camera_grid.setSpacing(15)
        
        cams_data = CONFIG["cameras"]
        self.cam1 = CameraFeedWidget(cams_data[0]["title"], cams_data[0]["location"])
        self.cam2 = CameraFeedWidget(cams_data[1]["title"], cams_data[1]["location"])
        self.cam3 = CameraFeedWidget(cams_data[2]["title"], cams_data[2]["location"])
        self.cam4 = CameraFeedWidget(cams_data[3]["title"], cams_data[3]["location"])
        
        camera_grid.addWidget(self.cam1, 0, 0)
        camera_grid.addWidget(self.cam2, 0, 1)
        camera_grid.addWidget(self.cam3, 1, 0)
        camera_grid.addWidget(self.cam4, 1, 1)
        
        left_col.addLayout(camera_grid)
        
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)
        
        val_alerts = CONFIG["open_alerts"]
        val_compliance = CONFIG["compliance"]
        
        # Cria as variáveis para podermos atualizá-las posteriormente
        self.card_posture = MetricCard("Posture Status", "Aguardando", is_yellow=True)
        self.card_epi = MetricCard("EPI Status", "Aguardando", is_green=True)
        self.card_alerts = MetricCard("Open Alerts", val_alerts, is_red=True)
        self.card_compliance = MetricCard("Global Compliance", val_compliance)
        
        metrics_layout.addWidget(self.card_posture)
        metrics_layout.addWidget(self.card_epi)
        metrics_layout.addWidget(self.card_alerts)
        metrics_layout.addWidget(self.card_compliance)
        
        left_col.addLayout(metrics_layout)
        content_layout.addLayout(left_col, 3)
        
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(f"""
            QFrame#rightPanel {{
                background-color: {COLOR_BG_CARD};
                border-radius: 12px;
                border: 1px solid {COLOR_BORDER};
            }}
        """)
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(20, 20, 20, 20)
        right_panel_layout.setSpacing(20)
        
        risk_title = QLabel("⚡ Risk Level")
        risk_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none; background: transparent;")
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

# [As classes AlertsPage, OpsPage e ReportsPage permanecem inalteradas no momento,
# mas são chamadas abaixo. Para brevidade e foco na lógica, foram simplificadas caso já as tenha.
# Vou incluí-las para o arquivo ficar completo.]
class AlertsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Alerts - Substitua com seu código de AlertsPage anterior caso necessário", styleSheet="color:white;"))

class OpsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Ops - Substitua com seu código de OpsPage anterior caso necessário", styleSheet="color:white;"))

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Reports - Substitua com seu código de ReportsPage anterior caso necessário", styleSheet="color:white;"))


class DashboardMainLayout(QWidget):
    """
    Subclasse que implementa a casca do Dashboard original e orquestra a inteligência.
    """
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        # INICIALIZAÇÃO DA LÓGICA DE NEGÓCIO (BACK-END)
        self.start_backend_pipeline()

    def start_backend_pipeline(self):
        """Inicializa a Thread de IA (app4.py) e conecta os retornos à Interface"""
        self.pipeline_thread = SafetyPipelineThread(porta_serial='COM3')
        
        # Conecta o sinal de vídeo à câmera 1
        self.pipeline_thread.frame_updated.connect(self.page_dashboard.cam1.set_frame)
        
        # Conecta as métricas calculadas na Thread para atualizar os textos e gráficos
        self.pipeline_thread.metrics_updated.connect(self.update_live_metrics)
        
        self.pipeline_thread.start()

    def update_live_metrics(self, postura, epi, risco_texto, cor, risco_percentual):
        """Recebe os dados do Back-end e atualiza os widgets do Dashboard"""
        # Atualiza o mostrador
        self.page_dashboard.gauge.set_value(risco_percentual)
        
        # Atualiza os cartões 
        self.page_dashboard.card_posture.set_value(postura.replace("Postura:", "").strip(), cor)
        self.page_dashboard.card_epi.set_value(epi.replace("EPI:", "").strip(), cor)
        
        # Atualiza status da Câmera
        self.page_dashboard.cam1.status_badge.setText(risco_texto)
        self.page_dashboard.cam1.status_badge.setStyleSheet(f"color: {cor}; font-weight: bold; font-size: 11px; background-color: {cor}25; border-radius: 4px; padding: 4px 8px;")

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {COLOR_BG_SIDEBAR}; border-right: 1px solid {COLOR_BORDER};")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 20)
        sidebar_layout.setSpacing(10)
        
        logo_lay = QVBoxLayout()
        logo_lay.setSpacing(2)
        logo = QLabel("ProSec")
        logo.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 22px; font-weight: bold; font-family: 'Segoe UI'; background: transparent;")
        logo_sub = QLabel("Industrial Safety System")
        logo_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; background: transparent;")
        logo_lay.addWidget(logo)
        logo_lay.addWidget(logo_sub)
        sidebar_layout.addLayout(logo_lay)
        sidebar_layout.addSpacing(30)
        
        self.btn_dashboard = QPushButton("📊  Dashboard")
        self.btn_alerts = QPushButton("⚠️  Alerts")
        self.btn_ops = QPushButton("👤  Ops")
        self.btn_reports = QPushButton("📋  Reports")
        self.btn_exit = QPushButton("↩️  Menu Principal")
        
        self.nav_buttons = [self.btn_dashboard, self.btn_alerts, self.btn_ops, self.btn_reports, self.btn_exit]
        
        for btn in self.nav_buttons:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_MUTED};
                    border: none;
                    font-weight: bold;
                    font-size: 13px;
                    text-align: left;
                    padding: 12px 15px;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: #20222B;
                    color: white;
                }}
                QPushButton:checked {{
                    background-color: {COLOR_YELLOW};
                    color: #121319;
                }}
            """)
            sidebar_layout.addWidget(btn)
            
        self.btn_dashboard.setChecked(True)
        sidebar_layout.addStretch()
        
        self.btn_exit.clicked.connect(self.back_requested.emit)
        
        val_sidebar_user = CONFIG["sidebar_user_name"]
        val_sidebar_role = CONFIG["sidebar_user_role"]
        
        profile_box = QFrame()
        profile_box.setObjectName("sidebarProfile")
        profile_box.setStyleSheet(f"QFrame#sidebarProfile {{ background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; }}")
        prof_lay = QHBoxLayout(profile_box)
        prof_lay.setContentsMargins(10, 10, 10, 10)
        
        sidebar_initials = "".join([part[0] for part in val_sidebar_user.split() if part])[:2]
        avatar = QLabel(sidebar_initials)
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background-color: {COLOR_YELLOW}; color: #121319; font-weight: bold; border-radius: 18px; border: none;")
        
        u_info = QVBoxLayout()
        u_info.setSpacing(1)
        u_name = QLabel(val_sidebar_user)
        u_name.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        u_role = QLabel(val_sidebar_role)
        u_role.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; border: none; background: transparent;")
        u_info.addWidget(u_name)
        u_info.addWidget(u_role)
        
        prof_lay.addWidget(avatar)
        prof_lay.addLayout(u_info)
        prof_lay.addStretch()
        
        sidebar_layout.addWidget(profile_box)
        main_layout.addWidget(sidebar)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLOR_BG_MAIN};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {COLOR_BG_MAIN};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)
        
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