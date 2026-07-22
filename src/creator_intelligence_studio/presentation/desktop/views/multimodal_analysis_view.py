"""Vista de linea temporal multimodal."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class MultimodalAnalysisThread(QThread):
    """Ejecuta analisis multimodal sin bloquear la GUI."""

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
            report = self.workspace.analyze_multimodal(
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


class MultimodalAnalysisView(QWidget):
    """Vista tecnica de timeline multimodal."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: MultimodalAnalysisThread | None = None

        self.status_label = QLabel("Sin analisis")
        self.status_label.setObjectName("MutedLabel")
        self.sources_label = QLabel("Fuentes no evaluadas")
        self.sources_label.setWordWrap(True)
        self.stale_label = QLabel("Stale: no")
        self.stale_label.setObjectName("MutedLabel")
        self.summary_label = QLabel("Metricas no disponibles")
        self.summary_label.setWordWrap(True)
        self.phase_label = QLabel("Preparando")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.analyze_button = QPushButton("Analizar multimodal")
        self.reanalyze_button = QPushButton("Reanalizar")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_timeline_button = QPushButton("Exportar timeline CSV")
        self.export_candidates_button = QPushButton("Exportar candidatos CSV")
        self.export_txt_button = QPushButton("Exportar resumen TXT")
        self.delete_button = QPushButton("Eliminar analisis")
        self.refresh_button = QPushButton("Actualizar")

        self.timeline_view = QGraphicsView()
        self.timeline_scene = QGraphicsScene(self)
        self.timeline_view.setScene(self.timeline_scene)
        self.timeline_view.setMinimumHeight(180)
        self.timeline_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.candidate_table = QTableWidget(0, 6)
        self.candidate_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Tipo", "Score", "Confidence"])
        self.window_table = QTableWidget(0, 6)
        self.window_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Actividad", "Transicion", "Novedad"])
        self.summary_text = QPlainTextEdit()
        self.summary_text.setReadOnly(True)

        actions = QHBoxLayout()
        for widget in (
            self.analyze_button,
            self.reanalyze_button,
            self.export_json_button,
            self.export_timeline_button,
            self.export_candidates_button,
            self.export_txt_button,
            self.delete_button,
            self.refresh_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Analisis multimodal")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Linea temporal unificada de transcripcion, voz, silencio, energia, escenas, cortes y movimiento.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.sources_label)
        layout.addWidget(self.stale_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Timeline multimodal"))
        layout.addWidget(self.timeline_view)
        layout.addWidget(QLabel("Ventanas"))
        layout.addWidget(self.window_table)
        layout.addWidget(QLabel("Candidatos"))
        layout.addWidget(self.candidate_table)
        layout.addWidget(QLabel("Resumen tecnico"))
        layout.addWidget(self.summary_text)

        self.analyze_button.clicked.connect(self._analyze)
        self.reanalyze_button.clicked.connect(lambda: self._analyze(force=True))
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_timeline_button.clicked.connect(lambda: self._export("timeline-csv"))
        self.export_candidates_button.clicked.connect(lambda: self._export("candidates-csv"))
        self.export_txt_button.clicked.connect(lambda: self._export("txt"))
        self.delete_button.clicked.connect(self._delete)
        self.refresh_button.clicked.connect(self.refresh)

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else None

    def refresh(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            self.status_label.setText("Selecciona un video para analizar.")
            self.sources_label.setText("Fuentes no evaluadas")
            self.stale_label.setText("Stale: no")
            self.summary_label.setText("Metricas no disponibles")
            self.summary_text.clear()
            self.window_table.setRowCount(0)
            self.candidate_table.setRowCount(0)
            self.timeline_scene.clear()
            return
        report = self.workspace.get_multimodal_analysis(video_id)
        self._render_report(report)

    def _render_report(self, report) -> None:
        self.status_label.setText(f"Estado: {report.status.value}")
        self.sources_label.setText(
            "Fuentes disponibles: "
            + (", ".join(report.available_sources) if report.available_sources else "ninguna")
            + " | Fuentes faltantes: "
            + (", ".join(report.missing_sources) if report.missing_sources else "ninguna")
        )
        self.stale_label.setText(f"Stale: {'si' if report.is_stale else 'no'}")
        if report.analysis is None:
            self.summary_label.setText("Metricas no disponibles")
            self.summary_text.setPlainText("No existe un analisis multimodal para este video.")
            self.window_table.setRowCount(0)
            self.candidate_table.setRowCount(0)
            self.timeline_scene.clear()
            self.phase_label.setText("Listo")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            return
        analysis = report.analysis
        self.summary_label.setText(
            " | ".join(
                [
                    f"Ventanas: {analysis.window_count}",
                    f"Candidatos: {analysis.candidate_count}",
                    f"Alta actividad: {analysis.high_activity_candidate_count}",
                    f"Transicion: {analysis.transition_candidate_count}",
                    f"Baja actividad: {analysis.silence_candidate_count}",
                    f"Duracion: {analysis.duration_seconds:.3f} s",
                ]
            )
        )
        self.summary_text.setPlainText(
            "\n".join(
                [
                    f"Analizador: {analysis.analyzer_version}",
                    f"Duracion total: {analysis.duration_seconds:.3f} s",
                    f"Ventanas: {analysis.window_count}",
                    f"Candidatos: {analysis.candidate_count}",
                    f"Fuentes: {', '.join(report.available_sources) or 'ninguna'}",
                    f"Fuentes faltantes: {', '.join(report.missing_sources) or 'ninguna'}",
                    f"Configuracion: {analysis.configuration_fingerprint}",
                ]
            )
        )
        self._populate_windows(report.windows)
        self._populate_candidates(report.candidates)
        self._render_timeline(report)

    def _populate_windows(self, windows) -> None:
        self.window_table.setRowCount(0)
        for row_index, window in enumerate(windows):
            self.window_table.insertRow(row_index)
            values = [
                str(window.window_index),
                f"{window.start_seconds:.3f}",
                f"{window.end_seconds:.3f}",
                f"{window.combined_activity_score:.3f}",
                f"{window.transition_score:.3f}",
                f"{window.novelty_score:.3f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.window_table.setItem(row_index, column, item)

    def _populate_candidates(self, candidates) -> None:
        self.candidate_table.setRowCount(0)
        for row_index, candidate in enumerate(candidates):
            self.candidate_table.insertRow(row_index)
            values = [
                str(candidate.candidate_index),
                f"{candidate.start_seconds:.3f}",
                f"{candidate.end_seconds:.3f}",
                candidate.candidate_type.value,
                f"{candidate.score:.3f}",
                f"{candidate.confidence:.3f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.candidate_table.setItem(row_index, column, item)

    def _render_timeline(self, report) -> None:
        self.timeline_scene.clear()
        if not report.windows:
            self.timeline_scene.addText("Sin datos de linea temporal.")
            return
        width_per_window = 12
        height = 150
        self.timeline_scene.setSceneRect(0, 0, max(700, len(report.windows) * width_per_window + 40), height)
        activity_colors = {
            "high": QColor("#22c55e"),
            "medium": QColor("#38bdf8"),
            "low": QColor("#64748b"),
            "silence": QColor("#0f172a"),
        }
        for index, window in enumerate(report.windows):
            x = 20 + index * width_per_window
            activity_height = max(8, int(window.combined_activity_score * 90))
            transition_height = max(6, int(window.transition_score * 70))
            rect = self.timeline_scene.addRect(
                x,
                95 - activity_height,
                width_per_window - 2,
                activity_height,
                pen=QPen(Qt.PenStyle.NoPen),
                brush=QBrush(activity_colors["high" if window.combined_activity_score >= 0.72 else "medium" if window.combined_activity_score >= 0.45 else "low"]),
            )
            rect.setToolTip(
                f"{window.start_seconds:.2f}-{window.end_seconds:.2f}s | act={window.combined_activity_score:.3f} | trans={window.transition_score:.3f}"
            )
            self.timeline_scene.addLine(
                x + (width_per_window / 2),
                120,
                x + (width_per_window / 2),
                120 - transition_height,
                QPen(QColor("#f97316"), 1.5),
            )
        for candidate in report.candidates:
            center = 20 + int((candidate.start_seconds / max(1e-6, report.analysis.duration_seconds)) * max(1, len(report.windows)) * width_per_window)
            marker = self.timeline_scene.addLine(center, 15, center, 135, QPen(QColor("#ef4444"), 2))
            marker.setToolTip(f"{candidate.candidate_type.value} | score={candidate.score:.3f} | conf={candidate.confidence:.3f}")
        self.timeline_scene.addText("Actividad combinada / transiciones")

    def _analyze(self, force: bool = False) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self.phase_label.setText("Cargando fuentes")
        self.progress_label.setText("0%")
        self.progress_bar.setValue(0)
        self._thread = MultimodalAnalysisThread(self.workspace, video_id, force=force)
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
            result = self.workspace.export_multimodal_analysis(video_id, format_name)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion", f"Exportado en: {result.path}")

    def _delete(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.delete_multimodal_analysis(video_id):
            self.refresh()
            QMessageBox.information(self, "Analisis multimodal", "Analisis eliminado.")

