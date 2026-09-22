import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame
)
from config import COLOR_BG_MAIN, COLOR_BORDER, COLOR_YELLOW, COLOR_TEXT_MUTED, LOGIN_BACKGROUND_IMAGE_PATH

class LoginView(QWidget):
    # Sinal emitido ao validar o login (conecta com a tela de entrada)
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ==============================================================================
        # 🔑 ÁREAS DE INPUT FACILMENTE ACESSÍVEIS (Mapeamento do Back-end)
        # ==============================================================================
        self.input_username = QLineEdit()       # Campo de Entrada: E-mail ou ID
        self.input_password = QLineEdit()       # Campo de Entrada: Senha (com máscara)
        self.chk_remember_me = QCheckBox()      # Checkbox: Lembrar de mim
        self.btn_enter = QPushButton()          # Botão: ENTRAR (Gera a ação de Login)
        # ==============================================================================

        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container centralizador de conteúdo (para garantir responsividade)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(40, 60, 40, 60)
        center_layout.setSpacing(10)
        
        # Cabeçalho da Marca
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        logo_lbl = QLabel("ProSec")
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 32px; font-weight: bold; background: transparent;")
        
        sub_logo_lbl = QLabel("Sistema de segurança industrial")
        sub_logo_lbl.setAlignment(Qt.AlignCenter)
        sub_logo_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
        
        header_layout.addWidget(logo_lbl)
        header_layout.addWidget(sub_logo_lbl)
        center_layout.addLayout(header_layout)
        center_layout.addSpacing(15)
        
        # Cartão de Login Principal
        login_card = QFrame()
        login_card.setObjectName("loginCard")
        login_card.setFixedWidth(400)
        login_card.setStyleSheet(f"""
            QFrame#loginCard {{
                background-color: rgba(22, 23, 29, 0.93);
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
        """)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(35, 35, 35, 35)
        card_layout.setSpacing(18)
        
        # Título Interno do Cartão
        card_title = QLabel("ENTRAR NO SISTEMA")
        card_title.setAlignment(Qt.AlignCenter)
        card_title.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        card_layout.addWidget(card_title)
        card_layout.addSpacing(5)
        
        # Configuração do Input: Usuário/E-mail
        user_container = QVBoxLayout()
        user_container.setSpacing(6)
        user_lbl = QLabel("E-mail ou ID")
        user_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        
        self.input_username.setPlaceholderText("✉️  E-mail ou ID")
        self.input_username.setStyleSheet(f"""
            QLineEdit {{
                background-color: #16171D;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                color: white;
                padding: 10px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_YELLOW};
            }}
        """)
        user_container.addWidget(user_lbl)
        user_container.addWidget(self.input_username)
        card_layout.addLayout(user_container)
        
        # Configuração do Input: Senha
        pass_container = QVBoxLayout()
        pass_container.setSpacing(6)
        pass_lbl = QLabel("Senha")
        pass_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        
        self.input_password.setPlaceholderText("🔒  Senha")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setStyleSheet(f"""
            QLineEdit {{
                background-color: #16171D;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                color: white;
                padding: 10px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_YELLOW};
            }}
        """)
        pass_container.addWidget(pass_lbl)
        pass_container.addWidget(self.input_password)
        card_layout.addLayout(pass_container)
        
        # Linha Alternativa: Lembrar de Mim & Esqueci Minha Senha
        options_layout = QHBoxLayout()
        self.chk_remember_me.setText("Lembrar de mim")
        self.chk_remember_me.setStyleSheet(f"""
            QCheckBox {{
                color: white;
                font-size: 12px;
                border: none;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                background-color: #16171D;
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLOR_YELLOW};
                border: 1px solid {COLOR_YELLOW};
            }}
        """)
        
        forgot_btn = QPushButton("Esqueci minha senha?")
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.setStyleSheet(f"color: {COLOR_YELLOW}; font-size: 12px; border: none; background: transparent; font-weight: bold;")
        
        options_layout.addWidget(self.chk_remember_me)
        options_layout.addStretch()
        options_layout.addWidget(forgot_btn)
        card_layout.addLayout(options_layout)
        card_layout.addSpacing(5)
        
        # Botão de Ação: Entrar no Sistema
        self.btn_enter.setText("ENTRAR")
        self.btn_enter.setCursor(Qt.PointingHandCursor)
        self.btn_enter.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_YELLOW};
                color: #121319;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 20px;
                padding: 12px;
            }}
            QPushButton:hover {{
                background-color: #D39E00;
            }}
        """)
        self.btn_enter.clicked.connect(self._handle_login)
        card_layout.addWidget(self.btn_enter)
        
        # Texto de rodapé no Cartão
        register_lbl = QLabel("Ainda não tem conta? <a href='#' style='color: #F4B400; text-decoration: underline;'>Entre em contato com o administrador</a>")
        register_lbl.setAlignment(Qt.AlignCenter)
        register_lbl.setOpenExternalLinks(False)
        register_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; border: none; background: transparent;")
        card_layout.addWidget(register_lbl)
        
        center_layout.addWidget(login_card, 0, Qt.AlignCenter)
        center_layout.addStretch()
        
        # Rodapé de Direitos Autorais Geral
        footer_lbl = QLabel("© 2024 ProSec Industrial Security. Todos os direitos reservados.")
        footer_lbl.setAlignment(Qt.AlignCenter)
        footer_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; background: transparent;")
        center_layout.addWidget(footer_lbl)
        
        main_layout.addWidget(center_widget)

    def _handle_login(self):
        """Dispara a transição de tela. O Back-end poderá validar as credenciais aqui."""
        self.login_successful.emit()

    def paintEvent(self, event):
        """Estiliza dinamicamente o fundo com a imagem especificada no config.py."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if LOGIN_BACKGROUND_IMAGE_PATH and os.path.exists(LOGIN_BACKGROUND_IMAGE_PATH):
            pixmap = QPixmap(LOGIN_BACKGROUND_IMAGE_PATH)
            # Escala cobrindo toda a janela sem distorcer
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled_pixmap)
            
            # Película escura protetora para manter o contraste do login
            painter.fillRect(self.rect(), QColor(15, 16, 20, 205))
        else:
            painter.fillRect(self.rect(), QColor(COLOR_BG_MAIN))