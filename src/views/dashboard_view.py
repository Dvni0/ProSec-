# dashboard_view.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QStackedWidget, QDialog,
    QCheckBox, QDialogButtonBox, QComboBox, QSizePolicy, QLineEdit
)
import pyqtgraph as pg

from configs.config import (
    COLOR_BG_MAIN, COLOR_BG_SIDEBAR, COLOR_BG_CARD, COLOR_BORDER,
    COLOR_YELLOW, COLOR_RED, COLOR_GREEN, COLOR_TEXT_MUTED, CONFIG
)

from controllers.pipelineThreadSource import SafetyPipelineThread

class TagSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Câmera")
        self.setStyleSheet("background-color: #1A1C23; color: white;")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("1. Origem do Vídeo:"))
        self.cam_combo = QComboBox()
        self.cam_combo.setStyleSheet("background-color: #121319; border: 1px solid #2B2E3C; padding: 5px;")
        self.cam_combo.addItems(["Câmera 0 (Notebook)", "Câmera 1 (USB 1)", "Câmera 2 (USB 2)", "Câmera RTSP"])
        layout.addWidget(self.cam_combo)

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://usuario:senha@ip:porta/caminho")
        self.rtsp_input.setStyleSheet("background-color: #121319; border: 1px solid #2B2E3C; padding: 5px;")
        self.rtsp_input.setEnabled(False)
        layout.addWidget(self.rtsp_input)
        self.cam_combo.currentIndexChanged.connect(
            lambda index: self.rtsp_input.setEnabled(index == 3)
        )
        layout.addSpacing(10)

        layout.addWidget(QLabel("2. Tags a serem verificadas (Quadrados):"))
        self.chk_postura = QCheckBox("Postura (RULA)")
        self.chk_capacete = QCheckBox("Capacete (Hard Hat)")
        self.chk_colete = QCheckBox("Colete (Safety Vest)")
        self.chk_oculos = QCheckBox("Óculos (Goggles)")
        self.chk_luvas = QCheckBox("Luvas (Gloves)")
        self.chk_botas = QCheckBox("Botas (Boots)")

        for chk in [self.chk_postura, self.chk_capacete, self.chk_colete, self.chk_oculos, self.chk_luvas, self.chk_botas]:
            chk.setChecked(True)
            layout.addWidget(chk)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        return {
            "camera_source": self.rtsp_input.text().strip() if self.cam_combo.currentIndex() == 3 else self.cam_combo.currentIndex(),
            "tags": {
                "postura": self.chk_postura.isChecked(),
                "capacete": self.chk_capacete.isChecked(),
                "colete": self.chk_colete.isChecked(),
                "oculos": self.chk_oculos.isChecked(),
                "luvas": self.chk_luvas.isChecked(),
                "botas": self.chk_botas.isChecked()
            }
        }

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

