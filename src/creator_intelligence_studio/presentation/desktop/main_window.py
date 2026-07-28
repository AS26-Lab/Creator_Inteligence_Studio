"""Ventana principal de la aplicación de escritorio."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.navigation import build_navigation_items
from creator_intelligence_studio.presentation.desktop.views.preferences_dialog import (
    PreferencesDialog,
)
from creator_intelligence_studio.presentation.desktop.theme import SIDEBAR_WIDTH
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views import (
    AcousticAnalysisView,
    ClipRankingView,
    CreatorsView,
    DashboardView,
    IntegrationsOverviewView,
    MarketOverviewView,
    AnalyticsView,
    AnalyticsLabView,
    AudienceOverviewView,
    ExperimentsView,
    CreatorMemoryView,
    CreatorLanguageView,
    OnboardingView,
    MultimodalAnalysisView,
    OperationalEvaluationView,
    PersonalizationDataView,
    PersonalizationModelsView,
    ProjectsView,
    SubtitleEditorView,
    TaskCenterView,
    ThumbnailLabView,
    InstagramIntegrationView,
    TikTokIntegrationView,
    YouTubeIntegrationView,
    WorkflowView,
    VisualAnalysisView,
    SystemView,
    TranscriptionView,
    VideosView,
)
from creator_intelligence_studio.presentation.desktop.widgets.inspector import InspectorPanel


class MainWindow(QMainWindow):
    """Ventana principal con navegación lateral y panel contextual."""

    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__()
        self.workspace = workspace
        self.setWindowTitle("Creator Intelligence Studio")
        self.resize(1600, 900)

        self._page_keys = [
            "home",
            "integrations",
            "market",
            "creators",
            "projects",
            "videos",
            "youtube",
            "instagram",
            "tiktok",
            "analytics",
            "audience",
            "analytics_lab",
            "experiments",
            "creator_memory",
            "creator_language",
            "thumbnails",
            "workflow",
            "tasks",
            "onboarding",
            "transcription",
            "subtitles",
            "analysis",
            "visual",
            "multimodal",
            "clips",
            "personalization",
            "evaluation",
            "models",
            "system",
        ]

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setSpacing(2)
        self.sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar.currentRowChanged.connect(self._change_page)

        self.creator_combo = QComboBox()
        self.project_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar en el espacio de trabajo")
        self.gpu_label = QLabel()
        self.gpu_label.setObjectName("MutedLabel")
        self.settings_button = QToolButton()
        self.settings_button.setText("Configuración")
        self.workspace_button = QToolButton()
        self.workspace_button.setText("Tareas")
        self.onboarding_button = QToolButton()
        self.onboarding_button.setText("Guia")

        self.creator_combo.setMinimumWidth(170)
        self.project_combo.setMinimumWidth(170)
        self.search_edit.setMinimumWidth(260)
        self.settings_button.setMinimumWidth(110)
        self.workspace_button.setMinimumWidth(110)
        self.onboarding_button.setMinimumWidth(90)
        self.gpu_label.setMinimumWidth(230)
        self.gpu_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.workspace_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.onboarding_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setToolTip("Abrir configuración de la aplicación")
        self.workspace_button.setToolTip("Abrir el centro de tareas")
        self.onboarding_button.setToolTip("Reabrir el onboarding")
        self.search_edit.setToolTip("Busca en el contenido visible del espacio de trabajo")
        self.creator_combo.setToolTip("Selecciona el creador activo")
        self.project_combo.setToolTip("Selecciona el proyecto activo")
        self.gpu_label.setToolTip("Resumen compacto del estado de GPU y CUDA detectados")

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(10)
        title = QLabel("Creator Intelligence Studio")
        title.setObjectName("TitleLabel")
        top_layout.addWidget(title)
        top_layout.addStretch(1)
        top_layout.addWidget(self.creator_combo)
        top_layout.addWidget(self.project_combo)
        top_layout.addWidget(self.search_edit)
        top_layout.addWidget(self.gpu_label)
        top_layout.addWidget(self.settings_button)
        top_layout.addWidget(self.workspace_button)
        top_layout.addWidget(self.onboarding_button)

        self.stack = QStackedWidget()
        self.inspector = InspectorPanel()
        self.inspector.set_compact_mode(True)
        self.dashboard_view = DashboardView(workspace)
        self.integrations_view = IntegrationsOverviewView(workspace)
        self.market_view = MarketOverviewView(workspace)
        self.creators_view = CreatorsView(workspace, self.inspector)
        self.projects_view = ProjectsView(workspace, self.inspector)
        self.videos_view = VideosView(
            workspace,
            self.inspector,
            open_acoustic_callback=lambda: self.show_page("analysis"),
            open_visual_callback=lambda: self.show_page("visual"),
            open_multimodal_callback=lambda: self.show_page("multimodal"),
            open_clips_callback=lambda: self.show_page("clips"),
            open_subtitles_callback=lambda: self.show_page("subtitles"),
            open_workflow_callback=lambda: self.show_page("workflow"),
        )
        self.analytics_view = AnalyticsView(workspace)
        self.audience_view = AudienceOverviewView(workspace)
        self.analytics_lab_view = AnalyticsLabView(workspace)
        self.experiments_view = ExperimentsView(workspace)
        self.creator_memory_view = CreatorMemoryView(workspace)
        self.creator_language_view = CreatorLanguageView(workspace)
        self.thumbnail_lab_view = ThumbnailLabView(workspace)
        self.youtube_view = YouTubeIntegrationView(workspace)
        self.instagram_view = InstagramIntegrationView(workspace)
        self.tiktok_view = TikTokIntegrationView(workspace)
        self.workflow_view = WorkflowView(workspace)
        self.task_center_view = TaskCenterView(workspace)
        self.onboarding_view = OnboardingView(workspace)
        self.transcription_view = TranscriptionView(workspace)
        self.subtitle_editor_view = SubtitleEditorView(workspace)
        self.acoustic_view = AcousticAnalysisView(workspace)
        self.visual_view = VisualAnalysisView(workspace)
        self.multimodal_view = MultimodalAnalysisView(workspace)
        self.clip_ranking_view = ClipRankingView(workspace)
        self.personalization_view = PersonalizationDataView(workspace)
        self.evaluation_view = OperationalEvaluationView(workspace)
        self.personalization_models_view = PersonalizationModelsView(workspace)
        self.system_view = SystemView(workspace)
        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.integrations_view)
        self.stack.addWidget(self.market_view)
        self.stack.addWidget(self.creators_view)
        self.stack.addWidget(self.projects_view)
        self.stack.addWidget(self.videos_view)
        self.stack.addWidget(self.youtube_view)
        self.stack.addWidget(self.instagram_view)
        self.stack.addWidget(self.tiktok_view)
        self.stack.addWidget(self.analytics_view)
        self.stack.addWidget(self.audience_view)
        self.stack.addWidget(self.analytics_lab_view)
        self.stack.addWidget(self.experiments_view)
        self.stack.addWidget(self.creator_memory_view)
        self.stack.addWidget(self.creator_language_view)
        self.stack.addWidget(self.thumbnail_lab_view)
        self.stack.addWidget(self.workflow_view)
        self.stack.addWidget(self.task_center_view)
        self.stack.addWidget(self.onboarding_view)
        self.stack.addWidget(self.transcription_view)
        self.stack.addWidget(self.subtitle_editor_view)
        self.stack.addWidget(self.acoustic_view)
        self.stack.addWidget(self.visual_view)
        self.stack.addWidget(self.multimodal_view)
        self.stack.addWidget(self.clip_ranking_view)
        self.stack.addWidget(self.personalization_view)
        self.stack.addWidget(self.evaluation_view)
        self.stack.addWidget(self.personalization_models_view)
        self.stack.addWidget(self.system_view)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(12, 12, 12, 12)
        central_layout.setSpacing(12)
        central_layout.addWidget(top_bar)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        body.addWidget(self.inspector)
        central_layout.addLayout(body, 1)
        self.setCentralWidget(central)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.setStatusBar(status)
        self.status_label = QLabel("Listo")
        self.statusBar().addPermanentWidget(self.status_label)

        self._build_sidebar()
        self._build_topbar()
        self.refresh_all()
        self.show_page(self.workspace.ui_state.last_page if self.workspace.ui_state.last_page in self._page_keys else "home")

    def _build_sidebar(self) -> None:
        for item in build_navigation_items():
            list_item = QListWidgetItem(item.label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.key)
            if not item.enabled and item.badge:
                list_item.setText(f"{item.label} · {item.badge}")
                list_item.setToolTip("Próximamente")
                list_item.setFlags(list_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                list_item.setToolTip(f"Abrir {item.label}")
            self.sidebar.addItem(list_item)
        self.sidebar.setCurrentRow(0)

    def _build_topbar(self) -> None:
        self.creator_combo.currentIndexChanged.connect(self._creator_changed)
        self.project_combo.currentIndexChanged.connect(self._project_changed)
        self.search_edit.textChanged.connect(self._search_changed)
        self.settings_button.clicked.connect(self._open_preferences)
        self.workspace_button.clicked.connect(lambda: self.show_page("tasks"))
        self.onboarding_button.clicked.connect(lambda: self.show_page("onboarding"))
        self._refresh_topbar()

    def refresh_all(self) -> None:
        self.workspace.refresh()
        self._refresh_topbar()
        self.dashboard_view.refresh()
        self.integrations_view.refresh()
        self.market_view.refresh()
        self.creators_view.refresh()
        self.projects_view.refresh()
        self.videos_view.refresh()
        self.analytics_view.refresh()
        self.audience_view.refresh()
        self.analytics_lab_view.refresh()
        self.experiments_view.refresh()
        self.creator_memory_view.refresh()
        self.creator_language_view.refresh()
        self.thumbnail_lab_view.refresh()
        self.youtube_view.refresh()
        self.instagram_view.refresh()
        self.tiktok_view.refresh()
        self.workflow_view.refresh()
        self.task_center_view.refresh()
        self.onboarding_view.refresh()
        self.transcription_view.refresh()
        self.subtitle_editor_view.refresh()
        self.visual_view.refresh()
        self.multimodal_view.refresh()
        self.clip_ranking_view.refresh()
        self.personalization_view.refresh()
        self.evaluation_view.refresh()
        self.personalization_models_view.refresh()
        self.system_view.refresh()
        self._refresh_gpu_state()

    def _refresh_topbar(self) -> None:
        self.creator_combo.blockSignals(True)
        self.project_combo.blockSignals(True)

        self.creator_combo.clear()
        self.creator_combo.addItem("Seleccionar creador", None)
        for creator in self.workspace.creators():
            self.creator_combo.addItem(creator.display_name, creator.id)
        index = self.creator_combo.findData(self.workspace.selected_creator_id) if self.workspace.selected_creator_id else -1
        self.creator_combo.setCurrentIndex(index if index >= 0 else 0)

        self.project_combo.clear()
        self.project_combo.addItem("Seleccionar proyecto", None)
        for project in self.workspace.projects_for_selected_creator():
            self.project_combo.addItem(project.name, project.id)
        index = self.project_combo.findData(self.workspace.selected_project_id) if self.workspace.selected_project_id else -1
        self.project_combo.setCurrentIndex(index if index >= 0 else 0)

        self.creator_combo.blockSignals(False)
        self.project_combo.blockSignals(False)
        self._refresh_context_label()

    def _refresh_context_label(self) -> None:
        creator = self.workspace.selected_creator()
        project = self.workspace.selected_project()
        context = f"Creador: {creator.display_name if creator else 'ninguno'} | Proyecto: {project.name if project else 'ninguno'}"
        if hasattr(self, "context_label"):
            self.context_label.setText(context)
        else:
            self.context_label = QLabel(context)
            self.context_label.setObjectName("MutedLabel")
            self.statusBar().addPermanentWidget(self.context_label)

    def _refresh_gpu_state(self) -> None:
        gpu_devices = self.workspace.diagnostic.gpu_devices
        if gpu_devices:
            gpu = gpu_devices[0]
            vram = (
                f"{gpu.memory_total_mib / 1024:.1f} GiB"
                if gpu.memory_total_mib is not None
                else "VRAM no verificada"
            )
            driver = gpu.driver_version or self.workspace.diagnostic.nvidia_driver_version
            driver_text = f" · Driver: {driver}" if driver else ""
            self.gpu_label.setText(f"GPU: {gpu.name} · {vram}{driver_text}")
        else:
            self.gpu_label.setText("GPU: no verificada")

    def _change_page(self, row: int) -> None:
        if row < 0:
            return
        current_item = self.sidebar.item(row)
        if current_item is None:
            return
        key = current_item.data(Qt.ItemDataRole.UserRole)
        if key not in self._page_keys:
            return
        self.stack.setCurrentIndex(self._page_keys.index(key))
        self.status_label.setText(current_item.text())
        self._search_changed(self.search_edit.text())
        self.workspace.set_last_page(key)

    def show_page(self, key: str) -> None:
        if key not in self._page_keys:
            return
        self.stack.setCurrentIndex(self._page_keys.index(key))
        for row in range(self.sidebar.count()):
            item = self.sidebar.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                self.sidebar.setCurrentRow(row)
                break
        self.workspace.set_last_page(key)

    def _creator_changed(self) -> None:
        creator_id = self.creator_combo.currentData()
        if not creator_id:
            return
        self.workspace.select_creator(str(creator_id))
        self.refresh_all()

    def _project_changed(self) -> None:
        project_id = self.project_combo.currentData()
        if not project_id:
            return
        self.workspace.select_project(str(project_id))
        self.videos_view.refresh()
        self.projects_view.refresh()
        self.workflow_view.refresh()
        self.task_center_view.refresh()

    def _search_changed(self, text: str) -> None:
        current_key = self._page_keys[self.stack.currentIndex()]
        if current_key == "videos":
            self.videos_view.search_edit.blockSignals(True)
            self.videos_view.search_edit.setText(text)
            self.videos_view.search_edit.blockSignals(False)
            self.videos_view.refresh()
        elif current_key == "integrations":
            self.integrations_view.refresh()
        elif current_key == "market":
            self.market_view.refresh()
        elif current_key == "multimodal":
            self.multimodal_view.refresh()
        elif current_key == "analytics":
            self.analytics_view.refresh()
        elif current_key == "audience":
            self.audience_view.refresh()
        elif current_key == "analytics_lab":
            self.analytics_lab_view.refresh()
        elif current_key == "experiments":
            self.experiments_view.refresh()
        elif current_key == "creator_memory":
            self.creator_memory_view.refresh()
        elif current_key == "creator_language":
            self.creator_language_view.refresh()
        elif current_key == "thumbnails":
            self.thumbnail_lab_view.refresh()
        elif current_key == "youtube":
            self.youtube_view.refresh()
        elif current_key == "instagram":
            self.instagram_view.refresh()
        elif current_key == "tiktok":
            self.tiktok_view.refresh()
        elif current_key == "transcription":
            self.transcription_view.refresh()
        elif current_key == "subtitles":
            self.subtitle_editor_view.refresh()
        elif current_key == "visual":
            self.visual_view.refresh()
        elif current_key == "clips":
            self.clip_ranking_view.refresh()
        elif current_key == "personalization":
            self.personalization_view.refresh()
        elif current_key == "evaluation":
            self.evaluation_view.refresh()

    def _open_preferences(self) -> None:
        dialog = PreferencesDialog(self.workspace, self)
        dialog.exec()
        self.refresh_all()
