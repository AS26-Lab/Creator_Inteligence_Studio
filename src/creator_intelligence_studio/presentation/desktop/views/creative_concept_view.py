"""Vista de conceptos creativos para packaging."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class CreativeConceptView(QWidget):
    """Crea conceptos desde cero y los lista."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "creative_packaging_service", None)
        self.platform = QComboBox()
        self.platform.addItems(["youtube_longform", "youtube_short", "instagram_reel", "tiktok", "manual_other"])
        self.content_type = QComboBox()
        self.content_type.addItems(["longform_video", "short_video", "reel", "tiktok", "live_replay", "community_post", "other"])
        self.concept_type = QComboBox()
        self.concept_type.addItems(["literal", "curiosity_driven", "personality_driven", "educational_clarity", "conflict_driven", "transformation", "result_focused", "reaction_focused", "comparison", "story_moment", "custom"])
        self.topic = QLineEdit()
        self.title = QLineEdit()
        self.objective = QLineEdit()
        self.audience = QLineEdit()
        self.create_button = QPushButton("Crear concepto")
        self.refresh_button = QPushButton("Actualizar")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Titulo", "Tipo", "Plataforma", "Contenido", "Tema", "Estado", "ID"])
        self.table.setColumnHidden(6, True)
        self.empty_state = EmptyStateWidget("Sin conceptos", "Crea un concepto para un prompt o brief.")

        form = QFormLayout()
        form.addRow("Plataforma", self.platform)
        form.addRow("Contenido", self.content_type)
        form.addRow("Tipo", self.concept_type)
        form.addRow("Tema", self.topic)
        form.addRow("Titulo", self.title)
        form.addRow("Objetivo", self.objective)
        form.addRow("Audiencia", self.audience)
        actions = QHBoxLayout()
        actions.addWidget(self.create_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)

        self.create_button.clicked.connect(self._create_concept)
        self.refresh_button.clicked.connect(self.refresh)

    def _create_concept(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            QMessageBox.information(self, "Conceptos", "Selecciona un creador primero.")
            return
        try:
            self.service.build_concepts(
                creator_id=self.workspace.selected_creator_id,
                platform=self.platform.currentText(),
                content_type=self.content_type.currentText(),
                topic=self.topic.text().strip() or None,
                title=self.title.text().strip() or None,
                objective=self.objective.text().strip() or None,
                audience=self.audience.text().strip() or None,
                concept_type=self.concept_type.currentText(),
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Conceptos", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            self.table.setRowCount(0)
            self.empty_state.show()
            return
        concepts = self.service.list_concepts(self.workspace.selected_creator_id)
        self.table.setRowCount(0)
        if not concepts:
            self.empty_state.show()
        else:
            self.empty_state.hide()
        for row_index, concept in enumerate(concepts):
            self.table.insertRow(row_index)
            values = [
                concept.title,
                concept.concept_type,
                concept.platform,
                concept.content_type,
                concept.topic or "",
                concept.status,
                concept.id,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()
