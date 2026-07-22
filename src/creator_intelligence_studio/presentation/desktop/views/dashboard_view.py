"""Vista de inicio."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import MetricCard


class DashboardView(QWidget):
    """Pantalla inicial con métricas resumidas."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.cards_container = QWidget(self)
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)
        for column in range(4):
            self.cards_layout.setColumnStretch(column, 1)

        self.activity_frame = QFrame(self)
        self.activity_frame.setObjectName("MutedPanel")
        activity_layout = QVBoxLayout(self.activity_frame)
        activity_layout.setContentsMargins(16, 16, 16, 16)
        activity_layout.setSpacing(8)
        activity_title = QLabel("Actividad reciente")
        activity_title.setObjectName("SectionLabel")
        self.activity_label = QLabel()
        self.activity_label.setWordWrap(True)
        self.activity_label.setObjectName("MutedLabel")
        activity_layout.addWidget(activity_title)
        activity_layout.addWidget(self.activity_label)
        activity_layout.addStretch(1)

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        title = QLabel("Inicio")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Estado operativo y resumen del espacio de trabajo.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.cards_container)
        layout.addWidget(self.activity_frame)
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
        cards = self.workspace.dashboard_cards()
        for index, card in enumerate(cards):
            self.cards_layout.addWidget(MetricCard(card), index // 4, index % 4)
        if self.workspace.activity_log:
            self.activity_label.setText("\n".join(f"- {entry}" for entry in self.workspace.activity_log[:5]))
        else:
            self.activity_label.setText(
                "No hay actividad reciente.\nCrea un proyecto o registra un video para comenzar."
            )
