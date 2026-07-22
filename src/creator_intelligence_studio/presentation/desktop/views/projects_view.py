"""Vista de proyectos."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.dialogs.entity_dialogs import ProjectDialog
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from creator_intelligence_studio.presentation.desktop.widgets.inspector import InspectorPanel


class ProjectsView(QWidget):
    """Lista y formularios de proyectos."""

    def __init__(self, workspace: WorkspaceViewModel, inspector: InspectorPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.inspector = inspector
        self.creator_combo = QComboBox()
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Nombre", "Tipo", "Estado", "Videos", "Descripción", "ID"])
        self.table.setColumnHidden(5, True)
        self.table.itemSelectionChanged.connect(self._sync_selection)
        self.empty_state = EmptyStateWidget(
            "No hay proyectos",
            "Selecciona o crea un creador para administrar sus proyectos.",
        )
        self.empty_state.hide()

        buttons = QHBoxLayout()
        self.create_button = QPushButton("Crear proyecto")
        self.archive_button = QPushButton("Archivar seleccionado")
        self.create_button.setToolTip("Crear un nuevo proyecto para el creador seleccionado")
        self.archive_button.setToolTip("Archivar el proyecto seleccionado")
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.archive_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Proyectos")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addWidget(self.creator_combo)
        layout.addLayout(buttons)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)

        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.archive_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.creator_combo.currentIndexChanged.connect(self._creator_changed)
        self.create_button.clicked.connect(self._create_project)
        self.archive_button.clicked.connect(self._archive_project)

    def refresh(self) -> None:
        creators = self.workspace.creators()
        self.creator_combo.blockSignals(True)
        self.creator_combo.clear()
        for creator in creators:
            self.creator_combo.addItem(f"{creator.display_name} ({creator.slug})", creator.id)
        if self.workspace.selected_creator_id:
            index = self.creator_combo.findData(self.workspace.selected_creator_id)
            if index >= 0:
                self.creator_combo.setCurrentIndex(index)
        self.creator_combo.blockSignals(False)
        self._reload_table()

    def _reload_table(self) -> None:
        projects = self.workspace.project_rows()
        self.table.setRowCount(0)
        if not self.workspace.selected_creator_id:
            self.table.hide()
            self.empty_state.show()
            self.inspector.set_empty("Inspector", "Selecciona un creador para ver proyectos.")
            return
        if not projects:
            self.table.hide()
            self.empty_state.show()
            self.inspector.set_empty("Inspector", "Este creador todavía no tiene proyectos.")
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, project in enumerate(projects):
            self.table.insertRow(row_index)
            values = [
                project.name,
                project.project_type,
                project.status,
                str(project.videos_count),
                project.description or "",
                project.id,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self._select_workspace_project_row()
        self._sync_selection()

    def _creator_changed(self) -> None:
        creator_id = self.creator_combo.currentData()
        if not creator_id:
            return
        self.workspace.select_creator(str(creator_id))
        self._reload_table()

    def _selected_project_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self.table.item(row, 5)
        return item.text() if item else None

    def _select_workspace_project_row(self) -> None:
        if self.workspace.selected_project_id is None:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 5)
            if item and item.text() == self.workspace.selected_project_id:
                self.table.selectRow(row)
                break

    def _sync_selection(self) -> None:
        project_id = self._selected_project_id()
        project = self.workspace.service.get_project(project_id) if project_id else self.workspace.selected_project()
        if project is None:
            self.inspector.set_empty("Inspector", "Selecciona un proyecto para ver sus detalles.")
            return
        self.workspace.select_project(project.id)
        self.inspector.set_items(
            f"Proyecto: {project.name}",
            self.workspace.project_inspector_items(project),
            footer="Los proyectos pertenecen a un creador activo y no aceptan videos si están archivados.",
        )

    def _create_project(self) -> None:
        creator = self.workspace.selected_creator()
        if creator is None:
            QMessageBox.information(self, "Sin creador", "Selecciona un creador antes de crear proyectos.")
            return
        dialog = ProjectDialog(creator.display_name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        try:
            project = self.workspace.create_project(
                creator_reference=creator.id,
                name=str(payload["name"]),
                project_type=str(payload["project_type"]),
                description=payload["description"],
            )
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo crear el proyecto", str(exc))
            return
        self.refresh()
        self.workspace.select_project(project.id)

    def _archive_project(self) -> None:
        project_id = self._selected_project_id()
        if not project_id:
            QMessageBox.information(self, "Sin selección", "Selecciona un proyecto primero.")
            return
        try:
            self.workspace.archive_project(project_id)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo archivar", str(exc))
            return
        self.refresh()
