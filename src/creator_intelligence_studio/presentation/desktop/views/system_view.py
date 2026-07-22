"""Vista del sistema."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.models import CardViewModel
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import MetricCard


class SystemView(QWidget):
    """Resumen técnico del sistema y del diagnóstico actual."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.cards_container = QWidget(self)
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.details_label = QLabel()
        self.details_label.setWordWrap(True)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        title = QLabel("Sistema")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Diagnóstico operativo sin verificación de CUDA runtime mediante PyTorch.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.cards_container)
        layout.addWidget(self.details_label)
        layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

    def refresh(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
        for index, item in enumerate(self.workspace.system_items()):
            self.cards_layout.addWidget(
                MetricCard(CardViewModel(title=item.label, value=item.value, detail="")),
                index // 2,
                index % 2,
            )
        details = [f"- {item.label}: {item.value}" for item in self.workspace.system_items()]
        self.details_label.setText("Detalle del sistema:\n" + "\n".join(details))