class ZoneFeedWidget(QWidget):
    dead_zones_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.dead_zones = []
        self.current_zone = []
        self.drawing_enabled = False
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")
        self.image_label.setScaledContents(False)
        self.image_label.hide()
        self.setMinimumSize(1, 1)
        self.setMouseTracking(True)

    def _apply_pixmap_to_label(self):
        if self.pixmap.isNull():
            self.update()
            return
        self.update()

    def set_frame(self, qt_img):
        if qt_img is None:
            self.clear_frame()
            return
        self.pixmap = QPixmap.fromImage(qt_img)
        self._apply_pixmap_to_label()
        self.update()

    def clear_frame(self):
        self.pixmap = QPixmap()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_pixmap_to_label()

    def _image_rect(self):
        if self.pixmap.isNull():
            return QRectF(self.rect())
        scaled_size = self.pixmap.size()
        scaled_size.scale(self.size(), Qt.KeepAspectRatio)
        x = (self.width() - scaled_size.width()) / 2
        y = (self.height() - scaled_size.height()) / 2
        return QRectF(x, y, scaled_size.width(), scaled_size.height())

    def _normalized_point(self, position):
        image_rect = self._image_rect()
        if not image_rect.contains(position):
            return None
        x = (position.x() - image_rect.left()) / image_rect.width()
        y = (position.y() - image_rect.top()) / image_rect.height()
        return (max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))

    def _screen_point(self, normalized_point):
        image_rect = self._image_rect()
        return QPoint(
            round(image_rect.left() + normalized_point[0] * image_rect.width()),
            round(image_rect.top() + normalized_point[1] * image_rect.height())
        )

    def begin_zone_drawing(self):
        self.drawing_enabled = not self.drawing_enabled
        if not self.drawing_enabled:
            self._finish_current_zone()
        self.update()

    def clear_zones(self):
        self.current_zone = []
        self.dead_zones = []
        self.dead_zones_changed.emit(self.dead_zones)
        self.update()

    def _finish_current_zone(self):
        if len(self.current_zone) >= 3:
            self.dead_zones.append(self.current_zone)
            self.dead_zones_changed.emit(self.dead_zones)
        self.current_zone = []
        self.update()

    def mousePressEvent(self, event):
        if not self.drawing_enabled:
            return
        if event.button() == Qt.RightButton:
            self._finish_current_zone()
            return
        if event.button() == Qt.LeftButton:
            point = self._normalized_point(event.position())
            if point is not None:
                self.current_zone.append(point)
                self.update()

    def mouseDoubleClickEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self._finish_current_zone()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#121319"))

        painter.setRenderHint(QPainter.Antialiasing)
        if not self.pixmap.isNull():
            image_rect = self._image_rect()
            painter.drawPixmap(image_rect.toRect(), self.pixmap)

        painter.setPen(QPen(QColor("#B8BEC9"), 2))
        painter.setBrush(QBrush(QColor(80, 80, 80, 90)))
        for zone in self.dead_zones:
            points = [self._screen_point(point) for point in zone]
            painter.drawPolygon(points)

        if self.current_zone:
            painter.setPen(QPen(QColor("#F4B400"), 2, Qt.DashLine))
            points = [self._screen_point(point) for point in self.current_zone]
            painter.drawPolyline(points)
            painter.setBrush(QBrush(QColor("#F4B400")))
            for point in points:
                painter.drawEllipse(point, 4, 4)

        if self.drawing_enabled:
            painter.setPen(QColor("white"))
            painter.setBrush(QBrush(QColor(18, 19, 25, 210)))
            painter.drawRoundedRect(12, 12, 250, 28, 5, 5)
            painter.drawText(22, 31, "Clique para marcar | duplo clique fecha")


