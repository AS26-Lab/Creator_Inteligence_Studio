"""Dialogos para crear y registrar entidades."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class CreatorDialog(QDialog):
    """Formulario para crear creadores."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo creador")
        self.name_edit = QLineEdit()
        self.slug_edit = QLineEdit()
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Descripción opcional")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Nombre", self.name_edit)
        form.addRow("Slug", self.slug_edit)
        form.addRow("Descripción", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict[str, str | None]:
        return {
            "display_name": self.name_edit.text().strip(),
            "slug": self.slug_edit.text().strip() or None,
            "description": self.description_edit.toPlainText().strip() or None,
        }


class ProjectDialog(QDialog):
    """Formulario para crear proyectos."""

    def __init__(self, creator_label: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo proyecto")
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["long_form", "short_form", "mixed", "research"])
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Descripción opcional")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        creator_field = QLineEdit(creator_label)
        creator_field.setEnabled(False)
        form.addRow("Creador", creator_field)
        form.addRow("Nombre", self.name_edit)
        form.addRow("Tipo", self.type_combo)
        form.addRow("Descripción", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict[str, str | None]:
        return {
            "name": self.name_edit.text().strip(),
            "project_type": self.type_combo.currentText(),
            "description": self.description_edit.toPlainText().strip() or None,
        }


class VideoDialog(QDialog):
    """Formulario para registrar videos locales."""

    def __init__(self, project_label: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registrar video")
        self.file_edit = QLineEdit()
        self.file_button = QPushButton("Buscar")
        self.title_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Notas opcionales")

        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit)
        file_row.addWidget(self.file_button)
        self.file_button.clicked.connect(self._browse)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        project_field = QLineEdit(project_label)
        project_field.setEnabled(False)
        form.addRow("Proyecto", project_field)
        form.addRow("Archivo", file_row)
        form.addRow("Título", self.title_edit)
        form.addRow("Notas", self.notes_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona un video",
            str(Path.home()),
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
        )
        if file_name:
            self.file_edit.setText(file_name)

    def payload(self) -> dict[str, str | None]:
        return {
            "file_path": self.file_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
