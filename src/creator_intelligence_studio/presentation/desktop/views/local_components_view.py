"""Guided local components screen."""

from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.local_components import (
    LocalComponentsActionViewModel,
    LocalComponentsCardViewModel,
    LocalComponentsStatusViewModel,
    LocalComponentsViewModel,
)
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class LocalComponentsRefreshThread(QThread):
    result_ready = Signal(object)
    error_ready = Signal(str)

    def __init__(self, vm: LocalComponentsViewModel) -> None:
        super().__init__()
        self.vm = vm

    def run(self) -> None:  # pragma: no cover - Qt thread
        try:
            result = self.vm.refresh_status()
        except Exception as exc:  # pragma: no cover - defensive
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(result)


class ComponentCardWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ComponentCard")
        self.title_label = QLabel()
        self.title_label.setObjectName("TitleLabel")
        self.state_label = QLabel()
        self.state_label.setObjectName("MutedLabel")
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.explanation_label = QLabel()
        self.explanation_label.setWordWrap(True)
        self.primary_button = QPushButton()
        self.secondary_button = QPushButton("Ver detalles")
        self.details_label = QLabel()
        self.details_label.setWordWrap(True)
        self.details_label.hide()

        button_row = QHBoxLayout()
        button_row.addWidget(self.primary_button)
        button_row.addWidget(self.secondary_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.explanation_label)
        layout.addWidget(self.details_label)
        layout.addLayout(button_row)

        self.primary_button.setVisible(False)
        self.primary_button.setEnabled(False)
        self.secondary_button.setEnabled(True)

    def set_card(self, card: LocalComponentsCardViewModel, *, show_details: bool) -> None:
        self.title_label.setText(card.title)
        self.state_label.setText(card.state_label)
        self.description_label.setText(card.description)
        self.explanation_label.setText(card.explanation)
        self.primary_button.setVisible(bool(card.primary_action_id and card.primary_action_label))
        self.primary_button.setEnabled(bool(card.primary_action_id and card.primary_action_label))
        if card.primary_action_label:
            self.primary_button.setText(card.primary_action_label)
        self.primary_button.setProperty("action_id", card.primary_action_id)
        self.secondary_button.setText(card.secondary_action_label)
        self.secondary_button.setProperty("action_id", card.secondary_action_id)
        details = list(card.details)
        details.extend(card.technical_details)
        self.details_label.setText("\n".join(details) if details else "Sin detalles tecnicos.")
        self.details_label.setVisible(show_details)


