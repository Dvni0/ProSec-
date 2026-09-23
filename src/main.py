import sys
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Importação das Telas (Front-end)
from views.login_view import LoginView
from views.selection_view import SelectionView
from views.dashboard_view import DashboardMainLayout

# Importação da Lógica de Negócio (Back-end)

from controllers.pipelineThreadSource import SafetyPipelineThread

class ApplicationOrchestrator(QMainWindow):

    """Orquestrador Central: Controla as telas e o ciclo de vida da Inteligência Artificial."""
    def __init__(self):

        super().__init__()
        self.setWindowTitle("ProSec - Industrial Safety Monitoring")
        self.resize(1300, 850)

        self.pipelines = {} # Dicionário para guardar as threads de múltiplas câmeras
        self.pipeline_thread = None

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

        # Conexão dos botões de adicionar
        self.dashboard_view.page_dashboard.cam1.btn_add.clicked.connect(lambda: self._configure_and_start_cam("cam1"))
        self.dashboard_view.page_dashboard.cam2.btn_add.clicked.connect(lambda: self._configure_and_start_cam("cam2"))
        self.dashboard_view.page_dashboard.cam3.btn_add.clicked.connect(lambda: self._configure_and_start_cam("cam3"))
        self.dashboard_view.page_dashboard.cam4.btn_add.clicked.connect(lambda: self._configure_and_start_cam("cam4"))

        # Conexão dos botões de fechar
        self.dashboard_view.page_dashboard.cam1.close_requested.connect(lambda: self._stop_cam("cam1"))
        self.dashboard_view.page_dashboard.cam2.close_requested.connect(lambda: self._stop_cam("cam2"))
        self.dashboard_view.page_dashboard.cam3.close_requested.connect(lambda: self._stop_cam("cam3"))
        self.dashboard_view.page_dashboard.cam4.close_requested.connect(lambda: self._stop_cam("cam4"))

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

    def _configure_and_start_cam(self, cam_id):
        from views.dashboard_view import TagSelectionDialog
        
        dialog = TagSelectionDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            
            # Pega dinamicamente o painel (cam1, cam2...) que foi clicado
            cam_widget = getattr(self.dashboard_view.page_dashboard, cam_id)
            cam_widget.stack.setCurrentIndex(1) # Mostra a tela de vídeo
            
            if cam_id in self.pipelines:
                self.pipelines[cam_id].stop()
                
            # A fonte pode ser um índice local ou uma URL RTSP.
            thread = SafetyPipelineThread(porta_serial='COM3', camera_index=settings["camera_source"])
            thread.frame_updated.connect(cam_widget.set_frame)
            thread.metrics_updated.connect(self.dashboard_view.update_live_metrics)
            cam_widget.dead_zones_changed.connect(thread.set_dead_zones)
            
            thread.set_tags(settings["tags"])
            thread.set_dead_zones(cam_widget.feed_placeholder.dead_zones)
            self.pipelines[cam_id] = thread
            thread.start()

    def _stop_cam(self, cam_id):
        """Para a câmera selecionada e volta a tela para o botão '+'"""
        if cam_id in self.pipelines:
            self.pipelines[cam_id].stop()
            del self.pipelines[cam_id]
            
        cam_widget = getattr(self.dashboard_view.page_dashboard, cam_id)
        cam_widget.stack.setCurrentIndex(0) # Volta para o botão '+'
        cam_widget.feed_placeholder.clear_frame()

    def closeEvent(self, event):
        """Garante que todas as câmeras soltem as portas USB ao fechar o app"""
        print("Encerrando todas as instâncias de IA...")
        for thread in self.pipelines.values():
            thread.stop()
        self.pipelines.clear()

        if self.pipeline_thread is not None:
            self.pipeline_thread.stop()
            self.pipeline_thread = None

        event.accept()

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

if __name__ == "__main__":

    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    orchestrator = ApplicationOrchestrator()
    orchestrator.show()
    sys.exit(app.exec())