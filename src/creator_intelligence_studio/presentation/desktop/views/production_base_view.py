"""Vistas base para Production Preparation."""

from __future__ import annotations

import json

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class ProductionSectionView(QWidget):
    section_title = "Production Preparation"
    data_method: str | None = None
    scope: str = "outline"

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.title = QLabel(self.section_title)
        self.title.setObjectName("TitleLabel")
        self.subtitle = QLabel("Outlines trazables, revisables y limitados por derechos, continuidad y capacidad.")
        self.subtitle.setObjectName("MutedLabel")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Titulo", "Estado", "Resumen"])
        self.empty_state = EmptyStateWidget("Sin datos", "No hay elementos de production preparation disponibles para esta seccion.")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)
        self.refresh()

    def _creator_id(self) -> str | None:
        return getattr(self.workspace, "selected_creator_id", None)

    def _rows(self):
        production_service = getattr(self.workspace, "production_service", None)
        creator_id = self._creator_id()
        if production_service is None or creator_id is None or self.data_method is None:
            return []
        loader = getattr(production_service, self.data_method, None)
        if not callable(loader):
            return []
        if self.scope == "creator":
            return loader(creator_id)
        outlines = production_service.list_outlines(creator_id)
        outline = next((item for item in outlines if getattr(item, "status", None) is not None and str(getattr(item.status, "value", item.status)) == "approved"), None)
        if outline is None:
            outline = outlines[0] if outlines else None
        if outline is None:
            return []
        return loader(outline.id)

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
                str(payload.get("title") or payload.get("name") or payload.get("segment_name") or payload.get("snapshot_type") or payload.get("report_type") or ""),
                str(payload.get("status") or payload.get("readiness_status") or payload.get("decision") or payload.get("section_type") or payload.get("gate_type") or ""),
                json.dumps(payload, ensure_ascii=False, default=str)[:240],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
