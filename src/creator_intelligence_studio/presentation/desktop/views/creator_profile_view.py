"""Vista del perfil creativo del creador."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


class CreatorProfileView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        self.title = QLabel("Creator Profile")
        self.title.setObjectName("TitleLabel")
        self.subtitle = QLabel("Perfil estructurado, versionado y trazable por creador.")
        self.subtitle.setObjectName("MutedLabel")

        self.display_name = QLineEdit()
        self.primary_language = QLineEdit()
        self.default_tone = QLineEdit()
        self.default_formality = QLineEdit()
        self.summary = QPlainTextEdit()
        self.secondary_languages = QPlainTextEdit()
        self.objectives = QPlainTextEdit()

        self.version_label = QLabel("Version: -")
        self.version_label.setObjectName("MutedLabel")
        self.status_label = QLabel("Estado: -")
        self.status_label.setObjectName("MutedLabel")
        self.last_updated_label = QLabel("Actualizado: -")
        self.last_updated_label.setObjectName("MutedLabel")

        self.save_button = QPushButton("Guardar perfil")
        self.snapshot_button = QPushButton("Crear snapshot")
        self.refresh_button = QPushButton("Actualizar")
        self.save_button.clicked.connect(self._save_profile)
        self.snapshot_button.clicked.connect(self._create_snapshot)
        self.refresh_button.clicked.connect(self.refresh)

        header = QHBoxLayout()
        header.addWidget(self.version_label)
        header.addWidget(self.status_label)
        header.addWidget(self.last_updated_label)
        header.addStretch(1)
        header.addWidget(self.save_button)
        header.addWidget(self.snapshot_button)
        header.addWidget(self.refresh_button)

        form = QGridLayout()
        form.addWidget(QLabel("Nombre"), 0, 0)
        form.addWidget(self.display_name, 0, 1)
        form.addWidget(QLabel("Idioma primario"), 0, 2)
        form.addWidget(self.primary_language, 0, 3)
        form.addWidget(QLabel("Tono"), 1, 0)
        form.addWidget(self.default_tone, 1, 1)
        form.addWidget(QLabel("Formalidad"), 1, 2)
        form.addWidget(self.default_formality, 1, 3)
        form.addWidget(QLabel("Idiomas secundarios JSON"), 2, 0)
        form.addWidget(self.secondary_languages, 2, 1, 1, 3)
        form.addWidget(QLabel("Objetivos JSON"), 3, 0)
        form.addWidget(self.objectives, 3, 1, 1, 3)
        form.addWidget(QLabel("Resumen"), 4, 0)
        form.addWidget(self.summary, 4, 1, 1, 3)

        self.empty_state = EmptyStateWidget(
            "Crea un perfil creativo o selecciona un creador.",
            "El perfil mantiene versionado, evidencia y contradicciones sin sobrescribir historial.",
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(header)
        layout.addLayout(form)
        layout.addWidget(self.empty_state)

        self.refresh()

    def _selected_creator_id(self) -> str | None:
        return self.workspace.selected_creator_id

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            self.empty_state.show()
            self.version_label.setText("Version: -")
            self.status_label.setText("Estado: -")
            self.last_updated_label.setText("Actualizado: -")
            self.display_name.clear()
            self.primary_language.clear()
            self.default_tone.clear()
            self.default_formality.clear()
            self.summary.clear()
            self.secondary_languages.setPlainText("[]")
            self.objectives.setPlainText("[]")
            return

        try:
            detail = self.workspace.get_creator_memory_profile_detail(creator_id)
        except Exception:
            detail = None
        if detail is None:
            self.empty_state.show()
            profile = self.workspace.get_creator_memory_profile(creator_id)
            if profile is None:
                self.empty_state.show()
                self.display_name.clear()
                self.primary_language.clear()
                self.default_tone.clear()
                self.default_formality.clear()
                self.summary.clear()
                self.secondary_languages.setPlainText("[]")
                self.objectives.setPlainText("[]")
                return
            self.display_name.setText(profile.display_name)
            self.primary_language.setText(profile.primary_language or "")
            self.default_tone.setText(profile.default_tone or "")
            self.default_formality.setText(profile.default_formality or "")
            self.summary.setPlainText(profile.summary or "")
            self.secondary_languages.setPlainText(profile.secondary_languages_json)
            self.objectives.setPlainText(profile.objectives_json)
            self.version_label.setText(f"Version: {profile.profile_version}")
            self.status_label.setText(f"Estado: {profile.status.value}")
            self.last_updated_label.setText(f"Actualizado: {profile.updated_at.isoformat()}")
            self.empty_state.hide()
            return

        profile = detail.profile
        self.empty_state.hide()
        self.display_name.setText(profile.display_name)
        self.primary_language.setText(profile.primary_language or "")
        self.default_tone.setText(profile.default_tone or "")
        self.default_formality.setText(profile.default_formality or "")
        self.summary.setPlainText(profile.summary or "")
        self.secondary_languages.setPlainText(profile.secondary_languages_json)
        self.objectives.setPlainText(profile.objectives_json)
        self.version_label.setText(f"Version: {profile.profile_version}")
        self.status_label.setText(f"Estado: {profile.status.value}")
        self.last_updated_label.setText(f"Actualizado: {profile.updated_at.isoformat()}")

    def _save_profile(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        payload = {
            "creator_id": creator_id,
            "display_name": self.display_name.text().strip() or creator_id,
            "summary": self.summary.toPlainText().strip() or None,
            "primary_language": self.primary_language.text().strip() or None,
            "secondary_languages": self.secondary_languages.toPlainText().strip() or "[]",
            "default_tone": self.default_tone.text().strip() or None,
            "default_formality": self.default_formality.text().strip() or None,
            "objectives": self.objectives.toPlainText().strip() or "[]",
        }
        try:
            self.workspace.update_creator_memory_profile(**payload)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _create_snapshot(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            snapshot = self.workspace.create_creator_profile_snapshot(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        QMessageBox.information(self, "Creator Memory", f"Snapshot creado: {snapshot.id}")
        self.refresh()
