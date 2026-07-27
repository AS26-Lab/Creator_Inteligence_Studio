"""Vista consolidada de integraciones de plataforma."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class _BaseIntegrationSection(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setObjectName("MutedLabel")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)
        header = QHBoxLayout()
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        self.layout = QVBoxLayout(self)
        self.layout.addLayout(header)
        self.layout.addWidget(self.subtitle_label)

    def refresh(self) -> None:
        pass


class IntegrationConnectionsView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Connections", "Resumen unificado de conexiones nativas y manuales.", parent)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Platform", "Status", "Account", "Connector", "Health", "Native status", "ID"])
        self.table.setColumnHidden(6, True)
        self.empty_state = EmptyStateWidget("Sin conexiones", "No hay conexiones registradas para el creador activo.")
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_connections(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            values = [row.platform.value, row.status.value, row.account_identifier or "-", row.connector_type.value, row.health_status.value, row.native_status, row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationHealthView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Health", "Verificacion local de credenciales, permisos, aprobaciones y ultima sincronizacion.", parent)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Platform", "Status", "Severity", "Message", "ID"])
        self.table.setColumnHidden(4, True)
        self.empty_state = EmptyStateWidget("Sin salud", "No hay comprobaciones registradas.")
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_health_checks(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        connections = {item.id: item for item in self.workspace.platform_service.list_connections(creator_id)} if self.workspace.platform_service and creator_id else {}
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            connection = connections.get(row.platform_connection_id)
            values = [connection.platform.value if connection else "-", row.status.value, row.severity.value, row.message or "-", row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationSyncCenterView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Sync Center", "Ejecuta sincronizaciones unificadas sin mezclar semanticas de plataforma.", parent)
        self.sync_all_button = QPushButton("Sync all")
        self.sync_incremental_button = QPushButton("Incremental")
        self.sync_resume_button = QPushButton("Resume latest")
        self.sync_cancel_button = QPushButton("Cancel latest")
        self.sync_all_button.clicked.connect(self._sync_all)
        self.sync_incremental_button.clicked.connect(self._sync_incremental)
        self.sync_resume_button.clicked.connect(self._resume_latest)
        self.sync_cancel_button.clicked.connect(self._cancel_latest)
        buttons = QHBoxLayout()
        for button in (self.sync_all_button, self.sync_incremental_button, self.sync_resume_button, self.sync_cancel_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Mode", "Status", "Platforms", "Warnings", "ID"])
        self.table.setColumnHidden(5, True)
        self.empty_state = EmptyStateWidget("Sin grupos", "Los grupos de sync aparecen aqui.")
        self.layout.addLayout(buttons)
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def _sync_all(self) -> None:
        if self.workspace.platform_service is None or self.workspace.selected_creator_id is None:
            return
        self.workspace.platform_service.start_sync(creator_id=self.workspace.selected_creator_id, platforms=None, mode="sequential", incremental=True)
        self.refresh()

    def _sync_incremental(self) -> None:
        self._sync_all()

    def _resume_latest(self) -> None:
        group = self._selected_group()
        if group is None or self.workspace.platform_service is None:
            return
        self.workspace.platform_service.resume_sync(group.id)

    def _cancel_latest(self) -> None:
        group = self._selected_group()
        if group is None or self.workspace.platform_service is None:
            return
        self.workspace.platform_service.cancel_sync(group.id)
        self.refresh()

    def _selected_group(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 5)
        if item is None or self.workspace.platform_service is None:
            return None
        return self.workspace.platform_service.repository.get_platform_sync_group(item.text())

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_sync_groups(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            payload = json.loads(row.configuration_json or "{}")
            values = [row.name, row.sync_mode.value, row.status.value, ",".join(str(item) for item in payload.get("platforms", [])) or str(row.platform_count), row.warning_count, row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationCapabilitiesView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Capabilities", "Capacidades disponibles, limitadas o deshabilitadas por plataforma.", parent)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Platform", "Capability", "Availability", "Limit", "ID"])
        self.table.setColumnHidden(4, True)
        self.empty_state = EmptyStateWidget("Sin capacidades", "No hay snapshots de capacidades aun.")
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_capabilities(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        connections = {item.id: item for item in self.workspace.platform_service.list_connections(creator_id)} if self.workspace.platform_service and creator_id else {}
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            connection = connections.get(row.platform_connection_id)
            values = [connection.platform.value if connection else "-", row.capability_key, row.availability_status.value, row.limitation_code or "-", row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationDataAvailabilityView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Data Availability", "Datos automaticos, manuales y ausentes sin mezclar semanticas.", parent)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Platform", "Category", "Key", "Availability", "Manual", "ID"])
        self.table.setColumnHidden(5, True)
        self.empty_state = EmptyStateWidget("Sin disponibilidad", "No hay disponibilidad registrada aun.")
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_data_availability(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        connections = {item.id: item for item in self.workspace.platform_service.list_connections(creator_id)} if self.workspace.platform_service and creator_id else {}
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            connection = connections.get(row.platform_connection_id)
            values = [connection.platform.value if connection else "-", row.data_category.value, row.data_key, row.availability_status.value, "si" if row.manual_import_available else "no", row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationHistoryView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "History", "Historial de grupos de sync y eventos consolidados.", parent)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Type", "Status", "Warnings", "Errors", "Created", "ID"])
        self.table.setColumnHidden(5, True)
        self.empty_state = EmptyStateWidget("Sin historial", "No hay grupos de sync consolidados.")
        self.layout.addWidget(self.empty_state)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        rows = self.workspace.platform_service.list_sync_groups(creator_id) if self.workspace.platform_service and creator_id else []
        self.table.setRowCount(0)
        if not rows:
            self.empty_state.show()
            self.table.hide()
            return
        self.empty_state.hide()
        self.table.show()
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            values = ["sync_group", row.status.value, row.warning_count, row.error_count, row.created_at.isoformat(), row.id]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class IntegrationPrivacyView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Privacy", "Garantias de solo lectura, sin publicaciones ni escritura remota.", parent)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.layout.addWidget(self.text)
        self.refresh()

    def refresh(self) -> None:
        self.text.setPlainText(
            "Privacy summary:\n"
            "- Read-only integrations only.\n"
            "- No remote writes, publishing, uploads or scraping.\n"
            "- Tokens stay out of the primary SQLite database.\n"
            "- Manual imports remain separate from platform APIs.\n"
            "- Remote delete is not performed by this consolidator.\n"
        )


class IntegrationOnboardingView(_BaseIntegrationSection):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(workspace, "Onboarding", "Guia para conectar, verificar y sincronizar plataformas.", parent)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.layout.addWidget(self.text)
        self.refresh()

    def refresh(self) -> None:
        self.text.setPlainText(
            "Onboarding:\n"
            "1. Selecciona un creador.\n"
            "2. Revisa conexiones por plataforma.\n"
            "3. Verifica permisos y aprobaciones.\n"
            "4. Ejecuta sync incremental o un grupo completo.\n"
            "5. Revisa availability y gaps manuales.\n"
            "6. Mantén el modelo de datos separado por plataforma.\n"
        )


class IntegrationsOverviewView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        title = QLabel("Integrations")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Consolidacion de YouTube, Instagram, TikTok y fuentes manuales sin mezclar semanticas.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")
        self.creator_label = QLabel("Creador activo: ninguno")
        self.creator_label.setObjectName("MutedLabel")
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)

        header = QHBoxLayout()
        header.addWidget(self.creator_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)

        self.tabs = QTabWidget()
        self.connections_view = IntegrationConnectionsView(workspace)
        self.health_view = IntegrationHealthView(workspace)
        self.sync_center_view = IntegrationSyncCenterView(workspace)
        self.capabilities_view = IntegrationCapabilitiesView(workspace)
        self.data_availability_view = IntegrationDataAvailabilityView(workspace)
        self.history_view = IntegrationHistoryView(workspace)
        self.privacy_view = IntegrationPrivacyView(workspace)
        self.onboarding_view = IntegrationOnboardingView(workspace)
        for view, label in (
            (self.connections_view, "Connections"),
            (self.health_view, "Health"),
            (self.sync_center_view, "Sync Center"),
            (self.capabilities_view, "Capabilities"),
            (self.data_availability_view, "Data Availability"),
            (self.history_view, "History"),
            (self.privacy_view, "Privacy"),
            (self.onboarding_view, "Onboarding"),
        ):
            self.tabs.addTab(view, label)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.creator_label)
        layout.addLayout(header)
        layout.addWidget(self.tabs)
        self.refresh()

    def refresh(self) -> None:
        self.creator_label.setText(f"Creador activo: {self.workspace.selected_creator_id or 'ninguno'}")
        self.connections_view.refresh()
        self.health_view.refresh()
        self.sync_center_view.refresh()
        self.capabilities_view.refresh()
        self.data_availability_view.refresh()
        self.history_view.refresh()
        self.privacy_view.refresh()
        self.onboarding_view.refresh()
