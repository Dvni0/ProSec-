import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from login_view import LoginView
from selection_view import SelectionView
from dashboard_view import DashboardMainLayout

class ApplicationOrchestrator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProSec - Industrial Safety Monitoring")
        self.resize(1300, 850)
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)
        self.init_views()
        
    def init_views(self):
        self.login_view = LoginView()
        self.selection_view = SelectionView()
        self.dashboard_view = DashboardMainLayout()
        
        self.central_stack.addWidget(self.login_view)      # Índice 0
        self.central_stack.addWidget(self.selection_view)  # Índice 1
        self.central_stack.addWidget(self.dashboard_view)  # Índice 2
        
        self.login_view.login_successful.connect(self._goto_selection_screen)
        
        # Conexões independentes para abrir o Dashboard na aba correta
        self.selection_view.camera_selected.connect(lambda: self._goto_dashboard_screen(0))
        self.selection_view.settings_selected.connect(lambda: self._goto_dashboard_screen(2)) # Ops
        self.selection_view.ranking_selected.connect(lambda: self._goto_dashboard_screen(3))  # Reports
        
        self.selection_view.back_requested.connect(self._goto_login_screen)
        self.dashboard_view.back_requested.connect(self._goto_selection_screen)
        
    def _goto_login_screen(self):
        self.central_stack.setCurrentIndex(0)
        
    def _goto_selection_screen(self):
        self.central_stack.setCurrentIndex(1)
        
    def _goto_dashboard_screen(self, page_index=0):
        # 1. Troca a aba ativa no Stack central do Dashboard
        self.dashboard_view.stack.setCurrentIndex(page_index)
        
        # 2. Desmarca todos os botões da Sidebar
        for btn in self.dashboard_view.nav_buttons:
            btn.setChecked(False)
            
        # 3. Marca o botão visual correto na Sidebar
        self.dashboard_view.nav_buttons[page_index].setChecked(True)
        
        # 4. Transita para a tela do Dashboard de fato
        self.central_stack.setCurrentIndex(2)

    def closeEvent(self, event):
        try:
            if hasattr(self, 'dashboard_view') and hasattr(self.dashboard_view, 'pipeline_thread'):
                print("Encerrando a Inteligência Artificial e liberando hardware...")
                self.dashboard_view.pipeline_thread.stop()
        except Exception as e:
            print(f"Aviso ao encerrar as threads e a câmera: {e}")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    orchestrator = ApplicationOrchestrator()
    orchestrator.show()
    sys.exit(app.exec())