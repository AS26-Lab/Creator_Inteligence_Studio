"""Panel de integracion oficial de solo lectura para TikTok."""

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

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokLinkMethod
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class TikTokIntegrationView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.service = getattr(workspace, "tiktok_service", None)

        self.tabs = QTabWidget()
        self.connection_tab = QWidget()
        self.profile_tab = QWidget()
        self.sync_tab = QWidget()
        self.videos_tab = QWidget()
        self.links_tab = QWidget()
        self.metrics_tab = QWidget()
        self.history_tab = QWidget()
        self.rate_limit_tab = QWidget()
        self.privacy_tab = QWidget()
        for tab, label in (
            (self.connection_tab, "Connection"),
            (self.profile_tab, "Profile"),
            (self.sync_tab, "Sync"),
            (self.videos_tab, "Remote Videos"),
            (self.links_tab, "Content Links"),
            (self.metrics_tab, "Public Metrics"),
            (self.history_tab, "Sync History"),
            (self.rate_limit_tab, "Rate Limits"),
            (self.privacy_tab, "Privacy"),
        ):
            self.tabs.addTab(tab, label)

        self._build_connection_tab()
        self._build_profile_tab()
        self._build_sync_tab()
        self._build_videos_tab()
        self._build_links_tab()
        self._build_metrics_tab()
        self._build_history_tab()
        self._build_rate_limit_tab()
        self._build_privacy_tab()

        title = QLabel("TikTok Integration")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Integracion oficial, segura y estrictamente de lectura para TikTok Login Kit y Display API.")
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
        self.connection_table.setHorizontalHeaderLabels(["Estado", "Cuenta", "Scopes", "API", "Acceso", "Verificada", "ID"])
        self.connection_table.setColumnHidden(6, True)
        self.connection_empty = EmptyStateWidget("Sin conexiones", "Conecta una cuenta TikTok usando OAuth oficial de escritorio.")
        self.connection_connect = QPushButton("Conectar")
        self.connection_verify = QPushButton("Verificar")
        self.connection_disconnect = QPushButton("Desconectar")
        self.connection_revoke = QPushButton("Revocar")
        self.connection_connect.clicked.connect(self._connect)
        self.connection_verify.clicked.connect(self._verify)
        self.connection_disconnect.clicked.connect(self._disconnect)
        self.connection_revoke.clicked.connect(self._revoke)
        layout = QVBoxLayout(self.connection_tab)
        actions = QHBoxLayout()
        for widget in (self.connection_connect, self.connection_verify, self.connection_disconnect, self.connection_revoke):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.connection_empty)
        layout.addWidget(self.connection_table)

    def _build_profile_tab(self) -> None:
        self.profile_table = QTableWidget(0, 8)
        self.profile_table.setHorizontalHeaderLabels(["Display", "Username", "Followers", "Following", "Likes", "Videos", "Selected", "ID"])
        self.profile_table.setColumnHidden(7, True)
        self.profile_empty = EmptyStateWidget("Sin perfiles", "Los perfiles autorizados aparecen aqui.")
        self.profile_select = QPushButton("Seleccionar")
        self.profile_sync = QPushButton("Sync perfil")
        self.profile_select.clicked.connect(self._select_profile)
        self.profile_sync.clicked.connect(self._sync_profile)
        layout = QVBoxLayout(self.profile_tab)
        actions = QHBoxLayout()
        actions.addWidget(self.profile_select)
        actions.addWidget(self.profile_sync)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.profile_empty)
        layout.addWidget(self.profile_table)

    def _build_sync_tab(self) -> None:
        self.sync_profile_label = QLabel("Perfil: ninguno")
        self.sync_cursor_label = QLabel("Cursor: ninguno")
        self.sync_profile_button = QPushButton("Sync perfil")
        self.sync_videos_button = QPushButton("Sync videos")
        self.sync_incremental_button = QPushButton("Incremental")
        self.sync_public_metrics_button = QPushButton("Metricas publicas")
        self.sync_repair_button = QPushButton("Repair")
        self.sync_profile_button.clicked.connect(self._sync_profile)
        self.sync_videos_button.clicked.connect(self._sync_videos)
        self.sync_incremental_button.clicked.connect(self._sync_incremental)
        self.sync_public_metrics_button.clicked.connect(self._sync_public_metrics)
        self.sync_repair_button.clicked.connect(self._sync_repair)
        self.sync_notes = QLabel("Solo lectura. No hay publicaciones, uploads, drafts, comentarios ni mensajes.")
        self.sync_notes.setWordWrap(True)
        self.sync_notes.setObjectName("MutedLabel")
        layout = QVBoxLayout(self.sync_tab)
        layout.addWidget(self.sync_profile_label)
        layout.addWidget(self.sync_cursor_label)
        actions = QHBoxLayout()
        for widget in (self.sync_profile_button, self.sync_videos_button, self.sync_incremental_button, self.sync_public_metrics_button, self.sync_repair_button):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.sync_notes)

    def _build_videos_tab(self) -> None:
        self.videos_table = QTableWidget(0, 8)
        self.videos_table.setHorizontalHeaderLabels(["Titulo", "Descripcion", "Create", "Views", "Likes", "Shares", "Cover", "ID"])
        self.videos_table.setColumnHidden(7, True)
        self.videos_empty = EmptyStateWidget("Sin videos", "Los videos publicos propios importados aparecen aqui.")
        self.video_refresh = QPushButton("Refrescar cover")
        self.video_refresh.clicked.connect(self._refresh_video)
        layout = QVBoxLayout(self.videos_tab)
        layout.addWidget(self.video_refresh)
        layout.addWidget(self.videos_empty)
        layout.addWidget(self.videos_table)

    def _build_links_tab(self) -> None:
        self.links_table = QTableWidget(0, 7)
        self.links_table.setHorizontalHeaderLabels(["Metodo", "Confianza", "Estado", "Video remoto", "Publicacion", "Packaging", "ID"])
        self.links_table.setColumnHidden(6, True)
        self.links_empty = EmptyStateWidget("Sin vinculos", "Los enlaces de contenido se muestran aqui.")
        self.link_button = QPushButton("Vincular exacto")
        self.unlink_button = QPushButton("Desvincular")
        self.link_button.clicked.connect(self._link_content)
        self.unlink_button.clicked.connect(self._unlink_content)
        layout = QVBoxLayout(self.links_tab)
        actions = QHBoxLayout()
        actions.addWidget(self.link_button)
        actions.addWidget(self.unlink_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self.links_empty)
        layout.addWidget(self.links_table)

    def _build_metrics_tab(self) -> None:
        self.metrics_table = QTableWidget(0, 7)
        self.metrics_table.setHorizontalHeaderLabels(["Scope", "Metric", "Value", "Unit", "Observed", "Source", "ID"])
        self.metrics_table.setColumnHidden(6, True)
        self.metrics_empty = EmptyStateWidget("Sin metricas", "Las metricas publicas importadas aparecen aqui.")
        layout = QVBoxLayout(self.metrics_tab)
        layout.addWidget(self.metrics_empty)
        layout.addWidget(self.metrics_table)

    def _build_history_tab(self) -> None:
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["Tipo", "Estado", "Discovered", "Imported", "Updated", "Cursor", "ID"])
        self.history_table.setColumnHidden(6, True)
        self.history_empty = EmptyStateWidget("Sin historial", "Las corridas de sincronizacion aparecen aqui.")
        self.resume_button = QPushButton("Reanudar")
        self.resume_button.clicked.connect(self._resume)
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.resume_button)
        layout.addWidget(self.history_empty)
        layout.addWidget(self.history_table)

    def _build_rate_limit_tab(self) -> None:
        self.rate_limit_table = QTableWidget(0, 5)
        self.rate_limit_table.setHorizontalHeaderLabels(["Operacion", "Endpoint", "Solicitudes", "Uso estimado", "ID"])
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
            "- Solo scopes de lectura aprobados.\n"
            "- No se guardan tokens en SQLite principal.\n"
            "- No hay uploads, publication o content posting.\n"
            "- No se accede a comentarios, mensajes o Research API.\n"
            "- El contenido privado no se inventa.\n"
            "- La importacion manual CSV/XLSX sigue para metricas privadas.\n"
        )
        layout = QVBoxLayout(self.privacy_tab)
        layout.addWidget(self.privacy_text)

    def _selected_connection_id(self) -> str | None:
        rows = self.connection_table.selectionModel().selectedRows() if self.connection_table.selectionModel() else []
        if not rows:
            return None
        item = self.connection_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def _selected_profile_id(self) -> str | None:
        rows = self.profile_table.selectionModel().selectedRows() if self.profile_table.selectionModel() else []
        if not rows:
            return None
        item = self.profile_table.item(rows[0].row(), 7)
        return item.text() if item else None

    def _selected_video_id(self) -> str | None:
        rows = self.videos_table.selectionModel().selectedRows() if self.videos_table.selectionModel() else []
        if not rows:
            return None
        item = self.videos_table.item(rows[0].row(), 7)
        return item.text() if item else None

    def _selected_run_id(self) -> str | None:
        rows = self.history_table.selectionModel().selectedRows() if self.history_table.selectionModel() else []
        if not rows:
            return None
        item = self.history_table.item(rows[0].row(), 6)
        return item.text() if item else None

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id or ""
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        self._refresh_connections(creator_id)
        self._refresh_profiles(creator_id)
        self._refresh_videos()
        self._refresh_links(creator_id)
        self._refresh_metrics(creator_id)
        self._refresh_history(creator_id)
        self._refresh_rate_limits()

    def _refresh_connections(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_tiktok_connections(creator_id))
        self.connection_table.setRowCount(0)
        if not items:
            self.connection_table.hide()
            self.connection_empty.show()
            return
        self.connection_empty.hide()
        self.connection_table.show()
        for row, item in enumerate(items):
            self.connection_table.insertRow(row)
            values = [item.status.value, item.account_identifier or item.open_id or "", item.granted_scopes_json, item.api_version, item.access_level.value if item.access_level else "", item.last_verified_at.isoformat() if item.last_verified_at else "", item.id]
            for col, value in enumerate(values):
                self.connection_table.setItem(row, col, _item(value))

    def _refresh_profiles(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_tiktok_profiles(creator_id))
        self.profile_table.setRowCount(0)
        if not items:
            self.profile_table.hide()
            self.profile_empty.show()
            return
        self.profile_empty.hide()
        self.profile_table.show()
        for row, item in enumerate(items):
            self.profile_table.insertRow(row)
            values = [item.display_name or "", item.username or "", item.follower_count, item.following_count, item.likes_count, item.video_count, "si" if item.selected_for_sync else "no", item.id]
            for col, value in enumerate(values):
                self.profile_table.setItem(row, col, _item(value))

    def _refresh_videos(self) -> None:
        profile_id = self._selected_profile_id()
        items = [] if not profile_id else list(self.workspace.list_tiktok_videos(profile_id))
        self.videos_table.setRowCount(0)
        if not items:
            self.videos_table.hide()
            self.videos_empty.show()
            return
        self.videos_empty.hide()
        self.videos_table.show()
        for row, item in enumerate(items):
            self.videos_table.insertRow(row)
            values = [item.title or "", item.video_description or "", item.create_time.isoformat(), item.view_count, item.like_count, item.share_count, item.cover_image_url or "", item.id]
            for col, value in enumerate(values):
                self.videos_table.setItem(row, col, _item(value))

    def _refresh_links(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_tiktok_content_links(creator_id))
        self.links_table.setRowCount(0)
        if not items:
            self.links_table.hide()
            self.links_empty.show()
            return
        self.links_empty.hide()
        self.links_table.show()
        for row, item in enumerate(items):
            self.links_table.insertRow(row)
            values = [item.link_method.value, item.confidence_level, item.status, item.remote_video_id, item.publication_id or "", item.packaging_asset_id or "", item.id]
            for col, value in enumerate(values):
                self.links_table.setItem(row, col, _item(value))

    def _refresh_metrics(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_tiktok_metric_imports(creator_id))
        self.metrics_table.setRowCount(0)
        if not items:
            self.metrics_table.hide()
            self.metrics_empty.show()
            return
        self.metrics_empty.hide()
        self.metrics_table.show()
        for row, item in enumerate(items):
            self.metrics_table.insertRow(row)
            values = [item.metric_scope.value, item.metric_scope.value, item.observed_at.isoformat(), item.source_type.value, item.profile_id, item.remote_video_id or "", item.id]
            # columns intentionally carry raw source context for inspection
            for col, value in enumerate(values):
                self.metrics_table.setItem(row, col, _item(value))

    def _refresh_history(self, creator_id: str) -> None:
        items = [] if not creator_id else list(self.workspace.list_tiktok_sync_runs(creator_id))
        self.history_table.setRowCount(0)
        if not items:
            self.history_table.hide()
            self.history_empty.show()
            return
        self.history_empty.hide()
        self.history_table.show()
        for row, item in enumerate(items):
            self.history_table.insertRow(row)
            values = [item.sync_type.value, item.status.value, item.discovered_count, item.imported_count, item.updated_count, item.cursor_json or "", item.id]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, _item(value))

    def _refresh_rate_limits(self) -> None:
        connection_id = self._selected_connection_id()
        items = [] if not connection_id else list(self.workspace.list_tiktok_rate_limit_usage(connection_id))
        self.rate_limit_table.setRowCount(0)
        if not items:
            self.rate_limit_table.hide()
            self.rate_limit_empty.show()
            return
        self.rate_limit_empty.hide()
        self.rate_limit_table.show()
        for row, item in enumerate(items):
            self.rate_limit_table.insertRow(row)
            values = [item.operation_key, item.endpoint, item.request_count, item.estimated_usage or "", item.id]
            for col, value in enumerate(values):
                self.rate_limit_table.setItem(row, col, _item(value))

    def _connect(self) -> None:
        QMessageBox.information(self, "TikTok", "Usa la CLI o la integracion de escritorio para iniciar el OAuth de escritorio.")

    def _verify(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        if self.service is not None:
            self.service.verify_connection(connection_id)
        self.refresh()

    def _disconnect(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        if self.service is not None:
            self.service.disconnect_connection(connection_id)
        self.refresh()

    def _revoke(self) -> None:
        connection_id = self._selected_connection_id()
        if not connection_id:
            return
        if self.service is not None:
            self.service.revoke_connection(connection_id)
        self.refresh()

    def _select_profile(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.select_profile(profile_id)
        self.refresh()

    def _sync_profile(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.sync_profile(profile_id=profile_id)
        self.refresh()

    def _sync_videos(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.sync_videos(profile_id=profile_id)
        self.refresh()

    def _sync_incremental(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.sync_incremental(profile_id=profile_id)
        self.refresh()

    def _sync_public_metrics(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.sync_public_metrics(profile_id=profile_id)
        self.refresh()

    def _sync_repair(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id and self.service is not None:
            self.service.sync_repair(profile_id=profile_id)
        self.refresh()

    def _refresh_video(self) -> None:
        video_id = self._selected_video_id()
        if video_id and self.service is not None:
            self.service.sync_cover_refresh(remote_video_id=video_id)
        self.refresh()

    def _link_content(self) -> None:
        video_id = self._selected_video_id()
        if video_id and self.service is not None:
            self.service.link_content(remote_video_id=video_id, link_method=TikTokLinkMethod.EXACT_TIKTOK_ID, confidence_level="high", status="approved")
        self.refresh()

    def _unlink_content(self) -> None:
        video_id = self._selected_video_id()
        if video_id and self.service is not None:
            self.service.unlink_content(remote_video_id=video_id)
        self.refresh()

    def _resume(self) -> None:
        run_id = self._selected_run_id()
        if run_id and self.service is not None:
            self.service.resume_sync(run_id)
        self.refresh()

