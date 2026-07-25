"""Vista principal de Thumbnail Lab and Titles Foundation."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
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
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from .creative_concept_view import CreativeConceptView
from .packaging_history_view import PackagingHistoryView
from .prompt_builder_view import PromptBuilderView
from .thumbnail_review_view import ThumbnailReviewView
from .title_lab_view import TitleLabView


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class ThumbnailLabView(QWidget):
    """Panel integrado para titulos, miniaturas, conceptos y prompts."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "creative_packaging_service", None)

        self.tabs = QTabWidget()
        self.overview_tab = QWidget()
        self.brand_profile_tab = QWidget()
        self.references_tab = QWidget()
        self.titles_tab = QWidget()
        self.thumbnails_tab = QWidget()
        self.pair_tab = QWidget()
        self.frame_tab = QWidget()
        self.concepts_tab = QWidget()
        self.prompt_tab = QWidget()
        self.review_tab = QWidget()
        self.history_tab = QWidget()
        for tab, label in (
            (self.overview_tab, "Overview"),
            (self.brand_profile_tab, "Brand Profile"),
            (self.references_tab, "References"),
            (self.titles_tab, "Titles"),
            (self.thumbnails_tab, "Thumbnails"),
            (self.pair_tab, "Pair Evaluation"),
            (self.frame_tab, "Frame Candidates"),
            (self.concepts_tab, "Concepts"),
            (self.prompt_tab, "Prompt Builder"),
            (self.review_tab, "Thumbnail Review"),
            (self.history_tab, "History"),
        ):
            self.tabs.addTab(tab, label)

        self._build_overview_tab()
        self._build_brand_profile_tab()
        self._build_references_tab()
        self._build_titles_tab()
        self._build_thumbnails_tab()
        self._build_pair_tab()
        self._build_frame_tab()
        self._build_concepts_tab()
        self._build_prompt_tab()
        self._build_review_tab()
        self._build_history_tab()

        title = QLabel("Thumbnail Lab")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Analisis de titulos, miniaturas, conceptos y prompts con marca del creador.")
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

    def _build_overview_tab(self) -> None:
        self.overview_counts = {
            "assets": QLabel("0"),
            "titles": QLabel("0"),
            "thumbnails": QLabel("0"),
            "references": QLabel("0"),
            "brand_profiles": QLabel("0"),
        }
        self.overview_warning = QLabel("Completa brand profile y referencias para mejorar la evaluacion.")
        self.overview_warning.setObjectName("MutedLabel")
        self.overview_warning.setWordWrap(True)
        self.overview_table = QTableWidget(0, 6)
        self.overview_table.setHorizontalHeaderLabels(["Tipo", "Titulo", "Plataforma", "Contenido", "Estado", "ID"])
        self.overview_table.setColumnHidden(5, True)
        grid = QGridLayout(self.overview_tab)
        grid.addWidget(QLabel("Assets"), 0, 0)
        grid.addWidget(self.overview_counts["assets"], 0, 1)
        grid.addWidget(QLabel("Titulos"), 0, 2)
        grid.addWidget(self.overview_counts["titles"], 0, 3)
        grid.addWidget(QLabel("Miniaturas"), 1, 0)
        grid.addWidget(self.overview_counts["thumbnails"], 1, 1)
        grid.addWidget(QLabel("Referencias"), 1, 2)
        grid.addWidget(self.overview_counts["references"], 1, 3)
        grid.addWidget(QLabel("Brand profiles"), 2, 0)
        grid.addWidget(self.overview_counts["brand_profiles"], 2, 1)
        grid.addWidget(self.overview_warning, 3, 0, 1, 4)
        grid.addWidget(self.overview_table, 4, 0, 1, 4)

    def _build_brand_profile_tab(self) -> None:
        self.brand_summary = QPlainTextEdit()
        self.brand_summary.setReadOnly(True)
        self.brand_build = QPushButton("Construir perfil de marca")
        self.brand_build.clicked.connect(self._build_brand_profile)
        self.brand_profiles_table = QTableWidget(0, 5)
        self.brand_profiles_table.setHorizontalHeaderLabels(["Version", "Estado", "Resumen", "Confianza", "ID"])
        self.brand_profiles_table.setColumnHidden(4, True)
        self.brand_detail = QPlainTextEdit()
        self.brand_detail.setReadOnly(True)
        layout = QVBoxLayout(self.brand_profile_tab)
        layout.addWidget(self.brand_build)
        layout.addWidget(QLabel("Resumen"))
        layout.addWidget(self.brand_summary)
        layout.addWidget(QLabel("Versiones"))
        layout.addWidget(self.brand_profiles_table)
        layout.addWidget(QLabel("Detalle estructurado"))
        layout.addWidget(self.brand_detail)

    def _build_references_tab(self) -> None:
        self.reference_type = QLineEdit("prior_approved_thumbnail")
        self.reference_image_path = QLineEdit()
        self.reference_text = QLineEdit()
        self.reference_platform = QLineEdit()
        self.reference_content_type = QLineEdit()
        self.reference_topic = QLineEdit()
        self.reference_source_type = QLineEdit("manual")
        self.reference_source_creator = QLineEdit()
        self.reference_source_url = QLineEdit()
        self.reference_permission = QLineEdit("reviewed")
        self.reference_represents_creator = QCheckBox("Representa al creador")
        self.reference_approval = QLineEdit("approved")
        self.reference_purpose = QLineEdit()
        self.reference_notes = QLineEdit()
        self.reference_add = QPushButton("Agregar referencia")
        self.reference_review = QPushButton("Revisar referencia")
        self.reference_add.clicked.connect(self._add_reference)
        self.reference_review.clicked.connect(self._review_reference)
        self.references_table = QTableWidget(0, 8)
        self.references_table.setHorizontalHeaderLabels(["Tipo", "Propósito", "Permiso", "Aprobacion", "Plataforma", "Contenido", "Fuente", "ID"])
        self.references_table.setColumnHidden(7, True)
        form = QFormLayout()
        form.addRow("Tipo", self.reference_type)
        form.addRow("Image path", self.reference_image_path)
        form.addRow("Text", self.reference_text)
        form.addRow("Plataforma", self.reference_platform)
        form.addRow("Contenido", self.reference_content_type)
        form.addRow("Tema", self.reference_topic)
        form.addRow("Source type", self.reference_source_type)
        form.addRow("Source creator", self.reference_source_creator)
        form.addRow("Source url", self.reference_source_url)
        form.addRow("Permission", self.reference_permission)
        form.addRow("Approval", self.reference_approval)
        form.addRow("Purpose", self.reference_purpose)
        form.addRow("Notes", self.reference_notes)
        form.addRow("", self.reference_represents_creator)
        actions = QHBoxLayout()
        actions.addWidget(self.reference_add)
        actions.addWidget(self.reference_review)
        actions.addStretch(1)
        layout = QVBoxLayout(self.references_tab)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.references_table)

    def _build_titles_tab(self) -> None:
        self.titles_view = TitleLabView(self.workspace)
        layout = QVBoxLayout(self.titles_tab)
        layout.addWidget(self.titles_view)

    def _build_thumbnails_tab(self) -> None:
        self.thumbnail_packaging_asset_id = QLineEdit()
        self.thumbnail_image_path = QLineEdit()
        self.thumbnail_source_type = QLineEdit("manual")
        self.thumbnail_concept_id = QLineEdit()
        self.thumbnail_create = QPushButton("Crear miniatura")
        self.thumbnail_analyze = QPushButton("Analizar miniatura")
        self.thumbnail_create.clicked.connect(self._create_thumbnail)
        self.thumbnail_analyze.clicked.connect(self._analyze_thumbnail)
        self.thumbnails_table = QTableWidget(0, 8)
        self.thumbnails_table.setHorizontalHeaderLabels(["Miniatura", "Plataforma", "Contenido", "Version", "Seleccionada", "Aprobacion", "Huella", "ID"])
        self.thumbnails_table.setColumnHidden(7, True)
        self.thumbnail_metrics_table = QTableWidget(0, 5)
        self.thumbnail_metrics_table.setHorizontalHeaderLabels(["Metrica", "Valor", "Unidad", "Confianza", "Warnings"])
        form = QFormLayout()
        form.addRow("Packaging asset id", self.thumbnail_packaging_asset_id)
        form.addRow("Image path", self.thumbnail_image_path)
        form.addRow("Source type", self.thumbnail_source_type)
        form.addRow("Concept id", self.thumbnail_concept_id)
        actions = QHBoxLayout()
        actions.addWidget(self.thumbnail_create)
        actions.addWidget(self.thumbnail_analyze)
        actions.addStretch(1)
        layout = QVBoxLayout(self.thumbnails_tab)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.thumbnails_table)
        layout.addWidget(QLabel("Metricas"))
        layout.addWidget(self.thumbnail_metrics_table)

    def _build_pair_tab(self) -> None:
        self.pair_title_id = QComboBox()
        self.pair_thumbnail_id = QComboBox()
        self.pair_publication_id = QLineEdit()
        self.pair_create = QPushButton("Evaluar par")
        self.pair_create.clicked.connect(self._evaluate_pair)
        self.pair_table = QTableWidget(0, 9)
        self.pair_table.setHorizontalHeaderLabels(["Titulo", "Miniatura", "Visual", "Contenido", "Marca", "Plataforma", "Historico", "Recomendacion", "ID"])
        self.pair_table.setColumnHidden(8, True)
        layout = QGridLayout(self.pair_tab)
        layout.addWidget(QLabel("Titulo"), 0, 0)
        layout.addWidget(self.pair_title_id, 0, 1)
        layout.addWidget(QLabel("Miniatura"), 0, 2)
        layout.addWidget(self.pair_thumbnail_id, 0, 3)
        layout.addWidget(QLabel("Publication id"), 1, 0)
        layout.addWidget(self.pair_publication_id, 1, 1)
        layout.addWidget(self.pair_create, 1, 3)
        layout.addWidget(self.pair_table, 2, 0, 1, 4)

    def _build_frame_tab(self) -> None:
        self.frame_video_id = QLineEdit()
        self.frame_extract = QPushButton("Extraer frames")
        self.frame_extract.clicked.connect(self._extract_frames)
        self.frame_table = QTableWidget(0, 8)
        self.frame_table.setHorizontalHeaderLabels(["Timestamp", "Path", "Sharpness", "Brightness", "Contrast", "Motion blur", "Estado", "ID"])
        self.frame_table.setColumnHidden(7, True)
        layout = QGridLayout(self.frame_tab)
        layout.addWidget(QLabel("Video id"), 0, 0)
        layout.addWidget(self.frame_video_id, 0, 1)
        layout.addWidget(self.frame_extract, 0, 2)
        layout.addWidget(self.frame_table, 1, 0, 1, 3)

    def _build_concepts_tab(self) -> None:
        self.concepts_view = CreativeConceptView(self.workspace)
        layout = QVBoxLayout(self.concepts_tab)
        layout.addWidget(self.concepts_view)

    def _build_prompt_tab(self) -> None:
        self.prompt_view = PromptBuilderView(self.workspace)
        layout = QVBoxLayout(self.prompt_tab)
        layout.addWidget(self.prompt_view)

    def _build_review_tab(self) -> None:
        self.review_view = ThumbnailReviewView(self.workspace)
        layout = QVBoxLayout(self.review_tab)
        layout.addWidget(self.review_view)

    def _build_history_tab(self) -> None:
        self.history_view = PackagingHistoryView(self.workspace)
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.history_view)

    def _selected_creator_id(self) -> str | None:
        return self.workspace.selected_creator_id

    def _selected_title_id(self) -> str | None:
        return self.pair_title_id.currentData() if self.pair_title_id.count() else None

    def _selected_thumbnail_id(self) -> str | None:
        return self.pair_thumbnail_id.currentData() if self.pair_thumbnail_id.count() else None

    def refresh(self) -> None:
        creator_id = self._selected_creator_id()
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        if creator_id is None or self.service is None:
            self._clear_tables()
            return

        assets = self.workspace.list_packaging_assets(creator_id)
        references = self.workspace.list_packaging_reference_assets(creator_id)
        brand_profiles = self.workspace.list_packaging_brand_profiles(creator_id)
        titles = [title for asset in assets for title in self.workspace.list_packaging_title_versions(asset.id)]
        thumbnails = [thumbnail for asset in assets for thumbnail in self.workspace.list_packaging_thumbnail_versions(asset.id)]
        pair_evaluations = self.workspace.list_packaging_pair_evaluations(creator_id)
        frame_candidates = self.workspace.list_packaging_frame_candidates(creator_id)
        decisions = self.workspace.list_packaging_decisions(creator_id)
        brand_detail = self.workspace.get_packaging_brand_profile_detail(creator_id)

        self.overview_counts["assets"].setText(str(len(assets)))
        self.overview_counts["titles"].setText(str(len(titles)))
        self.overview_counts["thumbnails"].setText(str(len(thumbnails)))
        self.overview_counts["references"].setText(str(len(references)))
        self.overview_counts["brand_profiles"].setText(str(len(brand_profiles)))
        self.overview_warning.setText("Perfil incompleto: agrega referencias y construye el brand profile." if not brand_profiles else "Perfil de marca disponible.")

        self.overview_table.setRowCount(0)
        for row_index, asset in enumerate(assets):
            self.overview_table.insertRow(row_index)
            values = [asset.asset_type.value, asset.publication_id or asset.video_asset_id or asset.id, asset.platform, asset.content_type, asset.status.value, asset.id]
            for column, value in enumerate(values):
                self.overview_table.setItem(row_index, column, _item(value))

        self.brand_profiles_table.setRowCount(0)
        for row_index, profile in enumerate(brand_profiles):
            self.brand_profiles_table.insertRow(row_index)
            values = [profile.profile_version, profile.status.value, profile.brand_summary[:120], profile.created_at.isoformat(), profile.id]
            for column, value in enumerate(values):
                self.brand_profiles_table.setItem(row_index, column, _item(value))
        if brand_detail and brand_detail.profile:
            self.brand_summary.setPlainText(brand_detail.profile.brand_summary if hasattr(brand_detail.profile, "brand_summary") else brand_detail.profile.summary)
            self.brand_detail.setPlainText(json.dumps(brand_detail.to_dict(), ensure_ascii=False, indent=2, default=str))
        else:
            self.brand_summary.setPlainText("Sin perfil de marca construido.")
            self.brand_detail.setPlainText("")

        self.references_table.setRowCount(0)
        for row_index, reference in enumerate(references):
            self.references_table.insertRow(row_index)
            values = [
                reference.reference_type.value,
                reference.reference_purpose,
                reference.usage_permission,
                reference.approval_status.value,
                reference.platform or "",
                reference.content_type or "",
                reference.source_creator_name or reference.source_type,
                reference.id,
            ]
            for column, value in enumerate(values):
                self.references_table.setItem(row_index, column, _item(value))

        self.thumbnails_table.setRowCount(0)
        for row_index, thumbnail in enumerate(thumbnails):
            self.thumbnails_table.insertRow(row_index)
            values = [
                thumbnail.image_path or thumbnail.source_type,
                thumbnail.platform,
                thumbnail.content_type,
                thumbnail.version_number,
                "si" if thumbnail.is_selected else "no",
                thumbnail.creator_approval_status,
                thumbnail.file_fingerprint or "",
                thumbnail.id,
            ]
            for column, value in enumerate(values):
                self.thumbnails_table.setItem(row_index, column, _item(value))

        self.pair_title_id.blockSignals(True)
        self.pair_thumbnail_id.blockSignals(True)
        current_title = self.pair_title_id.currentData()
        current_thumbnail = self.pair_thumbnail_id.currentData()
        self.pair_title_id.clear()
        self.pair_thumbnail_id.clear()
        for title in titles:
            self.pair_title_id.addItem(title.title_text, title.id)
        for thumbnail in thumbnails:
            self.pair_thumbnail_id.addItem(thumbnail.image_path or f"Thumbnail {thumbnail.version_number}", thumbnail.id)
        if current_title:
            index = self.pair_title_id.findData(current_title)
            if index >= 0:
                self.pair_title_id.setCurrentIndex(index)
        if current_thumbnail:
            index = self.pair_thumbnail_id.findData(current_thumbnail)
            if index >= 0:
                self.pair_thumbnail_id.setCurrentIndex(index)
        self.pair_title_id.blockSignals(False)
        self.pair_thumbnail_id.blockSignals(False)

        self.pair_table.setRowCount(0)
        for row_index, evaluation in enumerate(pair_evaluations):
            self.pair_table.insertRow(row_index)
            values = [
                evaluation.title_version_id,
                evaluation.thumbnail_version_id,
                evaluation.visual_quality_score,
                evaluation.content_alignment_score,
                evaluation.creator_brand_alignment_score,
                evaluation.platform_fit_score,
                evaluation.historical_fit_score,
                evaluation.recommendation_status,
                evaluation.id,
            ]
            for column, value in enumerate(values):
                self.pair_table.setItem(row_index, column, _item(value))

        self.frame_table.setRowCount(0)
        for row_index, candidate in enumerate(frame_candidates):
            self.frame_table.insertRow(row_index)
            values = [
                candidate.timestamp_seconds,
                candidate.frame_path,
                candidate.sharpness_score,
                candidate.brightness_score,
                candidate.contrast_score,
                candidate.motion_blur_score,
                candidate.quality_status.value,
                candidate.id,
            ]
            for column, value in enumerate(values):
                self.frame_table.setItem(row_index, column, _item(value))

        for table in (
            self.overview_table,
            self.brand_profiles_table,
            self.references_table,
            self.thumbnails_table,
            self.pair_table,
            self.frame_table,
        ):
            table.resizeColumnsToContents()

        self.titles_view.refresh()
        self.concepts_view.refresh()
        self.prompt_view.refresh()
        self.review_view.refresh()
        self.history_view.refresh()
        self._populate_concept_and_prompt_context()

    def _clear_tables(self) -> None:
        for table in (
            self.overview_table,
            self.brand_profiles_table,
            self.references_table,
            self.thumbnails_table,
            self.pair_table,
            self.frame_table,
        ):
            table.setRowCount(0)
        self.overview_counts["assets"].setText("0")
        self.overview_counts["titles"].setText("0")
        self.overview_counts["thumbnails"].setText("0")
        self.overview_counts["references"].setText("0")
        self.overview_counts["brand_profiles"].setText("0")
        self.overview_warning.setText("Completa brand profile y referencias para mejorar la evaluacion.")
        self.brand_summary.setPlainText("")
        self.brand_detail.setPlainText("")
        self.titles_view.refresh()
        self.concepts_view.refresh()
        self.prompt_view.refresh()
        self.review_view.refresh()
        self.history_view.refresh()

    def _populate_concept_and_prompt_context(self) -> None:
        if self.workspace.selected_creator_id is None:
            return
        self.concepts_view.refresh()
        self.prompt_view.refresh()
        self.review_view.refresh()

    def _build_brand_profile(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona un creador primero.")
            return
        try:
            self.workspace.build_packaging_brand_profile(creator_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _add_reference(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona un creador primero.")
            return
        try:
            self.workspace.add_packaging_reference_asset(
                creator_id=creator_id,
                reference_type=self.reference_type.text().strip() or "prior_approved_thumbnail",
                image_path=self.reference_image_path.text().strip() or None,
                text_content=self.reference_text.text().strip() or None,
                platform=self.reference_platform.text().strip() or None,
                content_type=self.reference_content_type.text().strip() or None,
                topic=self.reference_topic.text().strip() or None,
                source_type=self.reference_source_type.text().strip() or "manual",
                source_creator_name=self.reference_source_creator.text().strip() or None,
                source_url=self.reference_source_url.text().strip() or None,
                usage_permission=self.reference_permission.text().strip() or "reviewed",
                represents_creator=self.reference_represents_creator.isChecked(),
                approval_status=self.reference_approval.text().strip() or "approved",
                reference_purpose=self.reference_purpose.text().strip() or "brand_reference",
                notes=self.reference_notes.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _review_reference(self) -> None:
        rows = self.references_table.selectionModel().selectedRows() if self.references_table.selectionModel() else []
        if not rows:
            return
        reference_id = self.references_table.item(rows[0].row(), 7).text()
        try:
            self.workspace.review_packaging_reference_asset(reference_id, approval_status="approved", notes="Revisada desde UI")
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _create_thumbnail(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona un creador primero.")
            return
        try:
            asset = self.workspace.create_packaging_thumbnail_version(
                creator_id=creator_id,
                platform="youtube_longform",
                content_type="longform_video",
                source_type=self.thumbnail_source_type.text().strip() or "manual",
                image_path=self.thumbnail_image_path.text().strip() or None,
                packaging_asset_id=self.thumbnail_packaging_asset_id.text().strip() or None,
                concept_id=self.thumbnail_concept_id.text().strip() or None,
            )
            self.thumbnail_image_path.setText(asset.image_path or "")
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _analyze_thumbnail(self) -> None:
        rows = self.thumbnails_table.selectionModel().selectedRows() if self.thumbnails_table.selectionModel() else []
        if not rows:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona una miniatura primero.")
            return
        thumbnail_id = self.thumbnails_table.item(rows[0].row(), 7).text()
        try:
            self.workspace.analyze_packaging_thumbnail(thumbnail_id, force_recompute=True)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _evaluate_pair(self) -> None:
        title_id = self.pair_title_id.currentData()
        thumbnail_id = self.pair_thumbnail_id.currentData()
        if not title_id or not thumbnail_id:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona titulo y miniatura primero.")
            return
        try:
            self.workspace.evaluate_packaging_pair(str(title_id), str(thumbnail_id), publication_id=self.pair_publication_id.text().strip() or None)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()

    def _extract_frames(self) -> None:
        creator_id = self._selected_creator_id()
        if creator_id is None:
            QMessageBox.information(self, "Thumbnail Lab", "Selecciona un creador primero.")
            return
        video_id = self.frame_video_id.text().strip()
        if not video_id:
            QMessageBox.information(self, "Thumbnail Lab", "Proporciona un video id.")
            return
        try:
            self.workspace.extract_packaging_frame_candidates(creator_id=creator_id, video_asset_id=video_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Thumbnail Lab", str(exc))
            return
        self.refresh()
