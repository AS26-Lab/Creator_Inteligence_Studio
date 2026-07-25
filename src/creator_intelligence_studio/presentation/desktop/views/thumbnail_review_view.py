"""Vista de revision de miniaturas."""

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


class ThumbnailReviewView(QWidget):
    """Revisa una miniatura existente contra marca y contenido."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "creative_packaging_service", None)
        self.thumbnail_id = QComboBox()
        self.title_id = QComboBox()
        self.publication_id = QLineEdit()
        self.concept_id = QComboBox()
        self.prompt_id = QComboBox()
        self.review_button = QPushButton("Revisar")
        self.refresh_button = QPushButton("Actualizar")
        self.instructions = QPlainTextEdit()
        self.instructions.setReadOnly(True)
        self.reviews_table = QTableWidget(0, 5)
        self.reviews_table.setHorizontalHeaderLabels(["Status", "Tipo", "Miniatura", "Titulo", "ID"])
        self.reviews_table.setColumnHidden(4, True)
        self.empty_state = EmptyStateWidget("Sin revisiones", "Selecciona una miniatura para revisar.")

        form = QFormLayout()
        form.addRow("Miniatura", self.thumbnail_id)
        form.addRow("Titulo", self.title_id)
        form.addRow("Publication ID", self.publication_id)
        form.addRow("Concepto", self.concept_id)
        form.addRow("Prompt", self.prompt_id)
        actions = QHBoxLayout()
        actions.addWidget(self.review_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(QLabel("Instrucciones"))
        layout.addWidget(self.instructions)
        layout.addWidget(QLabel("Revisiones"))
        layout.addWidget(self.reviews_table)

        self.review_button.clicked.connect(self._review)
        self.refresh_button.clicked.connect(self.refresh)

    def _review(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            QMessageBox.information(self, "Revision", "Selecciona un creador primero.")
            return
        thumbnail_id = self.thumbnail_id.currentData()
        if not thumbnail_id:
            QMessageBox.information(self, "Revision", "Selecciona una miniatura primero.")
            return
        try:
            review = self.service.review_thumbnail(
                thumbnail_version_id=str(thumbnail_id),
                title_version_id=str(self.title_id.currentData()) if self.title_id.currentData() else None,
                publication_id=self.publication_id.text().strip() or None,
                concept_id=str(self.concept_id.currentData()) if self.concept_id.currentData() else None,
                prompt_id=str(self.prompt_id.currentData()) if self.prompt_id.currentData() else None,
            )
            self.instructions.setPlainText(review.final_recommendation)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Revision", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            for combo in (self.thumbnail_id, self.title_id, self.concept_id, self.prompt_id):
                combo.clear()
            self.reviews_table.setRowCount(0)
            self.empty_state.show()
            return
        creator_id = self.workspace.selected_creator_id
        assets = self.service.list_assets(creator_id)
        thumbnails = [thumbnail for asset in assets for thumbnail in self.service.list_thumbnail_versions(asset.id)]
        titles = [title for asset in assets for title in self.service.list_title_versions(asset.id)]
        concepts = self.service.list_concepts(creator_id)
        prompts = [prompt for concept in concepts for prompt in self.service.list_prompts(concept.id)]
        current_thumbnail = self.thumbnail_id.currentData()
        current_title = self.title_id.currentData()
        current_concept = self.concept_id.currentData()
        current_prompt = self.prompt_id.currentData()
        for combo, values in (
            (self.thumbnail_id, thumbnails),
            (self.title_id, titles),
            (self.concept_id, concepts),
            (self.prompt_id, prompts),
        ):
            combo.blockSignals(True)
            combo.clear()
            for value in values:
                combo.addItem(getattr(value, "title_text", None) or getattr(value, "title", None) or getattr(value, "concept_type", None) or getattr(value, "prompt_text", None) or getattr(value, "image_path", None) or value.id, value.id)
            combo.blockSignals(False)
        for combo, current in (
            (self.thumbnail_id, current_thumbnail),
            (self.title_id, current_title),
            (self.concept_id, current_concept),
            (self.prompt_id, current_prompt),
        ):
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)
        reviews = self.service.list_thumbnail_reviews(creator_id)
        self.reviews_table.setRowCount(0)
        if not reviews:
            self.empty_state.show()
        else:
            self.empty_state.hide()
        for row_index, review in enumerate(reviews):
            self.reviews_table.insertRow(row_index)
            values = [review.overall_status, review.review_type, review.thumbnail_version_id, review.title_version_id or "", review.id]
            for column, value in enumerate(values):
                self.reviews_table.setItem(row_index, column, _item(value))
        self.reviews_table.resizeColumnsToContents()
