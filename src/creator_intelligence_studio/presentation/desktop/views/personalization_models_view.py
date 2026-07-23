"""Vista de modelos personalizados por creador."""

from __future__ import annotations

import json

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class ModelTrainingThread(QThread):
    """Ejecuta validacion o entrenamiento sin bloquear la UI."""

    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, snapshot_id: str, *, action: str, force: bool = False) -> None:
        super().__init__()
        self.workspace = workspace
        self.snapshot_id = snapshot_id
        self.action = action
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            if self.action == "validate":
                result = self.workspace.validate_training_snapshot(self.snapshot_id)
            else:
                result = self.workspace.train_personalization_baseline(
                    self.snapshot_id,
                    force=self.force,
                    progress_callback=lambda phase, ratio: self.progress_ready.emit(str(phase), float(ratio or 0.0)),
                )
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(result)


class PersonalizationModelsView(QWidget):
    """Vista tecnica para entrenamiento y activacion del baseline personalizado."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: ModelTrainingThread | None = None

        self.status_label = QLabel("Sin modelo")
        self.status_label.setObjectName("MutedLabel")
        self.summary_label = QLabel("Selecciona un creador para ver modelos.")
        self.summary_label.setWordWrap(True)
        self.phase_label = QLabel("Listo")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.readiness_label = QLabel("Readiness: no disponible")
        self.readiness_label.setObjectName("MutedLabel")
        self.model_label = QLabel("Modelo activo: ninguno")
        self.model_label.setObjectName("MutedLabel")

        self.validate_button = QPushButton("Validar snapshot")
        self.train_button = QPushButton("Entrenar baseline")
        self.refresh_button = QPushButton("Actualizar")
        self.activate_button = QPushButton("Activar")
        self.deactivate_button = QPushButton("Desactivar")
        self.retire_button = QPushButton("Retirar")
        self.verify_button = QPushButton("Verificar artefacto")
        self.delete_artifact_button = QPushButton("Eliminar artefacto local")
        self.export_button = QPushButton("Exportar métricas")

        self.runs_table = QTableWidget(0, 8)
        self.runs_table.setHorizontalHeaderLabels(["Run", "Estado", "Modelo", "Train", "Val", "Test", "Métricas", "ID"])
        self.runs_table.setColumnHidden(7, True)
        self.runs_table.itemSelectionChanged.connect(self._selection_changed)

        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Split", "Métrica", "Valor", "Support"])

        self.predictions_table = QTableWidget(0, 6)
        self.predictions_table.setHorizontalHeaderLabels(["Ejemplo", "Split", "Label real", "Predicción", "Score", "Correcto"])

        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)

        actions = QHBoxLayout()
        for widget in (
            self.validate_button,
            self.train_button,
            self.refresh_button,
            self.activate_button,
            self.deactivate_button,
            self.retire_button,
            self.verify_button,
            self.delete_artifact_button,
            self.export_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Personalization Models")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Entrenamiento baseline interpretable por creador, con activacion explicita.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.readiness_label)
        layout.addWidget(self.model_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Runs"))
        layout.addWidget(self.runs_table)
        layout.addWidget(QLabel("Metrics"))
        layout.addWidget(self.metrics_table)
        layout.addWidget(QLabel("Predictions"))
        layout.addWidget(self.predictions_table)
        layout.addWidget(QLabel("Detalle tecnico"))
        layout.addWidget(self.detail)

        self.validate_button.clicked.connect(self._validate_snapshot)
        self.train_button.clicked.connect(self._train)
        self.refresh_button.clicked.connect(self.refresh)
        self.activate_button.clicked.connect(self._activate)
        self.deactivate_button.clicked.connect(self._deactivate)
        self.retire_button.clicked.connect(self._retire)
        self.verify_button.clicked.connect(self._verify)
        self.delete_artifact_button.clicked.connect(self._delete_artifact)
        self.export_button.clicked.connect(self._export)

        self._update_action_state()

    def _selected_creator_id(self) -> str | None:
        creator = self.workspace.selected_creator()
        return creator.id if creator else None

    def _selected_run_id(self) -> str | None:
        rows = self.runs_table.selectionModel().selectedRows() if self.runs_table.selectionModel() else []
        if not rows:
            return None
        item = self.runs_table.item(rows[0].row(), 7)
        return item.text() if item else None

    def _selected_snapshot_id(self):
        run_id = self._selected_run_id()
        if not run_id:
            return None
        run = self.workspace.get_training_run(run_id)
        return run.snapshot_id if run else None

    def _latest_snapshot_id(self) -> str | None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            return None
        try:
            report = self.workspace.get_latest_creator_dataset(creator_id)
        except Exception:
            return None
        snapshot = getattr(report, "snapshot", None)
        return snapshot.id if snapshot is not None else None

    def _update_action_state(self) -> None:
        enabled = self.workspace.model_service is not None and self._selected_creator_id() is not None
        for button in (
            self.validate_button,
            self.train_button,
            self.refresh_button,
            self.activate_button,
            self.deactivate_button,
            self.retire_button,
            self.verify_button,
            self.delete_artifact_button,
            self.export_button,
        ):
            button.setEnabled(enabled)

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None or self.workspace.model_service is None:
            self.status_label.setText("Selecciona un creador para entrenar modelos.")
            self.summary_label.setText("Sin modelo activo.")
            self.readiness_label.setText("Readiness: no disponible")
            self.model_label.setText("Modelo activo: ninguno")
            self.runs_table.setRowCount(0)
            self.metrics_table.setRowCount(0)
            self.predictions_table.setRowCount(0)
            self.detail.clear()
            self._update_action_state()
            return

        readiness = self.workspace.get_creator_readiness(creator_id)
        self.readiness_label.setText(f"Readiness: {readiness.readiness_status.value} ({readiness.readiness_score:.3f})")
        active = self.workspace.get_active_creator_model(creator_id, project_id=self.workspace.selected_project_id)
        if active is None:
            self.model_label.setText("Modelo activo: ninguno")
        else:
            self.model_label.setText(
                f"Modelo activo: {active.registry_entry.model_name} | Estado: {active.registry_entry.status.value}"
            )
        runs = self.workspace.list_creator_training_runs(creator_id)
        self.status_label.setText(f"Training runs: {len(runs)}")
        self.summary_label.setText("Historial de entrenamiento y evaluación del baseline personalizado.")
        self.runs_table.setRowCount(0)
        for row_index, run in enumerate(runs):
            self.runs_table.insertRow(row_index)
            values = [
                run.id,
                run.status.value,
                run.model_version,
                str(run.train_count),
                str(run.validation_count),
                str(run.test_count),
                run.decision_threshold,
                run.id,
            ]
            for column, value in enumerate(values):
                self.runs_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        if runs:
            self.runs_table.selectRow(0)
            self._load_run(runs[0].id)
        else:
            self.metrics_table.setRowCount(0)
            self.predictions_table.setRowCount(0)
            self.detail.setPlainText("No hay training runs todavia.")
        self._update_action_state()

    def _load_run(self, run_id: str) -> None:
        run = self.workspace.get_training_run(run_id)
        metrics = self.workspace.get_training_metrics(run_id)
        predictions = self.workspace.list_training_predictions(run_id)
        detail = {
            "run": run.to_dict() if run else None,
            "metrics": [metric.to_dict() for metric in metrics],
            "predictions": [prediction.to_dict() for prediction in predictions],
        }
        self.detail.setPlainText(json.dumps(detail, ensure_ascii=False, indent=2))
        self.metrics_table.setRowCount(0)
        for row_index, metric in enumerate(metrics):
            self.metrics_table.insertRow(row_index)
            values = [metric.split_name, metric.metric_name, f"{metric.metric_value:.6f}" if metric.metric_value is not None else "null", str(metric.support)]
            for column, value in enumerate(values):
                self.metrics_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.predictions_table.setRowCount(0)
        for row_index, prediction in enumerate(predictions):
            self.predictions_table.insertRow(row_index)
            values = [
                prediction.dataset_example_id,
                prediction.split_name,
                prediction.true_label,
                prediction.predicted_label,
                f"{prediction.positive_score:.6f}",
                "si" if prediction.is_correct else "no",
            ]
            for column, value in enumerate(values):
                self.predictions_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _selection_changed(self) -> None:
        run_id = self._selected_run_id()
        if run_id:
            self._load_run(run_id)

    def _start_thread(self, action: str, snapshot_id: str, *, force: bool = False) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        thread = ModelTrainingThread(self.workspace, snapshot_id, action=action, force=force)
        thread.result_ready.connect(self._thread_finished)
        thread.error_ready.connect(self._thread_failed)
        thread.progress_ready.connect(self._thread_progress)
        self._thread = thread
        self.phase_label.setText("Procesando")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._update_action_state()
        thread.start()

    def _thread_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(str(phase))
        self.progress_bar.setValue(int(max(0.0, min(1.0, ratio)) * 100))
        self.progress_label.setText(f"{int(max(0.0, min(1.0, ratio)) * 100)}%")

    def _thread_failed(self, message: str) -> None:
        self.phase_label.setText("Error")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self._thread = None
        self._update_action_state()
        QMessageBox.critical(self, "Personalization Models", message)

    def _thread_finished(self, result) -> None:
        self.phase_label.setText("Completado")
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._thread = None
        self.refresh()
        if result is not None:
            self.detail.setPlainText(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    def _validate_snapshot(self) -> None:
        snapshot_id = self._latest_snapshot_id()
        if snapshot_id is None:
            QMessageBox.information(self, "Personalization Models", "No hay snapshot disponible para validar.")
            return
        self._start_thread("validate", snapshot_id)

    def _train(self) -> None:
        snapshot_id = self._latest_snapshot_id()
        if snapshot_id is None:
            QMessageBox.information(self, "Personalization Models", "No hay snapshot disponible para entrenar.")
            return
        self._start_thread("train", snapshot_id, force=False)

    def _activate(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            entry = self.workspace.activate_model(run_id)
        except DomainError as exc:
            QMessageBox.critical(self, "Personalization Models", str(exc))
            return
        self.detail.setPlainText(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        self.refresh()

    def _deactivate(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            entry = self.workspace.deactivate_model(run_id)
        except DomainError as exc:
            QMessageBox.critical(self, "Personalization Models", str(exc))
            return
        if entry is not None:
            self.detail.setPlainText(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        self.refresh()

    def _retire(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            entry = self.workspace.retire_model(run_id)
        except DomainError as exc:
            QMessageBox.critical(self, "Personalization Models", str(exc))
            return
        if entry is not None:
            self.detail.setPlainText(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2))
        self.refresh()

    def _verify(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            report = self.workspace.verify_model_artifact(run_id)
        except DomainError as exc:
            QMessageBox.critical(self, "Personalization Models", str(exc))
            return
        self.detail.setPlainText(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))

    def _delete_artifact(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            deleted = self.workspace.delete_model_artifact(run_id)
        except DomainError as exc:
            QMessageBox.critical(self, "Personalization Models", str(exc))
            return
        QMessageBox.information(self, "Personalization Models", "Artefacto eliminado" if deleted else "No existia artefacto local")
        self.refresh()

    def _export(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        run = self.workspace.get_training_run(run_id)
        metrics = self.workspace.get_training_metrics(run_id)
        predictions = self.workspace.list_training_predictions(run_id)
        payload = {
            "run": run.to_dict() if run else None,
            "metrics": [metric.to_dict() for metric in metrics],
            "predictions": [prediction.to_dict() for prediction in predictions],
        }
        self.detail.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
