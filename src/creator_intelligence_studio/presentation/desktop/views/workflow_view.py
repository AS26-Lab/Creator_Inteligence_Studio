"""Vista unificada de workflow por video."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.error_mapping import map_error
from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class WorkflowThread(QThread):
    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, video_id: str, *, mode: str, stage_name: str | None = None) -> None:
        super().__init__()
        self.workspace = workspace
        self.video_id = video_id
        self.mode = mode
        self.stage_name = stage_name
        self._task_id: str | None = None

    def _progress(self, phase: str, ratio: float) -> None:
        self.progress_ready.emit(str(phase), float(ratio or 0.0))
        if self._task_id is not None:
            self.workspace.update_background_task(
                self._task_id,
                stage_name=phase,
                progress_percent=max(0.0, min(100.0, float(ratio or 0.0) * 100.0)),
                message=str(phase),
            )

    def run(self) -> None:  # pragma: no cover - flujo Qt
        task = self.workspace.register_background_task(
            title="Workflow de video",
            status="running",
            stage_name=self.stage_name,
            video_id=self.video_id,
            video_title=getattr(self.workspace.selected_video(), "title", None),
            action_id=self.mode,
            message="Tarea iniciada",
        )
        self._task_id = task.task_id
        try:
            if self.mode == "next":
                result = self.workspace.run_pipeline_next_step(self.video_id, progress_callback=self._progress)
            elif self.mode == "group":
                result = self.workspace.run_pipeline_group(
                    self.video_id,
                    self.stage_name or "seleccion",
                    progress_callback=self._progress,
                )
            elif self.mode == "until_ranking":
                result = self.workspace.run_pipeline_until_ranking(self.video_id, progress_callback=self._progress)
            elif self.mode == "retry":
                result = self.workspace.retry_pipeline_stage(
                    self.video_id,
                    self.stage_name or "inspection",
                    progress_callback=self._progress,
                )
            else:
                raise ValueError("Modo de workflow no reconocido.")
        except Exception as exc:  # pragma: no cover - defensa general
            self.workspace.fail_background_task(task.task_id, str(exc))
            self.error_ready.emit(map_error(exc).explanation)
            return
        self.workspace.complete_background_task(task.task_id, "Workflow completado")
        self.result_ready.emit(result)


class WorkflowView(QWidget):
    """Resumen accionable del estado y de la siguiente accion recomendada."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: WorkflowThread | None = None

        self.empty_state = EmptyStateWidget(
            "Sin video activo",
            "Selecciona o importa un video para ver su workflow y su siguiente accion.",
        )

        self.video_label = QLabel("Video: no seleccionado")
        self.video_label.setObjectName("SectionLabel")
        self.status_label = QLabel("Estado: pendiente")
        self.status_label.setObjectName("MutedLabel")
        self.action_label = QLabel("Siguiente accion: selecciona un video")
        self.action_label.setWordWrap(True)
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.blocked_label = QLabel("")
        self.blocked_label.setWordWrap(True)
        self.blocked_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.group_combo = QComboBox()
        self.group_combo.addItem("Importacion", "importacion")
        self.group_combo.addItem("Preparacion", "preparacion")
        self.group_combo.addItem("Comprension", "comprension")
        self.group_combo.addItem("Seleccion", "seleccion")
        self.retry_combo = QComboBox()
        self.retry_combo.addItems(["inspection", "audio", "transcription", "acoustic", "visual", "multimodal", "ranking"])

        self.refresh_button = QPushButton("Actualizar")
        self.next_button = QPushButton("Ejecutar siguiente etapa")
        self.group_button = QPushButton("Ejecutar grupo")
        self.until_ranking_button = QPushButton("Hasta ranking")
        self.retry_button = QPushButton("Reintentar etapa")
        self.open_video_button = QPushButton("Abrir en videos")

        self.stage_table = QTableWidget(0, 7)
        self.stage_table.setHorizontalHeaderLabels(["Etapa", "Estado", "Disponible", "Stale", "Fin", "Accion", "Resumen"])
        self.stage_table.setColumnHidden(5, True)

        buttons = QHBoxLayout()
        for widget in (
            self.refresh_button,
            self.next_button,
            self.group_combo,
            self.group_button,
            self.until_ranking_button,
            self.retry_combo,
            self.retry_button,
            self.open_video_button,
        ):
            buttons.addWidget(widget)
        buttons.addStretch(1)

        summary_panel = QFrame(self)
        summary_panel.setObjectName("MutedPanel")
        summary_layout = QVBoxLayout(summary_panel)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(self.video_label)
        summary_layout.addWidget(self.status_label)
        summary_layout.addWidget(self.action_label)
        summary_layout.addWidget(self.blocked_label)
        summary_layout.addWidget(self.progress_label)
        summary_layout.addWidget(self.progress_bar)

        layout = QVBoxLayout(self)
        title = QLabel("Workflow de video")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Una vista guiada con la siguiente accion recomendada y el progreso actual.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(summary_panel)
        layout.addLayout(buttons)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.stage_table)

        self.refresh_button.clicked.connect(self.refresh)
        self.next_button.clicked.connect(self._run_next)
        self.group_button.clicked.connect(self._run_group)
        self.until_ranking_button.clicked.connect(self._run_until_ranking)
        self.retry_button.clicked.connect(self._retry_stage)
        self.open_video_button.clicked.connect(self._open_video)

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else self.workspace.selected_video_id

    def _selected_video_title(self) -> str:
        video = self.workspace.selected_video()
        return video.title if video else "Sin video"

    def refresh(self) -> None:
        video_id = self._selected_video_id()
        if not video_id:
            self.empty_state.show()
            self.stage_table.hide()
            self.video_label.setText("Video: no seleccionado")
            self.status_label.setText("Estado: pendiente")
            self.action_label.setText("Siguiente accion: selecciona un video")
            self.blocked_label.setText("")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            self._update_buttons()
            return
        self.empty_state.hide()
        self.stage_table.show()
        status = self.workspace.video_pipeline_status(video_id)
        self.video_label.setText(f"Video: {self._selected_video_title()}")
        self.status_label.setText(f"Estado: {status.overall_status} | Etapa actual: {status.current_stage}")
        self.action_label.setText(f"Siguiente accion recomendada: {status.recommended_action}")
        self.blocked_label.setText(f"Bloqueo: {status.blocked_reason}" if status.blocked_reason else "")
        self.progress_bar.setValue(int(status.progress_percent))
        self.progress_label.setText(f"{status.progress_percent:.1f}%")
        self.stage_table.setRowCount(0)
        for row_index, stage in enumerate(status.stages):
            self.stage_table.insertRow(row_index)
            values = [
                stage.display_name,
                stage.status,
                "si" if stage.available else "no",
                "si" if stage.stale else "no",
                stage.completed_at or "",
                stage.action_id or "",
                stage.summary,
            ]
            for column, value in enumerate(values):
                self.stage_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.stage_table.resizeColumnsToContents()
        self._update_buttons(status)

    def _update_buttons(self, status=None) -> None:
        enabled = self._thread is None and self._selected_video_id() is not None
        self.next_button.setEnabled(enabled)
        self.group_button.setEnabled(enabled)
        self.until_ranking_button.setEnabled(enabled)
        self.retry_button.setEnabled(enabled)
        self.open_video_button.setEnabled(enabled)
        self.refresh_button.setEnabled(True)
        if status is not None:
            self.retry_combo.setEnabled(enabled)
            self.group_combo.setEnabled(enabled)

    def _start_thread(self, mode: str, stage_name: str | None = None) -> None:
        video_id = self._selected_video_id()
        if not video_id:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self._thread = WorkflowThread(self.workspace, video_id, mode=mode, stage_name=stage_name)
        self._thread.result_ready.connect(self._thread_finished)
        self._thread.error_ready.connect(self._thread_failed)
        self._thread.progress_ready.connect(self._thread_progress)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()
        self._update_buttons()

    def _thread_progress(self, phase: str, ratio: float) -> None:
        self.action_label.setText(f"Ejecutando: {phase}")
        self.progress_bar.setValue(int(max(0.0, min(1.0, ratio)) * 100))
        self.progress_label.setText(f"{int(max(0.0, min(1.0, ratio)) * 100)}%")

    def _thread_failed(self, message: str) -> None:
        self._thread = None
        self._update_buttons()
        QMessageBox.warning(self, "Workflow", message)
        self.refresh()

    def _thread_finished(self, result) -> None:
        self._thread = None
        self._update_buttons()
        self.refresh()
        if isinstance(result, list):
            message = " -> ".join(item.stage_name for item in result if getattr(item, "stage_name", None))
        else:
            message = getattr(result, "message", "Workflow completado")
        QMessageBox.information(self, "Workflow", message)

    def _run_next(self) -> None:
        self._start_thread("next")

    def _run_group(self) -> None:
        self._start_thread("group", stage_name=str(self.group_combo.currentData() or "seleccion"))

    def _run_until_ranking(self) -> None:
        self._start_thread("until_ranking")

    def _retry_stage(self) -> None:
        self._start_thread("retry", stage_name=self.retry_combo.currentText())

    def _open_video(self) -> None:
        self.workspace.select_video(self._selected_video_id())

