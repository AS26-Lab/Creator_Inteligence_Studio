"""Vista de datasets de personalizacion por creador."""

from __future__ import annotations

import json

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationLabel, PersonalizationSplitName
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class PersonalizationDatasetThread(QThread):
    """Ejecuta la construccion del snapshot sin bloquear la UI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, creator_id: str, project_id: str | None, force: bool) -> None:
        super().__init__()
        self.workspace = workspace
        self.creator_id = creator_id
        self.project_id = project_id
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            report = self.workspace.build_creator_dataset(
                self.creator_id,
                project_id=self.project_id,
                force=self.force,
                progress_callback=lambda phase, ratio: self.progress_ready.emit(str(phase), float(ratio or 0.0)),
            )
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(report)


class PersonalizationDataView(QWidget):
    """Vista tecnica de datasets de personalizacion por creador."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: PersonalizationDatasetThread | None = None
        self._current_snapshot_id: str | None = None

        self.status_label = QLabel("Sin snapshot")
        self.status_label.setObjectName("MutedLabel")
        self.creator_label = QLabel("Creador: no seleccionado")
        self.project_label = QLabel("Proyecto: todos")
        self.project_label.setObjectName("MutedLabel")
        self.readiness_label = QLabel("Readiness: no disponible")
        self.readiness_label.setObjectName("MutedLabel")
        self.warnings_label = QLabel("Warnings: ninguno")
        self.warnings_label.setWordWrap(True)
        self.phase_label = QLabel("Preparando")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.label_filter = QComboBox()
        self.label_filter.addItems(["Todos", PersonalizationLabel.POSITIVE.value, PersonalizationLabel.NEGATIVE.value, PersonalizationLabel.NEUTRAL_OR_UNCERTAIN.value, PersonalizationLabel.EXCLUDED.value])
        self.split_filter = QComboBox()
        self.split_filter.addItems(["Todos", PersonalizationSplitName.TRAIN.value, PersonalizationSplitName.VALIDATION.value, PersonalizationSplitName.TEST.value, PersonalizationSplitName.EXCLUDED.value])
        self.conflict_filter = QComboBox()
        self.conflict_filter.addItems(["Todos", "Solo conflictos", "Sin conflictos"])
        self.excluded_filter = QComboBox()
        self.excluded_filter.addItems(["Todos", "Excluidos", "No excluidos"])

        self.build_button = QPushButton("Construir snapshot")
        self.rebuild_button = QPushButton("Reconstruir")
        self.compare_button = QPushButton("Comparar")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_csv_button = QPushButton("Exportar CSV")
        self.export_jsonl_button = QPushButton("Exportar JSONL")
        self.archive_button = QPushButton("Archivar")
        self.refresh_button = QPushButton("Actualizar")

        self.snapshots_table = QTableWidget(0, 10)
        self.snapshots_table.setHorizontalHeaderLabels(["Version", "Estado", "Ejemplos", "Labels", "Splits", "Conflictos", "Readiness", "Stale", "Actualizado", "ID"])
        self.snapshots_table.setColumnHidden(9, True)
        self.snapshots_table.itemSelectionChanged.connect(self._selection_changed)
        self.examples_table = QTableWidget(0, 10)
        self.examples_table.setHorizontalHeaderLabels(["Video", "Inicio", "Fin", "Label", "Split", "Weight", "Review", "Rating", "Tipo", "ID"])
        self.examples_table.setColumnHidden(9, True)
        self.examples_table.itemSelectionChanged.connect(self._example_selection_changed)
        self.quality_text = QPlainTextEdit()
        self.quality_text.setReadOnly(True)
        self.detail_text = QPlainTextEdit()
        self.detail_text.setReadOnly(True)

        actions = QHBoxLayout()
        for widget in (
            self.build_button,
            self.rebuild_button,
            self.compare_button,
            self.export_json_button,
            self.export_csv_button,
            self.export_jsonl_button,
            self.archive_button,
            self.refresh_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        filters = QHBoxLayout()
        for widget in (self.label_filter, self.split_filter, self.conflict_filter, self.excluded_filter):
            filters.addWidget(widget)
        filters.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Personalization Data")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Snapshots reproducibles, versionados y aislados por creador.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addLayout(filters)
        layout.addWidget(self.status_label)
        layout.addWidget(self.creator_label)
        layout.addWidget(self.project_label)
        layout.addWidget(self.readiness_label)
        layout.addWidget(self.warnings_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Snapshots"))
        layout.addWidget(self.snapshots_table)
        layout.addWidget(QLabel("Ejemplos"))
        layout.addWidget(self.examples_table)
        layout.addWidget(QLabel("Quality report"))
        layout.addWidget(self.quality_text)
        layout.addWidget(QLabel("Detalle tecnico"))
        layout.addWidget(self.detail_text)

        self.build_button.clicked.connect(self._build_snapshot)
        self.rebuild_button.clicked.connect(lambda: self._build_snapshot(force=True))
        self.compare_button.clicked.connect(self._compare_selected)
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        self.export_csv_button.clicked.connect(lambda: self._export("csv"))
        self.export_jsonl_button.clicked.connect(lambda: self._export("jsonl"))
        self.archive_button.clicked.connect(self._archive_selected)
        self.refresh_button.clicked.connect(self.refresh)
        for combo in (self.label_filter, self.split_filter, self.conflict_filter, self.excluded_filter):
            combo.currentIndexChanged.connect(self._apply_filters)
        self._update_action_state()

    def _selected_creator_id(self) -> str | None:
        creator = self.workspace.selected_creator()
        return creator.id if creator else None

    def _selected_project_id(self) -> str | None:
        project = self.workspace.selected_project()
        return project.id if project else None

    def _selected_snapshot_id(self) -> str | None:
        rows = self.snapshots_table.selectionModel().selectedRows() if self.snapshots_table.selectionModel() else []
        if not rows:
            return self._current_snapshot_id
        row = rows[0].row()
        item = self.snapshots_table.item(row, 9)
        return item.text() if item else None

    def _selected_example_id(self) -> str | None:
        rows = self.examples_table.selectionModel().selectedRows() if self.examples_table.selectionModel() else []
        if not rows:
            return None
        row = rows[0].row()
        item = self.examples_table.item(row, 9)
        return item.text() if item else None

    def _update_action_state(self) -> None:
        enabled = self.workspace.personalization_service is not None and self._selected_creator_id() is not None
        for button in (self.build_button, self.rebuild_button, self.export_json_button, self.export_csv_button, self.export_jsonl_button, self.archive_button, self.compare_button):
            button.setEnabled(enabled)

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None or self.workspace.personalization_service is None:
            self.status_label.setText("Selecciona un creador para preparar datos.")
            self.creator_label.setText("Creador: no seleccionado")
            self.project_label.setText("Proyecto: todos")
            self.readiness_label.setText("Readiness: no disponible")
            self.warnings_label.setText("Warnings: ninguno")
            self.snapshots_table.setRowCount(0)
            self.examples_table.setRowCount(0)
            self.quality_text.clear()
            self.detail_text.clear()
            self._current_snapshot_id = None
            self._update_action_state()
            return
        creator = self.workspace.selected_creator()
        project = self.workspace.selected_project()
        self.creator_label.setText(f"Creador: {creator.display_name if creator else creator_id}")
        self.project_label.setText(f"Proyecto: {project.name if project else 'todos'}")
        readiness = self.workspace.get_creator_readiness(creator_id)
        self.readiness_label.setText(f"Readiness: {readiness.readiness_status.value} ({readiness.readiness_score:.3f})")
        self.warnings_label.setText("Warnings: " + ("; ".join(readiness.warnings) if readiness.warnings else "ninguno"))
        snapshots = self.workspace.list_creator_datasets(creator_id)
        self.snapshots_table.setRowCount(0)
        for row_index, snapshot in enumerate(snapshots):
            self.snapshots_table.insertRow(row_index)
            values = [
                snapshot.dataset_version,
                snapshot.status.value,
                str(snapshot.example_count),
                f"{snapshot.positive_count}/{snapshot.negative_count}/{snapshot.neutral_count}/{snapshot.excluded_count}",
                f"{snapshot.train_count}/{snapshot.validation_count}/{snapshot.test_count}",
                str(snapshot.conflict_count),
                f"{snapshot.readiness_status.value} ({snapshot.readiness_score:.3f})",
                "Si" if self.workspace.is_dataset_stale(snapshot.id) else "No",
                snapshot.updated_at.isoformat(),
                snapshot.id,
            ]
            for column, value in enumerate(values):
                self.snapshots_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        if snapshots:
            self._current_snapshot_id = snapshots[0].id
            self.snapshots_table.selectRow(0)
            self._load_snapshot(snapshots[0].id)
        else:
            self._current_snapshot_id = None
            self.examples_table.setRowCount(0)
            self.quality_text.setPlainText("No hay snapshots todavia.")
            self.detail_text.clear()
        self._update_action_state()

    def _load_snapshot(self, snapshot_id: str) -> None:
        report = self.workspace.get_dataset_snapshot(snapshot_id)
        self._current_snapshot_id = snapshot_id
        self.status_label.setText(f"Estado: {report.status.value}")
        readiness_status = report.quality_report.readiness_status.value if report.quality_report else "no disponible"
        readiness_score = report.quality_report.readiness_score if report.quality_report else 0.0
        self.readiness_label.setText(f"Readiness: {readiness_status} ({readiness_score:.3f})")
        self.warnings_label.setText("Warnings: " + ("; ".join(report.warnings) if report.warnings else "ninguno"))
        self.quality_text.setPlainText(json.dumps(report.quality_report.to_dict() if report.quality_report else {}, ensure_ascii=False, indent=2, default=str))
        self._render_examples(report)

    def _render_examples(self, report) -> None:
        examples = list(report.examples)
        label_filter = self.label_filter.currentText()
        split_filter = self.split_filter.currentText()
        conflict_filter = self.conflict_filter.currentText()
        excluded_filter = self.excluded_filter.currentText()
        if label_filter != "Todos":
            examples = [example for example in examples if example.label.value == label_filter]
        if split_filter != "Todos":
            examples = [example for example in examples if example.split_name.value == split_filter]
        if conflict_filter == "Solo conflictos":
            examples = [example for example in examples if example.quality_flags.get("is_conflicted")]
        elif conflict_filter == "Sin conflictos":
            examples = [example for example in examples if not example.quality_flags.get("is_conflicted")]
        if excluded_filter == "Excluidos":
            examples = [example for example in examples if example.label == PersonalizationLabel.EXCLUDED]
        elif excluded_filter == "No excluidos":
            examples = [example for example in examples if example.label != PersonalizationLabel.EXCLUDED]
        self.examples_table.setRowCount(0)
        for row_index, example in enumerate(examples):
            self.examples_table.insertRow(row_index)
            values = [
                example.video_asset_id,
                f"{example.start_seconds:.3f}",
                f"{example.end_seconds:.3f}",
                example.label.value,
                example.split_name.value,
                f"{example.sample_weight:.3f}",
                example.human_review_status or "",
                "" if example.human_rating is None else str(example.human_rating),
                str(example.feature_vector.get("candidate_type", "")),
                example.id,
            ]
            for column, value in enumerate(values):
                self.examples_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        if examples:
            self.examples_table.resizeColumnsToContents()
        self._update_detail_panel(report)

    def _update_detail_panel(self, report) -> None:
        example_id = self._selected_example_id()
        if example_id is None and report.examples:
            example_id = report.examples[0].id
        if example_id is None:
            self.detail_text.setPlainText("No hay ejemplos para mostrar.")
            return
        example = next((item for item in report.examples if item.id == example_id), None)
        if example is None:
            self.detail_text.setPlainText("No hay detalle disponible.")
            return
        self.detail_text.setPlainText(json.dumps(example.to_dict(), ensure_ascii=False, indent=2, default=str))

    def _selection_changed(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        self._load_snapshot(snapshot_id)

    def _example_selection_changed(self) -> None:
        snapshot_id = self._current_snapshot_id or self._selected_snapshot_id()
        if snapshot_id is None:
            return
        report = self.workspace.get_dataset_snapshot(snapshot_id)
        self._update_detail_panel(report)

    def _apply_filters(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        report = self.workspace.get_dataset_snapshot(snapshot_id)
        self._render_examples(report)

    def _build_snapshot(self, force: bool = False) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Sin creador", "Selecciona un creador primero.")
            return
        project_id = self._selected_project_id()
        self.phase_label.setText("Cargando feedback")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._thread = PersonalizationDatasetThread(self.workspace, creator_id, project_id, force)
        self._thread.progress_ready.connect(self._progress_update)
        self._thread.error_ready.connect(self._build_error)
        self._thread.result_ready.connect(self._build_result)
        self._thread.start()

    def _progress_update(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(phase)
        self.progress_bar.setValue(int(ratio * 100))
        self.progress_label.setText(f"{int(ratio * 100)}%")

    def _build_error(self, message: str) -> None:
        QMessageBox.warning(self, "No se pudo construir el dataset", message)
        self.phase_label.setText("Error")

    def _build_result(self, report) -> None:
        self.phase_label.setText("Completado")
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._current_snapshot_id = report.snapshot.id if report.snapshot else None
        self.refresh()

    def _compare_selected(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            return
        snapshots = self.workspace.list_creator_datasets(creator_id)
        if len(snapshots) < 2:
            QMessageBox.information(self, "Comparacion insuficiente", "Se necesitan al menos dos snapshots.")
            return
        comparison = self.workspace.compare_dataset_snapshots(snapshots[1].id, snapshots[0].id)
        self.detail_text.setPlainText(json.dumps(comparison.to_dict(), ensure_ascii=False, indent=2, default=str))

    def _archive_selected(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        try:
            self.workspace.archive_dataset_snapshot(snapshot_id)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo archivar", str(exc))
            return
        self.refresh()

    def _export(self, format_name: str) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        try:
            result = self.workspace.export_dataset(snapshot_id, format_name)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo exportar", str(exc))
            return
        QMessageBox.information(self, "Exportacion completada", result.path)
