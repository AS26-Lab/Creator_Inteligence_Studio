"""Vista de ranking de clips."""

from __future__ import annotations

import json

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class ClipRankingThread(QThread):
    """Ejecuta el ranking de clips sin bloquear la GUI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, video_id: str, profile: str, force: bool = False) -> None:
        super().__init__()
        self.workspace = workspace
        self.video_id = video_id
        self.profile = profile
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            report = self.workspace.rank_clip_candidates(
                self.video_id,
                profile=self.profile,
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


class RenderClipThread(QThread):
    """Ejecuta un render de clip o coleccion sin bloquear la GUI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(
        self,
        workspace: WorkspaceViewModel,
        *,
        candidate_id: str | None = None,
        collection_id: str | None = None,
        profile: str = "balanced",
        output: str | None = None,
        output_root: str | None = None,
        explicit: bool = False,
        allow_stale: bool = False,
        allow_overwrite: bool = False,
        custom_name: str | None = None,
    ) -> None:
        super().__init__()
        self.workspace = workspace
        self.candidate_id = candidate_id
        self.collection_id = collection_id
        self.profile = profile
        self.output = output
        self.output_root = output_root
        self.explicit = explicit
        self.allow_stale = allow_stale
        self.allow_overwrite = allow_overwrite
        self.custom_name = custom_name

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            if self.collection_id is not None:
                report = self.workspace.render_collection(
                    self.collection_id,
                    profile=self.profile,
                    output_root=self.output_root,
                    explicit=self.explicit,
                    allow_stale=self.allow_stale,
                )
            elif self.candidate_id is not None:
                report = self.workspace.render_candidate(
                    self.candidate_id,
                    profile=self.profile,
                    output=self.output,
                    output_root_override=self.output_root,
                    explicit=self.explicit,
                    allow_stale=self.allow_stale,
                    allow_overwrite=self.allow_overwrite,
                    custom_name=self.custom_name,
                    progress_callback=lambda phase, ratio, _payload: self.progress_ready.emit(phase, float(ratio or 0.0)),
                )
            else:
                raise ValueError("Render sin destino.")
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(report)


