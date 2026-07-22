"""Vista de creadores."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from creator_intelligence_studio.presentation.desktop.dialogs.entity_dialogs import CreatorDialog
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from creator_intelligence_studio.presentation.desktop.widgets.inspector import InspectorPanel


class CreatorsView(QWidget):
    """Lista y formularios de creadores."""

    def __init__(self, workspace: WorkspaceViewModel, inspector: InspectorPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.inspector = inspector
        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(["Nombre", "Slug", "Estado", "Proyectos", "Videos", "Descripción", "ID"])
        self.table.setColumnHidden(6, True)
        self.table.itemSelectionChanged.connect(self._sync_selection)

        self.empty_state = EmptyStateWidget(
            "No hay creadores",
            "Crea el primer creador para empezar a organizar proyectos y videos.",
        )
        self.empty_state.hide()

        buttons = QHBoxLayout()
        self.create_button = QPushButton("Crear creador")
        self.archive_button = QPushButton("Archivar seleccionado")
        self.select_button = QPushButton("Seleccionar")
        self.create_button.setToolTip("Crear un nuevo creador")
        self.archive_button.setToolTip("Archivar el creador seleccionado")
        self.select_button.setToolTip("Seleccionar el creador marcado")
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.archive_button)
        buttons.addWidget(self.select_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        title = QLabel("Creadores")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addLayout(buttons)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)

        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.archive_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.clicked.connect(self._create_creator)
        self.archive_button.clicked.connect(self._archive_creator)
        self.select_button.clicked.connect(self._select_creator)

    def refresh(self) -> None:
        creators = self.workspace.creator_rows()
        self.table.setRowCount(0)
        if not creators:
            self.table.hide()
            self.empty_state.show()
            self.inspector.set_empty("Inspector", "No hay creadores para mostrar.")
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, creator in enumerate(creators):
            self.table.insertRow(row_index)
            values = [
                creator.display_name,
                creator.slug,
                creator.status,
                str(creator.projects_count),
                str(creator.videos_count),
                creator.description or "",
                creator.id,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 5:
                    item.setToolTip(value)
                self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()
        self._select_workspace_creator_row()

    def _selected_creator_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self.table.item(row, 6)
        return item.text() if item else None

    def _select_workspace_creator_row(self) -> None:
        if self.workspace.selected_creator_id is None:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 6)
            if item and item.text() == self.workspace.selected_creator_id:
                self.table.selectRow(row)
                break

    def _sync_selection(self) -> None:
        creator_id = self._selected_creator_id()
        creator = self.workspace.service.get_creator(creator_id) if creator_id else self.workspace.selected_creator()
        if creator is None:
            self.inspector.set_empty("Inspector", "Selecciona un creador para ver sus detalles.")
            return
        self.workspace.select_creator(creator.id)
        self.inspector.set_items(
            f"Creador: {creator.display_name}",
            self.workspace.creator_inspector_items(creator),
            footer="Los datos se gestionan mediante CatalogService y no desde SQLite directo.",
        )

    def _create_creator(self) -> None:
        dialog = CreatorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        try:
            creator = self.workspace.create_creator(
                display_name=str(payload["display_name"]),
                slug=payload["slug"],
                description=payload["description"],
            )
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo crear el creador", str(exc))
            return
        self.refresh()
        self.workspace.select_creator(creator.id)

    def _archive_creator(self) -> None:
        creator_id = self._selected_creator_id()
        if not creator_id:
            QMessageBox.information(self, "Sin selección", "Selecciona un creador primero.")
            return
        try:
            self.workspace.archive_creator(creator_id)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo archivar", str(exc))
            return
        self.refresh()

    def _select_creator(self) -> None:
        creator_id = self._selected_creator_id()
        if not creator_id:
            return
        self.workspace.select_creator(creator_id)
        self.refresh()
