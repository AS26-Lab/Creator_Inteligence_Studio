"""Vista de analisis visual local."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class VisualAnalysisThread(QThread):
    """Ejecuta el analisis visual sin bloquear la GUI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, video_id: str, force: bool = False) -> None:
        super().__init__()
        self.workspace = workspace
        self.video_id = video_id
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            report = self.workspace.analyze_visuals(
                self.video_id,
                force=self.force,
                progress_callback=lambda phase, ratio: self.progress_ready.emit(phase, float(ratio or 0.0)),
            )
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(report)


class VisualAnalysisView(QWidget):
    """Vista tecnica inicial para analisis visual."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: VisualAnalysisThread | None = None

        self.status_label = QLabel("Sin analisis")
        self.status_label.setObjectName("MutedLabel")
        self.stale_label = QLabel("Stale: no")
        self.stale_label.setObjectName("MutedLabel")
        self.metrics_label = QLabel("Metricas no disponibles")
        self.metrics_label.setWordWrap(True)
        self.phase_label = QLabel("Preparando")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.analyze_button = QPushButton("Analizar video")
        self.reanalyze_button = QPushButton("Reanalizar")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_timeline_button = QPushButton("Exportar timeline CSV")
        self.export_scenes_button = QPushButton("Exportar escenas CSV")
        self.delete_button = QPushButton("Eliminar analisis")
        self.refresh_button = QPushButton("Actualizar")

        self.timeline_view = QGraphicsView()
        self.timeline_scene = QGraphicsScene(self)
        self.timeline_view.setScene(self.timeline_scene)
        self.timeline_view.setMinimumHeight(160)
        self.timeline_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.scene_table = QTableWidget(0, 5)
        self.scene_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Duracion", "Keyframe"])
        self.event_table = QTableWidget(0, 5)
        self.event_table.setHorizontalHeaderLabels(["#", "Tipo", "Inicio", "Fin", "Confianza"])
        self.summary_text = QPlainTextEdit()
        self.summary_text.setReadOnly(True)

        self.keyframe_container = QWidget()
        self.keyframe_grid = QGridLayout(self.keyframe_container)
        self.keyframe_grid.setContentsMargins(0, 0, 0, 0)
        self.keyframe_grid.setSpacing(8)
        keyframe_scroll = QScrollArea()
        keyframe_scroll.setWidgetResizable(True)
        keyframe_scroll.setWidget(self.keyframe_container)
        keyframe_scroll.setMinimumHeight(180)

        actions = QHBoxLayout()
        for widget in (
            self.analyze_button,
            self.reanalyze_button,
            self.export_json_button,
            self.export_timeline_button,
            self.export_scenes_button,
            self.delete_button,
            self.refresh_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Analisis visual")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Linea temporal tecnica con cortes, escenas, keyframes, brillo, contraste y movimiento.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stale_label)
        layout.addWidget(self.metrics_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Linea temporal visual"))
        layout.addWidget(self.timeline_view)
        layout.addWidget(QLabel("Escenas"))
        layout.addWidget(self.scene_table)
        layout.addWidget(QLabel("Keyframes"))
        layout.addWidget(keyframe_scroll)
        layout.addWidget(QLabel("Eventos tecnicos"))
        layout.addWidget(self.event_table)
        layout.addWidget(QLabel("Resumen tecnico"))
        layout.addWidget(self.summary_text)

        self.analyze_button.clicked.connect(self._analyze)
        self.reanalyze_button.clicked.connect(lambda: self._analyze(force=True))
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_timeline_button.clicked.connect(lambda: self._export("timeline-csv"))
        self.export_scenes_button.clicked.connect(lambda: self._export("scenes-csv"))
        self.delete_button.clicked.connect(self._delete)
        self.refresh_button.clicked.connect(self.refresh)

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else None

    def refresh(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            self.status_label.setText("Selecciona un video para analizar.")
            self.stale_label.setText("Stale: no")
            self.metrics_label.setText("Metricas no disponibles")
            self.summary_text.clear()
            self.scene_table.setRowCount(0)
            self.event_table.setRowCount(0)
            self.timeline_scene.clear()
            self._clear_keyframes()
            return
        report = self.workspace.get_visual_analysis(video_id)
        self._render_report(report)

    def _render_report(self, report) -> None:
        self.status_label.setText(f"Estado: {report.status.value}")
        self.stale_label.setText(f"Stale: {'si' if report.is_stale else 'no'}")
        if report.analysis is None:
            self.metrics_label.setText("Metricas no disponibles")
            self.summary_text.setPlainText("No existe un analisis visual para este video.")
            self.scene_table.setRowCount(0)
            self.event_table.setRowCount(0)
            self.timeline_scene.clear()
            self._clear_keyframes()
            self.phase_label.setText("Listo")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            return
        analysis = report.analysis
        self.metrics_label.setText(
            " | ".join(
                [
                    f"Cortes: {analysis.detected_cut_count}",
                    f"Escenas: {analysis.detected_scene_count}",
                    f"Keyframes: {analysis.keyframe_count}",
                    f"Movimiento medio: {analysis.average_motion:.4f}",
                    f"Movimiento pico: {analysis.peak_motion:.4f}",
                    f"Brillo medio: {analysis.average_brightness:.4f}",
                    f"Contraste medio: {analysis.average_contrast:.4f}",
                    f"Segmentos estaticos: {analysis.static_segment_count}",
                    f"Frames negros: {analysis.black_frame_event_count}",
                    f"Congelamientos: {analysis.freeze_event_count}",
                ]
            )
        )
        self.summary_text.setPlainText(
            "\n".join(
                [
                    f"Analizador: {analysis.analyzer_version}",
                    f"Duracion total: {analysis.duration_seconds:.3f} s",
                    f"Frames muestreados: {analysis.sampled_frame_count}",
                    f"Duracion de analisis: {(analysis.completed_at - analysis.started_at).total_seconds():.3f} s",
                    f"Variacion de brillo: {analysis.brightness_variation:.4f}",
                    f"Archivo fuente: {analysis.source_file_size_bytes or 'N/D'} bytes",
                ]
            )
        )
        self._populate_scenes(report.scenes)
        self._populate_events(report.events)
        self._populate_keyframes(report.scenes)
        self._render_timeline(report)

    def _populate_scenes(self, scenes) -> None:
        self.scene_table.setRowCount(0)
        for row_index, scene in enumerate(scenes):
            self.scene_table.insertRow(row_index)
            values = [
                str(scene.scene_index),
                f"{scene.start_seconds:.3f}",
                f"{scene.end_seconds:.3f}",
                f"{scene.duration_seconds:.3f}",
                scene.representative_keyframe_path or "N/D",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.scene_table.setItem(row_index, column, item)

    def _populate_events(self, events) -> None:
        self.event_table.setRowCount(0)
        for row_index, event in enumerate(events):
            self.event_table.insertRow(row_index)
            values = [
                str(event.event_index),
                event.event_type.value,
                f"{event.start_seconds:.3f}",
                f"{event.end_seconds:.3f}",
                f"{event.confidence:.3f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.event_table.setItem(row_index, column, item)

    def _clear_keyframes(self) -> None:
        while self.keyframe_grid.count():
            item = self.keyframe_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_keyframes(self, scenes) -> None:
        self._clear_keyframes()
        for index, scene in enumerate(scenes):
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(4)
            label = QLabel(f"Escena {scene.scene_index}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview = QLabel()
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setMinimumSize(180, 100)
            preview.setObjectName("MutedLabel")
            if scene.representative_keyframe_path:
                keyframe_path = Path(scene.representative_keyframe_path)
                if not keyframe_path.is_absolute():
                    keyframe_path = self.workspace.paths.project_root / keyframe_path
                if keyframe_path.exists():
                    pixmap = QPixmap(str(keyframe_path))
                    if not pixmap.isNull():
                        preview.setPixmap(pixmap.scaled(180, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    else:
                        preview.setText("Preview no disponible")
                else:
                    preview.setText("Archivo faltante")
            else:
                preview.setText("Sin keyframe")
            box_layout.addWidget(preview)
            box_layout.addWidget(label)
            row = index // 3
            column = index % 3
            self.keyframe_grid.addWidget(box, row, column)

    def _render_timeline(self, report) -> None:
        self.timeline_scene.clear()
        if not report.windows:
            self.timeline_scene.addText("Sin datos de linea temporal.")
            return
        width_per_window = 10
        max_height = 100
        height = 120
        self.timeline_scene.setSceneRect(0, 0, max(700, len(report.windows) * width_per_window + 40), height)
        labels = {
            "static": QColor("#475569"),
            "low_motion": QColor("#64748b"),
            "moderate_motion": QColor("#38bdf8"),
            "high_motion": QColor("#0ea5e9"),
            "dark": QColor("#1f2937"),
            "normal_exposure": QColor("#22c55e"),
            "bright": QColor("#f59e0b"),
            "possible_black_frame": QColor("#000000"),
            "possible_freeze": QColor("#ef4444"),
            "transition_candidate": QColor("#a855f7"),
            "unknown": QColor("#94a3b8"),
        }
        for index, window in enumerate(report.windows):
            x = 20 + index * width_per_window
            bar_height = max(6, int(window.motion_score * max_height))
            y = 90 - bar_height
            rect = self.timeline_scene.addRect(
                x,
                y,
                width_per_window - 2,
                bar_height,
                pen=QPen(Qt.PenStyle.NoPen),
                brush=QBrush(labels.get(window.activity_label.value, QColor("#94a3b8"))),
            )
            rect.setToolTip(
                f"{window.start_seconds:.2f}-{window.end_seconds:.2f}s | {window.activity_label.value} | motion={window.motion_score:.4f}"
            )
        for event in report.events:
            center = 20 + int((event.start_seconds / max(1e-6, report.analysis.duration_seconds)) * max(1, len(report.windows)) * width_per_window)
            marker = self.timeline_scene.addLine(center, 15, center, 100, QPen(QColor("#ef4444"), 2))
            marker.setToolTip(f"{event.event_type.value} | conf={event.confidence:.3f}")
        self.timeline_scene.addText("Movimiento")

    def _analyze(self, force: bool = False) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self.phase_label.setText("Preparando video")
        self.progress_label.setText("0%")
        self.progress_bar.setValue(0)
        self._thread = VisualAnalysisThread(self.workspace, video_id, force=force)
        self._thread.result_ready.connect(self._analysis_finished)
        self._thread.error_ready.connect(self._analysis_failed)
        self._thread.progress_ready.connect(self._analysis_progress)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _analysis_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(phase)
        value = max(0, min(100, int(ratio * 100)))
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}% aproximado")

    def _analysis_finished(self, report) -> None:
        self._thread = None
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._render_report(report)

    def _analysis_failed(self, message: str) -> None:
        self._thread = None
        QMessageBox.warning(self, "No se pudo analizar", message)
        self.refresh()

    def _export(self, format_name: str) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        try:
            result = self.workspace.export_visual_analysis(video_id, format_name)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion", f"Exportado en: {result.path}")

    def _delete(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.delete_visual_analysis(video_id):
            self.refresh()
            QMessageBox.information(self, "Analisis visual", "Analisis eliminado.")
