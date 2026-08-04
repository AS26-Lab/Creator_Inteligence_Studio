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

    def _is_ai_runtime_diagnostic_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "ai_runtime_diagnostic")

    def _ai_runtime_task_details(self, task) -> dict[str, str]:
        payload = getattr(task, "payload", {}) if task is not None else {}
        execution_id = str(payload.get("execution_id") or "")
        provider = str(payload.get("provider") or "auto")
        role = str(payload.get("role") or payload.get("model_role") or "provider_diagnostic")
        model = str(payload.get("model_id") or payload.get("model_catalog_id") or "-")
        status = str((payload.get("approval_state") or task.status) if task is not None else "")
        return {
            "execution_id": execution_id,
            "provider": provider,
            "role": role,
            "model": model,
            "status": status,
            "updated_at": str(getattr(task, "updated_at", "") or ""),
            "created_at": str(getattr(task, "created_at", "") or ""),
            "message": str(getattr(task, "message", "") or ""),
        }

    def _is_creator_language_analysis_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_analysis")

    def _is_creator_language_snapshot_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_profile_snapshot")

    def _is_creator_language_export_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "creator_language_export")

    def _is_packaging_title_analysis_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_title_analysis")

    def _is_packaging_thumbnail_analysis_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_thumbnail_analysis")

    def _is_packaging_brand_profile_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_brand_profile")

    def _is_packaging_pair_evaluation_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_pair_evaluation")

    def _is_packaging_frame_candidates_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_frame_candidates")

    def _is_packaging_concept_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_concept_build")

    def _is_packaging_prompt_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_prompt_build")

    def _is_packaging_review_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_thumbnail_review")

    def _is_packaging_export_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "packaging_export")

    def _is_audience_model_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "audience_model_build")

    def _is_youtube_sync_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "youtube_sync")

    def _is_instagram_sync_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "instagram_sync")

    def _is_tiktok_sync_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "tiktok_sync")

    def _is_platform_sync_group_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "platform_sync_group")

    def _is_market_research_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "market_research_run")

    def _is_market_opportunity_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "market_opportunity_candidate")

    def _is_planning_run_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "planning_run")

    def _is_brief_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "brief_run")

    def _is_production_task(self, task) -> bool:
        return bool(getattr(task, "payload", {}).get("kind") == "production_run")

    def _task_video_id(self, task) -> str | None:
        return getattr(task, "video_id", None)

    def _task_video_title(self, task) -> str | None:
        return getattr(task, "video_title", None)

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
            if self._is_ai_runtime_diagnostic_task(task):
                details = self._ai_runtime_task_details(task)
                title = f"AI Provider Diagnostics ({details['provider']})"
                video_value = f"{details['provider']} / {details['model']}"
                stage_value = str(getattr(task, "stage_name", "") or details["status"] or "")
                status_value = str(getattr(task, "status", "") or details["status"] or "")
                message_value = details["message"]
                if details["execution_id"]:
                    message_value = f"{message_value} | execution_id={details['execution_id']}" if message_value else f"execution_id={details['execution_id']}"
                updated_value = f"{getattr(task, 'updated_at', '')} | started {details['created_at']}" if details["created_at"] else str(getattr(task, "updated_at", "") or "")
            else:
                title = task.title
                video_value = self._task_video_title(task) or self._task_video_id(task) or ""
                stage_value = task.stage_name or ""
                status_value = task.status
                message_value = task.message or task.error or ""
                updated_value = task.updated_at
            values = [
                title,
                video_value,
                stage_value,
                status_value,
                f"{task.progress_percent:.1f}%",
                message_value,
                updated_value,
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
        if self._is_ai_runtime_diagnostic_task(task):
            details = self._ai_runtime_task_details(task)
            QMessageBox.information(
                self,
                "Task Center",
                (
                    "Diagnostico IA\n"
                    f"execution_id: {details['execution_id'] or '-'}\n"
                    f"proveedor: {details['provider']}\n"
                    f"modelo: {details['model']}\n"
                    f"estado: {details['status'] or task.status}\n"
                    f"actualizada: {details['updated_at'] or task.updated_at}"
                ),
            )
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
        if self._is_packaging_title_analysis_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Analisis de titulo: {payload.get('title_version_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_thumbnail_analysis_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Analisis de miniatura: {payload.get('thumbnail_version_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_brand_profile_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Brand profile: {payload.get('creator_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_pair_evaluation_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Par evaluado: {payload.get('title_version_id', task.task_id)} / {payload.get('thumbnail_version_id', '')}")
            return
        if self._is_packaging_frame_candidates_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Frames candidatos: {payload.get('video_asset_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_concept_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Concepto: {payload.get('creator_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_prompt_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Prompt: {payload.get('concept_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_review_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Revision de miniatura: {payload.get('thumbnail_version_id', task.task_id)} / {task.status}")
            return
        if self._is_packaging_export_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Export de packaging: {payload.get('format', task.task_id)} / {task.status}")
            return
        if self._is_audience_model_task(task):
            payload = getattr(task, "payload", {})
            QMessageBox.information(self, "Task Center", f"Modelo de audiencia: {payload.get('creator_id', task.task_id)} / {task.status}")
            return
        if self._is_youtube_sync_task(task):
            report = self.workspace.export_youtube_sync_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "La sincronizacion no tiene un reporte disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte de YouTube disponible en: {report}")
            return
        if self._is_instagram_sync_task(task):
            report = self.workspace.export_instagram_sync_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "La sincronizacion no tiene un reporte disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte de Instagram disponible en: {report}")
            return
        if self._is_tiktok_sync_task(task):
            report = self.workspace.export_tiktok_sync_report(task.task_id)
            if report is None:
                QMessageBox.information(self, "Task Center", "La sincronizacion no tiene un reporte disponible.")
            else:
                QMessageBox.information(self, "Task Center", f"Reporte de TikTok disponible en: {report}")
            return
        if self._is_platform_sync_group_task(task):
            payload = getattr(task, "payload", {})
            group = payload.get("group") or {}
            items = payload.get("items") or []
            QMessageBox.information(
                self,
                "Task Center",
                f"Grupo consolidado: {group.get('name', task.task_id)} / {group.get('status', task.status)} / items={len(items)}",
            )
            return
        if self._is_market_research_task(task):
            payload = getattr(task, "payload", {})
            run = payload.get("run") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Investigacion de mercado: {run.get('status', task.status)} / {run.get('discovered_count', 0)} elementos",
            )
            return
        if self._is_market_opportunity_task(task):
            payload = getattr(task, "payload", {})
            candidate = payload.get("candidate") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Candidato de oportunidad: {candidate.get('title', task.task_id)} / {candidate.get('status', task.status)}",
            )
            return
        if self._is_planning_run_task(task):
            payload = getattr(task, "payload", {})
            planning_task = payload.get("planning_task") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Planning: {planning_task.get('plan_id', task.task_id)} / {planning_task.get('status', task.status)}",
            )
            return
        if self._is_brief_task(task):
            payload = getattr(task, "payload", {})
            brief_task = payload.get("brief_task") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Brief: {brief_task.get('title', task.task_id)} / {brief_task.get('status', task.status)}",
            )
            return
        if self._is_production_task(task):
            payload = getattr(task, "payload", {})
            production_task = payload.get("production_task") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Production: {production_task.get('title', task.task_id)} / {production_task.get('status', task.status)}",
            )
            return
        if self._is_experiment_evaluation_task(task):
            payload = getattr(task, "payload", {})
            experiment = payload.get("experiment") or {}
            QMessageBox.information(
                self,
                "Task Center",
                f"Evaluacion de experimento: {experiment.get('name', self._task_video_title(task) or task.task_id)} / {task.status}",
            )
            return
        if self._task_video_id(task) is None:
            return
        self.workspace.select_video(self._task_video_id(task))
        QMessageBox.information(self, "Task Center", f"Video seleccionado: {self._task_video_title(task) or self._task_video_id(task)}")

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
        elif self._is_ai_runtime_diagnostic_task(task):
            details = self._ai_runtime_task_details(task)
            execution_id = details["execution_id"]
            if execution_id:
                self.workspace.ai_runtime_cancel_diagnostic_execution(
                    execution_id,
                    cancelled_by="usuario",
                    cancellation_reason="Cancelada desde Task Center.",
                )
            else:
                self.workspace.interrupt_background_task(task.task_id, "Cancelada desde Task Center")
        elif self._is_creator_language_analysis_task(task) or self._is_creator_language_snapshot_task(task) or self._is_creator_language_export_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif self._is_packaging_title_analysis_task(task) or self._is_packaging_thumbnail_analysis_task(task) or self._is_packaging_brand_profile_task(task) or self._is_packaging_pair_evaluation_task(task) or self._is_packaging_frame_candidates_task(task) or self._is_packaging_concept_task(task) or self._is_packaging_prompt_task(task) or self._is_packaging_review_task(task) or self._is_packaging_export_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif self._is_audience_model_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif self._is_youtube_sync_task(task):
            self.workspace.interrupt_youtube_sync_run(task.task_id, "Interrumpida desde Task Center")
        elif self._is_instagram_sync_task(task):
            self.workspace.interrupt_instagram_sync_run(task.task_id, "Interrumpida desde Task Center")
        elif self._is_tiktok_sync_task(task):
            self.workspace.interrupt_tiktok_sync_run(task.task_id, "Interrumpida desde Task Center")
        elif self._is_planning_run_task(task):
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        elif self._is_brief_task(task):
            if self.workspace.brief_service is not None:
                self.workspace.brief_service.cancel_run(task.task_id)
        elif self._is_production_task(task):
            if self.workspace.production_service is not None:
                self.workspace.production_service.cancel_run(task.task_id)
        elif self._is_platform_sync_group_task(task):
            if self.workspace.platform_service is not None:
                self.workspace.platform_service.cancel_sync(task.task_id)
        elif self._is_market_research_task(task):
            if self.workspace.market_service is not None:
                self.workspace.market_service.cancel_research_run(task.task_id)
        elif task.title == "Render de clip":
            self.workspace.cancel_render(task.task_id)
        else:
            self.workspace.interrupt_background_task(task.task_id, "Interrumpida desde Task Center")
        self.refresh()

    def _retry_task(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        if self._task_video_id(task):
            self.workspace.select_video(self._task_video_id(task))
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
        if self._is_ai_runtime_diagnostic_task(task):
            details = self._ai_runtime_task_details(task)
            provider = details["provider"] if details["provider"] != "auto" else None
            role = details["role"] if details["role"] != "provider_diagnostic" else None
            self.workspace.run_ai_runtime_diagnostic(
                provider=provider,
                role=role,
                cache_policy=str(getattr(task, "payload", {}).get("cache_policy") or "use"),
            )
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
        if self._is_packaging_title_analysis_task(task):
            payload = getattr(task, "payload", {})
            title_version_id = payload.get("title_version_id")
            if title_version_id:
                self.workspace.analyze_packaging_title(str(title_version_id), force_recompute=True)
            self.refresh()
            return
        if self._is_packaging_thumbnail_analysis_task(task):
            payload = getattr(task, "payload", {})
            thumbnail_version_id = payload.get("thumbnail_version_id")
            if thumbnail_version_id:
                self.workspace.analyze_packaging_thumbnail(str(thumbnail_version_id), force_recompute=True)
            self.refresh()
            return
        if self._is_packaging_brand_profile_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            if creator_id:
                self.workspace.build_packaging_brand_profile(str(creator_id))
            self.refresh()
            return
        if self._is_packaging_pair_evaluation_task(task):
            payload = getattr(task, "payload", {})
            title_version_id = payload.get("title_version_id")
            thumbnail_version_id = payload.get("thumbnail_version_id")
            publication_id = payload.get("publication_id")
            if title_version_id and thumbnail_version_id:
                self.workspace.evaluate_packaging_pair(str(title_version_id), str(thumbnail_version_id), publication_id=str(publication_id) if publication_id else None)
            self.refresh()
            return
        if self._is_packaging_frame_candidates_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            video_asset_id = payload.get("video_asset_id")
            timestamps = payload.get("timestamps")
            if creator_id and video_asset_id:
                self.workspace.extract_packaging_frame_candidates(str(creator_id), str(video_asset_id), timestamps=timestamps if isinstance(timestamps, list) else None)
            self.refresh()
            return
        if self._is_packaging_concept_task(task):
            payload = getattr(task, "payload", {})
            kwargs = payload.get("kwargs") or {}
            if isinstance(kwargs, dict) and kwargs.get("creator_id"):
                self.workspace.build_packaging_concepts(**kwargs)
            self.refresh()
            return
        if self._is_packaging_prompt_task(task):
            payload = getattr(task, "payload", {})
            concept_id = payload.get("concept_id")
            target_tool = payload.get("target_tool")
            title = payload.get("title")
            if concept_id and target_tool:
                self.workspace.build_packaging_prompt(concept_id=str(concept_id), target_tool=str(target_tool), title=str(title) if title else None)
            self.refresh()
            return
        if self._is_packaging_review_task(task):
            payload = getattr(task, "payload", {})
            thumbnail_version_id = payload.get("thumbnail_version_id")
            if thumbnail_version_id:
                self.workspace.review_packaging_thumbnail(
                    thumbnail_version_id=str(thumbnail_version_id),
                    title_version_id=str(payload.get("title_version_id")) if payload.get("title_version_id") else None,
                    publication_id=str(payload.get("publication_id")) if payload.get("publication_id") else None,
                    concept_id=str(payload.get("concept_id")) if payload.get("concept_id") else None,
                    prompt_id=str(payload.get("prompt_id")) if payload.get("prompt_id") else None,
                )
            self.refresh()
            return
        if self._is_packaging_export_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            format_name = payload.get("format") or "json"
            summary = bool(payload.get("summary"))
            if creator_id:
                self.workspace.export_packaging(creator_id=str(creator_id), format_name=str(format_name), summary=summary)
            self.refresh()
            return
        if self._is_audience_model_task(task):
            payload = getattr(task, "payload", {})
            creator_id = payload.get("creator_id")
            force = bool(payload.get("force", False))
            configuration = payload.get("configuration")
            if creator_id:
                self.workspace.build_audience_model(str(creator_id), force=force, configuration=configuration if isinstance(configuration, dict) else None)
            self.refresh()
            return
        if self._is_youtube_sync_task(task):
            self.workspace.resume_youtube_sync_run(task.task_id)
            self.refresh()
            return
        if self._is_instagram_sync_task(task):
            self.workspace.resume_instagram_sync_run(task.task_id)
            self.refresh()
            return
        if self._is_tiktok_sync_task(task):
            self.workspace.resume_tiktok_sync_run(task.task_id)
            self.refresh()
            return
        if self._is_platform_sync_group_task(task):
            if self.workspace.platform_service is not None:
                self.workspace.platform_service.resume_sync(task.task_id)
            self.refresh()
            return
        if self._is_market_research_task(task):
            if self.workspace.market_service is not None:
                self.workspace.market_service.resume_research_run(task.task_id)
            self.refresh()
            return
        if self._is_brief_task(task):
            if self.workspace.brief_service is not None:
                self.workspace.brief_service.resume_run(task.task_id)
            self.refresh()
            return
        if self._is_production_task(task):
            if self.workspace.production_service is not None:
                self.workspace.production_service.resume_run(task.task_id)
            self.refresh()
            return
        if task.title == "Render de clip":
            self.workspace.retry_render(task.task_id)
            self.refresh()
            return
        QMessageBox.information(self, "Task Center", "Abre el workflow del video para reintentar la etapa.")
