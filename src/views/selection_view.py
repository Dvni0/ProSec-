# selection_view.py
from PySide6.QtCore import Qt, Signal, QRectF, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from configs.config import COLOR_BG_MAIN, COLOR_BORDER, COLOR_YELLOW, COLOR_TEXT_MUTED, NOME_DO_OPERADOR

class OptionCard(QPushButton):
    """Card interativo com desenho vetorial estilizado dos ícones."""
    def __init__(self, title, icon_type, is_active=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.icon_type = icon_type
        self.is_active = is_active
        self.setFixedSize(180, 180)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bg_color = QColor("#171921") if self.is_active else QColor("#13151C")
        border_color = QColor(COLOR_YELLOW) if self.is_active else QColor(COLOR_BORDER)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        
        icon_color = COLOR_YELLOW if self.is_active else "#8A909F"
        pen = QPen(QColor(icon_color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        if self.icon_type == "camera":
            painter.save()
            painter.translate(90, 75)
            painter.rotate(-15)
            painter.drawRoundedRect(-25, -12, 50, 24, 4, 4)
            painter.drawRect(25, -8, 5, 16)
            painter.drawPolyline([QPoint(-25, -12), QPoint(-15, -16), QPoint(25, -16)])
            painter.restore()
            painter.save()
            painter.translate(90, 75)
            painter.drawLine(-25, 0, -40, 0)
            painter.drawLine(-40, 0, -40, 15)
            painter.restore()
            
        elif self.icon_type == "settings":
            painter.save()
            painter.translate(90, 75)
            painter.drawEllipse(-20, -20, 40, 40)
            painter.drawEllipse(-8, -8, 16, 16)
            for angle in range(0, 360, 45):
                painter.save()
                painter.rotate(angle)
                painter.drawRect(-4, -25, 8, 8)
                painter.restore()
            pen_wrench = QPen(QColor(icon_color), 3, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen_wrench)
            painter.drawLine(-12, 12, 12, -12)
            painter.restore()
            
        elif self.icon_type == "ranking":
            painter.save()
            painter.translate(90, 75)
            bars = [(-30, 32), (0, 48), (30, 64)]
            for x, h in bars:
                rect = QRectF(x - 10, 30 - h, 20, h)
                painter.setPen(QPen(QColor(COLOR_BORDER), 1.5))
                painter.setBrush(QBrush(QColor("#1A1C23")))
                painter.drawRoundedRect(rect, 4, 4)
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(COLOR_YELLOW if self.is_active else "#8A909F")))
                painter.drawRoundedRect(x - 10, 30 - h, 20, 8, 3, 3)
            painter.restore()
            
        painter.setPen(QColor("white") if self.is_active else QColor(COLOR_TEXT_MUTED))
        font = QFont("Segoe UI", 10, QFont.Bold if self.is_active else QFont.Normal)
        painter.setFont(font)
        text_rect = QRectF(10, 135, self.width() - 20, 30)
        painter.drawText(text_rect, Qt.AlignCenter, self.title)

class SelectionView(QWidget):
    # Sinais para navegação modularizada
    camera_selected = Signal()
    settings_selected = Signal()
    ranking_selected = Signal()
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)
        
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        self.user_lbl = QLabel(NOME_DO_OPERADOR)
        self.user_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
        
        sidebar_initials = "".join([part[0] for part in NOME_DO_OPERADOR.split() if part])[:2]
        self.avatar_lbl = QLabel(sidebar_initials)
        self.avatar_lbl.setFixedSize(32, 32)
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        self.avatar_lbl.setStyleSheet(f"background-color: {COLOR_BORDER}; color: #121319; font-weight: bold; border-radius: 16px; font-size: 11px; border: none;")
        
        top_bar.addWidget(self.user_lbl)
        top_bar.addWidget(self.avatar_lbl)
        main_layout.addLayout(top_bar)
        
        main_layout.addSpacing(60)
        title_lbl = QLabel("O que deseja acessar?")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: white; font-size: 36px; font-weight: 300; font-family: 'Segoe UI Light'; background: transparent;")
        main_layout.addWidget(title_lbl)
        main_layout.addSpacing(40)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(25)
        cards_layout.setAlignment(Qt.AlignCenter)
        
        card_cam = OptionCard("Acesso às câmeras", "camera", is_active=True)
        card_config = OptionCard("Configurações", "settings", is_active=True) # Ativado
        card_ranking = OptionCard("Ranking", "ranking", is_active=True)
        
        # Conectando todos os cards
        card_cam.clicked.connect(self.camera_selected.emit)
        card_config.clicked.connect(self.settings_selected.emit)
        card_ranking.clicked.connect(self.ranking_selected.emit)
        
        cards_layout.addWidget(card_cam)
        cards_layout.addWidget(card_config)
        cards_layout.addWidget(card_ranking)
        main_layout.addLayout(cards_layout)
        
        main_layout.addSpacing(70)
        bottom_btns = QHBoxLayout()
        bottom_btns.setSpacing(20)
        bottom_btns.setAlignment(Qt.AlignCenter)
        
        create_btn = QPushButton("CRIAÇÃO DE CONTA")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(f"QPushButton {{ background-color: {COLOR_YELLOW}; color: #121319; font-weight: bold; font-size: 13px; border: none; border-radius: 20px; padding: 12px 30px; }} QPushButton:hover {{ background-color: #D39E00; }}")
        
        manage_btn = QPushButton("Gerenciamento de contas")
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; color: {COLOR_YELLOW}; font-weight: bold; font-size: 13px; border: 2px solid {COLOR_YELLOW}; border-radius: 20px; padding: 10px 28px; }} QPushButton:hover {{ background-color: rgba(244,180,0,0.06); }}")
        
        bottom_btns.addWidget(create_btn)
        bottom_btns.addWidget(manage_btn)
        main_layout.addLayout(bottom_btns)
        
        main_layout.addStretch()
        
        back_layout = QHBoxLayout()
        back_btn = QPushButton("←\nVoltar")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"QPushButton {{ color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; text-align: center; border: none; background: transparent; }} QPushButton:hover {{ color: white; }}")
        back_btn.clicked.connect(self.back_requested.emit)
        
        back_layout.addWidget(back_btn)
        back_layout.addStretch()
        main_layout.addLayout(back_layout)

    def set_user(self, user):
        full_name = user.get("full_name", NOME_DO_OPERADOR)
        initials = "".join(part[0] for part in full_name.split() if part)[:2].upper()
        self.user_lbl.setText(full_name)
        self.avatar_lbl.setText(initials)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(COLOR_BG_MAIN))