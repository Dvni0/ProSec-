# main.py
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Importação dos módulos customizados
from login_view import LoginView
from selection_view import SelectionView
from dashboard_view import DashboardMainLayout

class ApplicationOrchestrator(QMainWindow):
    """Orquestrador da Janela de Navegação Geral do Aplicativo."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProSec - Industrial Safety Monitoring")
        self.resize(1300, 850)
        
        # Stack centralizador de todas as telas principais do sistema
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)
        
        self.init_views()
        
    def init_views(self):
        # Instanciação das views desacopladas
        self.login_view = LoginView()
        self.selection_view = SelectionView()
        self.dashboard_view = DashboardMainLayout()
        
        # Adiciona as telas ao gerenciador do Stack
        self.central_stack.addWidget(self.login_view)      # Índice 0 (Tela Inicial)
        self.central_stack.addWidget(self.selection_view)  # Índice 1
        self.central_stack.addWidget(self.dashboard_view)  # Índice 2
        
        # --- ORQUESTRADOR DE FLUXOS (SINAIS E SLOTS) ---
        
        # Tela 0 (Login) -> Tela 1 (Seleção de Acesso)
        self.login_view.login_successful.connect(self._goto_selection_screen)
        
        # Tela 1 (Seleção de Acesso) -> Tela 2 (Dashboard / Ranking)
        self.selection_view.ranking_selected.connect(self._goto_dashboard_screen)
        
        # Tela 1 (Seleção de Acesso) -> Retorna para Tela 0 (Login)
        self.selection_view.back_requested.connect(self._goto_login_screen)
        
        # Tela 2 (Dashboard) -> Retorna para Tela 1 (Seleção de Acesso)
        self.dashboard_view.back_requested.connect(self._goto_selection_screen)
        
    def _goto_login_screen(self):
        self.central_stack.setCurrentIndex(0)
        
    def _goto_selection_screen(self):
        self.central_stack.setCurrentIndex(1)
        
    def _goto_dashboard_screen(self):
        # Reseta o botão de navegação interna do dashboard para o painel inicial
        self.dashboard_view.btn_dashboard.setChecked(True)
        self.dashboard_view.stack.setCurrentIndex(0)
        
        self.central_stack.setCurrentIndex(2)

    def closeEvent(self, event):
        """
        Sobrescreve o comportamento de fechamento da janela para garantir
        que os recursos de hardware (câmera e serial USB) sejam liberados
        corretamente.
        """
        try:
            # Verifica se o dashboard foi instanciado e possui uma thread rodando
            if hasattr(self, 'dashboard_view') and hasattr(self.dashboard_view, 'pipeline_thread'):
                print("Encerrando a Inteligência Artificial e liberando hardware...")
                self.dashboard_view.pipeline_thread.stop()
        except Exception as e:
            print(f"Aviso ao encerrar as threads e a câmera: {e}")
        
        # Aceita e conclui o fechamento do aplicativo
        event.accept()

# -------------------------------------------------------------
# ENTRADA DE EXECUÇÃO DO PROGRAMA
# -------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Define a fonte global para garantir renderização idêntica em múltiplas plataformas
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    orchestrator = ApplicationOrchestrator()
    orchestrator.show()
    sys.exit(app.exec())