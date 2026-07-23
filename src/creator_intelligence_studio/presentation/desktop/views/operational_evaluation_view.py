"""Vista de evaluacion operativa end-to-end."""

from __future__ import annotations

import json

from PySide6.QtCore import QThread, Signal
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
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class EvaluationRunThread(QThread):
    result_ready = Signal(object)
    error_ready = Signal(str)
    progress_ready = Signal(str, float)

    def __init__(self, workspace: WorkspaceViewModel, scenario_id: str, *, force: bool = False) -> None:
        super().__init__()
        self.workspace = workspace
        self.scenario_id = scenario_id
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            result = self.workspace.run_operational_evaluation(
                self.scenario_id,
                force=self.force,
                progress_callback=lambda progress: self.progress_ready.emit(progress.stage_name, float(progress.ratio or 0.0)),
            )
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(result)


class OperationalEvaluationView(QWidget):
    """Vista tecnica para observabilidad end-to-end."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._thread: EvaluationRunThread | None = None

        self.scenario_combo = QComboBox()
        self.refresh_button = QPushButton("Actualizar")
        self.run_button = QPushButton("Ejecutar escenario")
        self.retry_button = QPushButton("Reintentar etapa")
        self.cancel_button = QPushButton("Cancelar")
        self.export_button = QPushButton("Exportar")
        self.clean_button = QPushButton("Limpiar assets")
        self.compare_button = QPushButton("Comparar runs")
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["Todas", "info", "warning", "error", "critical"])

        self.status_label = QLabel("Sin ejecucion")
        self.status_label.setObjectName("MutedLabel")
        self.summary_label = QLabel("Selecciona un escenario de evaluacion.")
        self.summary_label.setWordWrap(True)
        self.phase_label = QLabel("Listo")
        self.phase_label.setObjectName("MutedLabel")
        self.progress_label = QLabel("0%")
        self.progress_label.setObjectName("MutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.runs_table = QTableWidget(0, 7)
        self.runs_table.setHorizontalHeaderLabels(["Run", "Escenario", "Estado", "Resultado", "Duracion", "Etapas", "ID"])
        self.runs_table.setColumnHidden(6, True)
        self.runs_table.itemSelectionChanged.connect(self._selection_changed)
        self.stages_table = QTableWidget(0, 5)
        self.stages_table.setHorizontalHeaderLabels(["Indice", "Etapa", "Estado", "Duracion", "Cache"])
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Etapa", "Metrica", "Valor", "Unidad"])
        self.assertions_table = QTableWidget(0, 5)
        self.assertions_table.setHorizontalHeaderLabels(["Etapa", "Assertion", "Estado", "Severidad", "Mensaje"])
        self.artifacts_table = QTableWidget(0, 4)
        self.artifacts_table.setHorizontalHeaderLabels(["Etapa", "Tipo", "Ruta", "Existe"])
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)

        actions = QHBoxLayout()
        for widget in (
            self.refresh_button,
            self.run_button,
            self.retry_button,
            self.cancel_button,
            self.export_button,
            self.clean_button,
            self.compare_button,
        ):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Operational Evaluation")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Evaluacion tecnica y auditable del pipeline completo sobre assets de demostracion.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        top = QHBoxLayout()
        top.addWidget(QLabel("Escenario"))
        top.addWidget(self.scenario_combo)
        top.addWidget(QLabel("Severidad"))
        top.addWidget(self.severity_filter)
        top.addStretch(1)
        layout.addLayout(top)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Runs"))
        layout.addWidget(self.runs_table)
        layout.addWidget(QLabel("Stages"))
        layout.addWidget(self.stages_table)
        layout.addWidget(QLabel("Metrics"))
        layout.addWidget(self.metrics_table)
        layout.addWidget(QLabel("Assertions"))
        layout.addWidget(self.assertions_table)
        layout.addWidget(QLabel("Artifacts"))
        layout.addWidget(self.artifacts_table)
        layout.addWidget(QLabel("Detalle"))
        layout.addWidget(self.detail)

        self.refresh_button.clicked.connect(self.refresh)
        self.run_button.clicked.connect(self._run_selected_scenario)
        self.retry_button.clicked.connect(self._retry_stage)
        self.cancel_button.clicked.connect(self._cancel)
        self.export_button.clicked.connect(self._export)
        self.clean_button.clicked.connect(self._clean)
        self.compare_button.clicked.connect(self._compare)
        self.severity_filter.currentTextChanged.connect(self._load_current_run)
        self.scenario_combo.currentIndexChanged.connect(self._scenario_changed)
        self._update_action_state()

    def _selected_run_id(self) -> str | None:
        rows = self.runs_table.selectionModel().selectedRows() if self.runs_table.selectionModel() else []
        if not rows:
            return None
        item = self.runs_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def _selected_scenario_id(self) -> str | None:
        value = self.scenario_combo.currentData()
        return str(value) if value else None

    def _update_action_state(self) -> None:
        enabled = self.workspace.evaluation_service is not None and self._selected_scenario_id() is not None
        for button in (self.run_button, self.retry_button, self.cancel_button, self.export_button, self.clean_button, self.compare_button):
            button.setEnabled(enabled)

    def refresh(self) -> None:
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        self.scenario_combo.addItem("Seleccionar escenario", None)
        for scenario in self.workspace.list_operational_scenarios():
            self.scenario_combo.addItem(f"{scenario.name} ({scenario.id})", scenario.id)
        self.scenario_combo.blockSignals(False)
        if self.scenario_combo.count() > 1 and self.scenario_combo.currentIndex() == 0:
            self.scenario_combo.setCurrentIndex(1)
        self._reload_runs()

    def _reload_runs(self) -> None:
        scenario_id = self._selected_scenario_id()
        if scenario_id is None or self.workspace.evaluation_service is None:
            self.status_label.setText("Sin servicio de evaluacion operativa.")
            self.summary_label.setText("Selecciona un escenario.")
            self.runs_table.setRowCount(0)
            self.stages_table.setRowCount(0)
            self.metrics_table.setRowCount(0)
            self.assertions_table.setRowCount(0)
            self.artifacts_table.setRowCount(0)
            self.detail.clear()
            self._update_action_state()
            return
        runs = [run for run in self.workspace.evaluation_service.list_runs(scenario_id)]
        self.status_label.setText(f"Runs: {len(runs)}")
        self.summary_label.setText("Seguimiento operativo del pipeline end-to-end.")
        self.runs_table.setRowCount(0)
        for row_index, run in enumerate(runs):
            self.runs_table.insertRow(row_index)
            values = [
                run.id,
                run.scenario_id,
                run.status.value,
                run.final_result.value,
                f"{run.total_duration_seconds:.3f}" if run.total_duration_seconds is not None else "n/a",
                str(run.stage_count),
                run.id,
            ]
            for column, value in enumerate(values):
                self.runs_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        if runs:
            self.runs_table.selectRow(0)
            self._load_current_run()
        else:
            self.stages_table.setRowCount(0)
            self.metrics_table.setRowCount(0)
            self.assertions_table.setRowCount(0)
            self.artifacts_table.setRowCount(0)
            self.detail.clear()
        self._update_action_state()

    def _load_current_run(self) -> None:
        run_id = self._selected_run_id()
        if not run_id or self.workspace.evaluation_service is None:
            return
        report = self.workspace.get_operational_evaluation_run(run_id)
        if report is None:
            return
        self.phase_label.setText(report.run.status.value)
        self.progress_bar.setValue(100 if report.run.status.value in {"completed", "completed_with_warnings"} else 0)
        self.progress_label.setText(f"{self.progress_bar.value()}%")
        self.stages_table.setRowCount(0)
        for row_index, stage in enumerate(report.stages):
            self.stages_table.insertRow(row_index)
            values = [stage.stage_index, stage.stage_name, stage.status.value, f"{stage.duration_seconds:.3f}" if stage.duration_seconds is not None else "n/a", stage.cache_status.value]
            for column, value in enumerate(values):
                self.stages_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.metrics_table.setRowCount(0)
        for row_index, metric in enumerate(report.metrics):
            self.metrics_table.insertRow(row_index)
            values = [metric.stage_name or "", metric.metric_name, "" if metric.metric_value is None else f"{metric.metric_value:.6f}", metric.metric_unit or ""]
            for column, value in enumerate(values):
                self.metrics_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.assertions_table.setRowCount(0)
        severities = {self.severity_filter.currentText()} if self.severity_filter.currentText() != "Todas" else None
        assertions = report.assertions
        if severities is not None:
            assertions = [assertion for assertion in assertions if assertion.severity.value in severities]
        for row_index, assertion in enumerate(assertions):
            self.assertions_table.insertRow(row_index)
            values = [assertion.stage_name or "", assertion.assertion_name, assertion.status, assertion.severity.value, assertion.message]
            for column, value in enumerate(values):
                self.assertions_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.artifacts_table.setRowCount(0)
        for row_index, artifact in enumerate(report.artifacts):
            self.artifacts_table.insertRow(row_index)
            values = [artifact.stage_name, artifact.artifact_type, artifact.managed_path, "si" if artifact.exists_at_completion else "no"]
            for column, value in enumerate(values):
                self.artifacts_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.detail.setPlainText(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str))

    def _selection_changed(self) -> None:
        self._load_current_run()

    def _scenario_changed(self) -> None:
        self._update_action_state()
        self._reload_runs()

    def _start_thread(self, scenario_id: str) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        thread = EvaluationRunThread(self.workspace, scenario_id, force=False)
        thread.result_ready.connect(self._thread_finished)
        thread.error_ready.connect(self._thread_failed)
        thread.progress_ready.connect(self._thread_progress)
        self._thread = thread
        self.phase_label.setText("Preparando")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        thread.start()

    def _thread_progress(self, phase: str, ratio: float) -> None:
        self.phase_label.setText(str(phase))
        self.progress_bar.setValue(int(max(0.0, min(1.0, ratio)) * 100))
        self.progress_label.setText(f"{self.progress_bar.value()}%")

    def _thread_failed(self, message: str) -> None:
        self._thread = None
        QMessageBox.critical(self, "Operational Evaluation", message)
        self._reload_runs()

    def _thread_finished(self, result) -> None:
        self._thread = None
        self.phase_label.setText("Completado")
        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self._reload_runs()
        self.detail.setPlainText(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))

    def _run_selected_scenario(self) -> None:
        scenario_id = self._selected_scenario_id()
        if scenario_id is None:
            QMessageBox.information(self, "Operational Evaluation", "No hay escenario seleccionado.")
            return
        self._start_thread(scenario_id)

    def _retry_stage(self) -> None:
        run_id = self._selected_run_id()
        if not run_id or self.workspace.evaluation_service is None:
            return
        run = self.workspace.get_operational_evaluation_run(run_id)
        if run is None:
            return
        try:
            result = self.workspace.retry_operational_evaluation_stage(run_id, "transcribe")
        except Exception as exc:
            QMessageBox.critical(self, "Operational Evaluation", str(exc))
            return
        self.detail.setPlainText(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        self._reload_runs()

    def _cancel(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            cancelled = self.workspace.cancel_operational_evaluation(run_id)
        except Exception as exc:
            QMessageBox.critical(self, "Operational Evaluation", str(exc))
            return
        QMessageBox.information(self, "Operational Evaluation", "Run cancelado" if cancelled else "No habia ejecucion activa")

    def _export(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            path = self.workspace.export_operational_evaluation(run_id, "json")
        except Exception as exc:
            QMessageBox.critical(self, "Operational Evaluation", str(exc))
            return
        QMessageBox.information(self, "Operational Evaluation", f"Reporte exportado a {path}")

    def _clean(self) -> None:
        run_id = self._selected_run_id()
        if not run_id:
            return
        try:
            payload = self.workspace.clean_operational_evaluation(run_id, dry_run=False)
        except Exception as exc:
            QMessageBox.critical(self, "Operational Evaluation", str(exc))
            return
        QMessageBox.information(self, "Operational Evaluation", json.dumps(payload, ensure_ascii=False, indent=2))
        self._reload_runs()

    def _compare(self) -> None:
        rows = self.runs_table.selectionModel().selectedRows() if self.runs_table.selectionModel() else []
        if self.workspace.evaluation_service is None:
            QMessageBox.information(self, "Operational Evaluation", "No hay servicio de evaluacion operativa.")
            return
        if len(rows) >= 2:
            baseline = self.runs_table.item(rows[0].row(), 6)
            candidate = self.runs_table.item(rows[1].row(), 6)
        elif self.runs_table.rowCount() >= 2:
            baseline = self.runs_table.item(0, 6)
            candidate = self.runs_table.item(1, 6)
        else:
            QMessageBox.information(self, "Operational Evaluation", "Se necesitan al menos dos runs para comparar.")
            return
        if baseline is None or candidate is None:
            return
        try:
            comparison = self.workspace.compare_operational_evaluations(baseline.text(), candidate.text())
        except Exception as exc:
            QMessageBox.critical(self, "Operational Evaluation", str(exc))
            return
        self.detail.setPlainText(json.dumps(comparison.to_dict(), ensure_ascii=False, indent=2, default=str))
