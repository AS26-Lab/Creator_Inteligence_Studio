"""Centro global de tareas en segundo plano."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class TaskCenterView(QWidget):
    """Lista tareas persistidas por la interfaz."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.refresh_button = QPushButton("Actualizar")
        self.open_button = QPushButton("Abrir video")
        self.cancel_button = QPushButton("Marcar interrumpida")
        self.retry_button = QPushButton("Reintentar")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Titulo", "Video", "Etapa", "Estado", "Progreso", "Mensaje", "Actualizada", "ID"])
        self.table.setColumnHidden(7, True)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.empty_state = EmptyStateWidget("Sin tareas", "Las tareas activas y persistidas aparecen aqui.")

        title = QLabel("Task Center")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Seguimiento global de tareas en segundo plano y tareas interrumpidas.")
        subtitle.setObjectName("MutedLabel")

        actions = QHBoxLayout()
        for widget in (self.refresh_button, self.open_button, self.cancel_button, self.retry_button):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)

        self.refresh_button.clicked.connect(self.refresh)
        self.open_button.clicked.connect(self._open_video)
        self.cancel_button.clicked.connect(self._interrupt_task)
        self.retry_button.clicked.connect(self._retry_task)

    def _selected_task_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 7)
        return item.text() if item else None

    def _selected_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            return None
        return next((task for task in self.workspace.background_tasks() if task.task_id == task_id), None)

    def _is_delivery_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "subtitle_delivery")

    def _is_analytics_import_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "analytics_import")

    def _is_analytics_lab_analysis_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "analytics_lab_analysis")

    def _is_analytics_lab_report_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "analytics_lab_report")

    def _is_experiment_evaluation_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "experiment_evaluation")

    def _is_experiment_report_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "experiment_report")

    def _is_creator_language_analysis_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_analysis")

    def _is_creator_language_snapshot_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_profile_snapshot")

    def _is_creator_language_export_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_export")

    def refresh(self) -> None:
        tasks = self.workspace.background_tasks()
        self.table.setRowCount(0)
        if not tasks:
            self.table.hide()
            self.empty_state.show()
            self.open_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.retry_button.setEnabled(False)
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, task in enumerate(tasks):
            self.table.insertRow(row_index)
            values = [
                task.title,
                task.video_title or task.video_id or "",
                task.stage_name or "",
                task.status,
                f"{task.progress_percent:.1f}%",
                task.message or task.error or "",
                task.updated_at,
                task.task_id,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self._selection_changed()

    def _selection_changed(self) -> None:
        task = self._selected_task()
        enabled = task is not None
        self.open_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled and bool(getattr(task, "cancellable", True)))
        self.retry_button.setEnabled(enabled)

    def _open_video(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        if self._is_delivery_task(task):
            path = self.workspace.reveal_delivery(task.task_id)
            if path is None:
                QMessageBox.information(self, "Task Center", "La entrega ya no tiene una salida disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Resultado disponible en: {path}")
            return
        if self._is_analytics_import_task(task):
            report = self.workspace.reveal_analytics_import_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "La importacion no tiene un reporte disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte disponible en: {report}")
            return
        if self._is_analytics_lab_report_task(task):
            report = self.workspace.reveal_analytics_lab_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "El reporte no tiene una salida disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte disponible en: {report}")
            return
        if self._is_analytics_lab_analysis_task(task):
            payload = getattr(task, "payload", {})
            run = payload.get("run") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Corrida disponible: {run.get('run_type', '')} / {run.get('status', task.status)}",
            )
            return
        if self._is_experiment_report_task(task):
            report = self.workspace.reveal_experiment_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "El reporte de experimento no tiene una salida disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte de experimento disponible en: {report}")
            return
        if self._is_creator_language_analysis_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Analisis de lenguaje: {payload.get('corpus_id', task.task_id)} / {task.status}")
            return
        if self._is_creator_language_snapshot_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Snapshot de lenguaje: {payload.get('creator_id', task.task_id)} / {task.status}")
            return
        if self._is_creator_language_export_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Export de lenguaje: {payload.get('format', task.task_id)} / {task.status}")
            return
        if self._is_experiment_evaluation_task(task):
            payload = getattr(task, "payload", {})
            experiment = payload.get("experiment") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Evaluacion de experimento: {experiment.get('name', task.video_title or task.task_id)} / {task.status}",
            )
            return
        if task.video_id is None:
            return
        self.workspace.select_video(task.video_id)
        QMessageBox.information(self, "Task Center", f"Video seleccionado: {task.video_title or task.video_id}")

    def _interrupt_task(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        if self._is_delivery_task(task):
            self.workspace.cancel_delivery(task.task_id)
        elif self._is_analytics_import_task(task):
            self.workspace.cancel_analytics_import(task.task_id)
        elif self._is_analytics_lab_analysis_task(task) or self._is_analytics_lab_report_task(task) or self._is_experiment_evaluation_task(task) or self._is_experiment_report_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif self._is_creator_language_analysis_task(task) or self._is_creator_language_snapshot_task(task) or self._is_creator_language_export_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif task.title == "Render de clip":
            self.workspace.cancel_render(task.task_id)
        else:
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        self.refresh()

    def _retry_task(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        if task.video_id:
            self.workspace.select_video(task.video_id)
        if self._is_delivery_task(task):
            self.workspace.retry_delivery(task.task_id)
            self.refresh()
            return
        if self._is_analytics_import_task(task):
            self.workspace.retry_analytics_import(task.task_id)
            self.refresh()
            return
        if self._is_analytics_lab_analysis_task(task):
            payload = getattr(task, "payload", {})
            run = payload.get("run") or {}
            cohort_id = payload.get("cohort_id") or run.get("cohort_id")
            run_type = payload.get("run_type") or run.get("run_type")
            publication_id = payload.get("publication_id")
            if cohort_id and run_type == "publication_comparison" and publication_id:
                self.workspace.compare_analytics_publication(str(publication_id), str(cohort_id))
            elif cohort_id:
                self.workspace.analyze_analytics_lab_cohort(str(cohort_id))
            self.refresh()
            return
        if self._is_analytics_lab_report_task(task):
            payload = getattr(task, "payload", {})
            period_start = payload.get("period_start")
            period_end = payload.get("period_end")
            creator_id = payload.get("creator_id") or self.workspace.selected_creator_id
            if creator_id and period_start and period_end:
                self.workspace.generate_analytics_lab_weekly_report(str(creator_id), str(period_start), str(period_end))
            self.refresh()
            return
        if self._is_experiment_evaluation_task(task):
            payload = getattr(task, "payload", {})
            experiment = payload.get("experiment") or {}
            experiment_id = payload.get("experiment_id") or experiment.get("id")
            if experiment_id:
                self.workspace.evaluate_experiment(str(experiment_id))
            self.refresh()
            return
        if self._is_experiment_report_task(task):
            payload = getattr(task, "payload", {})
            experiment_id = payload.get("experiment_id")
            evaluation_id = payload.get("evaluation_id")
            if experiment_id:
                self.workspace.generate_experiment_report(str(experiment_id), str(evaluation_id) if evaluation_id else None)
            self.refresh()
            return
        if self._is_creator_language_analysis_task(task):
            payload = getattr(task, "payload", {})
            corpus_id = payload.get("corpus_id")
            if corpus_id:
                self.workspace.analyze_creator_language_corpus(str(corpus_id), force_recompute=True)
            self.refresh()
            return
        if self._is_creator_language_snapshot_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            if creator_id:
                self.workspace.create_creator_language_profile_snapshot(str(creator_id))
            self.refresh()
            return
        if self._is_creator_language_export_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            format_name = payload.get("format") or "json"
            if creator_id:
                self.workspace.export_creator_language(creator_id=str(creator_id), format_name=str(format_name))
            self.refresh()
            return
        if task.title == "Render de clip":
            self.workspace.retry_render(task.task_id)
            self.refresh()
            return
        QMessageBox.information(self, "Task Center", "Abre el workflow del video para reintentar la etapa.")
