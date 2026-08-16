"""Panel de integracion YouTube de solo lectura."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from creator_intelligence_studio.domain.integrations import IntegrationHealth, IntegrationUserStatus
from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


def _health_status_line(health: IntegrationHealth | None) -> tuple[str, str]:
    if health is None:
        return "No conectado", "Selecciona o vincula una cuenta de YouTube."
    label = health.user_status_label
    message = health.user_status_message
    if health.user_status == IntegrationUserStatus.QUOTA_EXHAUSTED:
        retry_parts: list[str] = []
        if health.rate_limit_state is not None:
            if health.rate_limit_state.retry_after_seconds is not None:
                retry_parts.append(f"Reintento sugerido: {int(health.rate_limit_state.retry_after_seconds)} s")
            if health.rate_limit_state.reset_at is not None:
                retry_parts.append(f"Restablecimiento estimado: {health.rate_limit_state.reset_at.isoformat()}")
        if retry_parts:
            message = f"{message} {' '.join(retry_parts)}"
    elif health.user_status == IntegrationUserStatus.CONNECTED and health.last_success_at is not None:
        message = f"{message} Última actualización: {health.last_success_at.isoformat()}"
    return label, message


class YouTubeIntegrationView(QWidget):
    """Vista integrada de conexiones, contenido y sincronizacion YouTube."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "youtube_service", None)

        self.tabs = QTabWidget()
        self.connection_tab = QWidget()
        self.channels_tab = QWidget()
        self.sync_tab = QWidget()
        self.videos_tab = QWidget()
        self.links_tab = QWidget()
        self.imports_tab = QWidget()
        self.history_tab = QWidget()
        self.quota_tab = QWidget()

        for tab, label in (
            (self.connection_tab, "Connection"),
            (self.channels_tab, "Channels"),
            (self.sync_tab, "Sync"),
            (self.videos_tab, "Remote Videos"),
            (self.links_tab, "Content Links"),
            (self.imports_tab, "Analytics Imports"),
            (self.history_tab, "Sync History"),
            (self.quota_tab, "Quota & Privacy"),
        ):
            self.tabs.addTab(tab, label)

        self._build_connection_tab()
        self._build_channels_tab()
        self._build_sync_tab()
        self._build_videos_tab()
        self._build_links_tab()
        self._build_imports_tab()
        self._build_history_tab()
        self._build_quota_tab()

        title = QLabel("YouTube Integration")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Integracion oficial de solo lectura para canales, videos, miniaturas y metricas.")
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

    def _build_connection_tab(self) -> None:
        self.connection_table = QTableWidget(0, 6)
        self.connection_table.setHorizontalHeaderLabels(["Estado", "Cuenta", "Scopes", "Conectada", "Verificada", "ID"])
        self.connection_table.setColumnHidden(5, True)
        self.connection_table.itemSelectionChanged.connect(self._selection_changed)
        self.connection_empty = EmptyStateWidget("Sin conexiones", "Conecta una cuenta de Google/YouTube con scopes de lectura.")
        oauth_configured = bool(getattr(self.workspace.settings, "youtube_oauth_client_id", None))
        self.oauth_identity_label = QLabel(
            "Identidad OAuth de la aplicacion: configurada"
            if oauth_configured
            else "Identidad OAuth de la aplicacion: falta configuracion de build"
        )
        self.oauth_identity_label.setObjectName("MutedLabel")
        self.oauth_identity_label.setWordWrap(True)
        self.status_label = QLabel("Estado YouTube: No conectado")
        self.status_label.setObjectName("TitleLabel")
        self.status_detail = QLabel("Selecciona o vincula una cuenta para ver el estado de cuota y autenticación.")
        self.status_detail.setObjectName("MutedLabel")
        self.status_detail.setWordWrap(True)
        self.google_account_identifier = QLineEdit()
        self.google_account_identifier.setPlaceholderText("account@example.com")
        self.scopes = QTextEdit()
        self.scopes.setPlainText("\n".join(READ_ONLY_SCOPES))
        self.scopes.setFixedHeight(80)
        self.connect_button = QPushButton("Iniciar conexion")
        self.verify_button = QPushButton("Verificar seleccionada")
        self.disconnect_button = QPushButton("Desconectar")
        self.revoke_button = QPushButton("Revocar")
        self.connect_button.clicked.connect(self._connect_account)
        self.verify_button.clicked.connect(self._verify_selected_connection)
        self.disconnect_button.clicked.connect(self._disconnect_selected_connection)
        self.revoke_button.clicked.connect(self._revoke_selected_connection)

        form = QFormLayout()
        form.addRow("Cuenta Google", self.google_account_identifier)
        form.addRow("Scopes lectura", self.scopes)

        actions = QHBoxLayout()
        for widget in (self.connect_button, self.verify_button, self.disconnect_button, self.revoke_button):
            actions.addWidget(widget)
        actions.addStretch(1)

        layout = QVBoxLayout(self.connection_tab)
        layout.addWidget(self.oauth_identity_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.status_detail)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.connection_empty)
        layout.addWidget(self.connection_table)

    def _build_channels_tab(self) -> None:
        self.channels_table = QTableWidget(0, 7)
        self.channels_table.setHorizontalHeaderLabels(["Titulo", "Channel ID", "Subs", "Videos", "Views", "Seleccionado", "ID"])
        self.channels_table.setColumnHidden(6, True)
        self.channels_table.itemSelectionChanged.connect(self._selection_changed)
        self.channels_empty = EmptyStateWidget("Sin canales", "Selecciona una conexion y sincroniza metadatos de canal.")
        self.select_channel_button = QPushButton("Seleccionar canal")
        self.select_channel_button.clicked.connect(self._select_selected_channel)
        layout = QVBoxLayout(self.channels_tab)
        layout.addWidget(self.select_channel_button)
        layout.addWidget(self.channels_empty)
        layout.addWidget(self.channels_table)

    def _build_sync_tab(self) -> None:
        self.sync_type = QLineEdit("incremental_sync")
        self.sync_cursor = QLineEdit()
        self.sync_channel_id = QLineEdit()
        self.sync_metrics = QTextEdit()
        self.sync_metrics.setFixedHeight(80)
        self.sync_include_thumbnails = QCheckBox("Importar miniaturas remotas")
        self.sync_include_analytics = QCheckBox("Importar metricas")
        self.sync_include_analytics.setChecked(True)
        self.sync_include_thumbnails.setChecked(False)
        self.sync_button = QPushButton("Sincronizar")
        self.sync_incremental_button = QPushButton("Incremental")
        self.sync_content_button = QPushButton("Catalogo")
        self.sync_analytics_button = QPushButton("Metricas")
        self.sync_repair_button = QPushButton("Repair")
        self.sync_resume_button = QPushButton("Reanudar corrida")
        self.sync_button.clicked.connect(self._sync_selected_channel)
        self.sync_incremental_button.clicked.connect(self._sync_incremental)
        self.sync_content_button.clicked.connect(self._sync_content)
        self.sync_analytics_button.clicked.connect(self._sync_analytics)
        self.sync_repair_button.clicked.connect(self._sync_repair)
        self.sync_resume_button.clicked.connect(self._resume_sync)
        form = QFormLayout()
        form.addRow("Channel ID", self.sync_channel_id)
        form.addRow("Sync type", self.sync_type)
        form.addRow("Cursor", self.sync_cursor)
        form.addRow("Metricas", self.sync_metrics)
        actions = QHBoxLayout()
        for widget in (self.sync_button, self.sync_incremental_button, self.sync_content_button, self.sync_analytics_button, self.sync_repair_button, self.sync_resume_button):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout = QVBoxLayout(self.sync_tab)
        layout.addLayout(form)
        layout.addWidget(self.sync_include_analytics)
        layout.addWidget(self.sync_include_thumbnails)
        layout.addLayout(actions)
        self.sync_help = QLabel("Usa sync incremental por defecto. No hay escrituras remotas.")
        self.sync_help.setObjectName("MutedLabel")
        self.sync_help.setWordWrap(True)
        layout.addWidget(self.sync_help)

    def _build_videos_tab(self) -> None:
        self.videos_table = QTableWidget(0, 7)
        self.videos_table.setHorizontalHeaderLabels(["Titulo", "Video ID", "Tipo", "Publicado", "Duracion", "Estado", "ID"])
        self.videos_table.setColumnHidden(6, True)
        self.videos_empty = EmptyStateWidget("Sin videos remotos", "Sincroniza un canal para importar su catalogo.")
        layout = QVBoxLayout(self.videos_tab)
        layout.addWidget(self.videos_empty)
        layout.addWidget(self.videos_table)

    def _build_links_tab(self) -> None:
        self.links_table = QTableWidget(0, 6)
        self.links_table.setHorizontalHeaderLabels(["Metodo", "Confianza", "Estado", "Video remoto", "Publicacion", "ID"])
        self.links_table.setColumnHidden(5, True)
        self.links_empty = EmptyStateWidget("Sin vinculos", "Los enlaces remotos a publicaciones apareceran aqui.")
        layout = QVBoxLayout(self.links_tab)
        layout.addWidget(self.links_empty)
        layout.addWidget(self.links_table)

    def _build_imports_tab(self) -> None:
        self.imports_table = QTableWidget(0, 7)
        self.imports_table.setHorizontalHeaderLabels(["Metrica", "Scope", "Periodo", "Valor", "Unidad", "Calidad", "ID"])
        self.imports_table.setColumnHidden(6, True)
        self.imports_empty = EmptyStateWidget("Sin importaciones", "Las metricas oficiales apareceran despues de sincronizar.")
        layout = QVBoxLayout(self.imports_tab)
        layout.addWidget(self.imports_empty)
        layout.addWidget(self.imports_table)

    def _build_history_tab(self) -> None:
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["Tipo", "Estado", "Discovered", "Imported", "Updated", "Warnings", "ID"])
        self.history_table.setColumnHidden(6, True)
        self.history_table.itemSelectionChanged.connect(self._selection_changed)
        self.history_empty = EmptyStateWidget("Sin historial", "Las corridas de sincronizacion apareceran aqui.")
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.history_empty)
        layout.addWidget(self.history_table)

    def _build_quota_tab(self) -> None:
        self.quota_table = QTableWidget(0, 4)
        self.quota_table.setHorizontalHeaderLabels(["Operacion", "Costo estimado", "Solicitudes", "Fecha"])
        self.quota_empty = EmptyStateWidget("Sin cuota registrada", "La cuota estimada se acumula localmente por operacion.")
        self.privacy_label = QLabel(
            "Privacidad: tokens protegidos fuera de SQLite principal. Solo se almacenan referencias locales, scopes y trazabilidad."
        )
        self.privacy_label.setWordWrap(True)
        self.privacy_label.setObjectName("MutedLabel")
        layout = QVBoxLayout(self.quota_tab)
        layout.addWidget(self.privacy_label)
        layout.addWidget(self.quota_empty)
        layout.addWidget(self.quota_table)

    def _selected_connection_id(self) -> str | None:
        rows = self.connection_table.selectionModel().selectedRows() if self.connection_table.selectionModel() else []
        if not rows:
            return None
        item = self.connection_table.item(rows[0].row(), 5)
        return item.text() if item else None

    def _selected_channel_id(self) -> str | None:
        rows = self.channels_table.selectionModel().selectedRows() if self.channels_table.selectionModel() else []
        if not rows:
            return None
        item = self.channels_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def _selected_run_id(self) -> str | None:
        rows = self.history_table.selectionModel().selectedRows() if self.history_table.selectionModel() else []
        if not rows:
            return None
        item = self.history_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def _active_connection(self, connections):
        selected_id = self._selected_connection_id()
        if selected_id:
            for connection in connections:
                if connection.id == selected_id:
                    return connection
        return connections[0] if connections else None

    def _selection_changed(self) -> None:
        enabled = self._selected_connection_id() is not None
        self.verify_button.setEnabled(enabled)
        self.disconnect_button.setEnabled(enabled)
        self.revoke_button.setEnabled(enabled)
        self.select_channel_button.setEnabled(self._selected_channel_id() is not None)
        self.sync_resume_button.setEnabled(self._selected_run_id() is not None)

    def _populate(self, table: QTableWidget, rows: list[list[object]]) -> None:
        table.setRowCount(0)
        for row_index, row in enumerate(rows):
            table.insertRow(row_index)
            for column, value in enumerate(row):
                table.setItem(row_index, column, _item(value))
        table.resizeColumnsToContents()

    def _connect_account(self) -> None:
        if self.service is None:
            QMessageBox.information(self, "YouTube", "El servicio de YouTube no esta disponible.")
            return
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "YouTube", "Selecciona un creador primero.")
            return
        scopes_text = self.scopes.toPlainText().strip()
        scopes = tuple(line.strip() for line in scopes_text.splitlines() if line.strip()) or READ_ONLY_SCOPES
        result = self.service.connect_account(
            creator_id=creator_id,
            google_account_identifier=self.google_account_identifier.text().strip() or None,
            scopes=scopes,
            interactive=True,
        )
        if result.authorization_url:
            QMessageBox.information(self, "YouTube", "Conexion iniciada. Revisa la URL de autorizacion si se mostro.")
        else:
            QMessageBox.information(self, "YouTube", "Cuenta de YouTube conectada correctamente.")
        self.refresh()

    def _verify_selected_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id or self.service is None:
            return
        try:
            self.service.verify_connection(connection_id)
        except Exception as exc:  # pragma: no cover - UI defensive
            QMessageBox.warning(self, "YouTube", str(exc))
            return
        self.refresh()

    def _disconnect_selected_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id or self.service is None:
            return
        self.service.disconnect_connection(connection_id)
        self.refresh()

    def _revoke_selected_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id or self.service is None:
            return
        self.service.revoke_connection(connection_id)
        self.refresh()

    def _select_selected_channel(self) -> None:
        channel_id = self._selected_channel_id()
        if not channel_id or self.service is None:
            return
        self.service.select_channel(channel_id)
        self.refresh()

    def _sync_selected_channel(self) -> None:
        if self.service is None:
            return
        channel_id = self.sync_channel_id.text().strip() or self._selected_channel_id()
        if not channel_id:
            QMessageBox.information(self, "YouTube", "Selecciona un canal primero.")
            return
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "YouTube", "Selecciona un creador primero.")
            return
        metrics = tuple(line.strip() for line in self.sync_metrics.toPlainText().splitlines() if line.strip()) if hasattr(self.sync_metrics, "toPlainText") else None
        self.service.sync_channel(
            creator_id=creator_id,
            channel_id=channel_id,
            sync_type=self.sync_type.text().strip() or "incremental_sync",
            cursor=self.sync_cursor.text().strip() or None,
            full_resync=False,
            include_analytics=self.sync_include_analytics.isChecked(),
            include_thumbnails=self.sync_include_thumbnails.isChecked(),
            metrics=metrics,
        )
        self.refresh()

    def _sync_incremental(self) -> None:
        if self.service is None:
            return
        channel_id = self.sync_channel_id.text().strip() or self._selected_channel_id()
        creator_id = self.workspace.selected_creator_id
        if not channel_id or not creator_id:
            return
        self.service.sync_incremental(creator_id=creator_id, channel_id=channel_id, cursor=self.sync_cursor.text().strip() or None)
        self.refresh()

    def _sync_content(self) -> None:
        if self.service is None:
            return
        channel_id = self.sync_channel_id.text().strip() or self._selected_channel_id()
        creator_id = self.workspace.selected_creator_id
        if not channel_id or not creator_id:
            return
        self.service.sync_content(creator_id=creator_id, channel_id=channel_id, cursor=self.sync_cursor.text().strip() or None)
        self.refresh()

    def _sync_analytics(self) -> None:
        if self.service is None:
            return
        channel_id = self.sync_channel_id.text().strip() or self._selected_channel_id()
        creator_id = self.workspace.selected_creator_id
        if not channel_id or not creator_id:
            return
        metrics = tuple(line.strip() for line in self.sync_metrics.toPlainText().splitlines() if line.strip())
        self.service.sync_analytics(creator_id=creator_id, channel_id=channel_id, cursor=self.sync_cursor.text().strip() or None, metrics=metrics or None)
        self.refresh()

    def _sync_repair(self) -> None:
        if self.service is None:
            return
        channel_id = self.sync_channel_id.text().strip() or self._selected_channel_id()
        creator_id = self.workspace.selected_creator_id
        if not channel_id or not creator_id:
            return
        self.service.sync_repair(creator_id=creator_id, channel_id=channel_id)
        self.refresh()

    def _resume_sync(self) -> None:
        run_id = self._selected_run_id()
        if not run_id or self.service is None:
            return
        self.service.resume_sync(run_id)
        self.refresh()

    def refresh(self) -> None:
        creator = self.workspace.selected_creator()
        self.creator_label.setText(f"Creador activo: {creator.display_name if creator else 'ninguno'}")
        if self.service is None or creator is None:
            self.connection_table.setRowCount(0)
            self.channels_table.setRowCount(0)
            self.videos_table.setRowCount(0)
            self.links_table.setRowCount(0)
            self.imports_table.setRowCount(0)
            self.history_table.setRowCount(0)
            self.quota_table.setRowCount(0)
            return

        connections = self.service.list_connections(creator.id)
        channels = self.service.list_channels(creator.id)
        sync_runs = self.service.list_sync_runs(creator.id)
        links = self.service.list_content_links(creator.id)
        imports = self.service.list_metric_imports(creator.id)
        active_connection = self._active_connection(connections)
        active_health = self.service.get_health(creator_id=creator.id, account_id=active_connection.id) if active_connection is not None else None
        status_label, status_detail = _health_status_line(active_health)
        self.status_label.setText(f"Estado YouTube: {status_label}")
        if active_health is not None and active_health.user_status == IntegrationUserStatus.QUOTA_EXHAUSTED and active_health.last_success_at is not None:
            status_detail = f"{status_detail} Última actualización: {active_health.last_success_at.isoformat()}"
        self.status_detail.setText(status_detail)

        self._populate(
            self.connection_table,
            [
                [
                    connection.status.value,
                    connection.google_account_identifier or "",
                    ", ".join(json.loads(connection.granted_scopes_json or "[]")),
                    connection.connected_at.isoformat() if connection.connected_at else "",
                    connection.last_verified_at.isoformat() if connection.last_verified_at else "",
                    connection.id,
                ]
                for connection in connections
            ],
        )
        self._populate(
            self.channels_table,
            [
                [
                    channel.title,
                    channel.youtube_channel_id,
                    channel.subscriber_count if channel.subscriber_count is not None else "oculto",
                    channel.video_count if channel.video_count is not None else "",
                    channel.view_count if channel.view_count is not None else "",
                    "si" if channel.selected_for_sync else "no",
                    channel.id,
                ]
                for channel in channels
            ],
        )
        videos = [video for channel in channels for video in self.service.list_remote_videos(channel.id)]
        self._populate(
            self.videos_table,
            [
                [
                    video.title,
                    video.youtube_video_id,
                    video.content_type.value,
                    video.published_at.isoformat(),
                    video.duration_seconds if video.duration_seconds is not None else "",
                    video.privacy_status or "unknown",
                    video.id,
                ]
                for video in videos
            ],
        )
        self._populate(
            self.links_table,
            [
                [
                    link.link_method.value,
                    link.confidence_level,
                    link.status,
                    link.remote_video_id,
                    link.publication_id or "",
                    link.id,
                ]
                for link in links
            ],
        )
        self._populate(
            self.imports_table,
            [
                [
                    value.metric_key,
                    import_record.metric_scope,
                    f"{import_record.date_start} -> {import_record.date_end}",
                    "",
                    "",
                    value.quality_status,
                    value.id,
                ]
                for import_record in imports
                for value in self.service.list_metric_values(import_record.id)[:1]
            ],
        )
        self._populate(
            self.history_table,
            [
                [
                    run.sync_type.value,
                    run.status.value,
                    run.discovered_count,
                    run.imported_count,
                    run.updated_count,
                    run.warning_count,
                    run.id,
                ]
                for run in sync_runs
            ],
        )
        quota_rows = self.service.list_quota_usage(connections[0].id) if connections else []
        self._populate(
            self.quota_table,
            [[quota.operation_key, quota.estimated_cost, quota.request_count, quota.usage_date] for quota in quota_rows],
        )

        self.connection_empty.setVisible(not connections)
        self.channels_empty.setVisible(not channels)
        self.videos_empty.setVisible(not videos)
        self.links_empty.setVisible(not links)
        self.imports_empty.setVisible(not imports)
        self.history_empty.setVisible(not sync_runs)
        self.quota_empty.setVisible(not quota_rows)
        self._selection_changed()
