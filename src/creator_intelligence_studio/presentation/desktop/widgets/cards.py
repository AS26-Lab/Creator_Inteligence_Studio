"""Tarjetas y estados vacíos de la interfaz."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.models import CardViewModel


class MetricCard(QFrame):
    """Tarjeta compacta para métricas principales."""

    def __init__(self, card: CardViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("accent", card.accent)
        self.setMinimumHeight(132)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        icon = QLabel(card.icon)
        icon.setObjectName("MetricIcon")
        title = QLabel(card.title)
        title.setObjectName("SectionLabel")
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(title, 1)
        header.addStretch(1)

        value = QLabel(card.value)
        value.setWordWrap(True)
        value.setObjectName("MetricValue")
        detail = QLabel(card.detail or "")
        detail.setObjectName("MutedLabel")
        detail.setWordWrap(True)

        layout.addLayout(header)
        layout.addWidget(value)
        layout.addWidget(detail)
        layout.addStretch(1)


class EmptyStateWidget(QFrame):
    """Estado vacío con mensaje accionable."""

    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MutedPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("SectionLabel")
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        description_label.setObjectName("MutedLabel")
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch(1)
