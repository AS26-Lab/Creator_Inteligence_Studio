"""Vista de titulos de packaging creativo."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class TitleLabView(QWidget):
    """Gestion local de titulos y su analisis."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "creative_packaging_service", None)
        self.title_text = QLineEdit()
        self.platform = QComboBox()
        self.platform.addItems(["youtube_longform", "youtube_short", "instagram_reel", "tiktok", "manual_other"])
        self.content_type = QComboBox()
        self.content_type.addItems(["longform_video", "short_video", "reel", "tiktok", "live_replay", "community_post", "other"])
        self.topic = QLineEdit()
        self.publication_id = QLineEdit()
        self.video_asset_id = QLineEdit()
        self.create_button = QPushButton("Crear titulo")
        self.analyze_button = QPushButton("Analizar titulo")
        self.refresh_button = QPushButton("Actualizar")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Titulo", "Plataforma", "Contenido", "Version", "Seleccionado", "Aprobacion", "Huella", "ID"])
        self.table.setColumnHidden(7, True)
        self.analysis_table = QTableWidget(0, 5)
        self.analysis_table.setHorizontalHeaderLabels(["Metrica", "Valor", "Unidad", "Confianza", "Warnings"])
        self.empty_state = EmptyStateWidget("Sin titulos", "Crea un titulo para empezar a analizar packaging.")

        form = QFormLayout()
        form.addRow("Titulo", self.title_text)
        form.addRow("Plataforma", self.platform)
        form.addRow("Contenido", self.content_type)
        form.addRow("Tema", self.topic)
        form.addRow("Publication ID", self.publication_id)
        form.addRow("Video ID", self.video_asset_id)

        actions = QHBoxLayout()
        actions.addWidget(self.create_button)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.empty_state)
        layout.addWidget(QLabel("Titulos"))
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Analisis"))
        layout.addWidget(self.analysis_table)

        self.create_button.clicked.connect(self._create_title)
        self.analyze_button.clicked.connect(self._analyze_title)
        self.refresh_button.clicked.connect(self.refresh)

    def _selected_title_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 7)
        return item.text() if item else None

    def _create_title(self) -> None:
        if self.service is None:
            QMessageBox.information(self, "Titulos", "El servicio de packaging no esta disponible.")
            return
        creator_id = self.workspace.selected_creator_id
        if creator_id is None:
            QMessageBox.information(self, "Titulos", "Selecciona un creador primero.")
            return
        try:
            self.service.create_title_version(
                creator_id=creator_id,
                title_text=self.title_text.text().strip() or "Titulo creativo",
                platform=self.platform.currentText(),
                content_type=self.content_type.currentText(),
                topic=self.topic.text().strip() or None,
                publication_id=self.publication_id.text().strip() or None,
                video_asset_id=self.video_asset_id.text().strip() or None,
            )
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Titulos", str(exc))
            return
        self.refresh()

    def _analyze_title(self) -> None:
        if self.service is None:
            return
        title_id = self._selected_title_id()
        if not title_id:
            QMessageBox.information(self, "Titulos", "Selecciona un titulo primero.")
            return
        try:
            self.service.analyze_title(title_id, force_recompute=True)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "Titulos", str(exc))
            return
        self.refresh()

    def refresh(self) -> None:
        if self.service is None or self.workspace.selected_creator_id is None:
            self.table.setRowCount(0)
            self.analysis_table.setRowCount(0)
            self.empty_state.show()
            return
        creator_id = self.workspace.selected_creator_id
        assets = self.service.list_assets(creator_id)
        titles = [title for asset in assets for title in self.service.list_title_versions(asset.id)]
        self.table.setRowCount(0)
        if not titles:
            self.empty_state.show()
        else:
            self.empty_state.hide()
        for row_index, title in enumerate(titles):
            self.table.insertRow(row_index)
            values = [
                title.title_text,
                title.platform,
                title.content_type,
                title.version_number,
                "si" if title.is_selected else "no",
                title.creator_approval_status,
                title.source_fingerprint[:12],
                title.id,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        latest_runs = self.service.list_title_analysis_runs(creator_id)
        analysis_metrics = self.service.list_title_analysis_metrics(latest_runs[0].id) if latest_runs else []
        self.analysis_table.setRowCount(0)
        for row_index, metric in enumerate(analysis_metrics):
            self.analysis_table.insertRow(row_index)
            values = [
                metric.metric_key,
                metric.numeric_value if metric.numeric_value is not None else metric.text_value,
                metric.unit,
                metric.confidence_level,
                metric.warning_codes_json,
            ]
            for column, value in enumerate(values):
                self.analysis_table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()
        self.analysis_table.resizeColumnsToContents()
