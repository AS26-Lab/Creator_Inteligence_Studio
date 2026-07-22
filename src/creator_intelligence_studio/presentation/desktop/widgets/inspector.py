"""Inspector contextual lateral."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.models import InspectorItemViewModel


class InspectorPanel(QFrame):
    """Panel lateral para detalles y acciones contextuales."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Inspector")
        self._compact = True
        self._container = QWidget(self)
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.set_empty(
            "Inspector",
            "Selecciona un elemento para ver sus detalles y acciones.",
        )

    def set_compact_mode(self, compact: bool) -> None:
        self._compact = compact
        if compact:
            self.setMinimumWidth(220)
            self.setMaximumWidth(260)
        else:
            self.setMinimumWidth(280)
            self.setMaximumWidth(360)
        self.updateGeometry()

    def _clear_layout(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_empty(self, title: str, description: str) -> None:
        self.set_compact_mode(True)
        self._clear_layout()
        title_label = QLabel(title)
        title_label.setObjectName("SectionLabel")
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setObjectName("MutedLabel")
        self._layout.addWidget(title_label)
        self._layout.addWidget(description_label)
        self._layout.addStretch(1)

    def set_items(self, title: str, items: list[InspectorItemViewModel], *, footer: str | None = None) -> None:
        self.set_compact_mode(False)
        self._clear_layout()
        title_label = QLabel(title)
        title_label.setObjectName("SectionLabel")
        self._layout.addWidget(title_label)
        for item in items:
            label = QLabel(item.label)
            label.setObjectName("MutedLabel")
            value = QLabel(item.value)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._layout.addWidget(label)
            self._layout.addWidget(value)
        if footer:
            footer_label = QLabel(footer)
            footer_label.setWordWrap(True)
            footer_label.setObjectName("MutedLabel")
            self._layout.addWidget(footer_label)
        self._layout.addStretch(1)

    def set_actions(self, actions: list[tuple[str, Callable[[], None]]]) -> None:
        for text, callback in actions:
            button = QPushButton(text)
            button.clicked.connect(callback)
            self._layout.addWidget(button)
