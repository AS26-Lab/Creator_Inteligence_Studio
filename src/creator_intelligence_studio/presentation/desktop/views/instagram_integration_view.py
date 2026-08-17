"""Panel de integracion de solo lectura para Instagram."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QFormLayout,
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

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider, InstagramLinkMethod
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class InstagramIntegrationView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "instagram_service", None)

        self.tabs = QTabWidget()
        self.connection_tab = QWidget()
        self.account_tab = QWidget()
        self.sync_tab = QWidget()
        self.media_tab = QWidget()
        self.links_tab = QWidget()
        self.insights_tab = QWidget()
        self.history_tab = QWidget()
        self.rate_limit_tab = QWidget()
        self.privacy_tab = QWidget()
        for tab, label in (
            (self.connection_tab, "Connection"),
            (self.account_tab, "Account"),
            (self.sync_tab, "Sync"),
            (self.media_tab, "Remote Media"),
            (self.links_tab, "Content Links"),
            (self.insights_tab, "Insights"),
            (self.history_tab, "Sync History"),
            (self.rate_limit_tab, "Rate Limits"),
            (self.privacy_tab, "Privacy"),
        ):
            self.tabs.addTab(tab, label)

        self._build_connection_tab()
        self._build_account_tab()
        self._build_sync_tab()
        self._build_media_tab()
        self._build_links_tab()
        self._build_insights_tab()
        self._build_history_tab()
        self._build_rate_limit_tab()
        self._build_privacy_tab()

        title = QLabel("Instagram Integration")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Integracion oficial, segura y de solo lectura para cuentas profesionales de Instagram.")
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

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(header)
        layout.addWidget(self.tabs)
        self.refresh()

    def _build_connection_tab(self) -> None:
        self.connection_table = QTableWidget(0, 7)
        self.connection_table.setHorizontalHeaderLabels(["Estado", "Cuenta", "Provider", "Scopes", "API", "Acceso", "ID"])
        self.connection_table.setColumnHidden(6, True)
        self.connection_empty = EmptyStateWidget("Sin conexiones", "Conecta una cuenta profesional mediante Instagram Login oficial.")
        self.connection_refresh = QPushButton("Actualizar")
        self.connection_verify = QPushButton("Verificar")
        self.connection_profile = QPushButton("Actualizar perfil")
        self.connection_disconnect = QPushButton("Desconectar")
        self.connection_revoke = QPushButton("Revocar")
        self.connection_refresh.clicked.connect(self.refresh)
        self.connection_verify.clicked.connect(self._verify_connection)
        self.connection_profile.clicked.connect(self._refresh_profile)
        self.connection_disconnect.clicked.connect(self._disconnect_connection)
        self.connection_revoke.clicked.connect(self._revoke_connection)
        layout = QVBoxLayout(self.connection_tab)
        actions = QHBoxLayout()
        for widget in (self.connection_refresh, self.connection_verify, self.connection_profile, self.connection_disconnect, self.connection_revoke):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.connection_empty)
        layout.addWidget(self.connection_table)

    def _build_account_tab(self) -> None:
        self.account_table = QTableWidget(0, 8)
        self.account_table.setHorizontalHeaderLabels(["Username", "Type", "Followers", "Follows", "Media", "Selected", "Last sync", "ID"])
        self.account_table.setColumnHidden(7, True)
        self.account_empty = EmptyStateWidget("Sin cuentas", "Las cuentas profesionales importadas aparecen aqui.")
        self.account_select = QPushButton("Seleccionar")
        self.account_select.clicked.connect(self._select_account)
        layout = QVBoxLayout(self.account_tab)
        layout.addWidget(self.account_select)
        layout.addWidget(self.account_empty)
        layout.addWidget(self.account_table)

    def _build_sync_tab(self) -> None:
        self.sync_account_id = QLabel("Cuenta: ninguna")
        self.sync_cursor = QLabel("Cursor: ninguno")
        self.sync_period = QLabel("Periodo: days_28")
        self.sync_account_button = QPushButton("Sync cuenta")
        self.sync_media_button = QPushButton("Sync media")
        self.sync_insights_button = QPushButton("Sync insights")
        self.sync_incremental_button = QPushButton("Incremental")
        self.sync_repair_button = QPushButton("Repair")
        self.sync_account_button.clicked.connect(self._sync_account)
        self.sync_media_button.clicked.connect(self._sync_media)
        self.sync_insights_button.clicked.connect(self._sync_insights)
        self.sync_incremental_button.clicked.connect(self._sync_incremental)
        self.sync_repair_button.clicked.connect(self._sync_repair)
        self.sync_notes = QLabel("Solo lectura. No hay publicaciones, comentarios ni mensajes.")
        self.sync_notes.setWordWrap(True)
        self.sync_notes.setObjectName("MutedLabel")
        layout = QVBoxLayout(self.sync_tab)
        layout.addWidget(self.sync_account_id)
        layout.addWidget(self.sync_cursor)
        layout.addWidget(self.sync_period)
        actions = QHBoxLayout()
        for widget in (self.sync_account_button, self.sync_media_button, self.sync_insights_button, self.sync_incremental_button, self.sync_repair_button):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.sync_notes)

    def _build_media_tab(self) -> None:
        self.media_table = QTableWidget(0, 8)
        self.media_table.setHorizontalHeaderLabels(["Type", "Product", "Caption", "Timestamp", "Permalink", "Children", "Remote status", "ID"])
        self.media_table.setColumnHidden(7, True)
        self.media_empty = EmptyStateWidget("Sin medios remotos", "Los medios propios sincronizados aparecen aqui.")
        layout = QVBoxLayout(self.media_tab)
        layout.addWidget(self.media_empty)
        layout.addWidget(self.media_table)

    def _build_links_tab(self) -> None:
        self.links_table = QTableWidget(0, 7)
        self.links_table.setHorizontalHeaderLabels(["Metodo", "Confianza", "Estado", "Remote media", "Publication", "Packaging", "ID"])
        self.links_table.setColumnHidden(6, True)
        self.links_empty = EmptyStateWidget("Sin vinculos", "Los vinculos locales con publicaciones o assets aparecen aqui.")
        layout = QVBoxLayout(self.links_tab)
        layout.addWidget(self.links_empty)
        layout.addWidget(self.links_table)

    def _build_insights_tab(self) -> None:
        self.insights_table = QTableWidget(0, 8)
        self.insights_table.setHorizontalHeaderLabels(["Scope", "Metric", "Raw metric", "Value", "Unit", "Period", "Quality", "ID"])
        self.insights_table.setColumnHidden(7, True)
        self.insights_empty = EmptyStateWidget("Sin insights", "Las metricas oficiales importadas aparecen aqui.")
        layout = QVBoxLayout(self.insights_tab)
        layout.addWidget(self.insights_empty)
        layout.addWidget(self.insights_table)

    def _build_history_tab(self) -> None:
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["Type", "Status", "Discovered", "Imported", "Warnings", "Cursor", "ID"])
        self.history_table.setColumnHidden(6, True)
        self.history_empty = EmptyStateWidget("Sin historial", "Las corridas de sincronizacion aparecen aqui.")
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.history_empty)
        layout.addWidget(self.history_table)

    def _build_rate_limit_tab(self) -> None:
        self.rate_limit_table = QTableWidget(0, 5)
        self.rate_limit_table.setHorizontalHeaderLabels(["Operation", "Estimated usage", "Requests", "Date", "ID"])
        self.rate_limit_table.setColumnHidden(4, True)
        self.rate_limit_empty = EmptyStateWidget("Sin uso", "El seguimiento local de rate limits aparece aqui.")
        layout = QVBoxLayout(self.rate_limit_tab)
        layout.addWidget(self.rate_limit_empty)
        layout.addWidget(self.rate_limit_table)

    def _build_privacy_tab(self) -> None:
        self.privacy_text = QTextEdit()
        self.privacy_text.setReadOnly(True)
        self.privacy_text.setPlainText(
            "Privacidad:\n"
            "- Solo cuentas profesionales compatibles.\n"
            "- Solo scopes de lectura aprobados.\n"
            "- Tokens protegidos fuera de SQLite principal.\n"
            "- No se publican, comentan ni eliminan medios.\n"
            "- No se descargan covers automaticamente.\n"
            "- TikTok sigue por importacion manual.\n"
        )
        layout = QVBoxLayout(self.privacy_tab)
        layout.addWidget(self.privacy_text)

    def _selected_connection_id(self) -> str | None:
        rows = self.connection_table.selectionModel().selectedRows() if self.connection_table.selectionModel() else []
        if not rows:
            return None
        item = self.connection_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def _selected_account_id(self) -> str | None:
        rows = self.account_table.selectionModel().selectedRows() if self.account_table.selectionModel() else []
        if not rows:
            return None
        item = self.account_table.item(rows[0].row(), 7)
        return item.text() if item else None

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id or ""
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        self._refresh_connections(creator_id)
        self._refresh_accounts(creator_id)
        self._refresh_media()
        self._refresh_links(creator_id)
        self._refresh_insights(creator_id)
        self._refresh_history(creator_id)
        self._refresh_rate_limits()

    def _refresh_connections(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_instagram_connections(creator_id))
        self.connection_table.setRowCount(0)
        if not items:
            self.connection_table.hide()
            self.connection_empty.show()
            return
        self.connection_empty.hide()
        self.connection_table.show()
        for row, item in enumerate(items):
            self.connection_table.insertRow(row)
            scopes = item.granted_scopes_json
            values = [item.status.value, item.account_identifier or "", item.provider, scopes, item.api_version, item.access_level.value if item.access_level else "", item.id]
            for col, value in enumerate(values):
                self.connection_table.setItem(row, col, _item(value))

    def _refresh_accounts(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_instagram_accounts(creator_id))
        self.account_table.setRowCount(0)
        if not items:
            self.account_table.hide()
            self.account_empty.show()
            return
        self.account_empty.hide()
        self.account_table.show()
        for row, item in enumerate(items):
            self.account_table.insertRow(row)
            values = [item.username, item.account_type.value, item.followers_count, item.follows_count, item.media_count, "1" if item.selected_for_sync else "0", item.last_synced_at.isoformat() if item.last_synced_at else "", item.id]
            for col, value in enumerate(values):
                self.account_table.setItem(row, col, _item(value))

    def _refresh_media(self) -> None:
        account_id = self._selected_account_id()
        items = [] if not account_id else list(self.workspace.list_instagram_media(account_id))
        self.media_table.setRowCount(0)
        if not items:
            self.media_table.hide()
            self.media_empty.show()
            return
        self.media_empty.hide()
        self.media_table.show()
        for row, item in enumerate(items):
            self.media_table.insertRow(row)
            values = [item.media_type.value, item.media_product_type or "", item.caption or "", item.timestamp.isoformat(), item.permalink or "", item.children_count or "", item.remote_status, item.id]
            for col, value in enumerate(values):
                self.media_table.setItem(row, col, _item(value))

    def _refresh_links(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_instagram_content_links(creator_id))
        self.links_table.setRowCount(0)
        if not items:
            self.links_table.hide()
            self.links_empty.show()
            return
        self.links_empty.hide()
        self.links_table.show()
        for row, item in enumerate(items):
            self.links_table.insertRow(row)
            values = [item.link_method.value, item.confidence_level, item.status, item.remote_media_id, item.publication_id or "", item.packaging_asset_id or "", item.id]
            for col, value in enumerate(values):
                self.links_table.setItem(row, col, _item(value))

    def _refresh_insights(self, creator_id: str) -> None:
        items = []
        if creator_id:
            for account in self.workspace.list_instagram_accounts(creator_id):
                items.extend(self.workspace.list_instagram_insight_imports(creator_id, account_id=account.id))
        self.insights_table.setRowCount(0)
        if not items:
            self.insights_table.hide()
            self.insights_empty.show()
            return
        self.insights_empty.hide()
        self.insights_table.show()
        row_index = 0
        for insight in items:
            for value in self.workspace.list_instagram_insight_values(insight.id):
                self.insights_table.insertRow(row_index)
                self.insights_table.setItem(row_index, 0, _item(insight.insight_scope.value))
                self.insights_table.setItem(row_index, 1, _item(value.metric_key))
                self.insights_table.setItem(row_index, 2, _item(value.raw_metric_name))
                self.insights_table.setItem(row_index, 3, _item(value.numeric_value if value.numeric_value is not None else value.text_value))
                self.insights_table.setItem(row_index, 4, _item(value.unit))
                self.insights_table.setItem(row_index, 5, _item(value.period))
                self.insights_table.setItem(row_index, 6, _item(value.quality_status))
                self.insights_table.setItem(row_index, 7, _item(value.id))
                row_index += 1

    def _refresh_history(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_instagram_sync_runs(creator_id))
        self.history_table.setRowCount(0)
        if not items:
            self.history_table.hide()
            self.history_empty.show()
            return
        self.history_empty.hide()
        self.history_table.show()
        for row, item in enumerate(items):
            self.history_table.insertRow(row)
            values = [item.sync_type.value, item.status.value, item.discovered_count, item.imported_count, item.warning_count, json.loads(item.cursor_json)["cursor"] if item.cursor_json else "", item.id]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, _item(value))

    def _refresh_rate_limits(self) -> None:
        connection_id = self._selected_connection_id()
        items = [] if not connection_id else list(self.workspace.list_instagram_rate_limit_usage(connection_id))
        self.rate_limit_table.setRowCount(0)
        if not items:
            self.rate_limit_table.hide()
            self.rate_limit_empty.show()
            return
        self.rate_limit_empty.hide()
        self.rate_limit_table.show()
        for row, item in enumerate(items):
            self.rate_limit_table.insertRow(row)
            values = [item.operation_key, item.estimated_usage or "", item.request_count, item.usage_date, item.id]
            for col, value in enumerate(values):
                self.rate_limit_table.setItem(row, col, _item(value))

    def _verify_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        try:
            result = self.workspace.verify_instagram_connection(connection_id)
        except Exception as exc:  # pragma: no cover - UI feedback only
            QMessageBox.warning(self, "Instagram", str(exc))
            return
        QMessageBox.information(self, "Instagram", f"Conexion verificada: {result.connection.status.value}")
        self.refresh()

    def _refresh_profile(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        try:
            result = self.workspace.read_instagram_account_profile(connection_id)
        except Exception as exc:  # pragma: no cover - UI feedback only
            QMessageBox.warning(self, "Instagram", str(exc))
            return
        if not getattr(result, "success", False):
            error = getattr(result, "error", None)
            message = getattr(error, "message", "No se pudo leer el perfil de Instagram.")
            QMessageBox.warning(self, "Instagram", message)
        else:
            account = result.account
            username = f"@{account.username}" if account and account.username else "perfil"
            QMessageBox.information(self, "Instagram", f"Perfil actualizado: {username}")
        self.refresh()

    def _disconnect_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        self.workspace.disconnect_instagram_connection(connection_id)
        self.refresh()

    def _revoke_connection(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        self.workspace.revoke_instagram_connection(connection_id)
        self.refresh()

    def _select_account(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.select_instagram_account(account_id)
        self.refresh()

    def _sync_account(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.sync_instagram_account(account_id)
        self.refresh()

    def _sync_media(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.sync_instagram_media(account_id)
        self.refresh()

    def _sync_insights(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.sync_instagram_insights(account_id, period=InstagramInsightPeriod.DAYS_28)
        self.refresh()

    def _sync_incremental(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.sync_instagram_incremental(account_id)
        self.refresh()

    def _sync_repair(self) -> None:
        account_id = self._selected_account_id()
        if not account_id:
            return
        self.workspace.sync_instagram_repair(account_id)
        self.refresh()
