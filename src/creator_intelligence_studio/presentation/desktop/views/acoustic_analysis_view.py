"""Vista de analisis acustico."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPainter, QPen
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

from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticAnalysisStatus
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class AcousticAnalysisThread(QThread):
    """Ejecuta el analisis acustico sin bloquear la UI."""

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
            report = self.workspace.analyze_acoustics(
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


class AcousticAnalysisView(QWidget):
    """Vista tecnica inicial para analisis acustico."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: AcousticAnalysisThread | None = None

        self.status_label = QLabel("Sin analisis")
        self.status_label.setObjectName("MutedLabel")
        self.stale_label = QLabel("Stale: no")
        self.stale_label.setObjectName("MutedLabel")
        self.metrics_label = QLabel("Métricas no disponibles")
        self.metrics_label.setWordWrap(True)
        self.phase_label = QLabel("Preparando")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.analyze_button = QPushButton("Analizar audio")
        self.reanalyze_button = QPushButton("Reanalizar")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_csv_button = QPushButton("Exportar CSV")
        self.delete_button = QPushButton("Eliminar analisis")
        self.refresh_button = QPushButton("Actualizar")

        self.timeline_view = QGraphicsView()
        self.timeline_scene = QGraphicsScene(self)
        self.timeline_view.setScene(self.timeline_scene)
        self.timeline_view.setMinimumHeight(160)
        self.timeline_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.window_table = QTableWidget(0, 7)
        self.window_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Actividad", "Voz", "Energia", "Pausa"])
        self.event_table = QTableWidget(0, 5)
        self.event_table.setHorizontalHeaderLabels(["#", "Tipo", "Inicio", "Fin", "Confianza"])
        self.summary_text = QPlainTextEdit()
        self.summary_text.setReadOnly(True)

        actions = QHBoxLayout()
        for widget in (
            self.analyze_button,
            self.reanalyze_button,
            self.export_json_button,
            self.export_csv_button,
            self.delete_button,
            self.refresh_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Analisis acustico")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Linea temporal tecnica con voz, silencio, energia, pausas y eventos candidatos.")
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
        layout.addWidget(QLabel("Linea temporal"))
        layout.addWidget(self.timeline_view)
        layout.addWidget(QLabel("Ventanas"))
        layout.addWidget(self.window_table)
        layout.addWidget(QLabel("Eventos candidatos"))
        layout.addWidget(self.event_table)
        layout.addWidget(QLabel("Resumen tecnico"))
        layout.addWidget(self.summary_text)

        self.analyze_button.clicked.connect(self._analyze)
        self.reanalyze_button.clicked.connect(lambda: self._analyze(force=True))
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_csv_button.clicked.connect(lambda: self._export("csv"))
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
            self.metrics_label.setText("Métricas no disponibles")
            self.summary_text.clear()
            self.window_table.setRowCount(0)
            self.event_table.setRowCount(0)
            self.timeline_scene.clear()
            return
        report = self.workspace.get_acoustic_analysis(video_id)
        self._render_report(report)

    def _render_report(self, report) -> None:
        self.status_label.setText(f"Estado: {report.status.value}")
        self.stale_label.setText(f"Stale: {'si' if report.is_stale else 'no'}")
        if report.analysis is None:
            self.metrics_label.setText("Métricas no disponibles")
            self.summary_text.setPlainText("No existe un analisis acustico para este video.")
            self.window_table.setRowCount(0)
            self.event_table.setRowCount(0)
            self.timeline_scene.clear()
            self.phase_label.setText("Listo")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            return
        analysis = report.analysis
        self.metrics_label.setText(
            " | ".join(
                [
                    f"Voz: {analysis.speech_duration_seconds:.2f} s",
                    f"Silencio: {analysis.silence_duration_seconds:.2f} s",
                    f"Speech ratio: {analysis.speech_ratio:.3f}",
                    f"WPM: {analysis.words_per_minute:.2f}" if analysis.words_per_minute is not None else "WPM: N/D",
                    f"Pausas: {analysis.pause_count}",
                    f"Energia media: {analysis.average_energy:.4f}",
                    f"Rango dinamico: {analysis.dynamic_range:.4f}",
                    f"Cambios: {analysis.abrupt_change_count}",
                    f"Eventos: {analysis.event_candidate_count}",
                ]
            )
        )
        self.summary_text.setPlainText(
            "\n".join(
                [
                    f"Analizador: {analysis.analyzer_version}",
                    f"Modelo de referencia: {analysis.transcription_id or 'sin transcripcion'}",
                    f"Duracion total: {analysis.duration_seconds:.3f} s",
                    f"Pausa promedio: {analysis.average_pause_seconds:.3f} s" if analysis.average_pause_seconds is not None else "Pausa promedio: N/D",
                    f"Pausa mas larga: {analysis.longest_pause_seconds:.3f} s" if analysis.longest_pause_seconds is not None else "Pausa mas larga: N/D",
                    f"Pausas cortas: {analysis.short_pause_count}",
                    f"Pausas medias: {analysis.medium_pause_count}",
                    f"Pausas largas: {analysis.long_pause_count}",
                ]
            )
        )
        self._populate_windows(report.windows)
        self._populate_events(report.events)
        self._render_timeline(report)

    def _populate_windows(self, windows) -> None:
        self.window_table.setRowCount(0)
        for row_index, window in enumerate(windows):
            self.window_table.insertRow(row_index)
            values = [
                str(window.window_index),
                f"{window.start_seconds:.3f}",
                f"{window.end_seconds:.3f}",
                window.activity_label.value,
                "si" if window.is_speech else "no",
                f"{window.normalized_energy:.4f}",
                f"{window.pause_duration_seconds:.3f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.window_table.setItem(row_index, column, item)

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
            "silence": QColor("#4b5563"),
            "low_activity": QColor("#64748b"),
            "speech_low": QColor("#22c55e"),
            "speech_normal": QColor("#38bdf8"),
            "speech_high": QColor("#0ea5e9"),
            "non_speech_activity": QColor("#f59e0b"),
            "unknown": QColor("#94a3b8"),
        }
        for index, window in enumerate(report.windows):
            x = 20 + index * width_per_window
            bar_height = max(6, int(window.normalized_energy * max_height))
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
                f"{window.start_seconds:.2f}-{window.end_seconds:.2f}s | {window.activity_label.value} | energia={window.normalized_energy:.4f}"
            )
        for event in report.events:
            center = 20 + int((event.start_seconds / max(1e-6, report.analysis.duration_seconds)) * max(1, len(report.windows)) * width_per_window)
            marker = self.timeline_scene.addLine(center, 15, center, 100, QPen(QColor("#ef4444"), 2))
            marker.setToolTip(f"{event.event_type.value} | conf={event.confidence:.3f}")
        self.timeline_scene.addText("Silencio")
        self.timeline_scene.addText("Energia")

    def _selected_video_id_required(self) -> str | None:
        return self._selected_video_id()

    def _analyze(self, force: bool = False) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self.phase_label.setText("Preparando")
        self.progress_label.setText("0%")
        self.progress_bar.setValue(0)
        self._thread = AcousticAnalysisThread(self.workspace, video_id, force=force)
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
            result = self.workspace.export_acoustic_analysis(video_id, format_name)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion", f"Exportado en: {result.path}")

    def _delete(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.delete_acoustic_analysis(video_id):
            self.refresh()
            QMessageBox.information(self, "Analisis acustico", "Analisis eliminado.")