class CameraFeedWidget(QFrame):
    close_requested = Signal()
    dead_zones_changed = Signal(object)
    def __init__(self, title, location, parent=None):
        super().__init__(parent)
        self.title = title
        self.location = location
        self.init_ui()
    def init_ui(self):
        self.setMinimumSize(320, 240)
        self.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QWidget()
        top_bar.setFixedHeight(45)
        top_bar.setStyleSheet("background: transparent; border: none;")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(15, 12, 15, 0)
        
        live_badge = QLabel("● LIVE")
        live_badge.setStyleSheet(f"color: {COLOR_RED}; font-weight: bold; font-size: 11px; background-color: rgba(217, 56, 58, 0.15); border-radius: 4px; padding: 4px 8px;")
        self.status_badge = QLabel("NORMAL")
        self.status_badge.setStyleSheet(f"color: {COLOR_GREEN}; font-weight: bold; font-size: 11px; background-color: rgba(45, 156, 86, 0.15); border-radius: 4px; padding: 4px 8px;")
        top_bar_layout.addWidget(live_badge)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.status_badge)

        self.btn_zones = QPushButton("Zonas mortas")
        self.btn_zones.setCursor(Qt.PointingHandCursor)
        self.btn_zones.setStyleSheet(f"background-color: {COLOR_YELLOW}; color: #121319; font-weight: bold; border: none; border-radius: 4px; padding: 4px 8px;")
        self.btn_zones.setToolTip("Desenhar uma área que não será analisada")
        self.btn_zones.clicked.connect(self._toggle_zone_drawing)
        top_bar_layout.addWidget(self.btn_zones)

        self.btn_clear_zones = QPushButton("Limpar")
        self.btn_clear_zones.setCursor(Qt.PointingHandCursor)
        self.btn_clear_zones.setStyleSheet("background: transparent; color: #B8BEC9; border: none; padding: 4px;")
        self.btn_clear_zones.clicked.connect(self._clear_zones)
        top_bar_layout.addWidget(self.btn_clear_zones)
        
        self.btn_close = QPushButton("✖")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("background: transparent; color: #D9383A; font-weight: bold; font-size: 14px; border: none; padding-left: 10px;")
        self.btn_close.clicked.connect(self.close_requested.emit)
        top_bar_layout.addWidget(self.btn_close)
        
        self.stack = QStackedWidget()

        self.btn_add = QPushButton("+ Adicionar Câmera")
        self.btn_add.setStyleSheet(f"background-color: {COLOR_YELLOW}; color: #121319; font-weight: bold; border-radius: 8px; padding: 15px;")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFixedSize(180, 45)

        btn_container = QWidget()
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.addWidget(self.btn_add, 0, Qt.AlignCenter)

        self.feed_placeholder = ZoneFeedWidget()
        self.feed_placeholder.dead_zones_changed.connect(self.dead_zones_changed.emit)

        self.stack.addWidget(btn_container)
        self.stack.addWidget(self.feed_placeholder)
        
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(70)
        bottom_bar.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 12, 15, 12)
        bottom_layout.setSpacing(2)
        cam_title = QLabel(self.title)
        cam_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        cam_sub = QLabel(self.location)
        cam_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; background: transparent;")
        bottom_layout.addWidget(cam_title)
        bottom_layout.addWidget(cam_sub)
        
        layout.addWidget(top_bar)
        layout.addWidget(self.stack, 1)
        layout.addWidget(bottom_bar)

    def set_frame(self, qt_img):
        self.feed_placeholder.set_frame(qt_img)

    def _toggle_zone_drawing(self):
        self.feed_placeholder.begin_zone_drawing()
        self.btn_zones.setText("Concluir" if self.feed_placeholder.drawing_enabled else "Zonas mortas")

    def _clear_zones(self):
        self.feed_placeholder.clear_zones()

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
        painter.setPen(QPen(QColor(COLOR_BORDER), 12, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(track_rect, 0, 360 * 16)
        span_angle = -360 * (self.value / 100)
        pen_active = QPen(QColor(COLOR_YELLOW), 12, Qt.SolidLine, Qt.RoundCap)
        if self.value > 60: pen_active.setColor(QColor(COLOR_RED))
        elif self.value <= 30: pen_active.setColor(QColor(COLOR_GREEN))
        painter.setPen(pen_active)
        painter.drawArc(track_rect, int(90 * 16), int(span_angle * 16))
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 28, QFont.Bold))
        painter.drawText(QRectF(cx - size/2, cy - size/4, size, size/3), Qt.AlignCenter, f"{self.value}%")
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QRectF(cx - size/2, cy + 12, size, size/3), Qt.AlignCenter, "Current Risk")

class MetricCard(QFrame):
    def __init__(self, title, value, subtitle="", is_red=False, is_green=False, is_yellow=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER};")
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
        self.val_lbl.setText(str(text))
        if color_hex:
            self.val_lbl.setStyleSheet(f"color: {color_hex}; font-size: 26px; font-weight: bold; border: none; background: transparent;")

class CustomChartWidget(QWidget):
    def __init__(self, x_labels, series, y_range=(0, 100), parent=None):
        super().__init__(parent)
        self.x_labels, self.series, self.y_range = x_labels, series, y_range
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
            painter.setPen(QPen(color, 3))
            points = []
            for i, val in enumerate(s["data"]):
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

    def update_data(self, x_labels, data):
        self.x_labels = x_labels
        self.series[0]["data"] = data
        self.update()

