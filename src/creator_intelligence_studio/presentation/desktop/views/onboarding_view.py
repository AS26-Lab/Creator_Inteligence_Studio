"""Guided onboarding shell for local transcription."""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.local_components import LocalComponentsViewModel
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class OnboardingView(QWidget):
    """Lightweight guided onboarding for the first local setup."""

    def __init__(
        self,
        workspace: WorkspaceViewModel,
        *,
        open_local_components_callback=None,
        open_transcription_callback=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.vm = LocalComponentsViewModel(workspace)
        self.open_local_components_callback = open_local_components_callback
        self.open_transcription_callback = open_transcription_callback
        self._status = None
        self._page_titles: list[QLabel] = []
        self._page_messages: list[QLabel] = []
        self._page_details: list[QLabel] = []

        title = QLabel("Configura la transcripcion local")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Creator Intelligence Studio puede procesar tus videos en tu computadora. Revisaremos que necesita tu equipo.")
        subtitle.setObjectName("MutedLabel")
        subtitle.setWordWrap(True)

        self.page_stack = QStackedWidget()
        for _index in range(5):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_title = QLabel()
            page_title.setObjectName("TitleLabel")
            page_message = QLabel()
            page_message.setWordWrap(True)
            page_details = QLabel()
            page_details.setWordWrap(True)
            page_details.setObjectName("MutedLabel")
            page_layout.addWidget(page_title)
            page_layout.addWidget(page_message)
            page_layout.addWidget(page_details)
            page_layout.addStretch(1)
            self.page_stack.addWidget(page)
            self._page_titles.append(page_title)
            self._page_messages.append(page_message)
            self._page_details.append(page_details)

        self.back_button = QPushButton("Volver")
        self.next_button = QPushButton("Continuar")
        self.skip_button = QPushButton("Ahora no")
        self.complete_button = QPushButton("Marcar como completado")
        self.components_button = QPushButton("Ver componentes")
        self.start_button = QPushButton("Comenzar")

        footer = QWidget()
        footer_layout = QVBoxLayout(footer)
        footer_layout.addWidget(self.page_stack)
        button_row = QWidget()
        row_layout = QHBoxLayout(button_row)
        row_layout.addWidget(self.back_button)
        row_layout.addWidget(self.next_button)
        row_layout.addWidget(self.components_button)
        row_layout.addWidget(self.start_button)
        row_layout.addWidget(self.complete_button)
        row_layout.addWidget(self.skip_button)
        row_layout.addStretch(1)
        footer_layout.addWidget(button_row)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(footer)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(scroll)

        self.back_button.clicked.connect(self._previous_page)
        self.next_button.clicked.connect(self._next_page)
        self.skip_button.clicked.connect(self._skip)
        self.complete_button.clicked.connect(self._complete)
        self.components_button.clicked.connect(self._open_local_components)
        self.start_button.clicked.connect(self._start_transcription)

        self._populate_default_pages()
        if os.environ.get("CIS_GUI_TEST_MODE") == "1" or hasattr(workspace, "_report"):
            self._status = self.vm.refresh_status()
            self._render_pages()
        self._sync_buttons()

    def refresh(self) -> None:
        self._status = self.vm.refresh_status()
        self._render_pages()
        self._sync_buttons()

    def _populate_default_pages(self) -> None:
        defaults = [
            (
                "Bienvenido",
                "Creator Intelligence Studio puede ayudarte a preparar la transcripcion local sin descargar nada al abrir.",
                [
                    "Revisaremos los componentes disponibles.",
                    "No se ejecutan descargas ni benchmarks automaticos.",
                    "Puedes saltar este paso en cualquier momento.",
                ],
            ),
            (
                "Revision del sistema",
                "Estado actual: revisando.",
                [
                    "Perfil recomendado: pendiente",
                    "Dispositivo: pendiente",
                    "FFmpeg: pendiente",
                    "Motor de transcripcion: pendiente",
                    "Modelo: pendiente",
                ],
            ),
            (
                "Recomendacion",
                "Recomendamos el perfil Equilibrado.",
                [
                    "Ofrece un balance razonable entre velocidad y precision.",
                    "Puedes usar otra opcion si prefieres una configuracion distinta.",
                ],
            ),
            (
                "Componentes requeridos",
                "Para este perfil necesitas los componentes locales que se muestran abajo.",
                [
                    "Componente multimedia",
                    "Motor de transcripcion",
                    "Modelo de transcripcion",
                    "Aceleracion por GPU: opcional segun tu equipo.",
                ],
            ),
            (
                "Listo o modo limitado",
                "Si todo esta listo, puedes comenzar. Si falta algo, puedes seguir en modo limitado.",
                [
                    "Todo listo: comenzar a transcribir.",
                    "No listo: revisar componentes y continuar sin bloquear la app.",
                ],
            ),
        ]
        for index, (page_title, page_message, detail_lines) in enumerate(defaults):
            self._page_titles[index].setText(page_title)
            self._page_messages[index].setText(page_message)
            self._page_details[index].setText("\n".join(f"- {line}" for line in detail_lines))

    def _render_pages(self) -> None:
        status = self._status
        if status is None:
            return
        pages = [
            (
                "Bienvenido",
                "Creator Intelligence Studio puede ayudarte a preparar la transcripcion local sin descargar nada al abrir.",
                [
                    "Revisaremos los componentes disponibles.",
                    "No se ejecutan descargas ni benchmarks automaticos.",
                    "Puedes saltar este paso en cualquier momento.",
                ],
            ),
            (
                "Revision del sistema",
                f"Estado actual: {status.primary_message}",
                [
                    f"Perfil recomendado: {status.recommended_profile_label}",
                    f"Dispositivo: {status.selected_device_label}",
                    f"FFmpeg: {status.ffmpeg_summary}",
                    f"Motor de transcripcion: {status.runtime_summary}",
                    f"Modelo: {status.model_summary}",
                ],
            ),
            (
                "Recomendacion",
                f"Recomendamos el perfil {status.recommended_profile_label}.",
                [
                    "Ofrece un balance razonable entre velocidad y precision.",
                    "Puedes usar otra opcion si prefieres una configuracion distinta.",
                ],
            ),
            (
                "Componentes requeridos",
                "Para este perfil necesitas los componentes locales que se muestran abajo.",
                [
                    "Componente multimedia",
                    "Motor de transcripcion",
                    "Modelo de transcripcion",
                    "Aceleracion por GPU: opcional segun tu equipo.",
                ],
            ),
            (
                "Listo o modo limitado",
                "Si todo esta listo, puedes comenzar. Si falta algo, puedes seguir en modo limitado.",
                [
                    "Todo listo: comenzar a transcribir.",
                    "No listo: revisar componentes y continuar sin bloquear la app.",
                ],
            ),
        ]
        for index, (page_title, page_message, detail_lines) in enumerate(pages):
            self._page_titles[index].setText(page_title)
            self._page_messages[index].setText(page_message)
            self._page_details[index].setText("\n".join(f"- {line}" for line in detail_lines))
        current_index = min(self.page_stack.currentIndex(), self.page_stack.count() - 1)
        self.page_stack.setCurrentIndex(max(current_index, 0))

        if status.can_transcribe_now:
            self.start_button.setText("Comenzar")
        else:
            self.start_button.setText("Continuar en modo limitado")

    def _sync_buttons(self) -> None:
        index = self.page_stack.currentIndex()
        self.back_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < self.page_stack.count() - 1)
        self.complete_button.setEnabled(index == self.page_stack.count() - 1)
        self.components_button.setEnabled(True)
        self.start_button.setEnabled(True)

    def _next_page(self) -> None:
        index = self.page_stack.currentIndex()
        if index >= self.page_stack.count() - 1:
            return
        self.page_stack.setCurrentIndex(index + 1)
        self._sync_buttons()

    def _previous_page(self) -> None:
        index = self.page_stack.currentIndex()
        if index <= 0:
            return
        self.page_stack.setCurrentIndex(index - 1)
        self._sync_buttons()

    def _skip(self) -> None:
        self.workspace.set_onboarding_state(seen=True, skipped=True, completed=False, last_status="skipped")
        if self.open_local_components_callback is not None:
            self.open_local_components_callback()

    def _complete(self) -> None:
        status = self._status or self.vm.refresh_status()
        self.workspace.set_onboarding_state(seen=True, skipped=False, completed=True, last_status="completed" if status.can_transcribe_now else "limited")
        if status.can_transcribe_now:
            if self.open_transcription_callback is not None:
                self.open_transcription_callback()
        elif self.open_local_components_callback is not None:
            self.open_local_components_callback()

    def _open_local_components(self) -> None:
        self.workspace.set_onboarding_state(seen=True, last_status="setup")
        if self.open_local_components_callback is not None:
            self.open_local_components_callback()

    def _start_transcription(self) -> None:
        status = self._status or self.vm.refresh_status()
        self.workspace.set_onboarding_state(
            seen=True,
            completed=status.can_transcribe_now,
            skipped=not status.can_transcribe_now,
            last_status="ready" if status.can_transcribe_now else "limited",
        )
        if status.can_transcribe_now and self.open_transcription_callback is not None:
            self.open_transcription_callback()
        elif self.open_local_components_callback is not None:
            self.open_local_components_callback()