class ClipRankingView(QWidget):
    """Vista tecnica para ranking y revision humana de clips."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: ClipRankingThread | None = None
        self._render_thread: RenderClipThread | None = None

        self.status_label = QLabel("Sin ranking")
        self.status_label.setObjectName("MutedLabel")
        self.stale_label = QLabel("Stale: no")
        self.stale_label.setObjectName("MutedLabel")
        self.summary_label = QLabel("Candidatos no disponibles")
        self.summary_label.setWordWrap(True)
        self.phase_label = QLabel("Cargando candidatos")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["balanced", "speech-focused", "visual-focused", "high-energy", "story-beats"])
        self.render_profile_combo = QComboBox()
        self.render_profile_combo.addItems(["balanced", "source_quality", "compact", "draft"])
        self.render_name_edit = QLineEdit()
        self.render_name_edit.setPlaceholderText("Nombre de salida opcional")
        self.render_folder_edit = QLineEdit()
        self.render_folder_edit.setPlaceholderText("Carpeta de salida opcional")
        self.review_filter_combo = QComboBox()
        self.review_filter_combo.addItems(["Todas", "unreviewed", "shortlisted", "approved", "rejected", "needs_review", "duplicate", "invalid", "exported"])
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["ranking", "time", "score", "duration", "rating", "review"])

        self.rank_button = QPushButton("Generar ranking")
        self.recalculate_button = QPushButton("Recalcular")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_csv_button = QPushButton("Exportar CSV")
        self.export_edl_button = QPushButton("Exportar EDL")
        self.delete_button = QPushButton("Eliminar ranking")
        self.render_button = QPushButton("Renderizar clip")
        self.render_collection_button = QPushButton("Renderizar colección")

        self.approve_button = QPushButton("Aprobar")
        self.reject_button = QPushButton("Rechazar")
        self.shortlist_button = QPushButton("Preseleccionar")
        self.needs_review_button = QPushButton("Revisar después")
        self.rate_button = QPushButton("Rating")
        self.note_button = QPushButton("Nota")
        self.tags_button = QPushButton("Tags")
        self.adjust_button = QPushButton("Ajustar bordes")
        self.reset_button = QPushButton("Restaurar bordes")
        self.collection_button = QPushButton("Agregar a colección")

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["#", "Inicio", "Fin", "Duracion", "Tipo", "Score", "Conf", "Estado", "Rating", "Tags"])
        self.table.setColumnHidden(9, False)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)

        top = QHBoxLayout()
        top.addWidget(QLabel("Perfil"))
        top.addWidget(self.profile_combo)
        top.addWidget(QLabel("Filtro"))
        top.addWidget(self.review_filter_combo)
        top.addWidget(QLabel("Orden"))
        top.addWidget(self.sort_combo)
        for widget in (self.rank_button, self.recalculate_button, self.export_json_button, self.export_csv_button, self.export_edl_button, self.delete_button):
            top.addWidget(widget)
        top.addStretch(1)

        render_row = QHBoxLayout()
        render_row.addWidget(QLabel("Render"))
        render_row.addWidget(QLabel("Perfil"))
        render_row.addWidget(self.render_profile_combo)
        render_row.addWidget(QLabel("Nombre"))
        render_row.addWidget(self.render_name_edit)
        render_row.addWidget(QLabel("Carpeta"))
        render_row.addWidget(self.render_folder_edit)
        render_row.addWidget(self.render_button)
        render_row.addWidget(self.render_collection_button)
        render_row.addStretch(1)

        actions = QHBoxLayout()
        for widget in (
            self.approve_button,
            self.reject_button,
            self.shortlist_button,
            self.needs_review_button,
            self.rate_button,
            self.note_button,
            self.tags_button,
            self.adjust_button,
            self.reset_button,
            self.collection_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Ranking de clips")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Capa tecnica y determinista para revisar candidatos multimodales.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(top)
        layout.addLayout(render_row)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stale_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Detalle tecnico"))
        layout.addWidget(self.detail)

        self.rank_button.clicked.connect(self._rank)
        self.recalculate_button.clicked.connect(lambda: self._rank(force=True))
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_csv_button.clicked.connect(lambda: self._export("csv"))
        self.export_edl_button.clicked.connect(lambda: self._export("edl"))
        self.delete_button.clicked.connect(self._delete)
        self.render_button.clicked.connect(self._render_candidate)
        self.render_collection_button.clicked.connect(self._render_collection)
        self.approve_button.clicked.connect(self._approve)
        self.reject_button.clicked.connect(self._reject)
        self.shortlist_button.clicked.connect(self._shortlist)
        self.needs_review_button.clicked.connect(self._needs_review)
        self.rate_button.clicked.connect(self._rate)
        self.note_button.clicked.connect(self._note)
        self.tags_button.clicked.connect(self._tags)
        self.adjust_button.clicked.connect(self._adjust)
        self.reset_button.clicked.connect(self._reset)
        self.collection_button.clicked.connect(self._add_to_collection)
        self.review_filter_combo.currentIndexChanged.connect(self.refresh)
        self.sort_combo.currentIndexChanged.connect(self.refresh)

    def _selected_video_id(self) -> str | None:
        video = self.workspace.selected_video()
        return video.id if video else None

    def _selected_candidate_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        row = rows[0].row()
        item = self.table.item(row, 9)
        return item.text() if item else None

    def _selection_changed(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            self.detail.clear()
            return
        report = self.workspace.get_ranking_run(video_id)
        self._render_report(report)

    def refresh(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            self.status_label.setText("Selecciona un video para rankear.")
            self.stale_label.setText("Stale: no")
            self.summary_label.setText("Candidatos no disponibles")
            self.detail.clear()
            self.table.setRowCount(0)
            self.phase_label.setText("Listo")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            return
        report = self.workspace.get_ranking_run(video_id)
        self._render_report(report)

    def _render_report(self, report) -> None:
        self.status_label.setText(f"Estado: {report.status.value}")
        self.stale_label.setText(f"Stale: {'si' if report.is_stale else 'no'}")
        if report.run is None:
            self.summary_label.setText("No existe ranking de clips para este video.")
            self.detail.setPlainText("Genera un ranking para ver candidatos y feedback.")
            self.table.setRowCount(0)
            self.phase_label.setText("Listo")
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
            return
        self.summary_label.setText(
            " | ".join(
                [
                    f"Total: {report.run.candidate_count}",
                    f"Rankeados: {report.run.ranked_candidate_count}",
                    f"Seleccionados: {report.run.selected_count}",
                    f"Rechazados: {report.run.rejected_count}",
                    f"Revisados: {report.run.review_count}",
                ]
            )
        )
        self._populate_table(report.candidates)
        self._render_selected_detail(report.candidates)

    def _populate_table(self, candidates) -> None:
        self.table.setRowCount(0)
        for row_index, candidate in enumerate(candidates):
            self.table.insertRow(row_index)
            values = [
                str(candidate.rank_position),
                f"{candidate.adjusted_start_seconds:.3f}",
                f"{candidate.adjusted_end_seconds:.3f}",
                f"{candidate.duration_seconds:.3f}",
                candidate.candidate_type,
                f"{candidate.rank_score:.3f}",
                f"{candidate.source_confidence:.3f}",
                candidate.review_status.value,
                "" if candidate.user_rating is None else str(candidate.user_rating),
                ",".join(candidate.tags),
                candidate.id,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_index, column, item)
        self.table.setColumnHidden(9, True)

    def _render_selected_detail(self, candidates) -> None:
        candidate = None
        candidate_id = self._selected_candidate_id()
        if candidate_id:
            candidate = next((item for item in candidates if item.id == candidate_id), None)
        if candidate is None and candidates:
            candidate = candidates[0]
        if candidate is None:
            self.detail.setPlainText("Sin candidatos.")
            return
        history = self.workspace.get_candidate_review_history(candidate.id)
        payload = {
            "candidate": candidate.to_dict(),
            "history": [event.to_dict() for event in history],
        }
        self.detail.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))

    def _current_candidate(self):
        candidate_id = self._selected_candidate_id()
        if not candidate_id:
            QMessageBox.information(self, "Clip ranking", "Selecciona un candidato.")
            return None
        return self.workspace.get_ranked_candidate(candidate_id)

    def _rank(self, force: bool = False) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Clip ranking", "Selecciona un video primero.")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        profile = self.profile_combo.currentText()
        self.phase_label.setText("Cargando candidatos")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._thread = ClipRankingThread(self.workspace, video_id, profile, force=force)
        self._thread.result_ready.connect(self._ranking_finished)
        self._thread.error_ready.connect(self._ranking_failed)
        self._thread.progress_ready.connect(self._progress)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _ranking_finished(self, report) -> None:
        self._render_report(report)

    def _ranking_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Clip ranking", message)
        self.phase_label.setText("Error")

    def _progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(phase)
        value = max(0, min(100, int(ratio * 100)))
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")

    def _render_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(f"Render: {phase}")
        value = max(0, min(100, int(ratio * 100)))
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")

    def _export(self, format_name: str) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        try:
            result = self.workspace.export_clip_plan(video_id, format_name)
        except DomainError as exc:
            QMessageBox.critical(self, "Clip ranking", str(exc))
            return
        QMessageBox.information(self, "Clip ranking", f"Exportado: {result.path}")

    def _delete(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            return
        if self.workspace.delete_clip_ranking(video_id):
            QMessageBox.information(self, "Clip ranking", "Ranking eliminado.")
            self.refresh()
        else:
            QMessageBox.information(self, "Clip ranking", "No existia ranking.")

    def _render_candidate(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        if self._render_thread is not None and self._render_thread.isRunning():
            return
        profile = self.render_profile_combo.currentText()
        custom_name = self.render_name_edit.text().strip() or None
        output_root = self.render_folder_edit.text().strip() or None
        self.phase_label.setText("Renderizando")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._render_thread = RenderClipThread(
            self.workspace,
            candidate_id=candidate.id,
            profile=profile,
            explicit=candidate.review_status.value == "needs_review",
            output_root=output_root,
            custom_name=custom_name,
        )
        self._render_thread.result_ready.connect(self._render_finished)
        self._render_thread.error_ready.connect(self._render_failed)
        self._render_thread.progress_ready.connect(self._render_progress)
        self._render_thread.finished.connect(self._render_thread.deleteLater)
        self._render_thread.start()

    def _render_collection(self) -> None:
        video_id = self._selected_video_id()
        if video_id is None:
            QMessageBox.information(self, "Clip ranking", "Selecciona un video primero.")
            return
        collections = self.workspace.list_clip_collections(video_id)
        if not collections:
            QMessageBox.information(self, "Clip ranking", "No hay colecciones para este video.")
            return
        selected, ok = QInputDialog.getItem(self, "Coleccion", "Selecciona una coleccion:", [collection.name for collection in collections], editable=False)
        if not ok or not selected:
            return
        collection = next((item for item in collections if item.name == selected), None)
        if collection is None:
            return
        if self._render_thread is not None and self._render_thread.isRunning():
            return
        profile = self.render_profile_combo.currentText()
        output_root = self.render_folder_edit.text().strip() or None
        self.phase_label.setText("Renderizando coleccion")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._render_thread = RenderClipThread(
            self.workspace,
            collection_id=collection.id,
            profile=profile,
            output_root=output_root,
            custom_name=self.render_name_edit.text().strip() or None,
            explicit=True,
        )
        self._render_thread.result_ready.connect(self._render_finished)
        self._render_thread.error_ready.connect(self._render_failed)
        self._render_thread.progress_ready.connect(self._render_progress)
        self._render_thread.finished.connect(self._render_thread.deleteLater)
        self._render_thread.start()

    def _render_finished(self, report) -> None:
        QMessageBox.information(self, "Clip ranking", "Render completado.")
        self.detail.setPlainText(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        self.refresh()

    def _render_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Clip ranking", message)
        self.phase_label.setText("Error render")

    def _approve(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        self.workspace.approve_candidate(candidate.id)
        self.refresh()

    def _reject(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        self.workspace.reject_candidate(candidate.id)
        self.refresh()

    def _shortlist(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        self.workspace.shortlist_candidate(candidate.id)
        self.refresh()

    def _needs_review(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        self.workspace.mark_candidate_needs_review(candidate.id)
        self.refresh()

    def _rate(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        rating, ok = QInputDialog.getInt(self, "Rating", "Rating 1 a 5:", value=candidate.user_rating or 3, min=1, max=5)
        if ok:
            self.workspace.rate_candidate(candidate.id, rating)
            self.refresh()

    def _note(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        text, ok = QInputDialog.getText(self, "Nota", "Nota humana:", text=candidate.user_note or "")
        if ok:
            self.workspace.add_candidate_note(candidate.id, text)
            self.refresh()

    def _tags(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        text, ok = QInputDialog.getText(self, "Tags", "Tags separadas por coma:", text=",".join(candidate.tags))
        if ok:
            tags = [tag.strip() for tag in text.split(",") if tag.strip()]
            self.workspace.set_candidate_tags(candidate.id, tags)
            self.refresh()

    def _adjust(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        start, ok = QInputDialog.getDouble(self, "Inicio", "Inicio en segundos:", value=candidate.adjusted_start_seconds, min=0.0, decimals=3)
        if not ok:
            return
        end, ok = QInputDialog.getDouble(self, "Fin", "Fin en segundos:", value=candidate.adjusted_end_seconds, min=0.0, decimals=3)
        if ok:
            self.workspace.adjust_candidate_bounds(candidate.id, start, end)
            self.refresh()

    def _reset(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        self.workspace.reset_candidate_review(candidate.id)
        self.refresh()

    def _add_to_collection(self) -> None:
        candidate = self._current_candidate()
        if candidate is None:
            return
        video_id = self._selected_video_id()
        if video_id is None:
            return
        name, ok = QInputDialog.getText(self, "Coleccion", "Nombre de la coleccion:")
        if not ok or not name.strip():
            return
        collection = self.workspace.create_clip_collection(video_id, name.strip())
        self.workspace.add_candidate_to_collection(collection.id, candidate.id)
        QMessageBox.information(self, "Clip ranking", f"Agregado a coleccion: {collection.name}")
