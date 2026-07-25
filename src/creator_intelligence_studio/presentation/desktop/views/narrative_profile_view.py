"""Vista del perfil narrativo de Creator Language."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class NarrativeProfileView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.refresh_button = QPushButton("Actualizar")
        self.snapshot_button = QPushButton("Crear snapshot")
        self.compare_button = QPushButton("Comparar versiones")
        self.summary_label = QLabel("Sin perfil narrativo.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setObjectName("MutedLabel")
        self.meta_label = QLabel("Version: -")
        self.meta_label.setObjectName("MutedLabel")
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Version", "Estado", "Resumen", "Actualizado", "ID"])
        self.history_table.setColumnHidden(4, True)
        self.compare_output = QPlainTextEdit()
        self.compare_output.setReadOnly(True)
        self.empty_state = EmptyStateWidget("Sin perfil narrativo", "Ejecuta un analisis de lenguaje para construir el perfil.")

        self.refresh_button.clicked.connect(self.refresh)
        self.snapshot_button.clicked.connect(self._create_snapshot)
        self.compare_button.clicked.connect(self._compare_latest)

        header = QHBoxLayout()
        header.addWidget(self.meta_label)
        header.addStretch(1)
        header.addWidget(self.snapshot_button)
        header.addWidget(self.compare_button)
        header.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        title = QLabel("Narrative Profile")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addLayout(header)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.history_table)
        layout.addWidget(QLabel("Comparacion"))
        layout.addWidget(self.compare_output)

        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if creator_id is None:
            self.empty_state.show()
            self.history_table.hide()
            self.compare_output.clear()
            self.meta_label.setText("Version: -")
            self.summary_label.setText("Sin perfil narrativo.")
            return
        detail = self.workspace.get_creator_language_profile_detail(creator_id)
        if detail is None:
            self.empty_state.show()
            self.history_table.hide()
            self.compare_output.clear()
            self.meta_label.setText("Version: -")
            self.summary_label.setText("Sin perfil narrativo.")
            return
        profile = detail.profile
        history = detail.snapshots
        if profile is None:
            self.empty_state.show()
            self.history_table.hide()
            self.compare_output.clear()
            self.meta_label.setText("Version: -")
            self.summary_label.setText("Sin perfil narrativo.")
            return
        self.empty_state.hide()
        self.history_table.show()
        self.meta_label.setText(f"Version: {profile.profile_version} | Estado: {profile.status}")
        self.summary_label.setText(profile.summary)
        self.history_table.setRowCount(0)
        for row_index, snapshot in enumerate(history):
            self.history_table.insertRow(row_index)
            values = [
                snapshot.profile_version,
                snapshot.status,
                snapshot.source_fingerprint[:16],
                snapshot.created_at.isoformat(),
                snapshot.id,
            ]
            for column, value in enumerate(values):
                self.history_table.setItem(row_index, column, _item(value))
        self.history_table.resizeColumnsToContents()
        self.compare_output.setPlainText(
            "\n".join(
                [
                    f"Corpus: {len(detail.corpora)}",
                    f"Fuentes: {len(detail.sources)}",
                    f"Metricas: {len(detail.metrics)}",
                    f"Patrones: {len(detail.patterns)}",
                    f"Candidates: {len(detail.candidates)}",
                    f"Warnings: {', '.join(detail.warnings) if detail.warnings else 'ninguno'}",
                ]
            )
        )

    def _create_snapshot(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if creator_id is None:
            QMessageBox.information(self, "Creator Language", "Selecciona un creador primero.")
            return
        try:
            snapshot = self.workspace.create_creator_language_profile_snapshot(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        QMessageBox.information(self, "Creator Language", f"Snapshot creado: {snapshot.id}")
        self.refresh()

    def _compare_latest(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if creator_id is None:
            return
        history = self.workspace.list_creator_language_profile_history(creator_id)
        if len(history) < 2:
            QMessageBox.information(self, "Creator Language", "Se necesitan al menos dos versiones para comparar.")
            return
        comparison = self.workspace.compare_creator_language_profiles(creator_id, history[-1].profile_version, history[0].profile_version)
        self.compare_output.setPlainText(
            "\n".join(
                [
                    f"Version base: {comparison.base_profile_version}",
                    f"Version comparada: {comparison.compare_profile_version}",
                    f"Secciones cambiadas: {', '.join(comparison.changed_sections) if comparison.changed_sections else 'ninguna'}",
                ]
            )
        )
