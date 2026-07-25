"""Vista de construccion de prompts creativos."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class PromptBuilderView(QWidget):
    """Genera prompts desde un concepto."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "creative_packaging_service", None)
        self.concept_id = QComboBox()
        self.target_tool = QComboBox()
        self.target_tool.addItems(["generic_image_tool", "chatgpt_images", "envato_ai", "manual_designer", "manual_creation", "other"])
        self.title_override = QLineEdit()
        self.build_button = QPushButton("Generar prompt")
        self.refresh_button = QPushButton("Actualizar")
        self.prompt_text = QPlainTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompts_table = QTableWidget(0, 5)
        self.prompts_table.setHorizontalHeaderLabels(["Version", "Herramienta", "Aprobacion", "ID", "Prompt"])
        self.prompts_table.setColumnHidden(3, True)
        self.references_table = QTableWidget(0, 4)
        self.references_table.setHorizontalHeaderLabels(["Rol", "Nivel", "Instruccion", "Referencia"])
        self.empty_state = EmptyStateWidget("Sin prompts", "Selecciona un concepto y crea un prompt personalizado.")

        form = QFormLayout()
        form.addRow("Concepto", self.concept_id)
        form.addRow("Herramienta", self.target_tool)
        form.addRow("Titulo opcional", self.title_override)
        actions = QHBoxLayout()
        actions.addWidget(self.build_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(QLabel("Prompt"))
        layout.addWidget(self.prompt_text)
        layout.addWidget(QLabel("Prompts"))
        layout.addWidget(self.prompts_table)
        layout.addWidget(QLabel("Referencias"))
        layout.addWidget(self.references_table)

        self.build_button.clicked.connect(self._build_prompt)
        self.refresh_button.clicked.connect(self.refresh)

    def _selected_concept_id(self) -> str | None:
        return self.concept_id.currentData() if self.concept_id.count() else None

    def _build_prompt(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            QMessageBox.information(self, "Prompts", "Selecciona un creador y un concepto primero.")
            return
        concept_id = self._selected_concept_id()
        if not concept_id:
            QMessageBox.information(self, "Prompts", "No hay concepto disponible.")
            return
        try:
            prompt = self.service.build_prompt(concept_id=concept_id, target_tool=self.target_tool.currentText(), title=self.title_override.text().strip() or None)
            self.prompt_text.setPlainText(prompt.prompt_text)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Prompts", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            self.concept_id.clear()
            self.prompts_table.setRowCount(0)
            self.references_table.setRowCount(0)
            self.empty_state.show()
            return
        concepts = self.service.list_concepts(self.workspace.selected_creator_id)
        current = self.concept_id.currentData()
        self.concept_id.blockSignals(True)
        self.concept_id.clear()
        for concept in concepts:
            self.concept_id.addItem(concept.title, concept.id)
        index = self.concept_id.findData(current)
        if index >= 0:
            self.concept_id.setCurrentIndex(index)
        self.concept_id.blockSignals(False)
        prompts = [prompt for concept in concepts for prompt in self.service.list_prompts(concept.id)]
        self.prompts_table.setRowCount(0)
        self.references_table.setRowCount(0)
        if not prompts:
            self.empty_state.show()
        else:
            self.empty_state.hide()
        for row_index, prompt in enumerate(prompts):
            self.prompts_table.insertRow(row_index)
            values = [prompt.version_number, prompt.target_tool.value, prompt.creator_approval_status, prompt.id, prompt.prompt_text[:120]]
            for column, value in enumerate(values):
                self.prompts_table.setItem(row_index, column, _item(value))
        selected_prompt = prompts[0] if prompts else None
        if selected_prompt is not None:
            for row_index, reference in enumerate(self.service.list_prompt_references(selected_prompt.id)):
                self.references_table.insertRow(row_index)
                values = [reference.reference_role, reference.required_level, reference.instruction, reference.reference_asset_id or ""]
                for column, value in enumerate(values):
                    self.references_table.setItem(row_index, column, _item(value))
        self.prompts_table.resizeColumnsToContents()
        self.references_table.resizeColumnsToContents()
