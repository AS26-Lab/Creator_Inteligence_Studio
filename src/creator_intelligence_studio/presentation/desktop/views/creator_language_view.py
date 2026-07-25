"""Vista principal de Creator Language Analysis."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from .narrative_profile_view import NarrativeProfileView


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class CreatorLanguageView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.tabs = QTabWidget()
        self.corpus_tab = QWidget()
        self.metrics_tab = QWidget()
        self.vocabulary_tab = QWidget()
        self.patterns_tab = QWidget()
        self.narrative_tab = QWidget()
        self.rhythm_tab = QWidget()
        self.platform_tab = QWidget()
        self.candidates_tab = QWidget()
        self.history_tab = QWidget()
        self.tabs.addTab(self.corpus_tab, "Corpus")
        self.tabs.addTab(self.metrics_tab, "Language Metrics")
        self.tabs.addTab(self.vocabulary_tab, "Vocabulary")
        self.tabs.addTab(self.patterns_tab, "Phrase Patterns")
        self.tabs.addTab(self.narrative_tab, "Narrative Structure")
        self.tabs.addTab(self.rhythm_tab, "Rhythm & Pauses")
        self.tabs.addTab(self.platform_tab, "Platform Differences")
        self.tabs.addTab(self.candidates_tab, "Candidates")
        self.tabs.addTab(self.history_tab, "Profile History")
        self._build_corpus_tab()
        self._build_metrics_tab()
        self._build_vocabulary_tab()
        self._build_patterns_tab()
        self._build_narrative_tab()
        self._build_rhythm_tab()
        self._build_platform_tab()
        self._build_candidates_tab()
        self._build_history_tab()

        title = QLabel("Creator Language")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Analisis local y determinista de lenguaje, narrativa y ritmo por creador.")
        subtitle.setObjectName("MutedLabel")
        self.creator_label = QLabel("Creador activo: ninguno")
        self.creator_label.setObjectName("MutedLabel")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)

        header = QHBoxLayout()
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

    def _build_corpus_tab(self) -> None:
        self.corpora_table = QTableWidget(0, 10)
        self.corpora_table.setHorizontalHeaderLabels(["Nombre", "Idioma", "Plataforma", "Tipo", "Tema", "Fuentes", "Tokens", "Estado", "Huella", "ID"])
        self.corpora_table.setColumnHidden(9, True)
        self.corpus_name = QLineEdit()
        self.corpus_description = QLineEdit()
        self.corpus_language = QLineEdit("es")
        self.corpus_platform = QLineEdit()
        self.corpus_content_type = QLineEdit()
        self.corpus_topic = QLineEdit()
        self.corpus_create = QPushButton("Crear corpus")
        self.corpus_analyze = QPushButton("Analizar corpus")
        self.corpus_snapshot = QPushButton("Crear snapshot")
        self.corpus_create.clicked.connect(self._create_corpus)
        self.corpus_analyze.clicked.connect(self._analyze_corpus)
        self.corpus_snapshot.clicked.connect(self._create_snapshot)
        controls = QGridLayout()
        controls.addWidget(QLabel("Nombre"), 0, 0)
        controls.addWidget(self.corpus_name, 0, 1)
        controls.addWidget(QLabel("Descripcion"), 0, 2)
        controls.addWidget(self.corpus_description, 0, 3)
        controls.addWidget(QLabel("Idioma"), 1, 0)
        controls.addWidget(self.corpus_language, 1, 1)
        controls.addWidget(QLabel("Plataforma"), 1, 2)
        controls.addWidget(self.corpus_platform, 1, 3)
        controls.addWidget(QLabel("Tipo"), 2, 0)
        controls.addWidget(self.corpus_content_type, 2, 1)
        controls.addWidget(QLabel("Tema"), 2, 2)
        controls.addWidget(self.corpus_topic, 2, 3)
        controls.addWidget(self.corpus_create, 3, 0)
        controls.addWidget(self.corpus_analyze, 3, 1)
        controls.addWidget(self.corpus_snapshot, 3, 2)

        self.sources_table = QTableWidget(0, 9)
        self.sources_table.setHorizontalHeaderLabels(["Tipo", "Source ID", "Plataforma", "Tipo contenido", "Idioma", "Incluida", "Razon", "Texto", "ID"])
        self.sources_table.setColumnHidden(8, True)
        self.source_type = QComboBox()
        self.source_type.addItems([
            "transcription",
            "transcript_segment",
            "subtitle_track",
            "subtitle_cue",
            "publication_title",
            "publication_caption",
            "publication_copy",
            "memory_example",
            "manual_text",
        ])
        self.source_id = QLineEdit()
        self.source_text = QLineEdit()
        self.source_platform = QLineEdit()
        self.source_content_type = QLineEdit()
        self.source_topic = QLineEdit()
        self.source_language = QLineEdit("es")
        self.source_include_status = QComboBox()
        self.source_include_status.addItems(["included", "excluded", "pending"])
        self.source_reason = QLineEdit()
        self.source_add = QPushButton("Agregar fuente")
        self.source_remove = QPushButton("Excluir seleccionada")
        self.source_add.clicked.connect(self._add_source)
        self.source_remove.clicked.connect(self._remove_source)
        source_controls = QGridLayout()
        source_controls.addWidget(QLabel("Source type"), 0, 0)
        source_controls.addWidget(self.source_type, 0, 1)
        source_controls.addWidget(QLabel("Source ID"), 0, 2)
        source_controls.addWidget(self.source_id, 0, 3)
        source_controls.addWidget(QLabel("Texto"), 1, 0)
        source_controls.addWidget(self.source_text, 1, 1, 1, 3)
        source_controls.addWidget(QLabel("Plataforma"), 2, 0)
        source_controls.addWidget(self.source_platform, 2, 1)
        source_controls.addWidget(QLabel("Tipo contenido"), 2, 2)
        source_controls.addWidget(self.source_content_type, 2, 3)
        source_controls.addWidget(QLabel("Tema"), 3, 0)
        source_controls.addWidget(self.source_topic, 3, 1)
        source_controls.addWidget(QLabel("Idioma"), 3, 2)
        source_controls.addWidget(self.source_language, 3, 3)
        source_controls.addWidget(QLabel("Estado"), 4, 0)
        source_controls.addWidget(self.source_include_status, 4, 1)
        source_controls.addWidget(QLabel("Razon"), 4, 2)
        source_controls.addWidget(self.source_reason, 4, 3)
        source_controls.addWidget(self.source_add, 5, 0)
        source_controls.addWidget(self.source_remove, 5, 1)

        self.corpus_empty = EmptyStateWidget("Sin corpus", "Crea un corpus y agrega fuentes locales seleccionadas.")
        layout = QVBoxLayout(self.corpus_tab)
        layout.addLayout(controls)
        layout.addWidget(self.corpus_empty)
        layout.addWidget(self.corpora_table)
        layout.addLayout(source_controls)
        layout.addWidget(self.sources_table)

    def _build_metrics_tab(self) -> None:
        self.metrics_table = QTableWidget(0, 8)
        self.metrics_table.setHorizontalHeaderLabels(["Metrica", "Grupo", "Valor", "Unidad", "Scope", "Plataforma", "Confianza", "Muestra"])
        layout = QVBoxLayout(self.metrics_tab)
        layout.addWidget(self.metrics_table)

    def _build_vocabulary_tab(self) -> None:
        self.vocabulary_table = QTableWidget(0, 7)
        self.vocabulary_table.setHorizontalHeaderLabels(["Patron", "Titulo", "Descripcion", "Plataforma", "Tipo contenido", "Confianza", "ID"])
        self.vocabulary_table.setColumnHidden(6, True)
        layout = QVBoxLayout(self.vocabulary_tab)
        layout.addWidget(self.vocabulary_table)

    def _build_patterns_tab(self) -> None:
        self.patterns_table = QTableWidget(0, 7)
        self.patterns_table.setHorizontalHeaderLabels(["Tipo", "Clave", "Titulo", "Scope", "Confianza", "Estado", "ID"])
        self.patterns_table.setColumnHidden(6, True)
        layout = QVBoxLayout(self.patterns_tab)
        layout.addWidget(self.patterns_table)

    def _build_narrative_tab(self) -> None:
        self.narrative_view = NarrativeProfileView(self.workspace)
        layout = QVBoxLayout(self.narrative_tab)
        layout.addWidget(self.narrative_view)

    def _build_rhythm_tab(self) -> None:
        self.rhythm_table = QTableWidget(0, 6)
        self.rhythm_table.setHorizontalHeaderLabels(["Metrica", "Valor", "Unidad", "Scope", "Confianza", "ID"])
        self.rhythm_table.setColumnHidden(5, True)
        layout = QVBoxLayout(self.rhythm_tab)
        layout.addWidget(self.rhythm_table)

    def _build_platform_tab(self) -> None:
        self.platform_table = QTableWidget(0, 7)
        self.platform_table.setHorizontalHeaderLabels(["Tipo", "Clave", "Titulo", "Plataforma", "Contenido", "Confianza", "ID"])
        self.platform_table.setColumnHidden(6, True)
        layout = QVBoxLayout(self.platform_tab)
        layout.addWidget(self.platform_table)

    def _build_candidates_tab(self) -> None:
        self.candidates_table = QTableWidget(0, 8)
        self.candidates_table.setHorizontalHeaderLabels(["Tipo", "Memoria", "Clave", "Valor propuesto", "Scope", "Confianza", "Estado", "ID"])
        self.candidates_table.setColumnHidden(7, True)
        self.candidate_decision = QComboBox()
        self.candidate_decision.addItems(["approve", "approve_with_changes", "reject", "needs_more_data"])
        self.candidate_reason = QLineEdit()
        self.candidate_modified_value = QLineEdit()
        self.candidate_review = QPushButton("Revisar candidato")
        self.candidate_review.clicked.connect(self._review_candidate)
        controls = QGridLayout()
        controls.addWidget(QLabel("Decision"), 0, 0)
        controls.addWidget(self.candidate_decision, 0, 1)
        controls.addWidget(QLabel("Razon"), 0, 2)
        controls.addWidget(self.candidate_reason, 0, 3)
        controls.addWidget(QLabel("Valor modificado"), 1, 0)
        controls.addWidget(self.candidate_modified_value, 1, 1, 1, 3)
        controls.addWidget(self.candidate_review, 2, 0)
        layout = QVBoxLayout(self.candidates_tab)
        layout.addLayout(controls)
        layout.addWidget(self.candidates_table)

    def _build_history_tab(self) -> None:
        self.history_view = NarrativeProfileView(self.workspace)
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.history_view)

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        if creator_id is None:
            for table in (
                self.corpora_table,
                self.sources_table,
                self.metrics_table,
                self.vocabulary_table,
                self.patterns_table,
                self.rhythm_table,
                self.platform_table,
                self.candidates_table,
            ):
                table.setRowCount(0)
            self.corpus_empty.show()
            self.narrative_view.refresh()
            self.history_view.refresh()
            return
        corpora = self.workspace.list_creator_language_corpora(creator_id)
        self.corpora_table.setRowCount(0)
        self.sources_table.setRowCount(0)
        if not corpora:
            self.corpus_empty.show()
        else:
            self.corpus_empty.hide()
        for row_index, corpus in enumerate(corpora):
            self.corpora_table.insertRow(row_index)
            values = [
                corpus.name,
                corpus.language,
                corpus.platform or "",
                corpus.content_type or "",
                corpus.topic or "",
                corpus.source_count,
                corpus.token_count,
                corpus.status.value,
                corpus.source_fingerprint[:16],
                corpus.id,
            ]
            for column, value in enumerate(values):
                self.corpora_table.setItem(row_index, column, _item(value))
            for source in self.workspace.list_creator_language_corpus_sources(corpus.id):
                source_row = self.sources_table.rowCount()
                self.sources_table.insertRow(source_row)
                values = [
                    source.source_type.value,
                    source.source_id,
                    source.platform or "",
                    source.content_type or "",
                    source.language,
                    source.include_status.value,
                    source.exclusion_reason or "",
                    source.text_snapshot[:120],
                    source.id,
                ]
                for column, value in enumerate(values):
                    self.sources_table.setItem(source_row, column, _item(value))
        latest_run = self.workspace.list_creator_language_analysis_runs(creator_id)
        metrics = self.workspace.list_creator_language_metrics(latest_run[0].id) if latest_run else []
        patterns = self.workspace.list_creator_language_patterns(creator_id, latest_run[0].id) if latest_run else []
        candidates = self.workspace.list_creator_language_candidates(creator_id)
        self.metrics_table.setRowCount(0)
        for row_index, metric in enumerate(metrics):
            self.metrics_table.insertRow(row_index)
            values = [
                metric.metric_key,
                metric.metric_group,
                metric.numeric_value if metric.numeric_value is not None else metric.text_value,
                metric.unit,
                metric.scope.value,
                metric.platform or "",
                metric.confidence_level.value,
                metric.sample_size,
            ]
            for column, value in enumerate(values):
                self.metrics_table.setItem(row_index, column, _item(value))
        self.vocabulary_table.setRowCount(0)
        self.patterns_table.setRowCount(0)
        self.rhythm_table.setRowCount(0)
        self.platform_table.setRowCount(0)
        for row_index, pattern in enumerate(patterns):
            pattern_row = [
                pattern.pattern_type.value,
                pattern.pattern_key,
                pattern.title,
                pattern.scope.value,
                pattern.confidence_level.value,
                pattern.status.value,
                pattern.id,
            ]
            self.patterns_table.insertRow(row_index)
            for column, value in enumerate(pattern_row):
                self.patterns_table.setItem(row_index, column, _item(value))
            if pattern.pattern_type.value in {"vocabulary_pattern", "phrase_pattern", "filler_pattern"}:
                vocab_row = self.vocabulary_table.rowCount()
                self.vocabulary_table.insertRow(vocab_row)
                vocab_values = [
                    pattern.pattern_key,
                    pattern.title,
                    pattern.description,
                    pattern.platform or "",
                    pattern.content_type or "",
                    pattern.confidence_level.value,
                    pattern.id,
                ]
                for column, value in enumerate(vocab_values):
                    self.vocabulary_table.setItem(vocab_row, column, _item(value))
            if pattern.pattern_type.value in {"pacing_pattern", "opening_pattern", "closing_pattern"}:
                rhythm_row = self.rhythm_table.rowCount()
                self.rhythm_table.insertRow(rhythm_row)
                rhythm_values = [
                    pattern.title,
                    pattern.frequency_count,
                    "count",
                    pattern.scope.value,
                    pattern.confidence_level.value,
                    pattern.id,
                ]
                for column, value in enumerate(rhythm_values):
                    self.rhythm_table.setItem(rhythm_row, column, _item(value))
            if pattern.pattern_type.value in {"platform_difference", "content_type_difference"}:
                platform_row = self.platform_table.rowCount()
                self.platform_table.insertRow(platform_row)
                platform_values = [
                    pattern.pattern_type.value,
                    pattern.pattern_key,
                    pattern.title,
                    pattern.platform or "",
                    pattern.content_type or "",
                    pattern.confidence_level.value,
                    pattern.id,
                ]
                for column, value in enumerate(platform_values):
                    self.platform_table.setItem(platform_row, column, _item(value))
        self.candidates_table.setRowCount(0)
        for row_index, candidate in enumerate(candidates):
            self.candidates_table.insertRow(row_index)
            values = [
                candidate.candidate_type,
                candidate.target_memory_type.value,
                candidate.proposed_key,
                candidate.proposed_value_json[:120],
                candidate.scope.value,
                candidate.confidence_level.value,
                candidate.status.value,
                candidate.id,
            ]
            for column, value in enumerate(values):
                self.candidates_table.setItem(row_index, column, _item(value))
        self.corpora_table.resizeColumnsToContents()
        self.sources_table.resizeColumnsToContents()
        self.metrics_table.resizeColumnsToContents()
        self.vocabulary_table.resizeColumnsToContents()
        self.patterns_table.resizeColumnsToContents()
        self.rhythm_table.resizeColumnsToContents()
        self.platform_table.resizeColumnsToContents()
        self.candidates_table.resizeColumnsToContents()
        self.narrative_view.refresh()
        self.history_view.refresh()

    def _selected_corpus_id(self) -> str | None:
        rows = self.corpora_table.selectionModel().selectedRows() if self.corpora_table.selectionModel() else []
        if not rows:
            return None
        item = self.corpora_table.item(rows[0].row(), 9)
        return item.text() if item else None

    def _create_corpus(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Language", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_language_corpus(
                creator_id=creator_id,
                name=self.corpus_name.text().strip() or "Corpus narrativo",
                description=self.corpus_description.text().strip() or None,
                language=self.corpus_language.text().strip() or "es",
                platform=self.corpus_platform.text().strip() or None,
                content_type=self.corpus_content_type.text().strip() or None,
                topic=self.corpus_topic.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()

    def _analyze_corpus(self) -> None:
        corpus_id = self._selected_corpus_id()
        if corpus_id is None:
            QMessageBox.information(self, "Creator Language", "Selecciona un corpus primero.")
            return
        try:
            self.workspace.analyze_creator_language_corpus(corpus_id, force_recompute=True)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()

    def _create_snapshot(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Creator Language", "Selecciona un creador primero.")
            return
        try:
            self.workspace.create_creator_language_profile_snapshot(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()

    def _selected_source_id(self) -> str | None:
        rows = self.sources_table.selectionModel().selectedRows() if self.sources_table.selectionModel() else []
        if not rows:
            return None
        item = self.sources_table.item(rows[0].row(), 8)
        return item.text() if item else None

    def _add_source(self) -> None:
        corpus_id = self._selected_corpus_id()
        if corpus_id is None:
            QMessageBox.information(self, "Creator Language", "Selecciona un corpus primero.")
            return
        try:
            self.workspace.add_creator_language_corpus_source(
                corpus_id=corpus_id,
                source_type=self.source_type.currentText(),
                source_id=self.source_id.text().strip() or self.source_type.currentText(),
                text_snapshot=self.source_text.text().strip() or None,
                language=self.source_language.text().strip() or None,
                platform=self.source_platform.text().strip() or None,
                content_type=self.source_content_type.text().strip() or None,
                topic=self.source_topic.text().strip() or None,
                include_status=self.source_include_status.currentText(),
                exclusion_reason=self.source_reason.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()

    def _remove_source(self) -> None:
        source_id = self._selected_source_id()
        if source_id is None:
            return
        try:
            self.workspace.remove_creator_language_corpus_source(source_id, reason="Excluida desde UI")
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()

    def _review_candidate(self) -> None:
        rows = self.candidates_table.selectionModel().selectedRows() if self.candidates_table.selectionModel() else []
        if not rows:
            return
        candidate_id = self.candidates_table.item(rows[0].row(), 7).text()
        try:
            self.workspace.review_creator_language_candidate(
                candidate_id,
                decision=self.candidate_decision.currentText(),
                reason=self.candidate_reason.text().strip() or None,
                modified_value_json=self.candidate_modified_value.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Creator Language", str(exc))
            return
        self.refresh()