# ----------------- PAGINAS INTERNAS -----------------
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
        header.addWidget(title)
        header.addWidget(QLabel("Real-time safety monitoring overview", styleSheet=f"color: {COLOR_TEXT_MUTED}; font-size: 13px;"))
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
        # Trava as 2 linhas e 2 colunas para manterem SEMPRE o mesmo tamanho
        camera_grid.setRowStretch(0, 1)
        camera_grid.setRowStretch(1, 1)
        camera_grid.setColumnStretch(0, 1)
        camera_grid.setColumnStretch(1, 1)
        left_col.addLayout(camera_grid)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)
        self.card_posture = MetricCard("Posture Status", "Aguardando", is_yellow=True)
        self.card_epi = MetricCard("EPI Status", "Aguardando", is_green=True)
        self.card_alerts = MetricCard("Open Alerts", CONFIG["open_alerts"], is_red=True)
        self.card_compliance = MetricCard("Global Compliance", CONFIG["compliance"])
        metrics_layout.addWidget(self.card_posture)
        metrics_layout.addWidget(self.card_epi)
        metrics_layout.addWidget(self.card_alerts)
        metrics_layout.addWidget(self.card_compliance)
        left_col.addLayout(metrics_layout)
        content_layout.addLayout(left_col, 3)
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-radius: 12px; border: 1px solid {COLOR_BORDER};")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(20, 20, 20, 20)
        right_panel_layout.addWidget(QLabel("⚡ Risk Level", styleSheet="color: white; font-size: 16px; font-weight: bold; background: transparent;"))
        self.gauge = CircularRiskGauge(0)
        right_panel_layout.addWidget(self.gauge, 0, Qt.AlignCenter)
        indicators = QVBoxLayout()
        indicators.addWidget(QLabel("Low   0-30", alignment=Qt.AlignCenter, styleSheet=f"color: {COLOR_GREEN}; background-color: rgba(45,156,86,0.1); border: 1px solid {COLOR_GREEN}; border-radius: 6px; padding: 10px; font-weight: bold;"))
        indicators.addWidget(QLabel("Medium   31-60", alignment=Qt.AlignCenter, styleSheet=f"color: {COLOR_YELLOW}; background-color: rgba(244,180,0,0.1); border: 1px solid {COLOR_YELLOW}; border-radius: 6px; padding: 10px; font-weight: bold;"))
        indicators.addWidget(QLabel("High   61-100", alignment=Qt.AlignCenter, styleSheet=f"color: {COLOR_RED}; background-color: rgba(217,56,58,0.1); border: 1px solid {COLOR_RED}; border-radius: 6px; padding: 10px; font-weight: bold;"))
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
        alert_info = CONFIG["critical_alert"]
        critical_box = QFrame()
        critical_box.setStyleSheet(f"background-color: #1F1517; border: 2px solid {COLOR_RED}; border-radius: 12px;")
        critical_layout = QVBoxLayout(critical_box)
        critical_layout.setContentsMargins(25, 25, 25, 25)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("⚠️", styleSheet="font-size: 26px; background: transparent; border: none;"))
        title_row.addWidget(QLabel("CRITICAL ALERT", styleSheet=f"color: {COLOR_RED}; font-size: 24px; font-weight: bold; background: transparent; border: none;"))
        title_row.addStretch()
        critical_layout.addLayout(title_row)
        critical_layout.addWidget(QLabel("Safety Protocol Violation Detected", styleSheet="color: white; font-size: 14px; font-weight: bold; background: transparent; border: none;"))
        meta_row = QHBoxLayout()
        for index, (k, v, c) in enumerate([("Location", alert_info["location"], "white"), ("Time", alert_info["time"], "white"), ("Severity", alert_info["severity"], COLOR_RED)]):
            card = QFrame()
            card.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.03); border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
            card_lay = QVBoxLayout(card)
            card_lay.addWidget(QLabel(k, styleSheet=f"color: {COLOR_TEXT_MUTED}; font-size: 11px; background: transparent; border: none;"))
            card_lay.addWidget(QLabel(v, styleSheet=f"color: {c}; font-size: 14px; font-weight: bold; background: transparent; border: none;"))
            meta_row.addWidget(card, 1)
        critical_layout.addLayout(meta_row)
        details = QFrame()
        details.setStyleSheet("background-color: rgba(217, 56, 58, 0.05); border: 1px solid rgba(217, 56, 58, 0.2); border-radius: 8px;")
        details_layout = QVBoxLayout(details)
        for detail_text in alert_info["details"]:
            details_layout.addWidget(QLabel(f"• {detail_text}", styleSheet="color: #FFC0C1; font-size: 13px; background: transparent; border: none;"))
        critical_layout.addWidget(details)
        self.trigger_btn = QPushButton("🚨 TRIGGER ALARM")
        self.trigger_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_RED}; color: white; font-size: 16px; font-weight: bold; border: none; border-radius: 8px; padding: 14px; }}")
        critical_layout.addWidget(self.trigger_btn)
        layout.addWidget(critical_box)
        layout.addWidget(QLabel("Recent Alerts", styleSheet="color: white; font-size: 18px; font-weight: bold;"))
        list_container = QVBoxLayout()
        for item in CONFIG["recent_alerts"]:
            col = COLOR_RED if item["severity"] == "HIGH" else COLOR_YELLOW if item["severity"] == "MEDIUM" else COLOR_GREEN
            row = QFrame()
            row.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            row_layout.addWidget(QLabel(item["severity"], styleSheet=f"color: {col}; font-weight: bold; font-size: 11px; background-color: rgba(255,255,255,0.04); border-radius: 4px; padding: 4px 10px; border: none;"))
            info = QVBoxLayout()
            info.addWidget(QLabel(item["name"], styleSheet="color: white; font-weight: bold; font-size: 13px; background: transparent; border: none;"))
            info.addWidget(QLabel(item["time_ago"], styleSheet=f"color: {COLOR_TEXT_MUTED}; font-size: 11px; background: transparent; border: none;"))
            row_layout.addLayout(info, 1)
            row_layout.addWidget(QLabel(item["status"], styleSheet=f"color: {col}; font-weight: bold; font-size: 11px; background-color: rgba(255,255,255,0.04); border-radius: 4px; padding: 6px 12px; border: none;"))
            list_container.addWidget(row)
        layout.addLayout(list_container)
        layout.addStretch()

class OpsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QVBoxLayout()
        header.addWidget(QLabel("Operator Profile", styleSheet="color: white; font-size: 24px; font-weight: bold;"))
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
        prof_layout.addWidget(avatar, 0, Qt.AlignCenter)
        prof_layout.addWidget(QLabel(CONFIG["op_name"], alignment=Qt.AlignCenter, styleSheet="color: white; font-size: 18px; font-weight: bold; background: transparent; border: none;"))
        prof_layout.addWidget(QLabel(CONFIG["op_role"], alignment=Qt.AlignCenter, styleSheet=f"color: {COLOR_TEXT_MUTED}; font-size: 12px; background: transparent; border: none;"))
        prof_layout.addStretch()
        panel_layout.addWidget(profile_card, 1)
        layout.addLayout(panel_layout)
        layout.addStretch()

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.occurrences_db = Path(__file__).resolve().parents[2] / "ocorrencias_risco.db"
        self._initialize_occurrences_db()
        self.init_ui()

    def _initialize_occurrences_db(self):
        with sqlite3.connect(self.occurrences_db) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    risk_percentage INTEGER NOT NULL,
                    risk_level TEXT NOT NULL
                )
                """
            )

    def _load_saved_risks(self):
        with sqlite3.connect(self.occurrences_db) as connection:
            rows = connection.execute(
                """
                SELECT risk_percentage
                FROM risk_occurrences
                ORDER BY id DESC
                LIMIT 60
                """
            ).fetchall()
        return [int(row[0]) for row in reversed(rows)]

    def _risk_level(self, risk_val):
        if risk_val <= 30:
            return "BAIXO"
        if risk_val <= 60:
            return "MÉDIO"
        return "ALTO"

    def _save_occurrence(self, risk_val, risk_level):
        with sqlite3.connect(self.occurrences_db) as connection:
            connection.execute(
                """
                INSERT INTO risk_occurrences (recorded_at, risk_percentage, risk_level)
                VALUES (?, ?, ?)
                """,
                (datetime.now().isoformat(timespec="seconds"), risk_val, risk_level),
            )

    def _load_daily_occurrences(self):
        today = datetime.now().date()
        first_day = today - timedelta(days=6)
        day_keys = [
            (first_day + timedelta(days=offset)).isoformat()
            for offset in range(7)
        ]
        with sqlite3.connect(self.occurrences_db) as connection:
            rows = connection.execute(
                """
                SELECT substr(recorded_at, 1, 10), COUNT(*)
                FROM risk_occurrences
                WHERE substr(recorded_at, 1, 10) >= ?
                GROUP BY substr(recorded_at, 1, 10)
                """,
                (first_day.isoformat(),),
            ).fetchall()
        counts = {day: count for day, count in rows}
        labels = [
            (first_day + timedelta(days=offset)).strftime("%d/%m")
            for offset in range(7)
        ]
        return labels, [counts.get(day, 0) for day in day_keys]

    def _refresh_daily_occurrences(self):
        labels, values = self._load_daily_occurrences()
        self.daily_chart.update_data(labels, values)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QVBoxLayout()
        header.addWidget(QLabel("Risk Evolution", styleSheet="color: white; font-size: 24px; font-weight: bold;"))
        layout.addLayout(header)
        
        # Integracao PyQtGraph[cite: 1]
        chart1_card = QFrame()
        chart1_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;")
        chart1_lay = QVBoxLayout(chart1_card)
        chart1_lay.addWidget(QLabel("📈 Real-time Risk Level Trend (%)", styleSheet="color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;"))
        
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
        saved_risks = self._load_saved_risks()
        self.risk_data = [0] * (60 - len(saved_risks)) + saved_risks
        self._last_risk_level = None
        self.pen = pg.mkPen(color=COLOR_RED, width=3)
        self.data_line = self.plot_widget.plot(self.time_data, self.risk_data, pen=self.pen)
        
        chart2_card = QFrame()
        chart2_card.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;")
        chart2_lay = QVBoxLayout(chart2_card)
        chart2_lay.addWidget(QLabel("📊 Daily Incident Count", styleSheet="color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;"))
        x_lbls, daily_values = self._load_daily_occurrences()
        series2 = [{"name": "Incidents", "color": COLOR_YELLOW, "data": daily_values}]
        self.daily_chart = CustomChartWidget(x_lbls, series2, (0, max(8, max(daily_values, default=0) + 1)))
        chart2_lay.addWidget(self.daily_chart)
        layout.addWidget(chart2_card)

    def update_chart(self, risk_val):
        risk_val = max(0, min(100, int(risk_val)))
        risk_level = self._risk_level(risk_val)
        if risk_level != self._last_risk_level:
            self._save_occurrence(risk_val, risk_level)
            self._last_risk_level = risk_level
            self._refresh_daily_occurrences()

        self.risk_data = self.risk_data[1:]
        self.risk_data.append(risk_val)
        self.data_line.setData(self.time_data, self.risk_data)

# ----------------- MAIN LAYOUT -----------------
class DashboardMainLayout(QWidget):
    back_requested = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()


    def update_live_metrics(self, postura, epi, risco_texto, cor, risco_percentual):
        self.page_dashboard.gauge.set_value(risco_percentual)
        self.page_dashboard.card_posture.set_value(postura.replace("Postura:", "").strip(), cor)
        self.page_dashboard.card_epi.set_value(epi.replace("EPI:", "").strip(), cor)
        self.page_dashboard.cam1.status_badge.setText(risco_texto)
        self.page_dashboard.cam1.status_badge.setStyleSheet(f"color: {cor}; font-weight: bold; font-size: 11px; background-color: {cor}25; border-radius: 4px; padding: 4px 8px;")
        
        # Atualiza gráfico ao vivo[cite: 1]
        self.page_reports.update_chart(risco_percentual)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {COLOR_BG_SIDEBAR}; border-right: 1px solid {COLOR_BORDER};")
        sidebar_layout = QVBoxLayout(sidebar)
        logo = QLabel("ProSec", styleSheet=f"color: {COLOR_YELLOW}; font-size: 22px; font-weight: bold; background: transparent;")
        sidebar_layout.addWidget(logo)
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
            btn.setStyleSheet(f"QPushButton {{ background-color: transparent; color: {COLOR_TEXT_MUTED}; border: none; font-weight: bold; font-size: 13px; text-align: left; padding: 12px 15px; border-radius: 8px; }} QPushButton:hover {{ background-color: #20222B; color: white; }} QPushButton:checked {{ background-color: {COLOR_YELLOW}; color: #121319; }}")
            sidebar_layout.addWidget(btn)
        
        self.btn_dashboard.setChecked(True)
        sidebar_layout.addStretch()
        self.btn_exit.clicked.connect(self.back_requested.emit)
        main_layout.addWidget(sidebar)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {COLOR_BG_MAIN}; }}")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
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
        
        # Conexão de Abas da Sidebar
        self.btn_dashboard.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_alerts.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.btn_ops.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.btn_reports.clicked.connect(lambda: self.stack.setCurrentIndex(3))