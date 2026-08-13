"""Vista principal de Creator Memory."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from .creator_preferences_view import CreatorPreferencesView


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class CreatorMemoryView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        self.tabs = QTabWidget()
        self.profile_tab = QWidget()
        self.traits_tab = QWidget()
        self.vocabulary_tab = QWidget()
        self.examples_tab = QWidget()
        self.rules_tab = QWidget()
        self.limits_tab = QWidget()
        self.objectives_tab = QWidget()
        self.evidence_tab = QWidget()
        self.history_tab = QWidget()
        self.preferences_tab = QWidget()
        self.tabs.addTab(self.profile_tab, "Profile")
        self.tabs.addTab(self.traits_tab, "Traits")
        self.tabs.addTab(self.vocabulary_tab, "Vocabulary")
        self.tabs.addTab(self.examples_tab, "Examples")
        self.tabs.addTab(self.rules_tab, "Style Rules")
        self.tabs.addTab(self.limits_tab, "Limits")
        self.tabs.addTab(self.objectives_tab, "Objectives")
        self.tabs.addTab(self.evidence_tab, "Evidence")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.preferences_tab, "Preferences")

        self._build_profile_tab()
        self._build_traits_tab()
        self._build_vocabulary_tab()
        self._build_examples_tab()
        self._build_rules_tab()
        self._build_limits_tab()
        self._build_objectives_tab()
        self._build_evidence_tab()
        self._build_history_tab()
        self._build_preferences_tab()

        title = QLabel("Creator Memory")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Memoria creativa estructurada, editable, versionada y trazable.")
        subtitle.setObjectName("MutedLabel")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)

        header = QHBoxLayout()
        self.creator_label = QLabel("Creador activo: ninguno")
        self.creator_label.setObjectName("MutedLabel")
        header.addWidget(self.creator_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(header)
        layout.addWidget(self.tabs)

        self.refresh()

    def _selected_creator_id(self) -> str | None:
        return self.workspace.selected_creator_id

    def _build_profile_tab(self) -> None:
        from .creator_profile_view import CreatorProfileView

        self.profile_view = CreatorProfileView(self.workspace)
        layout = QVBoxLayout(self.profile_tab)
        layout.addWidget(self.profile_view)

    def _build_traits_tab(self) -> None:
        self.traits_table = QTableWidget(0, 8)
        self.traits_table.setHorizontalHeaderLabels(["Tipo", "Clave", "Nombre", "Scope", "Plataforma", "Confianza", "Estado", "ID"])
        self.traits_table.setColumnHidden(7, True)
        self.trait_type = QComboBox()
        self.trait_type.addItems([
            "tone",
            "formality",
            "humor",
            "vocabulary",
            "phrase_pattern",
            "filler_word",
            "narrative_rhythm",
            "sentence_length",
            "explanation_style",
            "analogy_style",
            "opening_style",
            "closing_style",
            "callback_style",
            "punchline_style",
            "exaggeration_level",
            "emotional_expression",
            "call_to_action_style",
            "editing_preference",
            "visual_preference",
            "pacing_preference",
            "topic_preference",
            "platform_behavior",
            "content_structure",
            "personal_boundary",
            "other",
        ])
        self.trait_key = QLineEdit()
        self.trait_display_name = QLineEdit()
        self.trait_platform = QLineEdit()
        self.trait_content_type = QLineEdit()
        self.trait_scope = QComboBox()
        self.trait_scope.addItems(["creator_general", "platform_specific", "content_type_specific", "topic_specific", "format_specific"])
        self.trait_confidence = QComboBox()
        self.trait_confidence.addItems(["very_low", "low", "medium", "high"])
        self.trait_status = QComboBox()
        self.trait_status.addItems(["observed", "provisional", "confirmed", "rejected", "deprecated", "needs_more_data"])
        self.trait_create = QPushButton("Crear trait")
        self.trait_archive = QPushButton("Archivar seleccionado")
        self.trait_create.clicked.connect(self._create_trait)
        self.trait_archive.clicked.connect(self._archive_trait)
        controls = QGridLayout()
        controls.addWidget(QLabel("Tipo"), 0, 0)
        controls.addWidget(self.trait_type, 0, 1)
        controls.addWidget(QLabel("Clave"), 0, 2)
        controls.addWidget(self.trait_key, 0, 3)
        controls.addWidget(QLabel("Nombre"), 1, 0)
        controls.addWidget(self.trait_display_name, 1, 1)
        controls.addWidget(QLabel("Scope"), 1, 2)
        controls.addWidget(self.trait_scope, 1, 3)
        controls.addWidget(QLabel("Plataforma"), 2, 0)
        controls.addWidget(self.trait_platform, 2, 1)
        controls.addWidget(QLabel("content_type"), 2, 2)
        controls.addWidget(self.trait_content_type, 2, 3)
        controls.addWidget(QLabel("Confianza"), 3, 0)
        controls.addWidget(self.trait_confidence, 3, 1)
        controls.addWidget(QLabel("Estado"), 3, 2)
        controls.addWidget(self.trait_status, 3, 3)
        controls.addWidget(self.trait_create, 4, 0)
        controls.addWidget(self.trait_archive, 4, 1)
        layout = QVBoxLayout(self.traits_tab)
        layout.addLayout(controls)
        layout.addWidget(self.traits_table)

    def _build_vocabulary_tab(self) -> None:
        self.vocabulary_table = QTableWidget(0, 7)
        self.vocabulary_table.setHorizontalHeaderLabels(["Termino", "Tipo", "Frecuencia", "Plataforma", "Contenido", "Estado", "ID"])
        self.vocabulary_table.setColumnHidden(6, True)
        self.vocabulary_term = QLineEdit()
        self.vocabulary_type = QComboBox()
        self.vocabulary_type.addItems([
            "frequent_term",
            "catchphrase",
            "filler_word",
            "recurring_expression",
            "reference",
            "preferred_term",
            "avoided_term",
            "prohibited_term",
            "platform_specific_term",
        ])
        self.vocabulary_platform = QLineEdit()
        self.vocabulary_content_type = QLineEdit()
        self.vocabulary_status = QComboBox()
        self.vocabulary_status.addItems(["active", "rejected", "deprecated", "needs_more_data"])
        self.vocabulary_create = QPushButton("Agregar vocabulario")
        self.vocabulary_create.clicked.connect(self._create_vocabulary)
        controls = QGridLayout()
        controls.addWidget(QLabel("Termino"), 0, 0)
        controls.addWidget(self.vocabulary_term, 0, 1)
        controls.addWidget(QLabel("Tipo"), 0, 2)
        controls.addWidget(self.vocabulary_type, 0, 3)
        controls.addWidget(QLabel("Plataforma"), 1, 0)
        controls.addWidget(self.vocabulary_platform, 1, 1)
        controls.addWidget(QLabel("content_type"), 1, 2)
        controls.addWidget(self.vocabulary_content_type, 1, 3)
        controls.addWidget(QLabel("Estado"), 2, 0)
        controls.addWidget(self.vocabulary_status, 2, 1)
        controls.addWidget(self.vocabulary_create, 2, 3)
        layout = QVBoxLayout(self.vocabulary_tab)
        layout.addLayout(controls)
        layout.addWidget(self.vocabulary_table)

    def _build_examples_tab(self) -> None:
        self.examples_table = QTableWidget(0, 8)
        self.examples_table.setHorizontalHeaderLabels(["Titulo", "Tipo", "Categoria", "Plataforma", "Aprobacion", "Contexto", "Estado", "ID"])
        self.examples_table.setColumnHidden(7, True)
        self.example_title = QLineEdit()
        self.example_type = QComboBox()
        self.example_type.addItems([
            "represents_creator",
            "does_not_represent_creator",
            "approved_style",
            "rejected_style",
            "good_hook",
            "bad_hook",
            "good_explanation",
            "bad_explanation",
            "good_humor",
            "forced_humor",
            "preferred_edit",
            "rejected_edit",
            "preferred_copy",
            "rejected_copy",
            "preferred_title_direction",
            "rejected_title_direction",
            "other",
        ])
        self.example_category = QLineEdit()
        self.example_source_type = QLineEdit()
        self.example_platform = QLineEdit()
        self.example_approval = QComboBox()
        self.example_approval.addItems(["approved", "rejected", "pending", "needs_review"])
        self.example_create = QPushButton("Crear ejemplo")
        self.example_create.clicked.connect(self._create_example)
        controls = QGridLayout()
        controls.addWidget(QLabel("Titulo"), 0, 0)
        controls.addWidget(self.example_title, 0, 1)
        controls.addWidget(QLabel("Tipo"), 0, 2)
        controls.addWidget(self.example_type, 0, 3)
        controls.addWidget(QLabel("Categoria"), 1, 0)
        controls.addWidget(self.example_category, 1, 1)
        controls.addWidget(QLabel("Source type"), 1, 2)
        controls.addWidget(self.example_source_type, 1, 3)
        controls.addWidget(QLabel("Plataforma"), 2, 0)
        controls.addWidget(self.example_platform, 2, 1)
        controls.addWidget(QLabel("Aprobacion"), 2, 2)
        controls.addWidget(self.example_approval, 2, 3)
        controls.addWidget(self.example_create, 3, 0)
        layout = QVBoxLayout(self.examples_tab)
        layout.addLayout(controls)
        layout.addWidget(self.examples_table)

    def _build_rules_tab(self) -> None:
        self.rules_table = QTableWidget(0, 7)
        self.rules_table.setHorizontalHeaderLabels(["Regla", "Scope", "Plataforma", "Contenido", "Confianza", "Estado", "ID"])
        self.rules_table.setColumnHidden(6, True)
        self.rule_type = QComboBox()
        self.rule_type.addItems([
            "observed",
            "provisional",
            "confirmed",
            "rejected",
            "deprecated",
            "needs_more_data",
        ])
        self.rule_statement = QLineEdit()
        self.rule_scope = QComboBox()
        self.rule_scope.addItems(["creator_general", "platform_specific", "content_type_specific", "topic_specific", "format_specific"])
        self.rule_platform = QLineEdit()
        self.rule_content_type = QLineEdit()
        self.rule_create = QPushButton("Crear regla")
        self.rule_create.clicked.connect(self._create_rule)
        controls = QGridLayout()
        controls.addWidget(QLabel("Tipo"), 0, 0)
        controls.addWidget(self.rule_type, 0, 1)
        controls.addWidget(QLabel("Scope"), 0, 2)
        controls.addWidget(self.rule_scope, 0, 3)
        controls.addWidget(QLabel("Statement"), 1, 0)
        controls.addWidget(self.rule_statement, 1, 1, 1, 3)
        controls.addWidget(QLabel("Plataforma"), 2, 0)
        controls.addWidget(self.rule_platform, 2, 1)
        controls.addWidget(QLabel("content_type"), 2, 2)
        controls.addWidget(self.rule_content_type, 2, 3)
        controls.addWidget(self.rule_create, 3, 0)
        layout = QVBoxLayout(self.rules_tab)
        layout.addLayout(controls)
        layout.addWidget(self.rules_table)

    def _build_limits_tab(self) -> None:
        self.limits_table = QTableWidget(0, 6)
        self.limits_table.setHorizontalHeaderLabels(["Tipo", "Categoria", "Severidad", "Scope", "Plataforma", "ID"])
        self.limits_table.setColumnHidden(5, True)
        self.limit_type = QComboBox()
        self.limit_type.addItems([
            "personal_boundary",
            "sensitive_topic",
            "prohibited_claim",
            "prohibited_phrase",
            "brand_safety",
            "privacy",
            "legal",
            "platform_specific",
            "other",
        ])
        self.limit_category = QLineEdit()
        self.limit_statement = QLineEdit()
        self.limit_severity = QComboBox()
        self.limit_severity.addItems(["note", "caution", "strong", "absolute"])
        self.limit_scope = QComboBox()
        self.limit_scope.addItems(["creator_general", "platform_specific", "content_type_specific", "topic_specific", "format_specific"])
        self.limit_platform = QLineEdit()
        self.limit_create = QPushButton("Crear limite")
        self.limit_create.clicked.connect(self._create_limit)
        controls = QGridLayout()
        controls.addWidget(QLabel("Tipo"), 0, 0)
        controls.addWidget(self.limit_type, 0, 1)
        controls.addWidget(QLabel("Categoria"), 0, 2)
        controls.addWidget(self.limit_category, 0, 3)
        controls.addWidget(QLabel("Statement"), 1, 0)
        controls.addWidget(self.limit_statement, 1, 1, 1, 3)
        controls.addWidget(QLabel("Severidad"), 2, 0)
        controls.addWidget(self.limit_severity, 2, 1)
        controls.addWidget(QLabel("Scope"), 2, 2)
        controls.addWidget(self.limit_scope, 2, 3)
        controls.addWidget(QLabel("Plataforma"), 3, 0)
        controls.addWidget(self.limit_platform, 3, 1)
        controls.addWidget(self.limit_create, 3, 3)
        layout = QVBoxLayout(self.limits_tab)
        layout.addLayout(controls)
        layout.addWidget(self.limits_table)

    def _build_objectives_tab(self) -> None:
        self.objectives_summary = QLabel("Sin objetivos.")
        self.objectives_summary.setWordWrap(True)
        self.objectives_summary.setObjectName("MutedLabel")
        self.objectives_table = QTableWidget(0, 5)
        self.objectives_table.setHorizontalHeaderLabels(["Tipo", "Plataforma", "Prioridad", "Estado", "Notas"])
        layout = QVBoxLayout(self.objectives_tab)
        layout.addWidget(self.objectives_summary)
        layout.addWidget(self.objectives_table)

    def _build_evidence_tab(self) -> None:
        self.evidence_table = QTableWidget(0, 7)
        self.evidence_table.setHorizontalHeaderLabels(["Trait", "Source", "Tipo", "Publicacion", "Video", "Peso", "ID"])
        self.evidence_table.setColumnHidden(6, True)
        layout = QVBoxLayout(self.evidence_tab)
        layout.addWidget(self.evidence_table)

    def _build_history_tab(self) -> None:
        self.snapshots_table = QTableWidget(0, 5)
        self.snapshots_table.setHorizontalHeaderLabels(["Version", "Estado", "Fingerprint", "Creado", "ID"])
        self.snapshots_table.setColumnHidden(4, True)
        self.feedback_table = QTableWidget(0, 5)
        self.feedback_table.setHorizontalHeaderLabels(["Tipo", "Target", "Reason", "Creado", "ID"])
        self.feedback_table.setColumnHidden(4, True)
        self.snapshot_create = QPushButton("Crear snapshot")
        self.snapshot_compare = QPushButton("Comparar seleccionados")
        self.snapshot_create.clicked.connect(self._create_snapshot)
        self.snapshot_compare.clicked.connect(self._compare_snapshots)
        controls = QHBoxLayout()
        controls.addWidget(self.snapshot_create)
        controls.addWidget(self.snapshot_compare)
        controls.addStretch(1)
        layout = QVBoxLayout(self.history_tab)
        layout.addLayout(controls)
        layout.addWidget(self.snapshots_table)
        layout.addWidget(self.feedback_table)

    def _build_preferences_tab(self) -> None:
        self.preferences_view = CreatorPreferencesView(self.workspace)
        layout = QVBoxLayout(self.preferences_tab)
        layout.addWidget(self.preferences_view)

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            self.creator_label.setText("Creador activo: ninguno")
            self._clear_tables()
            self.objectives_summary.setText("Sin objetivos.")
            return

        self.creator_label.setText(f"Creador activo: {creator_id}")
        try:
            detail = self.workspace.get_creator_memory_profile_detail(creator_id)
        except Exception:
            detail = None
        if detail is None:
            self.profile_view.refresh()
            self._clear_tables()
            self.objectives_summary.setText("Sin objetivos.")
            return

        self.profile_view.refresh()
        self._populate_traits(detail.traits)
        self._populate_vocabulary(detail.vocabulary)
        self._populate_examples(detail.examples)
        self._populate_rules(detail.rules)
        self._populate_limits(detail.limits)
        self._populate_evidence(detail.evidence)
        self._populate_snapshots(detail.snapshots)
        self._populate_feedback(detail.feedback)
        self._populate_objectives(detail.profile.objectives_json)
        self.preferences_view.refresh()

    def _clear_tables(self) -> None:
        for table in (
            self.traits_table,
            self.vocabulary_table,
            self.examples_table,
            self.rules_table,
            self.limits_table,
            self.evidence_table,
            self.snapshots_table,
            self.feedback_table,
            self.objectives_table,
        ):
            table.setRowCount(0)

    def _populate_traits(self, traits) -> None:
        self.traits_table.setRowCount(0)
        for row_index, trait in enumerate(traits):
            self.traits_table.insertRow(row_index)
            values = [trait.trait_type.value, trait.trait_key, trait.display_name, trait.scope.value, trait.platform or "", trait.confidence_level.value, trait.status.value, trait.id]
            for column, value in enumerate(values):
                self.traits_table.setItem(row_index, column, _item(value))
        self.traits_table.resizeColumnsToContents()

    def _populate_vocabulary(self, vocabulary) -> None:
        self.vocabulary_table.setRowCount(0)
        for row_index, entry in enumerate(vocabulary):
            self.vocabulary_table.insertRow(row_index)
            values = [entry.term, entry.vocabulary_type.value, entry.frequency_count, entry.platform or "", entry.content_type or "", entry.status.value, entry.id]
            for column, value in enumerate(values):
                self.vocabulary_table.setItem(row_index, column, _item(value))
        self.vocabulary_table.resizeColumnsToContents()

    def _populate_examples(self, examples) -> None:
        self.examples_table.setRowCount(0)
        for row_index, example in enumerate(examples):
            self.examples_table.insertRow(row_index)
            values = [example.title, example.example_type.value, example.category, example.platform or "", example.approval_status.value, example.text_content or example.source_type, example.approval_status.value, example.id]
            for column, value in enumerate(values):
                self.examples_table.setItem(row_index, column, _item(value))
        self.examples_table.resizeColumnsToContents()

    def _populate_rules(self, rules) -> None:
        self.rules_table.setRowCount(0)
        for row_index, rule in enumerate(rules):
            self.rules_table.insertRow(row_index)
            values = [rule.statement, rule.scope.value, rule.platform or "", rule.content_type or "", rule.confidence_level.value, rule.status.value, rule.id]
            for column, value in enumerate(values):
                self.rules_table.setItem(row_index, column, _item(value))
        self.rules_table.resizeColumnsToContents()

    def _populate_limits(self, limits) -> None:
        self.limits_table.setRowCount(0)
        for row_index, limit in enumerate(limits):
            self.limits_table.insertRow(row_index)
            values = [limit.limit_type.value, limit.category, limit.severity.value, limit.scope.value, limit.platform or "", limit.id]
            for column, value in enumerate(values):
                self.limits_table.setItem(row_index, column, _item(value))
        self.limits_table.resizeColumnsToContents()

    def _populate_objectives(self, objectives_json: str) -> None:
        try:
            objectives = json.loads(objectives_json or "[]")
        except Exception:
            objectives = []
        self.objectives_table.setRowCount(0)
        for row_index, objective in enumerate(objectives):
            self.objectives_table.insertRow(row_index)
            values = [
                objective.get("type") or objective.get("objective_type") or "",
                objective.get("platform") or "",
                objective.get("priority") or "",
                objective.get("status") or "",
                objective.get("notes") or "",
            ]
            for column, value in enumerate(values):
                self.objectives_table.setItem(row_index, column, _item(value))
        self.objectives_table.resizeColumnsToContents()
        self.objectives_summary.setText(f"Objetivos activos: {len(objectives)}")

    def _populate_evidence(self, evidence) -> None:
        self.evidence_table.setRowCount(0)
        for row_index, item in enumerate(evidence):
            self.evidence_table.insertRow(row_index)
            values = [item.trait_id, item.source_type, item.evidence_type.value, item.publication_id or "", item.video_asset_id or "", item.weight, item.id]
            for column, value in enumerate(values):
                self.evidence_table.setItem(row_index, column, _item(value))
        self.evidence_table.resizeColumnsToContents()

    def _populate_snapshots(self, snapshots) -> None:
        self.snapshots_table.setRowCount(0)
        for row_index, snapshot in enumerate(snapshots):
            self.snapshots_table.insertRow(row_index)
            values = [snapshot.profile_version, snapshot.status.value, snapshot.source_fingerprint, snapshot.created_at.isoformat(), snapshot.id]
            for column, value in enumerate(values):
                self.snapshots_table.setItem(row_index, column, _item(value))
        self.snapshots_table.resizeColumnsToContents()

    def _populate_feedback(self, feedback) -> None:
        self.feedback_table.setRowCount(0)
        for row_index, item in enumerate(feedback):
            self.feedback_table.insertRow(row_index)
            values = [item.feedback_type.value, f"{item.target_type}:{item.target_id}", item.reason, item.created_at.isoformat(), item.id]
            for column, value in enumerate(values):
                self.feedback_table.setItem(row_index, column, _item(value))
        self.feedback_table.resizeColumnsToContents()

    def _create_trait(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_trait(
                creator_id=creator_id,
                trait_type=self.trait_type.currentText(),
                trait_key=self.trait_key.text().strip() or self.trait_display_name.text().strip() or "trait",
                display_name=self.trait_display_name.text().strip() or self.trait_key.text().strip() or "Trait",
                scope=self.trait_scope.currentText(),
                platform=self.trait_platform.text().strip() or None,
                content_type=self.trait_content_type.text().strip() or None,
                confidence_level=self.trait_confidence.currentText(),
                status=self.trait_status.currentText(),
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _archive_trait(self) -> None:
        rows = self.traits_table.selectionModel().selectedRows() if self.traits_table.selectionModel() else []
        if not rows:
            return
        item = self.traits_table.item(rows[0].row(), 7)
        if item is None:
            return
        try:
            self.workspace.archive_creator_trait(item.text())
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _create_vocabulary(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_vocabulary_entry(
                creator_id=creator_id,
                term=self.vocabulary_term.text().strip() or "term",
                vocabulary_type=self.vocabulary_type.currentText(),
                platform=self.vocabulary_platform.text().strip() or None,
                content_type=self.vocabulary_content_type.text().strip() or None,
                status=self.vocabulary_status.currentText(),
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _create_example(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_example(
                creator_id=creator_id,
                example_type=self.example_type.currentText(),
                category=self.example_category.text().strip() or "general",
                title=self.example_title.text().strip() or "Example",
                source_type=self.example_source_type.text().strip() or "manual_observation",
                platform=self.example_platform.text().strip() or None,
                approval_status=self.example_approval.currentText(),
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _create_rule(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_style_rule(
                creator_id=creator_id,
                rule_type=self.rule_type.currentText(),
                statement=self.rule_statement.text().strip() or "Rule",
                scope=self.rule_scope.currentText(),
                platform=self.rule_platform.text().strip() or None,
                content_type=self.rule_content_type.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        self.refresh()

    def _create_limit(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Memory", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_limit(
                creator_id=creator_id,
                limit_type=self.limit_type.currentText(),
                category=self.limit_category.text().strip() or "general",
                statement=self.limit_statement.text().strip() or "Limit",
                severity=self.limit_severity.currentText(),
                scope=self.limit_scope.currentText(),
                platform=self.limit_platform.text().strip() or None,
            )
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

    def _compare_snapshots(self) -> None:
        rows = self.snapshots_table.selectionModel().selectedRows() if self.snapshots_table.selectionModel() else []
        if len(rows) < 2:
            QMessageBox.information(self, "Creator Memory", "Selecciona dos snapshots para comparar.")
            return
        first = self.snapshots_table.item(rows[0].row(), 4)
        second = self.snapshots_table.item(rows[1].row(), 4)
        if first is None or second is None:
            return
        creator_id = self._selected_creator_id()
        if creator_id is None:
            return
        try:
            comparison = self.workspace.compare_creator_profile_snapshots(creator_id, first.text(), second.text())
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Memory", str(exc))
            return
        QMessageBox.information(self, "Creator Memory", comparison.summary)
