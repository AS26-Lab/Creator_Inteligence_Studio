"""Vistas base para Strategic Planning."""

from __future__ import annotations

import json

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class PlanningSectionView(QWidget):
    section_title = "Strategic Planning"
    data_method: str | None = None

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.title = QLabel(self.section_title)
        self.title.setObjectName("TitleLabel")
        self.subtitle = QLabel("Planificacion estrategica local, trazable y revisable.")
        self.subtitle.setObjectName("MutedLabel")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Estado", "Resumen"])
        self.empty_state = EmptyStateWidget("Sin datos", "No hay un plan activo o no existe informacion para esta seccion.")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)
        self.refresh()

    def _active_plan_id(self) -> str | None:
        if self.workspace.selected_creator_id is None:
            return None
        planning_service = getattr(self.workspace, "planning_service", None)
        if planning_service is None:
            return None
        plans = planning_service.list_plans(self.workspace.selected_creator_id)
        if not plans:
            return None
        active = next((plan for plan in plans if getattr(plan, "status", None) and plan.status.value == "active"), plans[0])
        return active.id

    def _rows(self):
        planning_service = getattr(self.workspace, "planning_service", None)
        plan_id = self._active_plan_id()
        if planning_service is None or plan_id is None or self.data_method is None:
            return []
        loader = getattr(planning_service, self.data_method, None)
        if not callable(loader):
            return []
        return loader(plan_id)

    def refresh(self) -> None:
        rows = self._rows()
        self.table.setRowCount(0)
        if not rows:
            self.table.hide()
            self.empty_state.show()
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, row in enumerate(rows):
            payload = row.to_dict() if hasattr(row, "to_dict") else dict(row)
            self.table.insertRow(row_index)
            values = [
                str(payload.get("id", "")),
                str(payload.get("name") or payload.get("title") or payload.get("snapshot_type") or payload.get("report_type") or ""),
                str(payload.get("status") or payload.get("series_type") or payload.get("theme_type") or payload.get("objective_type") or ""),
                json.dumps(payload, ensure_ascii=False, default=str)[:240],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
