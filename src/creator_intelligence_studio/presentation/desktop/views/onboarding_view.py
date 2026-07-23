"""Onboarding corto para primeros pasos."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


class OnboardingView(QWidget):
    """Secuencia breve para orientar sin bloquear."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.dismiss_checkbox = QCheckBox("No volver a mostrar al iniciar")
        self.finish_button = QPushButton("Marcar como visto")
        self.reopen_button = QPushButton("Reabrir onboarding")

        title = QLabel("Onboarding")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Una secuencia corta para entender el flujo sin descargar modelos ni procesar videos grandes.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")
        steps = EmptyStateWidget(
            "Pasos iniciales",
            "\n".join(
                [
                    "1. Que hace Creator Intelligence Studio.",
                    "2. Seleccionar almacenamiento.",
                    "3. Verificar FFmpeg.",
                    "4. Verificar transcripcion.",
                    "5. Crear primer creador.",
                    "6. Crear primer proyecto.",
                    "7. Importar primer video.",
                ]
            ),
        )

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(steps)
        layout.addWidget(self.dismiss_checkbox)
        layout.addWidget(self.finish_button)
        layout.addWidget(self.reopen_button)
        layout.addStretch(1)

        self.finish_button.clicked.connect(self._finish)
        self.reopen_button.clicked.connect(self._reopen)

    def refresh(self) -> None:
        self.dismiss_checkbox.setChecked(bool(self.workspace.ui_state.onboarding_seen))

    def _finish(self) -> None:
        self.workspace.ui_state = self.workspace.ui_state_store.update(
            self.workspace.ui_state,
            onboarding_seen=self.dismiss_checkbox.isChecked(),
        )

    def _reopen(self) -> None:
        self.workspace.ui_state = self.workspace.ui_state_store.update(
            self.workspace.ui_state,
            onboarding_seen=False,
        )
