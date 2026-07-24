"""Vista de Experiments and Verifiable Learning."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from .learning_memory_view import LearningMemoryView


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class ExperimentsView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.tabs = QTabWidget()
        self.overview_tab = QWidget()
        self.recommendations_tab = QWidget()
        self.experiments_tab = QWidget()
        self.assignments_tab = QWidget()
        self.evaluations_tab = QWidget()
        self.learning_tab = LearningMemoryView(workspace)
        self.reports_tab = QWidget()
        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.recommendations_tab, "Recommendations")
        self.tabs.addTab(self.experiments_tab, "Experiments")
        self.tabs.addTab(self.assignments_tab, "Assignments")
        self.tabs.addTab(self.evaluations_tab, "Evaluations")
        self.tabs.addTab(self.learning_tab, "Learning Memory")
        self.tabs.addTab(self.reports_tab, "Reports")
        self._build_overview_tab()
        self._build_recommendations_tab()
        self._build_experiments_tab()
        self._build_assignments_tab()
        self._build_evaluations_tab()
        self._build_reports_tab()

        title = QLabel("Experiments & Learning")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Registro verificable de recomendaciones, ejecucion real, evaluacion y memoria de aprendizaje.")
        subtitle.setObjectName("MutedLabel")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)

        header = QHBoxLayout()
        header.addWidget(QLabel("Creador activo:"))
        self.creator_label = QLabel("ninguno")
        self.creator_label.setObjectName("MutedLabel")
        header.addWidget(self.creator_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(header)
        layout.addWidget(self.tabs)

        self.refresh()

    def _build_overview_tab(self) -> None:
        self.overview_counts = {
            "experiments": QLabel("0"),
            "recommendations": QLabel("0"),
            "evaluations": QLabel("0"),
            "learnings": QLabel("0"),
        }
        grid = QGridLayout(self.overview_tab)
        grid.addWidget(QLabel("Experimentos"), 0, 0)
        grid.addWidget(self.overview_counts["experiments"], 0, 1)
        grid.addWidget(QLabel("Recomendaciones"), 0, 2)
        grid.addWidget(self.overview_counts["recommendations"], 0, 3)
        grid.addWidget(QLabel("Evaluaciones"), 1, 0)
        grid.addWidget(self.overview_counts["evaluations"], 1, 1)
        grid.addWidget(QLabel("Aprendizajes"), 1, 2)
        grid.addWidget(self.overview_counts["learnings"], 1, 3)
        self.overview_table = QTableWidget(0, 5)
        self.overview_table.setHorizontalHeaderLabels(["Tipo", "Titulo", "Estado", "Confianza", "ID"])
        self.overview_table.setColumnHidden(4, True)
        grid.addWidget(self.overview_table, 2, 0, 1, 4)

    def _build_recommendations_tab(self) -> None:
        self.recommendations_table = QTableWidget(0, 7)
        self.recommendations_table.setHorizontalHeaderLabels(["Titulo", "Tipo", "Fuente", "Confianza", "Decision", "Evidencia", "ID"])
        self.recommendations_table.setColumnHidden(6, True)
        self.recommendation_title = QLineEdit()
        self.recommendation_title.setPlaceholderText("Titulo")
        self.recommendation_text = QLineEdit()
        self.recommendation_text.setPlaceholderText("Recomendacion")
        self.recommendation_source_type = QLineEdit()
        self.recommendation_source_type.setPlaceholderText("Source type")
        self.recommendation_type = QComboBox()
        self.recommendation_type.addItems([
            "content_structure",
            "hook",
            "duration",
            "publication_timing",
            "title_direction",
            "thumbnail_direction",
            "copy",
            "caption",
            "text_overlay",
            "clip_selection",
            "platform_adaptation",
            "pacing",
            "call_to_action",
            "other",
        ])
        self.recommendation_confidence = QComboBox()
        self.recommendation_confidence.addItems(["very_low", "low", "medium", "high"])
        self.recommendation_create = QPushButton("Crear recomendacion")
        self.recommendation_decision = QComboBox()
        self.recommendation_decision.addItems(["accepted", "accepted_with_changes", "rejected", "postponed", "not_applicable", "needs_more_data"])
        self.recommendation_decide = QPushButton("Registrar decision")
        self.recommendation_create.clicked.connect(self._create_recommendation)
        self.recommendation_decide.clicked.connect(self._decide_recommendation)
        controls = QGridLayout()
        controls.addWidget(QLabel("Titulo"), 0, 0)
        controls.addWidget(self.recommendation_title, 0, 1)
        controls.addWidget(QLabel("Tipo"), 0, 2)
        controls.addWidget(self.recommendation_type, 0, 3)
        controls.addWidget(QLabel("Fuente"), 1, 0)
        controls.addWidget(self.recommendation_source_type, 1, 1)
        controls.addWidget(QLabel("Confianza"), 1, 2)
        controls.addWidget(self.recommendation_confidence, 1, 3)
        controls.addWidget(QLabel("Recomendacion"), 2, 0)
        controls.addWidget(self.recommendation_text, 2, 1, 1, 3)
        controls.addWidget(self.recommendation_create, 3, 0)
        controls.addWidget(QLabel("Decision"), 3, 1)
        controls.addWidget(self.recommendation_decision, 3, 2)
        controls.addWidget(self.recommendation_decide, 3, 3)
        layout = QVBoxLayout(self.recommendations_tab)
        layout.addLayout(controls)
        layout.addWidget(self.recommendations_table)

    def _build_experiments_tab(self) -> None:
        self.experiments_table = QTableWidget(0, 8)
        self.experiments_table.setHorizontalHeaderLabels(["Nombre", "Tipo", "Plataforma", "Metrica", "Direccion", "Muestra", "Estado", "ID"])
        self.experiments_table.setColumnHidden(7, True)
        self.experiment_name = QLineEdit()
        self.experiment_description = QLineEdit()
        self.experiment_description.setPlaceholderText("Descripcion")
        self.experiment_type = QComboBox()
        self.experiment_type.addItems([
            "single_variable_test",
            "before_after_observation",
            "cohort_comparison",
            "sequential_test",
            "manual_observation",
        ])
        self.experiment_platform = QLineEdit()
        self.experiment_content_type = QLineEdit()
        self.experiment_hypothesis = QLineEdit()
        self.experiment_rationale = QLineEdit()
        self.experiment_primary_metric = QLineEdit()
        self.experiment_expected_direction = QComboBox()
        self.experiment_expected_direction.addItems(["up", "down"])
        self.experiment_sample = QLineEdit(str(self.workspace.ui_state.minimum_experiment_sample))
        self.experiment_create = QPushButton("Crear experimento")
        self.experiment_evaluate = QPushButton("Evaluar")
        self.experiment_archive = QPushButton("Archivar")
        self.experiment_create.clicked.connect(self._create_experiment)
        self.experiment_evaluate.clicked.connect(self._evaluate_experiment)
        self.experiment_archive.clicked.connect(self._archive_experiment)
        controls = QGridLayout()
        controls.addWidget(QLabel("Nombre"), 0, 0)
        controls.addWidget(self.experiment_name, 0, 1)
        controls.addWidget(QLabel("Tipo"), 0, 2)
        controls.addWidget(self.experiment_type, 0, 3)
        controls.addWidget(QLabel("Plataforma"), 1, 0)
        controls.addWidget(self.experiment_platform, 1, 1)
        controls.addWidget(QLabel("content_type"), 1, 2)
        controls.addWidget(self.experiment_content_type, 1, 3)
        controls.addWidget(QLabel("Hipotesis"), 2, 0)
        controls.addWidget(self.experiment_hypothesis, 2, 1, 1, 3)
        controls.addWidget(QLabel("Rationale"), 3, 0)
        controls.addWidget(self.experiment_rationale, 3, 1, 1, 3)
        controls.addWidget(QLabel("Metrica primaria"), 4, 0)
        controls.addWidget(self.experiment_primary_metric, 4, 1)
        controls.addWidget(QLabel("Direccion"), 4, 2)
        controls.addWidget(self.experiment_expected_direction, 4, 3)
        controls.addWidget(QLabel("Muestra minima"), 5, 0)
        controls.addWidget(self.experiment_sample, 5, 1)
        controls.addWidget(self.experiment_create, 6, 0)
        controls.addWidget(self.experiment_evaluate, 6, 1)
        controls.addWidget(self.experiment_archive, 6, 2)
        layout = QVBoxLayout(self.experiments_tab)
        layout.addLayout(controls)
        layout.addWidget(self.experiments_table)

    def _build_assignments_tab(self) -> None:
        self.assignments_table = QTableWidget(0, 7)
        self.assignments_table.setHorizontalHeaderLabels(["Experimento", "Publicacion", "Planeada", "Real", "Estado", "Notas", "ID"])
        self.assignments_table.setColumnHidden(6, True)
        self.assignment_publication = QComboBox()
        self.assignment_variant = QComboBox()
        self.assignment_variant.addItems(["control", "treatment", "treatment_a", "treatment_b"])
        self.assignment_actual = QLineEdit()
        self.assignment_notes = QLineEdit()
        self.assignment_create = QPushButton("Asignar")
        self.assignment_create.clicked.connect(self._assign_publication)
        controls = QGridLayout()
        controls.addWidget(QLabel("Publicacion"), 0, 0)
        controls.addWidget(self.assignment_publication, 0, 1)
        controls.addWidget(QLabel("Variante"), 0, 2)
        controls.addWidget(self.assignment_variant, 0, 3)
        controls.addWidget(QLabel("Variante real"), 1, 0)
        controls.addWidget(self.assignment_actual, 1, 1)
        controls.addWidget(QLabel("Notas"), 1, 2)
        controls.addWidget(self.assignment_notes, 1, 3)
        controls.addWidget(self.assignment_create, 2, 0)
        layout = QVBoxLayout(self.assignments_tab)
        layout.addLayout(controls)
        layout.addWidget(self.assignments_table)

    def _build_evaluations_tab(self) -> None:
        self.evaluations_table = QTableWidget(0, 8)
        self.evaluations_table.setHorizontalHeaderLabels(["Estado", "Muestra", "Control", "Treatment", "Dif", "Confianza", "Metrica", "ID"])
        self.evaluations_table.setColumnHidden(7, True)
        self.evaluations_detail = QLabel("Selecciona una evaluacion.")
        self.evaluations_detail.setWordWrap(True)
        self.evaluation_generate = QPushButton("Evaluar experimento")
        self.evaluation_generate.clicked.connect(self._evaluate_selected)
        layout = QVBoxLayout(self.evaluations_tab)
        layout.addWidget(self.evaluation_generate)
        layout.addWidget(self.evaluations_detail)
        layout.addWidget(self.evaluations_table)

    def _build_reports_tab(self) -> None:
        self.reports_table = QTableWidget(0, 6)
        self.reports_table.setHorizontalHeaderLabels(["Titulo", "Estado", "Evaluacion", "Creado", "Resumen", "ID"])
        self.reports_table.setColumnHidden(5, True)
        self.report_export_json = QPushButton("Exportar JSON")
        self.report_export_txt = QPushButton("Exportar TXT")
        self.report_export_csv = QPushButton("Exportar CSV")
        self.report_export_json.clicked.connect(lambda: self._export_report("json"))
        self.report_export_txt.clicked.connect(lambda: self._export_report("txt"))
        self.report_export_csv.clicked.connect(lambda: self._export_report("csv"))
        self.report_items = QTableWidget(0, 4)
        self.report_items.setHorizontalHeaderLabels(["Seccion", "Titulo", "Tipo", "Body"])
        layout = QVBoxLayout(self.reports_tab)
        buttons = QHBoxLayout()
        for widget in (self.report_export_json, self.report_export_txt, self.report_export_csv):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(self.reports_table)
        layout.addWidget(self.report_items)

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        self.creator_label.setText(str(creator_id or "ninguno"))
        if not creator_id:
            self._clear_all()
            return
        experiments = self.workspace.list_experiments(creator_id)
        recommendations = self.workspace.list_recommendations(creator_id)
        evaluations = [evaluation for experiment in experiments for evaluation in self.workspace.list_experiment_evaluations(experiment.id)]
        learnings = self.workspace.list_learnings(creator_id)
        reports = self.workspace.list_experiment_reports(creator_id)
        self.overview_counts["experiments"].setText(str(len(experiments)))
        self.overview_counts["recommendations"].setText(str(len(recommendations)))
        self.overview_counts["evaluations"].setText(str(len(evaluations)))
        self.overview_counts["learnings"].setText(str(len(learnings)))
        self._refresh_overview(experiments, recommendations, evaluations, learnings)
        self._refresh_recommendations(recommendations)
        self._refresh_experiments(experiments)
        self._refresh_assignments(experiments)
        self._refresh_evaluations(evaluations)
        self._refresh_reports(reports)
        self.learning_tab.refresh()

    def _clear_all(self) -> None:
        for table in (
            self.overview_table,
            self.recommendations_table,
            self.experiments_table,
            self.assignments_table,
            self.evaluations_table,
            self.reports_table,
            self.report_items,
        ):
            table.setRowCount(0)

    def _refresh_overview(self, experiments, recommendations, evaluations, learnings) -> None:
        self.overview_table.setRowCount(0)
        rows = []
        rows.extend(("Experiment", experiment.name, experiment.status.value, experiment.experiment_type.value, experiment.id) for experiment in experiments[:5])
        rows.extend(("Recommendation", recommendation.title, recommendation.status, recommendation.recommendation_type.value, recommendation.id) for recommendation in recommendations[:5])
        rows.extend(("Evaluation", evaluation.primary_metric_key, evaluation.evaluation_status.value, evaluation.confidence_level.value, evaluation.id) for evaluation in evaluations[:5])
        rows.extend(("Learning", learning.statement, learning.status.value, learning.confidence_level.value, learning.id) for learning in learnings[:5])
        for row_index, row_values in enumerate(rows):
            self.overview_table.insertRow(row_index)
            for column, value in enumerate(row_values):
                self.overview_table.setItem(row_index, column, _item(value))
        self.overview_table.resizeColumnsToContents()

    def _refresh_recommendations(self, recommendations) -> None:
        self.recommendations_table.setRowCount(0)
        for row_index, recommendation in enumerate(recommendations):
            decision = recommendation.status
            decisions = self.workspace.list_recommendation_decisions(recommendation.id)
            decision_text = decisions[0].decision.value if decisions else ""
            self.recommendations_table.insertRow(row_index)
            values = [recommendation.title, recommendation.recommendation_type.value, recommendation.source_type, recommendation.confidence_level.value, decision_text or decision, recommendation.evidence_json[:80], recommendation.id]
            for column, value in enumerate(values):
                self.recommendations_table.setItem(row_index, column, _item(value))
        self.recommendations_table.resizeColumnsToContents()

    def _refresh_experiments(self, experiments) -> None:
        self.experiments_table.setRowCount(0)
        self.assignment_publication.blockSignals(True)
        self.assignment_publication.clear()
        publications = self.workspace.list_analytics_publications(self.workspace.selected_creator_id) if self.workspace.selected_creator_id else []
        for publication in publications:
            self.assignment_publication.addItem(publication.title, publication.id)
        self.assignment_publication.blockSignals(False)
        for row_index, experiment in enumerate(experiments):
            self.experiments_table.insertRow(row_index)
            values = [
                experiment.name,
                experiment.experiment_type.value,
                experiment.platform or "",
                experiment.primary_metric_key,
                experiment.expected_direction,
                experiment.minimum_sample_size,
                experiment.status.value,
                experiment.id,
            ]
            for column, value in enumerate(values):
                self.experiments_table.setItem(row_index, column, _item(value))
        self.experiments_table.resizeColumnsToContents()

    def _refresh_assignments(self, experiments) -> None:
        self.assignments_table.setRowCount(0)
        experiment_id = self._selected_experiment_id()
        if not experiment_id and experiments:
            experiment_id = experiments[0].id
        assignments = self.workspace.list_experiment_assignments(experiment_id) if experiment_id else []
        for row_index, assignment in enumerate(assignments):
            self.assignments_table.insertRow(row_index)
            values = [
                assignment.experiment_id,
                assignment.publication_id or "",
                assignment.planned_variant,
                assignment.actual_variant or "",
                assignment.assignment_status,
                assignment.notes,
                assignment.id,
            ]
            for column, value in enumerate(values):
                self.assignments_table.setItem(row_index, column, _item(value))
        self.assignments_table.resizeColumnsToContents()

    def _refresh_evaluations(self, evaluations) -> None:
        self.evaluations_table.setRowCount(0)
        for row_index, evaluation in enumerate(evaluations):
            self.evaluations_table.insertRow(row_index)
            values = [
                evaluation.evaluation_status.value,
                evaluation.sample_size,
                evaluation.control_result,
                evaluation.treatment_result,
                evaluation.absolute_difference,
                evaluation.confidence_level.value,
                evaluation.primary_metric_key,
                evaluation.id,
            ]
            for column, value in enumerate(values):
                self.evaluations_table.setItem(row_index, column, _item(value))
        self.evaluations_table.resizeColumnsToContents()

    def _refresh_reports(self, reports) -> None:
        self.reports_table.setRowCount(0)
        for row_index, report in enumerate(reports):
            self.reports_table.insertRow(row_index)
            values = [
                report.title,
                report.status,
                report.evaluation_id or "",
                report.created_at.isoformat(),
                report.summary,
                report.id,
            ]
            for column, value in enumerate(values):
                self.reports_table.setItem(row_index, column, _item(value))
        self.reports_table.resizeColumnsToContents()

    def _selected_experiment_id(self) -> str | None:
        row = self.experiments_table.currentRow()
        if row < 0:
            return None
        item = self.experiments_table.item(row, 7)
        return item.text() if item else None

    def _selected_recommendation_id(self) -> str | None:
        row = self.recommendations_table.currentRow()
        if row < 0:
            return None
        item = self.recommendations_table.item(row, 6)
        return item.text() if item else None

    def _selected_report_id(self) -> str | None:
        row = self.reports_table.currentRow()
        if row < 0:
            return None
        item = self.reports_table.item(row, 5)
        return item.text() if item else None

    def _selected_evaluation_id(self) -> str | None:
        row = self.evaluations_table.currentRow()
        if row < 0:
            return None
        item = self.evaluations_table.item(row, 7)
        return item.text() if item else None

    def _create_recommendation(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "Experiments", "Selecciona un creador.")
            return
        recommendation = self.workspace.create_recommendation(
            creator_id=str(creator_id),
            source_type=self.recommendation_source_type.text().strip() or "manual",
            source_id=None,
            recommendation_type=self.recommendation_type.currentText(),
            title=self.recommendation_title.text().strip() or "Recomendacion manual",
            recommendation_text=self.recommendation_text.text().strip() or "Sin texto",
            evidence_json=json.dumps({"source": "manual"}, ensure_ascii=False),
            confidence_level=self.recommendation_confidence.currentText(),
        )
        self.recommendation_title.clear()
        self.recommendation_text.clear()
        QMessageBox.information(self, "Experiments", f"Recomendacion creada: {recommendation.title}")
        self.refresh()

    def _decide_recommendation(self) -> None:
        recommendation_id = self._selected_recommendation_id()
        if not recommendation_id:
            return
        self.workspace.decide_recommendation(
            recommendation_id,
            decision=self.recommendation_decision.currentText(),
            reason=self.recommendation_decision.currentText(),
        )
        self.refresh()

    def _create_experiment(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "Experiments", "Selecciona un creador.")
            return
        experiment = self.workspace.create_experiment(
            creator_id=str(creator_id),
            name=self.experiment_name.text().strip() or "Experimento manual",
            description=self.experiment_description.text().strip() or "Creado desde la GUI.",
            experiment_type=self.experiment_type.currentText(),
            hypothesis=self.experiment_hypothesis.text().strip() or "Hipotesis manual.",
            rationale=self.experiment_rationale.text().strip() or "Rationale manual.",
            primary_metric_key=self.experiment_primary_metric.text().strip() or "views",
            expected_direction=self.experiment_expected_direction.currentText(),
            minimum_sample_size=int(self.experiment_sample.text().strip() or self.workspace.ui_state.minimum_experiment_sample),
            platform=self.experiment_platform.text().strip() or None,
            content_type=self.experiment_content_type.text().strip() or None,
        )
        self.experiment_name.clear()
        self.experiment_description.clear()
        self.experiment_hypothesis.clear()
        self.experiment_rationale.clear()
        self.experiment_primary_metric.clear()
        QMessageBox.information(self, "Experiments", f"Experimento creado: {experiment.name}")
        self.refresh()

    def _evaluate_experiment(self) -> None:
        experiment_id = self._selected_experiment_id()
        if not experiment_id:
            QMessageBox.information(self, "Experiments", "Selecciona un experimento.")
            return
        evaluation = self.workspace.evaluate_experiment(experiment_id)
        QMessageBox.information(self, "Experiments", f"Evaluacion completada: {evaluation.evaluation_status.value}")
        self.refresh()

    def _archive_experiment(self) -> None:
        experiment_id = self._selected_experiment_id()
        if not experiment_id:
            return
        self.workspace.archive_experiment(experiment_id)
        self.refresh()

    def _assign_publication(self) -> None:
        experiment_id = self._selected_experiment_id()
        publication_id = self.assignment_publication.currentData()
        if not experiment_id or not publication_id:
            QMessageBox.information(self, "Experiments", "Selecciona experimento y publicacion.")
            return
        self.workspace.assign_experiment_publication(
            experiment_id=str(experiment_id),
            publication_id=str(publication_id),
            variant=self.assignment_variant.currentText(),
            actual_variant=self.assignment_actual.text().strip() or None,
            notes=self.assignment_notes.text().strip(),
        )
        self.assignment_actual.clear()
        self.assignment_notes.clear()
        self.refresh()

    def _evaluate_selected(self) -> None:
        experiment_id = self._selected_experiment_id()
        if not experiment_id:
            return
        evaluation = self.workspace.evaluate_experiment(experiment_id)
        QMessageBox.information(self, "Experiments", f"Evaluacion: {evaluation.evaluation_status.value}")
        self.refresh()

    def _export_report(self, format_name: str) -> None:
        report_id = self._selected_report_id()
        if not report_id:
            return
        path = self.workspace.export_experiment_report(report_id, format_name)
        QMessageBox.information(self, "Experiments", f"Reporte exportado: {path}")
