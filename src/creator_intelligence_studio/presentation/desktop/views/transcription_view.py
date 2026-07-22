"""Vista de transcripcion local."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionExportFormat,
    TranscriptionModelStatus,
    TranscriptionOptions,
)
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class TranscriptionTaskThread(QThread):
    """Ejecuta la transcripcion sin bloquear la GUI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, video_id: str, options: TranscriptionOptions) -> None:
        super().__init__()
        self.workspace = workspace
        self.video_id = video_id
        self.options = options

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            report = self.workspace.transcribe_video(
                self.video_id,
                self.options,
                progress_callback=lambda progress: self.progress_ready.emit(
                    progress.phase,
                    float(progress.progress_ratio or 0.0),
                ),
            )
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(report)


class ModelTaskThread(QThread):
    """Ejecuta acciones de modelo sin bloquear la GUI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, model_name: str, *, action: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.model_name = model_name
        self.action = action

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            if self.action == "download":
                result = self.workspace.download_transcription_model(
                    self.model_name,
                    progress_callback=lambda progress: self.progress_ready.emit(
                        progress.phase,
                        float(progress.progress_ratio or 0.0),
                    ),
                )
            elif self.action == "verify":
                result = self.workspace.verify_transcription_model(self.model_name)
            else:
                result = self.workspace.transcription_model_status(self.model_name)
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(result)


class TranscriptionView(QWidget):
    """Vista inicial para transcripcion local."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: TranscriptionTaskThread | None = None
        self._model_thread: ModelTaskThread | None = None

        self.status_label = QLabel("Sin transcripcion")
        self.status_label.setObjectName("MutedLabel")
        self.model_status_label = QLabel("Modelo no instalado")
        self.model_status_label.setObjectName("MutedLabel")
        self.phase_label = QLabel("Preparando")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["balanced", "fast", "quality"])
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        self.language_combo = QComboBox()
        self.language_combo.addItems(["auto", "es", "en"])
        self.model_combo = QComboBox()

        self.backend_button = QPushButton("Verificar backend")
        self.download_model_button = QPushButton("Descargar modelo")
        self.transcribe_button = QPushButton("Transcribir")
        self.cancel_button = QPushButton("Cancelar")
        self.export_txt_button = QPushButton("Exportar TXT")
        self.export_srt_button = QPushButton("Exportar SRT")
        self.export_json_button = QPushButton("Exportar JSON")
        self.delete_button = QPushButton("Eliminar")
        self.refresh_button = QPushButton("Actualizar")

        self.full_text = QPlainTextEdit()
        self.full_text.setReadOnly(True)
        self.segment_table = QTableWidget(0, 4)
        self.segment_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Texto"])
        self.segment_table.setWordWrap(True)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Perfil"))
        controls.addWidget(self.profile_combo)
        controls.addWidget(QLabel("Modelo"))
        controls.addWidget(self.model_combo)
        controls.addWidget(QLabel("Dispositivo"))
        controls.addWidget(self.device_combo)
        controls.addWidget(QLabel("Idioma"))
        controls.addWidget(self.language_combo)

        actions = QHBoxLayout()
        for widget in (
            self.backend_button,
            self.download_model_button,
            self.transcribe_button,
            self.cancel_button,
            self.export_txt_button,
            self.export_srt_button,
            self.export_json_button,
            self.delete_button,
            self.refresh_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Transcripcion")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Backend local con CUDA principal y CPU como respaldo.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.model_status_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Texto completo"))
        layout.addWidget(self.full_text)
        layout.addWidget(QLabel("Segmentos"))
        layout.addWidget(self.segment_table)

        self.backend_button.clicked.connect(self._verify_backend)
        self.download_model_button.clicked.connect(self._download_model)
        self.transcribe_button.clicked.connect(self._transcribe)
        self.cancel_button.clicked.connect(self._cancel)
        self.export_txt_button.clicked.connect(lambda: self._export(TranscriptionExportFormat.TXT))
        self.export_srt_button.clicked.connect(lambda: self._export(TranscriptionExportFormat.SRT))
        self.export_json_button.clicked.connect(lambda: self._export(TranscriptionExportFormat.JSON))
        self.delete_button.clicked.connect(self._delete)
        self.refresh_button.clicked.connect(self.refresh)
        self.model_combo.currentTextChanged.connect(lambda _: self._refresh_model_state())
        self._refresh_models()

    def _refresh_models(self) -> None:
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for model in self.workspace.transcription_models():
            self.model_combo.addItem(model.model_name, model.model_name)
        if current:
            index = self.model_combo.findText(current)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        if self.model_combo.currentIndex() < 0:
            self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)
        self._refresh_model_state()

    def _current_model_name(self) -> str:
        return self.model_combo.currentText() or "small"

    def _current_model_info(self):
        return self.workspace.transcription_model_status(self._current_model_name())

    def _refresh_model_state(self) -> None:
        model = self._current_model_info()
        self.model_status_label.setText(
            f"Modelo: {model.model_name} | Estado: {model.status.value} | Ruta: {model.path}"
        )
        ready = model.status == TranscriptionModelStatus.INSTALLED
        downloading = model.status == TranscriptionModelStatus.DOWNLOADING
        self.transcribe_button.setEnabled(ready and (self._thread is None or not self._thread.isRunning()))
        self.download_model_button.setEnabled(not ready and not downloading and (self._model_thread is None or not self._model_thread.isRunning()))
        if downloading:
            self.phase_label.setText("Descargando modelo")
            self.progress_label.setText("0% aproximado")
            self.progress_bar.setValue(0)
        elif not ready:
            self.phase_label.setText(model.notes or "Modelo no instalado")

    def _set_model_running(self, running: bool) -> None:
        self.download_model_button.setEnabled(not running)
        self.transcribe_button.setEnabled(not running and self._current_model_info().status == TranscriptionModelStatus.INSTALLED)

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else None

    def _set_running(self, running: bool) -> None:
        self.transcribe_button.setEnabled(not running and self._current_model_info().status == TranscriptionModelStatus.INSTALLED)
        self.cancel_button.setEnabled(running)

    def _set_report(self, report) -> None:
        self.status_label.setText(f"Estado: {report.status.value}")
        self.phase_label.setText(report.progress_message or ("Stale" if report.is_stale else "Listo"))
        self.full_text.setPlainText(report.transcription.full_text if report.transcription else "")
        self.segment_table.setRowCount(0)
        for row, segment in enumerate(report.segments):
            self.segment_table.insertRow(row)
            values = [
                str(segment.segment_index),
                f"{segment.start_seconds:.3f}",
                f"{segment.end_seconds:.3f}",
                segment.text,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                self.segment_table.setItem(row, column, item)

    def refresh(self) -> None:
        self._refresh_models()
        video_id = self._selected_video_id()
        if video_id is None:
            self.status_label.setText("Selecciona un video para transcribir.")
            self.full_text.clear()
            self.segment_table.setRowCount(0)
            return
        report = self.workspace.get_transcription(video_id)
        self._set_report(report)

    def _verify_backend(self) -> None:
        report = self.workspace.verify_transcription_backend()
        QMessageBox.information(
            self,
            "Backend de transcripcion",
            f"Backend: {report.backend.backend}\nDisponible: {'si' if report.backend.available else 'no'}\nDevice count: {report.backend.device_count}",
        )

    def _download_model(self) -> None:
        model_name = self._current_model_name()
        if self._model_thread is not None and self._model_thread.isRunning():
            return
        self._model_thread = ModelTaskThread(self.workspace, model_name, action="download")
        self._set_model_running(True)
        self._model_thread.result_ready.connect(self._download_finished)
        self._model_thread.error_ready.connect(self._download_failed)
        self._model_thread.progress_ready.connect(self._model_progress)
        self._model_thread.finished.connect(self._model_thread.deleteLater)
        self._model_thread.start()

    def _transcribe(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        if self._current_model_info().status != TranscriptionModelStatus.INSTALLED:
            QMessageBox.information(self, "Modelo no listo", "Descarga el modelo antes de transcribir.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        options = TranscriptionOptions(
            profile=self.profile_combo.currentText() or "balanced",
            model_name=self.model_combo.currentText() or "small",
            device=self.device_combo.currentText() or "auto",
            language=self.language_combo.currentText() or "auto",
            beam_size=5,
            vad_filter=False,
            word_timestamps=False,
        )
        self._set_running(True)
        self._thread = TranscriptionTaskThread(self.workspace, video_id, options)
        self._thread.result_ready.connect(self._transcription_finished)
        self._thread.error_ready.connect(self._transcription_failed)
        self._thread.progress_ready.connect(self._transcription_progress)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _transcription_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(phase)
        value = max(0, min(100, int(ratio * 100)))
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}% aproximado")

    def _transcription_finished(self, report) -> None:
        self._set_running(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._set_report(report)
        self._thread = None

    def _transcription_failed(self, message: str) -> None:
        self._set_running(False)
        QMessageBox.warning(self, "No se pudo transcribir", message)
        self._thread = None
        self._refresh_model_state()

    def _cancel(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.cancel_transcription(video_id):
            self.phase_label.setText("Cancelando")

    def _model_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(phase)
        value = max(0, min(100, int(ratio * 100)))
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}% aproximado")

    def _download_finished(self, result) -> None:
        self._model_thread = None
        self._set_model_running(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._refresh_models()
        status = getattr(result, "status", None)
        status_text = getattr(status, "value", status or "unknown")
        self.phase_label.setText(f"Modelo {status_text}")
        message = f"Estado: {status_text}\nRuta: {result.path}"
        if status_text != TranscriptionModelStatus.INSTALLED.value:
            QMessageBox.warning(self, "No se pudo descargar el modelo", message)
            return
        QMessageBox.information(self, "Modelo", message)

    def _download_failed(self, message: str) -> None:
        self._model_thread = None
        self._set_model_running(False)
        QMessageBox.warning(self, "No se pudo descargar el modelo", message)
        self._refresh_model_state()

    def _export(self, format: TranscriptionExportFormat) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        try:
            result = self.workspace.export_transcription(video_id, format)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion", f"Exportado en: {result.path}")

    def _delete(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.delete_transcription(video_id):
            self.status_label.setText("Transcripcion eliminada")
            self.full_text.clear()
            self.segment_table.setRowCount(0)
