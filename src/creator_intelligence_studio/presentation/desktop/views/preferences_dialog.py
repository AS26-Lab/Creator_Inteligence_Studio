"""Preferencias iniciales de UX."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class PreferencesDialog(QDialog):
    def __init__(self, workspace: WorkspaceViewModel, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.setWindowTitle("Preferencias")
        self.data_edit = QLineEdit(workspace.ui_state.preferred_data_directory or "")
        self.models_edit = QLineEdit(workspace.ui_state.preferred_models_directory or "")
        self.exports_edit = QLineEdit(workspace.ui_state.preferred_exports_directory or "")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        self.device_combo.setCurrentText(workspace.ui_state.preferred_transcription_device)
        self.transcription_combo = QComboBox()
        self.transcription_combo.addItems(["balanced", "fast", "quality"])
        self.transcription_combo.setCurrentText(workspace.ui_state.transcription_profile)
        self.ranking_combo = QComboBox()
        self.ranking_combo.addItems(["balanced", "conservative", "aggressive"])
        self.ranking_combo.setCurrentText(workspace.ui_state.ranking_profile)
        self.confirm_checkbox = QCheckBox("Confirmar acciones destructivas")
        self.confirm_checkbox.setChecked(workspace.ui_state.confirm_destructive_actions)
        self.technical_checkbox = QCheckBox("Mostrar detalles tecnicos por defecto")
        self.technical_checkbox.setChecked(workspace.ui_state.show_technical_details)
        self.save_button = QPushButton("Guardar")
        self.cancel_button = QPushButton("Cancelar")

        form = QFormLayout()
        form.addRow("Carpeta de datos", self.data_edit)
        form.addRow("Carpeta de modelos", self.models_edit)
        form.addRow("Carpeta de exportaciones", self.exports_edit)
        form.addRow("Dispositivo de transcripcion", self.device_combo)
        form.addRow("Perfil de transcripcion", self.transcription_combo)
        form.addRow("Perfil de ranking", self.ranking_combo)
        form.addRow(self.confirm_checkbox)
        form.addRow(self.technical_checkbox)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.save_button)
        layout.addWidget(self.cancel_button)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def accept(self) -> None:  # pragma: no cover - simple wiring
        self.workspace.ui_state = self.workspace.ui_state_store.update(
            self.workspace.ui_state,
            preferred_data_directory=self.data_edit.text().strip() or None,
            preferred_models_directory=self.models_edit.text().strip() or None,
            preferred_exports_directory=self.exports_edit.text().strip() or None,
            preferred_transcription_device=self.device_combo.currentText(),
            transcription_profile=self.transcription_combo.currentText(),
            ranking_profile=self.ranking_combo.currentText(),
            confirm_destructive_actions=self.confirm_checkbox.isChecked(),
            show_technical_details=self.technical_checkbox.isChecked(),
        )
        super().accept()