class LocalComponentsView(QWidget):
    """Guided UI for local transcription readiness and actions."""

    def __init__(
        self,
        workspace: WorkspaceViewModel,
        *,
        open_transcription_callback=None,
        open_task_center_callback=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.vm = LocalComponentsViewModel(workspace)
        self.open_transcription_callback = open_transcription_callback
        self.open_task_center_callback = open_task_center_callback
        self._refresh_thread: LocalComponentsRefreshThread | None = None
        self._status: LocalComponentsStatusViewModel | None = None
        self._cards: dict[str, ComponentCardWidget] = {}
        self._profile_buttons: dict[str, QPushButton] = {}
        self._action_buttons: dict[str, QPushButton] = {}

        self.title_label = QLabel("Componentes locales")
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel("Configura lo necesario para transcribir y analizar contenido en tu computadora.")
        self.subtitle_label.setObjectName("MutedLabel")
        self.summary_label = QLabel("Cargando estado...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("MutedLabel")
        self.secondary_label = QLabel()
        self.secondary_label.setWordWrap(True)
        self.secondary_label.setObjectName("MutedLabel")
        self.summary_device_label = QLabel()
        self.summary_device_label.setObjectName("MutedLabel")
        self.summary_profile_label = QLabel()
        self.summary_profile_label.setObjectName("MutedLabel")
        self.summary_compute_label = QLabel()
        self.summary_compute_label.setObjectName("MutedLabel")

        self.primary_action_button = QPushButton("Actualizar")
        self.secondary_action_button = QPushButton("Ver componentes")
        self.task_center_button = QPushButton("Abrir Task Center")
        self.profile_change_button = QPushButton("Cambiar perfil")
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("Detalles tecnicos")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(bool(self.workspace.ui_state.local_components_show_advanced_details))

        self.download_container = QWidget()
        self.download_layout = QVBoxLayout(self.download_container)
        self.download_layout.setContentsMargins(0, 0, 0, 0)
        self.download_layout.setSpacing(8)
        self.download_empty = QLabel("No hay descargas activas.")
        self.download_empty.setObjectName("MutedLabel")
        self.download_layout.addWidget(self.download_empty)

        self.profile_container = QWidget()
        self.profile_layout = QHBoxLayout(self.profile_container)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(10)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        self.actions_container = QWidget()
        self.actions_layout = QHBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.actions_layout.addStretch(1)

        self.advanced_container = QWidget()
        self.advanced_layout = QVBoxLayout(self.advanced_container)
        self.advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.advanced_layout.setSpacing(8)
        self.advanced_summary = QLabel()
        self.advanced_summary.setWordWrap(True)
        self.advanced_summary.setObjectName("MutedLabel")
        self.advanced_details = QLabel()
        self.advanced_details.setWordWrap(True)
        self.advanced_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.advanced_layout.addWidget(self.advanced_summary)
        self.advanced_layout.addWidget(self.advanced_details)
        self.advanced_container.hide()

        summary_frame = QFrame()
        summary_frame.setObjectName("SummaryCard")
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.secondary_label)
        summary_layout.addWidget(self.summary_profile_label)
        summary_layout.addWidget(self.summary_device_label)
        summary_layout.addWidget(self.summary_compute_label)
        summary_buttons = QHBoxLayout()
        summary_buttons.addWidget(self.primary_action_button)
        summary_buttons.addWidget(self.secondary_action_button)
        summary_buttons.addWidget(self.task_center_button)
        summary_buttons.addWidget(self.profile_change_button)
        summary_buttons.addWidget(self.advanced_toggle)
        summary_buttons.addStretch(1)
        summary_layout.addLayout(summary_buttons)

        profile_frame = QFrame()
        profile_frame.setObjectName("SectionCard")
        profile_outer = QVBoxLayout(profile_frame)
        profile_title = QLabel("Perfil recomendado")
        profile_title.setObjectName("TitleLabel")
        profile_hint = QLabel("Elige un perfil sin instalar ni descargar nada.")
        profile_hint.setObjectName("MutedLabel")
        profile_hint.setWordWrap(True)
        profile_outer.addWidget(profile_title)
        profile_outer.addWidget(profile_hint)
        profile_outer.addWidget(self.profile_container)

        download_frame = QFrame()
        download_frame.setObjectName("SectionCard")
        download_layout = QVBoxLayout(download_frame)
        download_title = QLabel("Descargas")
        download_title.setObjectName("TitleLabel")
        download_hint = QLabel("Solo aparecen tareas de descarga que ya existen.")
        download_hint.setObjectName("MutedLabel")
        download_hint.setWordWrap(True)
        download_layout.addWidget(download_title)
        download_layout.addWidget(download_hint)
        download_layout.addWidget(self.download_container)

        cards_frame = QFrame()
        cards_frame.setObjectName("SectionCard")
        cards_outer = QVBoxLayout(cards_frame)
        cards_title = QLabel("Componentes")
        cards_title.setObjectName("TitleLabel")
        cards_hint = QLabel("La fuente de verdad es el resolvedor canonical.")
        cards_hint.setObjectName("MutedLabel")
        cards_hint.setWordWrap(True)
        cards_outer.addWidget(cards_title)
        cards_outer.addWidget(cards_hint)
        cards_outer.addWidget(self.cards_container)

        actions_frame = QFrame()
        actions_frame.setObjectName("SectionCard")
        actions_outer = QVBoxLayout(actions_frame)
        actions_title = QLabel("Acciones sugeridas")
        actions_title.setObjectName("TitleLabel")
        actions_hint = QLabel("Las acciones provienen del resolvedor y no se recrean en la GUI.")
        actions_hint.setObjectName("MutedLabel")
        actions_hint.setWordWrap(True)
        actions_outer.addWidget(actions_title)
        actions_outer.addWidget(actions_hint)
        actions_outer.addWidget(self.actions_container)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.subtitle_label)
        content_layout.addWidget(summary_frame)
        content_layout.addWidget(profile_frame)
        content_layout.addWidget(cards_frame)
        content_layout.addWidget(actions_frame)
        content_layout.addWidget(download_frame)
        content_layout.addWidget(self.advanced_container)
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        self.primary_action_button.clicked.connect(self._trigger_primary_action)
        self.secondary_action_button.clicked.connect(self._open_transcription)
        self.task_center_button.clicked.connect(self._open_task_center)
        self.profile_change_button.clicked.connect(self._cycle_profile)
        self.advanced_toggle.toggled.connect(self._toggle_details)

    def _set_loading_state(self) -> None:
        self.summary_label.setText("Cargando estado de los componentes locales...")
        self.secondary_label.setText("")
        self.summary_profile_label.setText("")
        self.summary_device_label.setText("")
        self.summary_compute_label.setText("")

    def refresh(self) -> None:
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return
        self._set_loading_state()
        thread = LocalComponentsRefreshThread(self.vm)
        thread.result_ready.connect(self._apply_status)
        thread.error_ready.connect(self._apply_error)
        thread.finished.connect(thread.deleteLater)
        self._refresh_thread = thread
        thread.start()

    def refresh_after_task(self) -> None:
        self.refresh()

    def _apply_error(self, message: str) -> None:
        self.summary_label.setText("No se pudo cargar el estado local.")
        self.secondary_label.setText(message)
        self._refresh_thread = None

    def _apply_status(self, status: LocalComponentsStatusViewModel) -> None:
        self._status = status
        self._refresh_thread = None
        self.summary_label.setText(status.primary_message)
        self.secondary_label.setText(status.secondary_message)
        self.summary_profile_label.setText(f"Perfil recomendado: {status.recommended_profile_label}")
        self.summary_device_label.setText(f"Dispositivo: {status.selected_device_label}")
        self.summary_compute_label.setText(f"Computo: {status.compute_type_label}")
        self.advanced_summary.setText(status.technical_summary or "Ver detalles tecnicos para mas informacion.")
        advanced_lines = [
            f"Readiness: {status.readiness}",
            f"Can transcribe now: {status.can_transcribe_now}",
            f"Selected profile: {status.selected_profile_label}",
            f"Selected device: {status.selected_device_label}",
            f"FFmpeg: {status.ffmpeg_summary}",
            f"Runtime: {status.runtime_summary}",
            f"Model: {status.model_summary}",
            f"GPU: {status.gpu_summary}",
        ]
        if status.benchmark_age_label:
            advanced_lines.append(f"Benchmark age: {status.benchmark_age_label}")
        if status.disk_label:
            advanced_lines.append(f"Disk: {status.disk_label}")
        if status.execution_plan is not None:
            advanced_lines.append(f"Execution plan: {status.execution_plan.selected_profile_id}")
        self.advanced_details.setText("\n".join(advanced_lines))
        self.advanced_container.setVisible(self.advanced_toggle.isChecked())
        self.workspace.set_local_components_advanced_details_visible(self.advanced_toggle.isChecked())

        self._render_profiles(status)
        self._render_cards(status)
        self._render_actions(status)
        self._render_downloads(status)
        self._update_primary_action(status)

    def _render_profiles(self, status: LocalComponentsStatusViewModel) -> None:
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._profile_buttons.clear()
        for option in status.profile_options:
            button = QPushButton(option.title)
            button.setCheckable(True)
            button.setChecked(option.selected)
            button.setEnabled(option.available)
            tooltip = option.description
            if option.recommended:
                tooltip += " Recomendado."
            if not option.available:
                tooltip += " No disponible."
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, profile_id=option.profile_id: self._choose_profile(profile_id))
            self._profile_buttons[option.profile_id] = button
            column = QVBoxLayout()
            column_widget = QWidget()
            column_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            column_widget.setLayout(column)
            column.addWidget(button)
            label = QLabel(option.description)
            label.setWordWrap(True)
            label.setObjectName("MutedLabel")
            column.addWidget(label)
            self.profile_layout.addWidget(column_widget)
        self.profile_layout.addStretch(1)

    def _render_cards(self, status: LocalComponentsStatusViewModel) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()
        show_details = self.advanced_toggle.isChecked()
        for card in status.component_cards:
            widget = ComponentCardWidget()
            widget.set_card(card, show_details=show_details)
            widget.primary_button.clicked.connect(lambda _checked=False, card_id=card.primary_action_id: self._handle_card_action(card_id))
            widget.secondary_button.clicked.connect(lambda _checked=False, card_id=card.secondary_action_id: self._handle_card_action(card_id))
            self._cards[card.key] = widget
            self.cards_layout.addWidget(widget)

    def _render_actions(self, status: LocalComponentsStatusViewModel) -> None:
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.actions_layout.addStretch(1)
        self._action_buttons.clear()
        for action in status.suggested_actions:
            button = QPushButton(action.label)
            button.setEnabled(action.available_now)
            if not action.available_now:
                button.setToolTip("Disponible proximamente" if action.reason is None else action.reason)
            else:
                button.setToolTip(action.description or action.reason or "")
            button.clicked.connect(lambda _checked=False, action_id=action.action_id: self._trigger_action(action_id))
            self._action_buttons[action.action_id] = button
            self.actions_layout.insertWidget(self.actions_layout.count() - 1, button)

    def _render_downloads(self, status: LocalComponentsStatusViewModel) -> None:
        while self.download_layout.count():
            item = self.download_layout.takeAt(0)
            widget = item.widget()
            if widget is self.download_empty:
                continue
            if widget is not None:
                widget.deleteLater()
        if not status.download_tasks:
            self.download_layout.addWidget(self.download_empty)
            self.download_empty.show()
            return
        self.download_empty.hide()
        for task in status.download_tasks:
            row = QFrame()
            row_layout = QVBoxLayout(row)
            title = QLabel(task.title)
            title.setObjectName("TitleLabel")
            meta = QLabel(f"{task.status_label} | {task.source_label}")
            meta.setObjectName("MutedLabel")
            meta.setWordWrap(True)
            progress = QProgressBar()
            progress.setRange(0, 100)
            percent = 0
            if task.progress_label.endswith("%"):
                try:
                    percent = int(float(task.progress_label.rstrip("%")))
                except ValueError:
                    percent = 0
            progress.setValue(max(0, min(100, percent)))
            details = QLabel(f"{task.progress_label} | {task.speed_label} | {task.eta_label}")
            details.setWordWrap(True)
            row_layout.addWidget(title)
            row_layout.addWidget(meta)
            row_layout.addWidget(progress)
            row_layout.addWidget(details)
            self.download_layout.addWidget(row)

    def _update_primary_action(self, status: LocalComponentsStatusViewModel) -> None:
        if status.can_transcribe_now:
            self.primary_action_button.setText("Comenzar a transcribir")
            self.primary_action_button.setEnabled(True)
        elif status.suggested_actions:
            first_action = status.suggested_actions[0]
            self.primary_action_button.setText(first_action.label)
            self.primary_action_button.setEnabled(first_action.available_now)
        else:
            self.primary_action_button.setText("Actualizar")
            self.primary_action_button.setEnabled(True)
        if status.can_transcribe_now:
            self.secondary_action_button.setText("Ver componentes")
        else:
            self.secondary_action_button.setText("Continuar en modo limitado")

    def _toggle_details(self, checked: bool) -> None:
        self.advanced_container.setVisible(checked)
        self.workspace.set_local_components_advanced_details_visible(checked)
        if self._status is not None:
            self._apply_status(self._status)

    def _trigger_primary_action(self) -> None:
        if self._status is None:
            self.refresh()
            return
        if self._status.can_transcribe_now and self.open_transcription_callback is not None:
            self.open_transcription_callback()
            return
        if self._status.suggested_actions:
            self._trigger_action(self._status.suggested_actions[0].action_id)
            return
        self.refresh()

    def _trigger_action(self, action_id: str) -> None:
        if not self.vm.execute_available_action(action_id):
            QMessageBox.information(self, "Componentes locales", "Esta accion no esta disponible por ahora.")
            return
        self.refresh_after_task()

    def _choose_profile(self, profile_id: str) -> None:
        self.workspace.set_transcription_preferences(profile=profile_id)
        self.refresh_after_task()

    def _cycle_profile(self) -> None:
        if self._status is None:
            self.refresh()
            return
        available_profiles = [option for option in self._status.profile_options if option.available]
        if not available_profiles:
            return
        current_index = next((index for index, option in enumerate(available_profiles) if option.selected), -1)
        next_index = (current_index + 1) % len(available_profiles)
        self._choose_profile(available_profiles[next_index].profile_id)

    def _handle_card_action(self, action_id: str | None) -> None:
        if not action_id or action_id == "toggle_details":
            self.advanced_toggle.setChecked(not self.advanced_toggle.isChecked())
            return
        self._trigger_action(action_id)

    def _open_transcription(self) -> None:
        if self._status is not None and self._status.can_transcribe_now and self.open_transcription_callback is not None:
            self.open_transcription_callback()
            return
        if self._status is not None and not self._status.can_transcribe_now:
            self._trigger_action("continue_limited")
            if self.open_transcription_callback is not None:
                self.open_transcription_callback()

    def _open_task_center(self) -> None:
        if self.open_task_center_callback is not None:
            self.open_task_center_callback()
