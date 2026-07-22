"""Vista de videos."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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

from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.presentation.desktop.dialogs.entity_dialogs import VideoDialog
from creator_intelligence_studio.presentation.desktop.view_models.models import VideoFiltersViewModel
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from creator_intelligence_studio.presentation.desktop.widgets.inspector import InspectorPanel


class VideosView(QWidget):
    """Lista, filtros y registro de videos."""

    def __init__(self, workspace: WorkspaceViewModel, inspector: InspectorPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.inspector = inspector
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por título, nombre o ruta")
        self.project_combo = QComboBox()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Todos", "Registrado", "Pendiente", "Procesando", "Completado", "Archivo faltante", "Error"])
        self.availability_combo = QComboBox()
        self.availability_combo.addItems(["Todas", "Disponible", "Archivo faltante"])
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Todas", "Archivo local", "Importación de plataforma", "Referencia manual"])
        self.table = QTableWidget(0, 11, self)
        self.table.setHorizontalHeaderLabels(
            ["Título", "Original", "Extensión", "Tamaño", "Fuente", "Estado", "Disponible", "Registro", "Proyecto", "ID", "Ruta"]
        )
        self.table.setColumnHidden(8, True)
        self.table.setColumnHidden(9, True)
        self.table.setColumnHidden(10, True)
        self.table.itemSelectionChanged.connect(self._sync_selection)
        self.empty_state = EmptyStateWidget(
            "No hay videos",
            "Selecciona un proyecto para ver videos o registra uno nuevo.",
        )
        self.empty_state.hide()

        buttons = QHBoxLayout()
        self.register_button = QPushButton("Registrar video")
        self.verify_button = QPushButton("Verificar archivo")
        self.open_button = QPushButton("Abrir ubicación")
        self.analysis_button = QPushButton("Iniciar análisis")
        self.analysis_button.setEnabled(False)
        self.project_combo.setToolTip("Filtra los videos del proyecto activo")
        self.status_combo.setToolTip("Filtra por estado de procesamiento")
        self.availability_combo.setToolTip("Filtra por disponibilidad del archivo")
        self.source_combo.setToolTip("Filtra por tipo de fuente")
        self.search_edit.setToolTip("Busca por título, nombre original, ruta o notas")
        self.register_button.setToolTip("Registrar un video local como metadatos")
        self.verify_button.setToolTip("Comprobar si el archivo sigue disponible")
        self.open_button.setToolTip("Abrir la carpeta del archivo original")
        self.analysis_button.setToolTip("Análisis audiovisual no disponible todavía")
        for button in (self.register_button, self.verify_button, self.open_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.register_button)
        buttons.addWidget(self.verify_button)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.analysis_button)
        buttons.addStretch(1)

        filters = QHBoxLayout()
        filters.addWidget(self.project_combo)
        filters.addWidget(self.status_combo)
        filters.addWidget(self.availability_combo)
        filters.addWidget(self.source_combo)
        filters.addWidget(self.search_edit)

        layout = QVBoxLayout(self)
        title = QLabel("Videos")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        layout.addLayout(buttons)
        layout.addLayout(filters)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.table)

        self.project_combo.currentIndexChanged.connect(self._project_changed)
        self.status_combo.currentIndexChanged.connect(self.refresh)
        self.availability_combo.currentIndexChanged.connect(self.refresh)
        self.source_combo.currentIndexChanged.connect(self.refresh)
        self.search_edit.textChanged.connect(self.refresh)
        self.register_button.clicked.connect(self._register_video)
        self.verify_button.clicked.connect(self._verify_video)
        self.open_button.clicked.connect(self._open_location)

    def _selected_filters(self) -> VideoFiltersViewModel:
        return VideoFiltersViewModel(
            project_id=self.project_combo.currentData(),
            processing_status=None if self.status_combo.currentText() == "Todos" else self.status_combo.currentText(),
            availability=None if self.availability_combo.currentText() == "Todas" else self.availability_combo.currentText(),
            source_type=None if self.source_combo.currentText() == "Todas" else self.source_combo.currentText(),
            search_text=self.search_edit.text().strip(),
        )

    def refresh(self) -> None:
        projects = self.workspace.projects_for_selected_creator()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("Todos los proyectos", None)
        for project in projects:
            self.project_combo.addItem(project.name, project.id)
        if self.workspace.selected_project_id:
            index = self.project_combo.findData(self.workspace.selected_project_id)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
            else:
                self.project_combo.setCurrentIndex(0)
        else:
            self.project_combo.setCurrentIndex(0)
        self.project_combo.blockSignals(False)
        self._reload_table()

    def _reload_table(self) -> None:
        if self.workspace.selected_project_id is None:
            self.table.hide()
            self.empty_state.show()
            self.inspector.set_empty("Inspector", "Selecciona un proyecto para registrar o revisar videos.")
            return
        rows = self.workspace.video_rows(self._selected_filters())
        self.table.setRowCount(0)
        if not rows:
            self.table.hide()
            self.empty_state.show()
            self.inspector.set_empty("Inspector", "No hay videos que cumplan los filtros actuales.")
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, video in enumerate(rows):
            self.table.insertRow(row_index)
            values = [
                video.title,
                video.original_filename,
                video.extension,
                str(video.file_size_bytes),
                video.source_type,
                video.processing_status,
                "Sí" if video.file_available else "No",
                video.registered_at,
                video.project_id,
                video.id,
                video.source_path,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {0, 1, 10}:
                    item.setToolTip(value)
                self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()
        self._select_workspace_video_row()
        self._sync_selection()

    def _project_changed(self) -> None:
        project_id = self.project_combo.currentData()
        if not project_id:
            return
        self.workspace.select_project(str(project_id))
        self.refresh()

    def _selected_video_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self.table.item(row, 9)
        return item.text() if item else None

    def _select_workspace_video_row(self) -> None:
        if self.workspace.selected_video_id is None:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 9)
            if item and item.text() == self.workspace.selected_video_id:
                self.table.selectRow(row)
                break

    def _sync_selection(self) -> None:
        video_id = self._selected_video_id()
        video = self.workspace.service.get_video(video_id) if video_id else self.workspace.selected_video()
        if video is None:
            self.inspector.set_empty("Inspector", "Selecciona un video para ver sus detalles.")
            return
        self.workspace.select_video(video.id)
        items = self.workspace.video_inspector_items(video)
        footer = "Registrar un video no lo copia ni lo procesa; solo guarda metadatos locales."
        self.inspector.set_items(f"Video: {video.title}", items, footer=footer)
        self.inspector.set_actions(
            [
                ("Verificar archivo", self._verify_video),
                ("Abrir ubicación", self._open_location),
            ]
        )

    def _register_video(self) -> None:
        project = self.workspace.selected_project()
        if project is None:
            QMessageBox.information(self, "Sin proyecto", "Selecciona un proyecto antes de registrar videos.")
            return
        dialog = VideoDialog(project.name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        try:
            video = self.workspace.register_video(
                project_id=project.id,
                file_path=str(payload["file_path"]),
                title=str(payload["title"]),
                notes=payload["notes"],
            )
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo registrar", str(exc))
            return
        self.refresh()
        self.workspace.select_video(video.id)

    def _verify_video(self) -> None:
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        if not video_id:
            QMessageBox.information(self, "Sin selección", "Selecciona un video primero.")
            return
        try:
            report = self.workspace.verify_video(video_id)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo verificar", str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self,
            "Verificación completada",
            f"Estado: {report.status}\nMetadata modificada: {'sí' if report.metadata_changed else 'no'}",
        )

    def _open_location(self) -> None:
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        if not video_id:
            QMessageBox.information(self, "Sin selección", "Selecciona un video primero.")
            return
        video = self.workspace.service.get_video(video_id)
        if video is None:
            QMessageBox.warning(self, "Video no encontrado", "El video seleccionado no existe.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(video.source_path).parent)))
