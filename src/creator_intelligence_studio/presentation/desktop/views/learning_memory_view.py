"""Vista simple de memoria de aprendizaje."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class LearningMemoryView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.refresh_button = QPushButton("Actualizar")
        self.confirm_button = QPushButton("Confirmar")
        self.reject_button = QPushButton("Rechazar")
        self.more_data_button = QPushButton("Necesita mas datos")
        self.deprecate_button = QPushButton("Deprecate")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Statement", "Scope", "Type", "Status", "Confidence", "Supports", "Contradictions", "ID"])
        self.table.setColumnHidden(7, True)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.empty_state = EmptyStateWidget("Sin memoria de aprendizaje", "Los experimentos completados pueden sugerir aprendizajes provisionales.")

        title = QLabel("Learning Memory")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Memoria estructurada y revisable, sin reglas ocultas ni promocion automatica.")
        subtitle.setObjectName("MutedLabel")

        actions = QHBoxLayout()
        for widget in (self.refresh_button, self.confirm_button, self.reject_button, self.more_data_button, self.deprecate_button):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Detalle"))
        layout.addWidget(self.detail)

        self.refresh_button.clicked.connect(self.refresh)
        self.confirm_button.clicked.connect(self._confirm)
        self.reject_button.clicked.connect(self._reject)
        self.more_data_button.clicked.connect(self._more_data)
        self.deprecate_button.clicked.connect(self._deprecate)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.refresh()

    def _selected_learning_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 7)
        return item.text() if item else None

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        learnings = self.workspace.list_learnings(creator_id) if creator_id else []
        self.table.setRowCount(0)
        if not learnings:
            self.table.hide()
            self.empty_state.show()
            self.detail.setPlainText("Sin aprendizajes.")
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, learning in enumerate(learnings):
            self.table.insertRow(row_index)
            values = [
                learning.statement,
                learning.scope,
                learning.learning_type.value,
                learning.status.value,
                learning.confidence_level.value,
                learning.supporting_example_count,
                learning.contradicting_example_count,
                learning.id,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        self._selection_changed()

    def _selection_changed(self) -> None:
        learning_id = self._selected_learning_id()
        enabled = learning_id is not None
        for button in (self.confirm_button, self.reject_button, self.more_data_button, self.deprecate_button):
            button.setEnabled(enabled)
        if not learning_id:
            return
        learning = self.workspace.get_learning(learning_id)
        if learning is None:
            return
        self.detail.setPlainText(learning.evidence_json)

    def _confirm(self) -> None:
        learning_id = self._selected_learning_id()
        if not learning_id:
            return
        self.workspace.confirm_learning(learning_id)
        self.refresh()

    def _reject(self) -> None:
        learning_id = self._selected_learning_id()
        if not learning_id:
            return
        self.workspace.reject_learning(learning_id)
        self.refresh()

    def _more_data(self) -> None:
        learning_id = self._selected_learning_id()
        if not learning_id:
            return
        self.workspace.needs_more_data_learning(learning_id)
        self.refresh()

    def _deprecate(self) -> None:
        learning_id = self._selected_learning_id()
        if not learning_id:
            return
        self.workspace.deprecate_learning(learning_id)
        self.refresh()

