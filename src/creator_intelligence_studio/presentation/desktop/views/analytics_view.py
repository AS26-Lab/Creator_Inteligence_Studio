"""Vista inicial de analytics manual."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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


class AnalyticsView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        self.tabs = QTabWidget()
        self.import_tab = QWidget()
        self.publications_tab = QWidget()
        self.tabs.addTab(self.import_tab, "Importacion")
        self.tabs.addTab(self.publications_tab, "Publicaciones")

        self._build_import_tab()
        self._build_publications_tab()

        layout = QVBoxLayout(self)
        title = QLabel("Analytics")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Base manual de analiticas historicas y aprendizaje.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.tabs)

        self.refresh()

    def _build_import_tab(self) -> None:
        self.creator_combo = QComboBox()
        self.channel_combo = QComboBox()
        self.platform_combo = QComboBox()
        self.file_path = QLineEdit()
        self.sheet_name = QLineEdit()
        self.mapping_name = QLineEdit()
        self.schema_preview = QTableWidget(0, 3)
        self.schema_preview.setHorizontalHeaderLabels(["Fuente", "Destino", "Confianza"])
        self.row_preview = QTableWidget(0, 4)
        self.row_preview.setHorizontalHeaderLabels(["Fila", "Titulo", "Plataforma", "Fecha"])
        self.import_csv_button = QPushButton("Importar CSV")
        self.import_excel_button = QPushButton("Importar Excel")
        self.inspect_button = QPushButton("Inspeccionar")
        self.detect_button = QPushButton("Detectar schema")
        self.browse_button = QPushButton("Abrir archivo")
        self.create_channel_button = QPushButton("Crear canal")
        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("MutedLabel")

        self.creator_combo.currentIndexChanged.connect(self._refresh_channels)
        self.browse_button.clicked.connect(self._browse_file)
        self.inspect_button.clicked.connect(self._inspect_file)
        self.detect_button.clicked.connect(self._detect_schema)
        self.import_csv_button.clicked.connect(self._import_csv)
        self.import_excel_button.clicked.connect(self._import_excel)
        self.create_channel_button.clicked.connect(self._create_channel)

        controls = QGridLayout(self.import_tab)
        controls.addWidget(QLabel("Creador"), 0, 0)
        controls.addWidget(self.creator_combo, 0, 1)
        controls.addWidget(QLabel("Canal"), 0, 2)
        controls.addWidget(self.channel_combo, 0, 3)
        controls.addWidget(self.create_channel_button, 0, 4)
        controls.addWidget(QLabel("Plataforma"), 1, 0)
        controls.addWidget(self.platform_combo, 1, 1)
        controls.addWidget(QLabel("Archivo"), 1, 2)
        controls.addWidget(self.file_path, 1, 3)
        controls.addWidget(self.browse_button, 1, 4)
        controls.addWidget(QLabel("Hoja"), 2, 0)
        controls.addWidget(self.sheet_name, 2, 1)
        controls.addWidget(QLabel("Mapping"), 2, 2)
        controls.addWidget(self.mapping_name, 2, 3)
        controls.addWidget(self.inspect_button, 2, 4)
        controls.addWidget(self.detect_button, 3, 0)
        controls.addWidget(self.import_csv_button, 3, 1)
        controls.addWidget(self.import_excel_button, 3, 2)
        controls.addWidget(self.status_label, 3, 3, 1, 2)
        controls.addWidget(QLabel("Sugerencias"), 4, 0, 1, 5)
        controls.addWidget(self.schema_preview, 5, 0, 1, 5)
        controls.addWidget(QLabel("Preview"), 6, 0, 1, 5)
        controls.addWidget(self.row_preview, 7, 0, 1, 5)

    def _build_publications_tab(self) -> None:
        self.publications_table = QTableWidget(0, 12)
        self.publications_table.setHorizontalHeaderLabels(
            [
                "Titulo",
                "Plataforma",
                "Tipo",
                "Fecha",
                "Duracion",
                "Vinculo local",
                "Ultimo snapshot",
                "Vistas",
                "Alcance",
                "Tiempo visto",
                "Completado",
                "Likes",
            ]
        )
        self.publications_empty = EmptyStateWidget(
            "No hay publicaciones normalizadas todavía.",
            "Importa un CSV o Excel para comenzar a construir el historial.",
        )
        layout = QVBoxLayout(self.publications_tab)
        layout.addWidget(self.publications_empty)
        layout.addWidget(self.publications_table)

    def refresh(self) -> None:
        creators = self.workspace.creators()
        self.creator_combo.blockSignals(True)
        self.creator_combo.clear()
        for creator in creators:
            self.creator_combo.addItem(creator.display_name, creator.id)
        if self.workspace.selected_creator_id:
            index = self.creator_combo.findData(self.workspace.selected_creator_id)
            self.creator_combo.setCurrentIndex(index if index >= 0 else 0)
        self.creator_combo.blockSignals(False)
        self._refresh_platforms()
        self._refresh_channels()
        self._refresh_publications()

    def _refresh_platforms(self) -> None:
        self.platform_combo.clear()
        for platform in self.workspace.list_analytics_platforms():
            self.platform_combo.addItem(platform.display_name, platform.platform_key)

    def _refresh_channels(self, *args) -> None:
        creator_id = self.creator_combo.currentData()
        self.channel_combo.clear()
        if not creator_id:
            return
        for channel in self.workspace.list_analytics_channels(str(creator_id)):
            self.channel_combo.addItem(channel.channel_name, channel.id)

    def _refresh_publications(self) -> None:
        creator_id = self.creator_combo.currentData()
        publications = self.workspace.list_analytics_publications(str(creator_id)) if creator_id else []
        self.publications_table.setRowCount(0)
        if not publications:
            self.publications_table.hide()
            self.publications_empty.show()
            return
        self.publications_empty.hide()
        self.publications_table.show()
        for row_index, publication in enumerate(publications):
            latest_metrics = self.workspace.get_analytics_latest_metrics(publication.id)
            views = latest_metrics.get("views")
            reach = latest_metrics.get("reach")
            watch_time = latest_metrics.get("watch_time_minutes")
            completion = latest_metrics.get("completion_rate")
            likes = latest_metrics.get("likes")
            snapshot = next(iter(latest_metrics.values()), None)
            values = [
                publication.title,
                publication.platform,
                publication.content_type.value,
                publication.published_at.isoformat(),
                "" if publication.duration_seconds is None else str(publication.duration_seconds),
                publication.video_asset_id or "",
                snapshot.captured_at.isoformat() if snapshot else "",
                "" if views is None or views.numeric_value is None else str(views.numeric_value),
                "" if reach is None or reach.numeric_value is None else str(reach.numeric_value),
                "" if watch_time is None or watch_time.numeric_value is None else str(watch_time.numeric_value),
                "" if completion is None or completion.numeric_value is None else str(completion.numeric_value),
                "" if likes is None or likes.numeric_value is None else str(likes.numeric_value),
            ]
            self.publications_table.insertRow(row_index)
            for column, value in enumerate(values):
                self.publications_table.setItem(row_index, column, QTableWidgetItem(value))
        self.publications_table.resizeColumnsToContents()

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de analytics",
            "",
            "Archivos CSV/XLSX (*.csv *.xlsx)",
        )
        if path:
            self.file_path.setText(path)

    def _inspect_file(self) -> None:
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.information(self, "Analytics", "Selecciona un archivo primero.")
            return
        table = self.workspace.inspect_analytics_file(file_path, sheet_name=self.sheet_name.text().strip() or None)
        self.row_preview.setRowCount(0)
        for row_index, row in enumerate(table.rows[:10]):
            self.row_preview.insertRow(row_index)
            values = [str(row_index + 1), str(row.get("title", "")), str(row.get("platform", "")), str(row.get("published_at", ""))]
            for column, value in enumerate(values):
                self.row_preview.setItem(row_index, column, QTableWidgetItem(value))
        self.status_label.setText(f"Vista previa: {len(table.rows)} filas")

    def _detect_schema(self) -> None:
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.information(self, "Analytics", "Selecciona un archivo primero.")
            return
        result = self.workspace.detect_analytics_schema(file_path, sheet_name=self.sheet_name.text().strip() or None)
        self.schema_preview.setRowCount(0)
        for row_index, suggestion in enumerate(result.suggestions):
            self.schema_preview.insertRow(row_index)
            for column, value in enumerate([suggestion.source_field, suggestion.target_field, f"{suggestion.confidence:.2f}"]):
                self.schema_preview.setItem(row_index, column, QTableWidgetItem(value))
        self.status_label.setText(f"Schema detectado: {len(result.suggestions)} mapeos")

    def _import_csv(self) -> None:
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.information(self, "Analytics", "Selecciona un archivo primero.")
            return
        creator_id = self.creator_combo.currentData()
        if not creator_id:
            QMessageBox.information(self, "Analytics", "Selecciona un creador.")
            return
        result = self.workspace.import_analytics_csv(
            creator_id=str(creator_id),
            file_path=file_path,
            channel_id=str(self.channel_combo.currentData()) if self.channel_combo.currentData() else None,
            platform=self.platform_combo.currentData(),
            mapping_name=self.mapping_name.text().strip() or None,
        )
        self.status_label.setText(result.summary.status)
        self._refresh_publications()

    def _import_excel(self) -> None:
        file_path = self.file_path.text().strip()
        if not file_path:
            QMessageBox.information(self, "Analytics", "Selecciona un archivo primero.")
            return
        creator_id = self.creator_combo.currentData()
        if not creator_id:
            QMessageBox.information(self, "Analytics", "Selecciona un creador.")
            return
        result = self.workspace.import_analytics_excel(
            creator_id=str(creator_id),
            file_path=file_path,
            channel_id=str(self.channel_combo.currentData()) if self.channel_combo.currentData() else None,
            platform=self.platform_combo.currentData(),
            sheet_name=self.sheet_name.text().strip() or None,
            mapping_name=self.mapping_name.text().strip() or None,
        )
        self.status_label.setText(result.summary.status)
        self._refresh_publications()

    def _create_channel(self) -> None:
        creator_id = self.creator_combo.currentData()
        platform = self.platform_combo.currentData()
        if not creator_id or not platform:
            QMessageBox.information(self, "Analytics", "Selecciona creador y plataforma.")
            return
        channel = self.workspace.create_analytics_channel(
            creator_id=str(creator_id),
            platform=str(platform),
            name=f"Canal {platform}",
            timezone_name="UTC",
        )
        self.status_label.setText(f"Canal creado: {channel.channel_name}")
        self._refresh_channels()
