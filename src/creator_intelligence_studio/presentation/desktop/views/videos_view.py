"""Vista de videos."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Qt, Signal
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


class InspectionThread(QThread):
    """Ejecuta inspecciones tecnicas sin bloquear la UI."""

    result_ready = Signal(object)
    error_ready = Signal(str)

    def __init__(self, workspace: WorkspaceViewModel, video_id: str, force: bool = False) -> None:
        super().__init__()
        self.workspace = workspace
        self.video_id = video_id
        self.force = force

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            report = self.workspace.inspect_video(self.video_id, force=self.force)
        except DomainError as exc:
            self.error_ready.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensa general
            self.error_ready.emit(str(exc))
            return
        self.result_ready.emit(report)


class VideosView(QWidget):
    """Lista, filtros y registro de videos."""

    def __init__(self, workspace: WorkspaceViewModel, inspector: InspectorPanel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.inspector = inspector
        self._inspection_thread: InspectionThread | None = None
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por titulo, nombre o ruta")
        self.project_combo = QComboBox()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Todos", "Registrado", "Pendiente", "Procesando", "Completado", "Archivo faltante", "Error"])
        self.availability_combo = QComboBox()
        self.availability_combo.addItems(["Todas", "Disponible", "Archivo faltante"])
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Todas", "Archivo local", "Importacion de plataforma", "Referencia manual"])
        self.table = QTableWidget(0, 11, self)
        self.table.setHorizontalHeaderLabels(
            ["Titulo", "Original", "Extension", "Tamano", "Fuente", "Estado", "Disponible", "Registro", "Proyecto", "ID", "Ruta"]
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

        self.register_button = QPushButton("Registrar video")
        self.inspect_button = QPushButton("Inspeccionar video")
        self.reinspect_button = QPushButton("Reinspeccionar")
        self.verify_button = QPushButton("Verificar archivo")
        self.open_button = QPushButton("Abrir ubicacion")
        self.analysis_button = QPushButton("Iniciar analisis")
        self.analysis_button.setEnabled(False)

        for widget, tip in (
            (self.project_combo, "Filtra los videos del proyecto activo"),
            (self.status_combo, "Filtra por estado de procesamiento"),
            (self.availability_combo, "Filtra por disponibilidad del archivo"),
            (self.source_combo, "Filtra por tipo de fuente"),
            (self.search_edit, "Busca por titulo, nombre original, ruta o notas"),
            (self.register_button, "Registrar un video local como metadatos"),
            (self.inspect_button, "Ejecutar inspeccion tecnica local"),
            (self.reinspect_button, "Forzar una nueva inspeccion tecnica"),
            (self.verify_button, "Comprobar si el archivo sigue disponible"),
            (self.open_button, "Abrir la carpeta del archivo original"),
            (self.analysis_button, "Analisis audiovisual no disponible todavia"),
        ):
            widget.setToolTip(tip)
        for button in (self.register_button, self.inspect_button, self.reinspect_button, self.verify_button, self.open_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons = QHBoxLayout()
        buttons.addWidget(self.register_button)
        buttons.addWidget(self.inspect_button)
        buttons.addWidget(self.reinspect_button)
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
        self.inspect_button.clicked.connect(self._inspect_video)
        self.reinspect_button.clicked.connect(self._reinspect_video)
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
            self.project_combo.setCurrentIndex(index if index >= 0 else 0)
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
                "Si" if video.file_available else "No",
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

    def _inspection_for_selected_video(self):
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        if not video_id:
            return None
        return self.workspace.get_video_inspection(video_id)

    def _sync_selection(self) -> None:
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        video = self.workspace.service.get_video(video_id) if video_id else self.workspace.selected_video()
        if video is None:
            self.inspect_button.setEnabled(False)
            self.reinspect_button.setEnabled(False)
            self.inspector.set_empty("Inspector", "Selecciona un video para ver sus detalles.")
            return
        self.workspace.select_video(video.id)
        inspection = self.workspace.get_video_inspection(video.id)
        items = self.workspace.video_inspector_items(video, inspection)
        footer = "Registrar un video no lo copia ni lo procesa; solo guarda metadatos locales."
        self.inspector.set_items(f"Video: {video.title}", items, footer=footer)
        self.inspector.set_actions(
            [
                ("Inspeccionar video", self._inspect_video),
                ("Reinspeccionar", self._reinspect_video),
                ("Verificar archivo", self._verify_video),
                ("Abrir ubicacion", self._open_location),
            ]
        )
        self.inspect_button.setEnabled(True)
        self.reinspect_button.setEnabled(inspection is not None)

    def _set_inspection_running(self, running: bool) -> None:
        self.inspect_button.setEnabled(not running)
        self.reinspect_button.setEnabled(not running and self.workspace.selected_video_id is not None)
        self.register_button.setEnabled(not running)
        self.verify_button.setEnabled(not running)
        self.open_button.setEnabled(not running)
        self.analysis_button.setEnabled(False)
        self.inspect_button.setText("Inspeccionando..." if running else "Inspeccionar video")
        self.reinspect_button.setText("Reinspeccionando..." if running else "Reinspeccionar")

    def _run_inspection(self, force: bool) -> None:
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        if not video_id:
            QMessageBox.information(self, "Sin seleccion", "Selecciona un video primero.")
            return
        if self._inspection_thread is not None and self._inspection_thread.isRunning():
            return
        self._set_inspection_running(True)
        self._inspection_thread = InspectionThread(self.workspace, video_id, force=force)
        self._inspection_thread.result_ready.connect(self._inspection_finished)
        self._inspection_thread.error_ready.connect(self._inspection_failed)
        self._inspection_thread.finished.connect(self._inspection_thread.deleteLater)
        self._inspection_thread.start()

    def _inspection_finished(self, report) -> None:
        self._set_inspection_running(False)
        self.refresh()
        self.workspace.select_video(report.video.id)
        self._sync_selection()
        QMessageBox.information(
            self,
            "Inspeccion tecnica",
            f"Estado: {report.status.value}\nVigente: {'si' if not report.is_stale else 'no'}",
        )
        self._inspection_thread = None

    def _inspection_failed(self, message: str) -> None:
        self._set_inspection_running(False)
        QMessageBox.warning(self, "No se pudo inspeccionar", message)
        self._inspection_thread = None

    def _inspect_video(self) -> None:
        self._run_inspection(force=False)

    def _reinspect_video(self) -> None:
        self._run_inspection(force=True)

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
            QMessageBox.information(self, "Sin seleccion", "Selecciona un video primero.")
            return
        try:
            report = self.workspace.verify_video(video_id)
        except DomainError as exc:
            QMessageBox.warning(self, "No se pudo verificar", str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self,
            "Verificacion completada",
            f"Estado: {report.status}\nMetadata modificada: {'si' if report.metadata_changed else 'no'}",
        )

    def _open_location(self) -> None:
        video_id = self._selected_video_id() or self.workspace.selected_video_id
        if not video_id:
            QMessageBox.information(self, "Sin seleccion", "Selecciona un video primero.")
            return
        video = self.workspace.service.get_video(video_id)
        if video is None:
            QMessageBox.warning(self, "Video no encontrado", "El video seleccionado no existe.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(video.source_path).parent)))
