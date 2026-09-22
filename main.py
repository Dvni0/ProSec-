import sys

from PySide6.QtCore import Qt

from PySide6.QtGui import QFont

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Importação das Telas (Front-end)

from login_view import LoginView

from selection_view import SelectionView

from dashboard_view import DashboardMainLayout

# Importação da Lógica de Negócio (Back-end)

from app4 import SafetyPipelineThread

class ApplicationOrchestrator(QMainWindow):

    """Orquestrador Central: Controla as telas e o ciclo de vida da Inteligência Artificial."""

    

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ProSec - Industrial Safety Monitoring")

        self.resize(1300, 850)

        

        self.pipeline_thread = None # A IA começa desligada

        

        # Stack centralizador de todas as telas principais do sistema

        self.central_stack = QStackedWidget()

        self.setCentralWidget(self.central_stack)

        

        self.init_views()

        

    def init_views(self):

        # 1. Instanciação das views

        self.login_view = LoginView()

        self.selection_view = SelectionView()

        self.dashboard_view = DashboardMainLayout()

        

        self.central_stack.addWidget(self.login_view)      # Índice 0

        self.central_stack.addWidget(self.selection_view)  # Índice 1

        self.central_stack.addWidget(self.dashboard_view)  # Índice 2

        

        # 2. Orquestração de Sinais e Navegação

        self.login_view.login_successful.connect(self._handle_login_success)

        

        self.selection_view.camera_selected.connect(lambda: self._goto_dashboard_screen(0))

        self.selection_view.settings_selected.connect(lambda: self._goto_dashboard_screen(2))

        self.selection_view.ranking_selected.connect(lambda: self._goto_dashboard_screen(3))

        

        self.selection_view.back_requested.connect(self._goto_login_screen)

        self.dashboard_view.back_requested.connect(self._goto_selection_screen)

    def _start_ai_pipeline(self):

        """Inicializa e conecta a Inteligência Artificial às telas"""

        if self.pipeline_thread is None:

            print("Iniciando carregamento dos modelos YOLO e XGBoost...")

            self.pipeline_thread = SafetyPipelineThread(porta_serial='COM3')

            

            # Conecta os sinais da IA (app4) DIRETAMENTE aos métodos da interface (dashboard_view)

            self.pipeline_thread.frame_updated.connect(self.dashboard_view.page_dashboard.cam1.set_frame)

            self.pipeline_thread.metrics_updated.connect(self.dashboard_view.update_live_metrics)

            

            self.pipeline_thread.start()

    def _handle_login_success(self):

        """Função chamada quando o usuário passa do login."""

        self.central_stack.setCurrentIndex(1)

        # Liga a câmera e a IA apenas quando o login estiver feito

        self._start_ai_pipeline()

    def _goto_login_screen(self):

        self.central_stack.setCurrentIndex(0)

        

    def _goto_selection_screen(self):

        self.central_stack.setCurrentIndex(1)

        

    def _goto_dashboard_screen(self, page_index=0):

        self.dashboard_view.stack.setCurrentIndex(page_index)

        for btn in self.dashboard_view.nav_buttons:

            btn.setChecked(False)

        self.dashboard_view.nav_buttons[page_index].setChecked(True)

        self.central_stack.setCurrentIndex(2)

    def closeEvent(self, event):

        """Libera de forma segura a Câmera e o Microcontrolador ao fechar o app."""

        if self.pipeline_thread is not None:

            print("Encerrando a Inteligência Artificial e liberando portas USB/Câmera...")

            self.pipeline_thread.stop()

            self.pipeline_thread = None

            

        event.accept()

if __name__ == "__main__":

    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)

    app.setFont(font)

    orchestrator = ApplicationOrchestrator()

    orchestrator.show()

    sys.exit(app.exec())