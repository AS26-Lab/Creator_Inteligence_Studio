"""Vista de sugerencias y preferencias confirmadas."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.domain.creator_preferences import CreatorPreferenceCandidateStatus
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


def _summary_from_json(payload: str | None) -> str:
    if not payload:
        return ""
    try:
        value = json.loads(payload)
    except Exception:
        return ""
    if not isinstance(value, dict):
        return ""
    return str(value.get("summary") or value.get("evidence_summary") or "")


class CreatorPreferencesView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        title = QLabel("Preferences")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Sugerencias estructurales locales, revisables y confirmables por el creador.")
        subtitle.setObjectName("MutedLabel")
        self.summary_label = QLabel("Sin datos.")
        self.summary_label.setObjectName("MutedLabel")
        self.summary_label.setWordWrap(True)

        self.refresh_button = QPushButton("Actualizar")
        self.synthesize_button = QPushButton("Sugerir preferencias")
        self.confirm_button = QPushButton("Recordar")
        self.edit_confirm_button = QPushButton("Editar y recordar")
        self.dismiss_button = QPushButton("No recordar")
        self.deactivate_button = QPushButton("Desactivar")
        self.reactivate_button = QPushButton("Reactivar")

        self.refresh_button.clicked.connect(self.refresh)
        self.synthesize_button.clicked.connect(self._synthesize)
        self.confirm_button.clicked.connect(self._confirm_selected)
        self.edit_confirm_button.clicked.connect(self._edit_and_confirm_selected)
        self.dismiss_button.clicked.connect(self._dismiss_selected)
        self.deactivate_button.clicked.connect(self._deactivate_selected)
        self.reactivate_button.clicked.connect(self._reactivate_selected)

        controls = QHBoxLayout()
        controls.addWidget(self.synthesize_button)
        controls.addWidget(self.confirm_button)
        controls.addWidget(self.edit_confirm_button)
        controls.addWidget(self.dismiss_button)
        controls.addWidget(self.deactivate_button)
        controls.addWidget(self.reactivate_button)
        controls.addStretch(1)
        controls.addWidget(self.refresh_button)

        self.candidates_table = QTableWidget(0, 8)
        self.candidates_table.setHorizontalHeaderLabels(["Tipo", "Valor", "Scope", "Evidencia", "Confianza", "Estado", "Resumen", "ID"])
        self.candidates_table.setColumnHidden(7, True)
        self.confirmed_table = QTableWidget(0, 7)
        self.confirmed_table.setHorizontalHeaderLabels(["Tipo", "Valor", "Scope", "Activo", "Confirmado por", "Origen", "ID"])
        self.confirmed_table.setColumnHidden(6, True)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.summary_label)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Candidate preferences"))
        layout.addWidget(self.candidates_table)
        layout.addWidget(QLabel("Confirmed preferences"))
        layout.addWidget(self.confirmed_table)

        self.refresh()

    def _selected_creator_id(self) -> str | None:
        return self.workspace.selected_creator_id

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            self.summary_label.setText("Selecciona un creador para ver sugerencias.")
            self.candidates_table.setRowCount(0)
            self.confirmed_table.setRowCount(0)
            return
        try:
            self.workspace.synthesize_creator_preferences(creator_id)
            snapshot = self.workspace.get_creator_preference_snapshot(creator_id)
            candidates = self.workspace.list_creator_preference_candidates(creator_id)
            confirmed = self.workspace.list_creator_confirmed_preferences(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            self.summary_label.setText(str(exc))
            self.candidates_table.setRowCount(0)
            self.confirmed_table.setRowCount(0)
            return
        self.summary_label.setText(
            f"Candidatas: {snapshot.candidate_count} | activas: {snapshot.active_candidate_count} | confirmadas: {snapshot.active_confirmed_count} | descartadas: {snapshot.dismissed_candidate_count}"
        )
        self.candidates_table.setRowCount(0)
        for row_index, candidate in enumerate(candidates):
            self.candidates_table.insertRow(row_index)
            values = [
                candidate.preference_type.value,
                candidate.proposed_value,
                candidate.scope.value,
                candidate.evidence_count,
                candidate.confidence.value,
                candidate.status.value,
                _summary_from_json(candidate.explanation_json),
                candidate.id,
            ]
            for column, value in enumerate(values):
                self.candidates_table.setItem(row_index, column, _item(value))
        self.candidates_table.resizeColumnsToContents()
        self.confirmed_table.setRowCount(0)
        for row_index, preference in enumerate(confirmed):
            try:
                value_payload = json.loads(preference.value_json or "{}")
            except Exception:
                value_payload = {}
            value_text = value_payload.get("raw_text") or value_payload.get("direction") or preference.value_json
            origin = ""
            try:
                provenance = json.loads(preference.provenance_json or "{}")
                origin = str(provenance.get("origin") or "")
            except Exception:
                origin = ""
            self.confirmed_table.insertRow(row_index)
            values = [
                preference.preference_type.value,
                value_text,
                preference.scope.value,
                "si" if preference.active else "no",
                preference.confirmed_by,
                origin,
                preference.id,
            ]
            for column, value in enumerate(values):
                self.confirmed_table.setItem(row_index, column, _item(value))
        self.confirmed_table.resizeColumnsToContents()

    def _candidate_id_from_selection(self) -> str | None:
        rows = self.candidates_table.selectionModel().selectedRows() if self.candidates_table.selectionModel() else []
        if not rows:
            return None
        item = self.candidates_table.item(rows[0].row(), 7)
        return None if item is None else item.text()

    def _preference_id_from_selection(self) -> str | None:
        rows = self.confirmed_table.selectionModel().selectedRows() if self.confirmed_table.selectionModel() else []
        if not rows:
            return None
        item = self.confirmed_table.item(rows[0].row(), 6)
        return None if item is None else item.text()

    def _synthesize(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Preferences", "Selecciona un creador primero.")
            return
        try:
            self.workspace.synthesize_creator_preferences(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()

    def _confirm_selected(self) -> None:
        candidate_id = self._candidate_id_from_selection()
        if candidate_id is None:
            return
        try:
            self.workspace.confirm_creator_preference_candidate(candidate_id, confirmed_by="creator")
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()

    def _edit_and_confirm_selected(self) -> None:
        candidate_id = self._candidate_id_from_selection()
        if candidate_id is None:
            return
        candidate = self.workspace.get_creator_preference_candidate(candidate_id)
        if candidate is None:
            return
        value, accepted = QInputDialog.getText(
            self,
            "Editar preferencia",
            "Ajusta el valor final de la preferencia:",
            text=str(candidate.proposed_value),
        )
        if not accepted:
            return
        try:
            self.workspace.edit_and_confirm_creator_preference_candidate(candidate_id, confirmed_by="creator", edited_value=value.strip() or candidate.proposed_value)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()

    def _dismiss_selected(self) -> None:
        candidate_id = self._candidate_id_from_selection()
        if candidate_id is None:
            return
        reason, accepted = QInputDialog.getText(self, "No recordar", "Motivo breve:", text="No recordar")
        if not accepted:
            return
        try:
            self.workspace.dismiss_creator_preference_candidate(candidate_id, dismissed_by="creator", reason=reason.strip() or "No recordar")
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()

    def _deactivate_selected(self) -> None:
        preference_id = self._preference_id_from_selection()
        if preference_id is None:
            return
        try:
            self.workspace.deactivate_creator_preference(preference_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()

    def _reactivate_selected(self) -> None:
        preference_id = self._preference_id_from_selection()
        if preference_id is None:
            return
        try:
            self.workspace.reactivate_creator_preference(preference_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Preferences", str(exc))
            return
        self.refresh()
