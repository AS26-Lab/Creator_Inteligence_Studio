"""Vista inicial para edicion de subtitulos locales."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class SubtitleEditorView(QWidget):
    """Editor tecnico inicial de tracks de subtitulos."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._current_track_id: str | None = None
        self._current_cue_id: str | None = None

        self.track_combo = QComboBox()
        self.candidate_combo = QComboBox()
        self.language_label = QLabel("Idioma: -")
        self.source_label = QLabel("Fuente: -")
        self.version_label = QLabel("Version: -")
        self.status_label = QLabel("Estado: -")
        self.stale_label = QLabel("Stale: no")
        self.count_label = QLabel("Cues: 0")
        self.duration_label = QLabel("Duracion: 0.0 s")
        self.validation_label = QLabel("Validacion: -")
        self.preview_label = QLabel("Cue activo: -")
        self.preview_label.setWordWrap(True)

        self.track_combo.currentIndexChanged.connect(self._track_changed)
        self.candidate_combo.currentIndexChanged.connect(self._candidate_changed)

        self.generate_video_button = QPushButton("Generar video")
        self.generate_clip_button = QPushButton("Generar clip")
        self.import_button = QPushButton("Importar")
        self.export_button = QPushButton("Exportar")
        self.validate_button = QPushButton("Validar")
        self.refresh_button = QPushButton("Actualizar")
        self.lock_button = QPushButton("Bloquear")
        self.unlock_button = QPushButton("Desbloquear")
        self.duplicate_button = QPushButton("Duplicar")
        self.archive_button = QPushButton("Archivar")
        self.delete_track_button = QPushButton("Eliminar track")

        self.save_text_button = QPushButton("Guardar texto")
        self.save_time_button = QPushButton("Guardar tiempos")
        self.split_button = QPushButton("Dividir")
        self.merge_button = QPushButton("Fusionar con siguiente")
        self.delete_cue_button = QPushButton("Eliminar cue")
        self.restore_cue_button = QPushButton("Restaurar cue")
        self.shift_button = QPushButton("Desplazar track")

        self.cue_table = QTableWidget(0, 8)
        self.cue_table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Duracion", "Texto", "CPS", "Estado", "Warnings"])
        self.cue_table.itemSelectionChanged.connect(self._cue_selection_changed)

        self.cue_text = QPlainTextEdit()
        self.cue_text.setPlaceholderText("Texto del cue seleccionado")
        self.cue_start = QDoubleSpinBox()
        self.cue_start.setDecimals(3)
        self.cue_start.setRange(0.0, 99999.0)
        self.cue_end = QDoubleSpinBox()
        self.cue_end.setDecimals(3)
        self.cue_end.setRange(0.001, 99999.0)
        self.split_position = QSpinBox()
        self.split_position.setRange(1, 9999)
        self.shift_offset = QDoubleSpinBox()
        self.shift_offset.setDecimals(3)
        self.shift_offset.setRange(-99999.0, 99999.0)
        self.preview_time = QDoubleSpinBox()
        self.preview_time.setDecimals(3)
        self.preview_time.setRange(0.0, 99999.0)
        self.preview_time.valueChanged.connect(self._update_preview)
        self.active_cue_label = QLabel("Sin cue activo")
        self.active_cue_label.setWordWrap(True)

        top = QHBoxLayout()
        top.addWidget(QLabel("Track"))
        top.addWidget(self.track_combo)
        top.addWidget(QLabel("Candidato"))
        top.addWidget(self.candidate_combo)
        for widget in (self.generate_video_button, self.generate_clip_button, self.import_button, self.export_button, self.validate_button, self.refresh_button):
            top.addWidget(widget)
        top.addStretch(1)

        meta = QHBoxLayout()
        for widget in (
            self.language_label,
            self.source_label,
            self.version_label,
            self.status_label,
            self.stale_label,
            self.count_label,
            self.duration_label,
            self.validation_label,
        ):
            meta.addWidget(widget)
        meta.addStretch(1)

        track_actions = QHBoxLayout()
        for widget in (self.lock_button, self.unlock_button, self.duplicate_button, self.archive_button, self.delete_track_button, self.shift_button):
            track_actions.addWidget(widget)
        track_actions.addWidget(QLabel("Desplazar"))
        track_actions.addWidget(self.shift_offset)
        track_actions.addStretch(1)

        cue_controls = QHBoxLayout()
        cue_controls.addWidget(QLabel("Inicio"))
        cue_controls.addWidget(self.cue_start)
        cue_controls.addWidget(QLabel("Fin"))
        cue_controls.addWidget(self.cue_end)
        cue_controls.addWidget(QLabel("Split"))
        cue_controls.addWidget(self.split_position)
        for widget in (self.save_text_button, self.save_time_button, self.split_button, self.merge_button, self.delete_cue_button, self.restore_cue_button):
            cue_controls.addWidget(widget)
        cue_controls.addStretch(1)

        preview_controls = QHBoxLayout()
        preview_controls.addWidget(QLabel("Tiempo"))
        preview_controls.addWidget(self.preview_time)
        preview_controls.addWidget(self.active_cue_label, 1)

        editor = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Cues"))
        left.addWidget(self.cue_table)
        right = QVBoxLayout()
        right.addWidget(QLabel("Texto"))
        right.addWidget(self.cue_text)
        right.addLayout(cue_controls)
        right.addLayout(preview_controls)
        right.addWidget(self.preview_label)
        editor.addLayout(left, 2)
        editor.addLayout(right, 1)

        layout = QVBoxLayout(self)
        title = QLabel("Subtitulos")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Transcripcion y subtitulos son entidades distintas. Esta vista edita solo la capa editorial local.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(top)
        layout.addLayout(meta)
        layout.addLayout(track_actions)
        layout.addLayout(editor)

        self.generate_video_button.clicked.connect(self._generate_video)
        self.generate_clip_button.clicked.connect(self._generate_clip)
        self.import_button.clicked.connect(self._import)
        self.export_button.clicked.connect(self._export)
        self.validate_button.clicked.connect(self._validate)
        self.refresh_button.clicked.connect(self.refresh)
        self.lock_button.clicked.connect(self._lock_track)
        self.unlock_button.clicked.connect(self._unlock_track)
        self.duplicate_button.clicked.connect(self._duplicate_track)
        self.archive_button.clicked.connect(self._archive_track)
        self.delete_track_button.clicked.connect(self._delete_track)
        self.save_text_button.clicked.connect(self._save_text)
        self.save_time_button.clicked.connect(self._save_time)
        self.split_button.clicked.connect(self._split_cue)
        self.merge_button.clicked.connect(self._merge_cue)
        self.delete_cue_button.clicked.connect(self._delete_cue)
        self.restore_cue_button.clicked.connect(self._restore_cue)
        self.shift_button.clicked.connect(self._shift_track)

    def refresh(self) -> None:
        video = self.workspace.selected_video()
        self.track_combo.blockSignals(True)
        self.candidate_combo.blockSignals(True)
        self.track_combo.clear()
        self.candidate_combo.clear()
        if video is None:
            self.track_combo.addItem("Sin video", None)
            self.candidate_combo.addItem("Sin video", None)
            self._clear_details()
            self.track_combo.blockSignals(False)
            self.candidate_combo.blockSignals(False)
            return
        for track in self.workspace.list_video_subtitle_tracks(video.id):
            label = f"{track.name} ({track.status.value})"
            self.track_combo.addItem(label, track.id)
        for candidate in self.workspace.list_ranked_candidates(video.id):
            label = getattr(candidate, "name", None) or getattr(candidate, "title", None) or candidate.id
            self.candidate_combo.addItem(f"{label} [{getattr(candidate.review_status, 'value', candidate.review_status)}]", candidate.id)
        if self.track_combo.count() == 0:
            self.track_combo.addItem("Sin tracks", None)
        if self.candidate_combo.count() == 0:
            self.candidate_combo.addItem("Sin candidatos", None)
        self.track_combo.setCurrentIndex(0)
        self.candidate_combo.setCurrentIndex(0)
        self.track_combo.blockSignals(False)
        self.candidate_combo.blockSignals(False)
        self._load_current_track()

    def _track_changed(self, *_args) -> None:
        self._load_current_track()

    def _candidate_changed(self, *_args) -> None:
        self._update_preview()

    def _selected_track_id(self) -> str | None:
        return self.track_combo.currentData()

    def _selected_candidate_id(self) -> str | None:
        return self.candidate_combo.currentData()

    def _clear_details(self) -> None:
        self._current_track_id = None
        self._current_cue_id = None
        self.language_label.setText("Idioma: -")
        self.source_label.setText("Fuente: -")
        self.version_label.setText("Version: -")
        self.status_label.setText("Estado: -")
        self.stale_label.setText("Stale: no")
        self.count_label.setText("Cues: 0")
        self.duration_label.setText("Duracion: 0.0 s")
        self.validation_label.setText("Validacion: -")
        self.preview_label.setText("Cue activo: -")
        self.active_cue_label.setText("Sin cue activo")
        self.cue_table.setRowCount(0)
        self.cue_text.clear()

    def _load_current_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            self._clear_details()
            return
        report = self.workspace.get_subtitle_track(track_id)
        track = report.track
        if track is None:
            self._clear_details()
            return
        self._current_track_id = track.id
        self.language_label.setText(f"Idioma: {track.language}")
        self.source_label.setText(f"Fuente: {track.source_type.value}")
        self.version_label.setText(f"Version: {track.track_version}")
        self.status_label.setText(f"Estado: {track.status.value}")
        self.stale_label.setText(f"Stale: {'si' if report.is_stale else 'no'}")
        self.count_label.setText(f"Cues: {len(report.cues)}")
        duration = max(0.0, track.source_end_seconds - track.source_start_seconds)
        self.duration_label.setText(f"Duracion: {duration:.1f} s")
        blocking = ", ".join(report.validation.blocking_errors) if report.validation and report.validation.blocking_errors else "sin errores bloqueantes"
        self.validation_label.setText(f"Validacion: {blocking}")
        self.preview_time.setRange(0.0, max(duration, 0.001))
        self.preview_time.setValue(0.0)
        self._fill_cues(report.cues)
        self._update_preview()

    def _fill_cues(self, cues) -> None:
        self.cue_table.setRowCount(0)
        for row, cue in enumerate(cues):
            self.cue_table.insertRow(row)
            warnings = cue.warning_codes_json
            values = [
                str(cue.cue_index),
                f"{cue.start_seconds:.3f}",
                f"{cue.end_seconds:.3f}",
                f"{max(0.0, cue.end_seconds - cue.start_seconds):.3f}",
                cue.text,
                f"{cue.characters_per_second:.2f}",
                cue.validation_status.value,
                warnings,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                self.cue_table.setItem(row, column, item)

    def _current_report(self):
        track_id = self._selected_track_id()
        if not track_id:
            return None
        return self.workspace.get_subtitle_track(track_id)

    def _selected_cue(self):
        report = self._current_report()
        if report is None:
            return None
        row = self.cue_table.currentRow()
        if row < 0 or row >= len(report.cues):
            return None
        return report.cues[row]

    def _cue_selection_changed(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        self._current_cue_id = cue.id
        self.cue_text.setPlainText(cue.text)
        self.cue_start.setValue(cue.start_seconds)
        self.cue_end.setValue(cue.end_seconds)
        self.split_position.setValue(max(1, len(cue.text) // 2))
        self.preview_label.setText(f"Cue seleccionado: {cue.text}")
        self._update_preview()

    def _update_preview(self) -> None:
        report = self._current_report()
        if report is None:
            self.active_cue_label.setText("Sin cue activo")
            return
        current_time = self.preview_time.value()
        cue = next((item for item in report.cues if item.start_seconds <= current_time <= item.end_seconds), None)
        if cue is None:
            self.active_cue_label.setText(f"Tiempo {current_time:.3f}s: sin cue activo")
        else:
            self.active_cue_label.setText(f"Tiempo {current_time:.3f}s: {cue.text}")

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else None

    def _generate_video(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        try:
            self.workspace.generate_video_subtitles(video_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudieron generar subtitulos", str(exc))
            return
        self.refresh()

    def _generate_clip(self) -> None:
        candidate_id = self._selected_candidate_id()
        if candidate_id is None:
            QMessageBox.information(self, "Sin candidato", "Selecciona un candidato primero.")
            return
        try:
            self.workspace.generate_clip_subtitles(candidate_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudieron generar subtitulos", str(exc))
            return
        self.refresh()

    def _import(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Sin video", "Selecciona un video primero.")
            return
        file_name, _ = QFileDialog.getOpenFileName(self, "Importar subtitulos", "", "Subtitulos (*.srt *.vtt *.ass *.json);;Todos los archivos (*.*)")
        if not file_name:
            return
        try:
            self.workspace.import_subtitles(video_id, file_name)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo importar", str(exc))
            return
        self.refresh()

    def _export(self) -> None:
        track_id = self._selected_track_id()
        if track_id is None:
            QMessageBox.information(self, "Sin track", "Selecciona un track primero.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar subtitulos", "", "SRT (*.srt);;VTT (*.vtt);;ASS (*.ass);;TXT (*.txt);;JSON (*.json)")
        if not path:
            return
        suffix = Path(path).suffix.lower().lstrip(".") or "srt"
        try:
            result = self.workspace.export_subtitles(track_id, suffix, output=path)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion", f"Exportado en: {result.path}")

    def _validate(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        report = self.workspace.validate_subtitle_track(track_id)
        blocking = ", ".join(report.validation.blocking_errors) if report.validation else "sin validacion"
        QMessageBox.information(self, "Validacion", blocking)
        self._load_current_track()

    def _save_text(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        try:
            self.workspace.update_subtitle_cue_text(cue.id, self.cue_text.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo guardar el texto", str(exc))
            return
        self.refresh()

    def _save_time(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        try:
            self.workspace.update_subtitle_cue_timing(cue.id, self.cue_start.value(), self.cue_end.value())
        except Exception as exc:
            QMessageBox.warning(self, "No se pudieron guardar los tiempos", str(exc))
            return
        self.refresh()

    def _split_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        try:
            self.workspace.split_subtitle_cue(cue.id, self.split_position.value())
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo dividir", str(exc))
            return
        self.refresh()

    def _merge_cue(self) -> None:
        report = self._current_report()
        cue = self._selected_cue()
        if report is None or cue is None:
            return
        next_index = cue.cue_index + 1
        if next_index >= len(report.cues):
            return
        try:
            self.workspace.merge_subtitle_cues(cue.id, report.cues[next_index].id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo fusionar", str(exc))
            return
        self.refresh()

    def _delete_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        try:
            self.workspace.delete_subtitle_cue(cue.id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo eliminar", str(exc))
            return
        self.refresh()

    def _restore_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        try:
            self.workspace.restore_subtitle_cue(cue.id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo restaurar", str(exc))
            return
        self.refresh()

    def _shift_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.shift_subtitle_track(track_id, self.shift_offset.value())
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo desplazar", str(exc))
            return
        self.refresh()

    def _lock_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.lock_subtitle_track(track_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo bloquear", str(exc))
            return
        self.refresh()

    def _unlock_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.unlock_subtitle_track(track_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo desbloquear", str(exc))
            return
        self.refresh()

    def _duplicate_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.duplicate_subtitle_track(track_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo duplicar", str(exc))
            return
        self.refresh()

    def _archive_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.archive_subtitle_track(track_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo archivar", str(exc))
            return
        self.refresh()

    def _delete_track(self) -> None:
        track_id = self._selected_track_id()
        if not track_id:
            return
        try:
            self.workspace.delete_subtitle_track(track_id)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo eliminar el track", str(exc))
            return
        self.refresh()
