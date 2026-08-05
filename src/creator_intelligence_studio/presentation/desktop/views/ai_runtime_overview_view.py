"""Desktop view for AI runtime configuration and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import Callable

from PySide6.QtCore import QThread, Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.widgets.cards import EmptyStateWidget
from creator_intelligence_studio.presentation.desktop.error_mapping import map_error


logger = logging.getLogger(__name__)


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Si" if value else "No"
    return str(value)


def _safe_short_id(value: str | None) -> str:
    if not value:
        return "-"
    return value[:8]


def _safe_datetime(value: str | None) -> str:
    if not value:
        return "Sin comprobacion"
    return value.replace("T", " ").replace("Z", "")


class DiagnosticRunThread(QThread):
    result_ready = Signal(object)
    error_ready = Signal(str)

    def __init__(
        self,
        workspace: WorkspaceViewModel,
        provider: str,
        role: str,
        cache_policy: str,
        *,
        approval_execution_id: str | None = None,
        approved_by: str | None = None,
        approval_reason: str | None = None,
    ) -> None:
        super().__init__()
        self.workspace = workspace
        self.provider = provider
        self.role = role
        self.cache_policy = cache_policy
        self.approval_execution_id = approval_execution_id
        self.approved_by = approved_by
        self.approval_reason = approval_reason

    def run(self) -> None:  # pragma: no cover - flujo Qt
        try:
            if self.approval_execution_id:
                logger.info(
                    "ai_runtime_diagnostic.approval_continuation_started execution_id=%s provider=%s role=%s",
                    self.approval_execution_id,
                    self.provider,
                    self.role,
                )
                result = self.workspace.ai_runtime_approve_and_run_diagnostic(
                    self.approval_execution_id,
                    approved_by=self.approved_by,
                    approval_reason=self.approval_reason,
                )
            else:
                logger.info(
                    "ai_runtime_diagnostic.provider_call_started provider=%s role=%s cache_policy=%s",
                    self.provider,
                    self.role,
                    self.cache_policy,
                )
                result = self.workspace.run_ai_runtime_diagnostic(
                    provider=self.provider,
                    role=self.role,
                    cache_policy=self.cache_policy,
                )
        except Exception as exc:  # pragma: no cover - defensa general
            logger.info(
                "ai_runtime_diagnostic.execution_failed provider=%s role=%s error_class=%s",
                self.provider,
                self.role,
                exc.__class__.__name__,
            )
            self.error_ready.emit(str(exc))
            return
        if self.approval_execution_id:
            if getattr(result, "status", None) == "awaiting_approval":
                logger.info(
                    "ai_runtime_diagnostic.approval_continuation_failed execution_id=%s provider=%s role=%s",
                    self.approval_execution_id,
                    self.provider,
                    self.role,
                )
                self.error_ready.emit("No se pudo reanudar la ejecucion aprobada.")
                return
            logger.info(
                "ai_runtime_diagnostic.approval_continuation_completed execution_id=%s provider=%s role=%s",
                self.approval_execution_id,
                self.provider,
                self.role,
            )
        else:
            logger.info(
                "ai_runtime_diagnostic.provider_call_completed provider=%s role=%s",
                self.provider,
                self.role,
            )
        self.result_ready.emit(result)


def _capabilities_text(model: dict[str, object]) -> str:
    capabilities = model.get("capabilities_json")
    if isinstance(capabilities, dict) and capabilities:
        pieces: list[str] = []
        for key, value in sorted(capabilities.items()):
            if isinstance(value, bool):
                if value:
                    pieces.append(key)
            else:
                pieces.append(f"{key}={value}")
        if pieces:
            return ", ".join(pieces)
    flags: list[str] = []
    if model.get("supports_structured_output"):
        flags.append("structured_output")
    if model.get("supports_image_input"):
        flags.append("image_input")
    if model.get("supports_audio_input"):
        flags.append("audio_input")
    return ", ".join(flags) if flags else "-"


ROLE_LABELS = {
    "cheap_structured_model": "Modelo estructurado economico",
    "general_reasoning_model": "Modelo de razonamiento general",
    "creative_writing_model": "Modelo de escritura creativa",
    "multimodal_model": "Modelo multimodal",
    "transcription_fallback_model": "Modelo de respaldo para transcripcion",
    "evaluation_model": "Modelo de evaluacion",
}


PROVIDER_LINKS = {
    "openai": {
        "label": "OpenAI",
        "keys_url": "https://platform.openai.com/api-keys",
        "billing_url": "https://platform.openai.com/settings/organization/billing",
        "help_url": "https://help.openai.com/",
    },
    "anthropic": {
        "label": "Anthropic",
        "keys_url": "https://console.anthropic.com/settings/keys",
        "billing_url": "https://console.anthropic.com/settings/billing",
        "help_url": "https://support.anthropic.com/",
    },
}


def _provider_state_label(state: dict[str, object], *, configured: bool) -> str:
    if not configured:
        return "No configurado"
    last_check = state.get("last_check") or {}
    if not isinstance(last_check, dict) or not last_check:
        return "Configurado"
    status = str(last_check.get("status") or "").lower()
    error = last_check.get("error")
    category = ""
    if isinstance(error, dict):
        category = str(error.get("category") or "").lower()
    if status == "ok":
        return "Configurado"
    if category in {"authentication_error", "authorization_error"}:
        return "Credencial invalida"
    if category in {"billing_error", "quota_error"}:
        return "Sin creditos"
    if category in {"timeout", "network_error", "rate_limit_error", "provider_error"}:
        return "Error temporal"
    if status in {"failed", "blocked"}:
        return "Error temporal"
    return "Configurado"


def _model_price_text(model: dict[str, object]) -> str:
    input_price = model.get("input_price_per_million")
    output_price = model.get("output_price_per_million")
    currency = model.get("pricing_currency") or "USD"
    if input_price is None or output_price is None:
        return "Precio pendiente de verificar"
    return f"{input_price}/{output_price} {currency}"


def _refresh_enclosing_overview(widget: QWidget) -> None:
    parent = widget.parentWidget()
    while parent is not None:
        if hasattr(parent, "refresh") and callable(getattr(parent, "refresh")) and hasattr(parent, "tabs"):
            try:
                parent.refresh()
            except Exception:
                pass
            return
        parent = parent.parentWidget()


class ProviderCredentialDialog(QDialog):
    def __init__(self, provider_label: str, provider_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.provider_name = provider_name
        self.setModal(True)
        self.setWindowTitle(f"{provider_label} - credencial")
        self.secret_edit = QLineEdit()
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_edit.setPlaceholderText("Pega aqui la clave API")
        self.toggle_button = QPushButton("Mostrar")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self._toggle_visibility)
        self.save_button = QPushButton("Guardar")
        self.cancel_button = QPushButton("Cancelar")
        self.buttons = QDialogButtonBox()
        self.buttons.addButton(self.save_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)

        title = QLabel(f"Configurar {provider_label}")
        title.setObjectName("TitleLabel")
        explanation = QLabel(
            "La clave se almacenara en Windows Credential Manager. "
            "ChatGPT/Claude web y sus APIs tienen facturacion separada."
        )
        explanation.setWordWrap(True)
        explanation.setObjectName("MutedLabel")
        warning = QLabel("No se rellena la clave almacenada. Solo se captura una nueva credencial.")
        warning.setWordWrap(True)
        warning.setObjectName("MutedLabel")

        form = QFormLayout()
        form.addRow("Clave API", self.secret_edit)
        form.addRow("", self.toggle_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(explanation)
        layout.addWidget(warning)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _toggle_visibility(self) -> None:
        if self.toggle_button.isChecked():
            self.secret_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_button.setText("Ocultar")
        else:
            self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_button.setText("Mostrar")

    def secret(self) -> str:
        return self.secret_edit.text().strip()

    def accept(self) -> None:  # pragma: no cover - modal wiring
        if not self.secret():
            QMessageBox.warning(self, "AI Runtime", "Debes escribir una clave antes de guardar.")
            return
        super().accept()


class ProviderCardWidget(QFrame):
    def __init__(self, provider_name: str, provider_label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.provider_name = provider_name
        self.setObjectName(f"provider_card_{provider_name}")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.title_label = QLabel(provider_label)
        self.title_label.setObjectName("SectionLabel")
        self.state_label = QLabel()
        self.state_label.setObjectName("MutedLabel")
        self.mask_label = QLabel()
        self.mask_label.setWordWrap(True)
        self.check_label = QLabel()
        self.check_label.setWordWrap(True)
        self.check_label.setObjectName("MutedLabel")
        self.enabled_label = QLabel()
        self.enabled_label.setObjectName("MutedLabel")
        self.sync_label = QLabel()
        self.sync_label.setWordWrap(True)
        self.sync_label.setObjectName("MutedLabel")

        self.configure_button = QPushButton("Configurar clave")
        self.replace_button = QPushButton("Reemplazar clave")
        self.delete_button = QPushButton("Eliminar clave")
        self.test_button = QPushButton("Probar conexion")
        self.sync_button = QPushButton("Actualizar modelos")
        self.keys_button = QPushButton("Abrir sitio oficial de claves")
        self.billing_button = QPushButton("Abrir facturacion")
        self.help_button = QPushButton("Ver ayuda")
        self.configure_button.setObjectName(f"{provider_name}_configure_button")
        self.replace_button.setObjectName(f"{provider_name}_replace_button")
        self.delete_button.setObjectName(f"{provider_name}_delete_button")
        self.test_button.setObjectName(f"{provider_name}_test_button")
        self.sync_button.setObjectName(f"{provider_name}_sync_button")
        self.keys_button.setObjectName(f"{provider_name}_keys_button")
        self.billing_button.setObjectName(f"{provider_name}_billing_button")
        self.help_button.setObjectName(f"{provider_name}_help_button")

        buttons = QGridLayout()
        buttons.addWidget(self.configure_button, 0, 0)
        buttons.addWidget(self.replace_button, 0, 1)
        buttons.addWidget(self.delete_button, 0, 2)
        buttons.addWidget(self.test_button, 1, 0)
        buttons.addWidget(self.sync_button, 1, 1)
        buttons.addWidget(self.keys_button, 1, 2)
        buttons.addWidget(self.billing_button, 2, 0)
        buttons.addWidget(self.help_button, 2, 1, 1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.mask_label)
        layout.addWidget(self.check_label)
        layout.addWidget(self.enabled_label)
        layout.addWidget(self.sync_label)
        layout.addLayout(buttons)

    def refresh(self, state: dict[str, object]) -> None:
        configured = bool(state.get("configured"))
        self.state_label.setText(f"Estado: {_provider_state_label(state, configured=configured)}")
        self.mask_label.setText(f"Credencial: {state.get('masked_key') or 'no configurado'}")
        last_check = state.get("last_check") or {}
        if isinstance(last_check, dict) and last_check:
            self.check_label.setText(
                "Ultima comprobacion: "
                f"{_safe_datetime(str(last_check.get('checked_at')))} · "
                f"{_fmt(last_check.get('status'))} · "
                f"{_fmt(last_check.get('message'))}"
            )
        else:
            self.check_label.setText("Ultima comprobacion: sin comprobacion")
        self.enabled_label.setText(f"Habilitado: {'Si' if state.get('enabled', True) else 'No'}")
        last_sync = state.get("last_model_sync") or {}
        if isinstance(last_sync, dict) and last_sync:
            self.sync_label.setText(
                "Ultima sincronizacion: "
                f"{_safe_datetime(str(last_sync.get('checked_at')))} · "
                f"{_fmt(last_sync.get('status'))} · "
                f"encontrados {_fmt(last_sync.get('found_count'))} / "
                f"compatibles {_fmt(last_sync.get('compatible_count'))} / "
                f"nuevos {_fmt(last_sync.get('new_count'))} / "
                f"actualizados {_fmt(last_sync.get('updated_count'))} / "
                f"no visibles {_fmt(last_sync.get('unavailable_count'))}"
            )
        else:
            self.sync_label.setText("Ultima sincronizacion: sin sincronizar")
        self.configure_button.setEnabled(True)
        self.configure_button.setText("Configurar clave" if not configured else "Reemplazar clave")
        self.replace_button.setEnabled(configured)
        self.delete_button.setEnabled(configured)
        self.test_button.setEnabled(configured)
        self.sync_button.setEnabled(configured)


class ProvidersTab(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.cards: dict[str, ProviderCardWidget] = {}
        self._active_dialog: ProviderCredentialDialog | None = None
        title = QLabel("Proveedores")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Estado, credenciales, comprobaciones y accesos oficiales por proveedor.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        grid = QGridLayout()
        for column, provider_name in enumerate(("openai", "anthropic")):
            meta = PROVIDER_LINKS[provider_name]
            card = ProviderCardWidget(provider_name, meta["label"])
            card.configure_button.clicked.connect(lambda _=False, p=provider_name: self._configure_provider(p))
            card.replace_button.clicked.connect(lambda _=False, p=provider_name: self._configure_provider(p, replace=True))
            card.delete_button.clicked.connect(lambda _=False, p=provider_name: self._delete_provider(p))
            card.test_button.clicked.connect(lambda _=False, p=provider_name: self._test_provider(p))
            card.sync_button.clicked.connect(lambda _=False, p=provider_name: self._refresh_models(p))
            card.keys_button.clicked.connect(lambda _=False, p=provider_name: self._open_url(p, "keys"))
            card.billing_button.clicked.connect(lambda _=False, p=provider_name: self._open_url(p, "billing"))
            card.help_button.clicked.connect(lambda _=False, p=provider_name: self._open_url(p, "help"))
            self.cards[provider_name] = card
            grid.addWidget(card, 0, column)

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(header)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.refresh()

    def _open_url(self, provider_name: str, kind: str) -> None:
        url = PROVIDER_LINKS[provider_name][f"{kind}_url"]
        QDesktopServices.openUrl(QUrl(url))

    def _configure_provider(self, provider_name: str, replace: bool = False) -> None:
        meta = PROVIDER_LINKS[provider_name]
        dialog = ProviderCredentialDialog(meta["label"], provider_name, self)
        self._active_dialog = dialog

        def _save() -> None:
            secret = dialog.secret()
            if not secret:
                return
            self.workspace.ai_runtime_store_provider_credential(provider_name, secret)
            self.refresh()
            _refresh_enclosing_overview(self)

        dialog.accepted.connect(_save)
        dialog.rejected.connect(lambda: None)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _delete_provider(self, provider_name: str) -> None:
        meta = PROVIDER_LINKS[provider_name]
        answer = QMessageBox.question(
            self,
            "AI Runtime",
            f"Eliminar la credencial de {meta['label']}?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.workspace.ai_runtime_delete_provider_credential(provider_name)
        self.refresh()
        _refresh_enclosing_overview(self)

    def _refresh_models(self, provider_name: str) -> None:
        report = self.workspace.ai_runtime_refresh_provider_models(provider_name)
        self.refresh()
        _refresh_enclosing_overview(self)
        if report.get("status") == "ok":
            QMessageBox.information(
                self,
                "AI Runtime",
                f"{PROVIDER_LINKS[provider_name]['label']}: modelos encontrados {report.get('found_count', 0)}, compatibles {report.get('compatible_count', 0)}, nuevos {report.get('new_count', 0)}, actualizados {report.get('updated_count', 0)}.",
            )
            return
        QMessageBox.warning(self, "AI Runtime", f"{PROVIDER_LINKS[provider_name]['label']}: {report.get('message')}")

    def _test_provider(self, provider_name: str) -> None:
        diagnostic = self.workspace.ai_runtime_test_provider(provider_name)
        sync_report = None
        if diagnostic.status == "ok":
            sync_report = self.workspace.ai_runtime_refresh_provider_models(provider_name)
        self.refresh()
        _refresh_enclosing_overview(self)
        if diagnostic.status == "ok":
            if isinstance(sync_report, dict) and sync_report.get("status") == "ok":
                QMessageBox.information(
                    self,
                    "AI Runtime",
                    f"{PROVIDER_LINKS[provider_name]['label']}: {diagnostic.message} | modelos encontrados {sync_report.get('found_count', 0)}, compatibles {sync_report.get('compatible_count', 0)}.",
                )
            else:
                QMessageBox.information(self, "AI Runtime", f"{PROVIDER_LINKS[provider_name]['label']}: {diagnostic.message}")
            return
        QMessageBox.warning(self, "AI Runtime", f"{PROVIDER_LINKS[provider_name]['label']}: {diagnostic.message}")

    def refresh(self) -> None:
        status = self.workspace.ai_runtime_provider_status()
        for provider_name, card in self.cards.items():
            card.refresh(status.get(provider_name, {}))


class RolesTab(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._current_creator_id: str | None = None
        title = QLabel("Modelos y roles")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Asignaciones de rol basadas en ModelRegistry, sin modelos fijos en la vista.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Configuracion recomendada", "recommended")
        self.mode_combo.addItem("Configuracion avanzada", "advanced")
        self.mode_help_label = QLabel()
        self.mode_help_label.setWordWrap(True)
        self.mode_help_label.setObjectName("MutedLabel")
        self.back_to_recommended_button = QPushButton("Volver a configuracion recomendada")
        self.back_to_recommended_button.clicked.connect(lambda *_: self._set_mode("recommended"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Económico", "economico")
        self.profile_combo.addItem("Equilibrado", "equilibrado")
        self.profile_combo.addItem("Máxima calidad", "maxima_calidad")
        self.profile_combo.addItem("Personalizado", "personalizado")
        self.profile_combo.setCurrentIndex(self.profile_combo.findData("equilibrado"))
        self.profile_hint_label = QLabel()
        self.profile_hint_label.setWordWrap(True)
        self.profile_hint_label.setObjectName("MutedLabel")
        self.guided_summary_label = QLabel()
        self.guided_summary_label.setWordWrap(True)
        self.guided_summary_label.setObjectName("MutedLabel")
        self.guided_warning_label = QLabel()
        self.guided_warning_label.setWordWrap(True)
        self.guided_warning_label.setObjectName("WarningLabel")
        self.guided_roles_table = QTableWidget(0, 6)
        self.guided_roles_table.setObjectName("ai_runtime_guided_roles_table")
        self.guided_roles_table.setHorizontalHeaderLabels(
            [
                "Rol",
                "Propuesta",
                "Confianza",
                "Ahora",
                "Razón",
                "Alternativas",
            ]
        )
        self.apply_recommended_button = QPushButton("Aplicar configuracion recomendada")
        self.open_advanced_button = QPushButton("Configuracion avanzada")
        self.apply_recommended_button.clicked.connect(self._apply_guided_configuration)
        self.open_advanced_button.clicked.connect(lambda *_: self._set_mode("advanced"))
        self.profile_combo.currentIndexChanged.connect(lambda *_: self._refresh_guided_summary())
        self.mode_combo.currentIndexChanged.connect(lambda *_: self._on_mode_changed())

        self.table = QTableWidget(0, 10)
        self.table.setObjectName("ai_runtime_roles_table")
        self.table.setHorizontalHeaderLabels(
            [
                "Rol",
                "Etiqueta",
                "Proveedor",
                "Modelo",
                "Estado",
                "Capacidades",
                "Version",
                "Precio",
                "Habilitado",
                "Fallback",
            ]
        )
        self.table.itemSelectionChanged.connect(self._sync_form_from_selection)

        self.role_combo = QComboBox()
        self.provider_combo = QComboBox()
        self.model_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nombre o model_id")
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem("Recomendados", "recommended")
        self.view_mode_combo.addItem("Compatibles", "compatible")
        self.view_mode_combo.addItem("Todos", "all")
        self.show_all_checkbox = QCheckBox("Mostrar todos los modelos")
        self.show_snapshots_checkbox = QCheckBox("Mostrar snapshots y previews")
        self.show_non_recommended_checkbox = QCheckBox("Mostrar modelos no recomendados")
        self.fallback_combo = QComboBox()
        self.enabled_checkbox = QCheckBox("Habilitado")
        self.default_checkbox = QCheckBox("Predeterminado")
        self.save_button = QPushButton("Guardar asignacion")
        self.refresh_catalog_button = QPushButton("Actualizar catalogo")
        self.counts_label = QLabel()
        self.counts_label.setWordWrap(True)
        self.model_detail = QTextEdit()
        self.model_detail.setReadOnly(True)
        self.model_detail.setObjectName("ai_runtime_model_detail")
        self._model_selection_summary: dict[str, object] = {}
        self.save_button.clicked.connect(self._save_assignment)
        self.refresh_catalog_button.clicked.connect(self._refresh_catalog)
        self.current_assignment_label = QLabel("Asignacion actual: sin seleccionar")
        self.current_assignment_label.setWordWrap(True)
        self.current_assignment_label.setObjectName("MutedLabel")
        self.model_hint_label = QLabel()
        self.model_hint_label.setWordWrap(True)
        self.model_hint_label.setObjectName("MutedLabel")

        self.mode_panel = QFrame()
        self.mode_panel.setObjectName("MutedPanel")
        mode_layout = QVBoxLayout(self.mode_panel)
        mode_header = QHBoxLayout()
        mode_header.addWidget(QLabel("Modo"))
        mode_header.addWidget(self.mode_combo)
        mode_header.addStretch(1)
        mode_layout.addLayout(mode_header)
        mode_layout.addWidget(self.mode_help_label)

        guided_header = QHBoxLayout()
        guided_header.addWidget(QLabel("Perfil"))
        guided_header.addWidget(self.profile_combo)
        guided_header.addStretch(1)

        self.guided_panel = QFrame()
        self.guided_panel.setObjectName("MutedPanel")
        guided_layout = QVBoxLayout(self.guided_panel)
        guided_layout.addLayout(guided_header)
        guided_layout.addWidget(self.profile_hint_label)
        guided_layout.addWidget(self.guided_summary_label)
        guided_layout.addWidget(self.guided_warning_label)
        guided_layout.addWidget(self.guided_roles_table)
        guided_actions = QHBoxLayout()
        guided_actions.addWidget(self.apply_recommended_button)
        guided_actions.addWidget(self.open_advanced_button)
        guided_actions.addStretch(1)
        guided_layout.addLayout(guided_actions)

        self.provider_combo.addItem("OpenAI", "openai")
        self.provider_combo.addItem("Anthropic", "anthropic")
        self.fallback_combo.addItem("Sin fallback", "none")
        self.fallback_combo.addItem("Fallback al proveedor", "provider")
        self.fallback_combo.addItem("Fallback entre proveedores", "cross_provider")

        form = QFormLayout()
        form.addRow("Rol", self.role_combo)
        form.addRow("Proveedor", self.provider_combo)
        form.addRow("Buscar", self.search_edit)
        form.addRow("Vista", self.view_mode_combo)
        form.addRow("", self.show_all_checkbox)
        form.addRow("", self.show_snapshots_checkbox)
        form.addRow("", self.show_non_recommended_checkbox)
        form.addRow("", self.counts_label)
        form.addRow("Modelo", self.model_combo)
        form.addRow("Detalle", self.model_detail)
        form.addRow("", self.refresh_catalog_button)
        form.addRow("", self.model_hint_label)
        form.addRow("Fallback", self.fallback_combo)
        form.addRow("", self.enabled_checkbox)
        form.addRow("", self.default_checkbox)
        form.addRow("", self.save_button)

        self.editor_frame = QFrame()
        self.editor_frame.setObjectName("MutedPanel")
        editor_layout = QVBoxLayout(self.editor_frame)
        editor_layout.addWidget(self.back_to_recommended_button)
        editor_layout.addWidget(self.current_assignment_label)
        editor_layout.addLayout(form)

        outer = QVBoxLayout(self)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addWidget(self.mode_panel)
        outer.addWidget(self.guided_panel)
        outer.addWidget(self.table)
        outer.addWidget(self.editor_frame)

        self._seed_role_combo()
        self._startup_refresh_pending = True
        self.role_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_combo())
        self.provider_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_combo())
        self.model_combo.currentIndexChanged.connect(lambda *_: self._on_model_combo_changed())
        self.search_edit.textChanged.connect(lambda *_: self._refresh_model_combo())
        self.view_mode_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_combo())
        self.show_all_checkbox.toggled.connect(lambda *_: self._refresh_model_combo())
        self.show_snapshots_checkbox.toggled.connect(lambda *_: self._refresh_model_combo())
        self.show_non_recommended_checkbox.toggled.connect(lambda *_: self._refresh_model_combo())
        self._sync_mode_controls(self._selected_mode())
        self._apply_mode_visibility()
        self.model_hint_label.setText("La carga de modelos se completara despues de abrir la ventana.")
        self.counts_label.setText("Catalogo pendiente")
        self.model_detail.setPlainText("El catalogo se cargara despues de abrir la ventana.")
        self.current_assignment_label.setText("Asignacion actual: pendiente de carga")
        self._startup_refresh_pending = False
        self._apply_mode_visibility()

    def _seed_role_combo(self) -> None:
        self.role_combo.blockSignals(True)
        self.role_combo.clear()
        for role, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, role)
        self.role_combo.setCurrentIndex(0 if self.role_combo.count() else -1)
        self.role_combo.blockSignals(False)

    def _selected_role(self) -> str:
        return str(self.role_combo.currentData() or "cheap_structured_model")

    def _selected_provider(self) -> str:
        return str(self.provider_combo.currentData() or "openai")

    def _selected_model(self) -> dict[str, object] | None:
        data = self.model_combo.currentData()
        if isinstance(data, dict):
            return data
        return None

    def _selected_model_id(self) -> str | None:
        model = self._selected_model()
        if model is None:
            return None
        model_id = str(model.get("model_id") or "").strip()
        return model_id or None

    def _selected_creator_scope(self) -> str | None:
        return self.workspace.selected_creator_id

    def _selected_profile(self) -> str:
        return str(self.profile_combo.currentData() or "equilibrado")

    def _selected_mode(self) -> str:
        if hasattr(self.workspace, "ai_runtime_roles_mode") and callable(getattr(self.workspace, "ai_runtime_roles_mode")):
            try:
                return str(self.workspace.ai_runtime_roles_mode() or "recommended")
            except Exception:
                pass
        return str(self.mode_combo.currentData() or "recommended")

    def _set_mode(self, mode: str) -> None:
        normalized = "advanced" if str(mode).strip().lower() == "advanced" else "recommended"
        if hasattr(self.workspace, "set_ai_runtime_roles_mode") and callable(getattr(self.workspace, "set_ai_runtime_roles_mode")):
            try:
                self.workspace.set_ai_runtime_roles_mode(normalized)
            except Exception:
                pass
        self._sync_mode_controls(normalized)
        self._apply_mode_visibility()

    def _sync_mode_controls(self, mode: str | None = None) -> None:
        normalized = "advanced" if str(mode or self._selected_mode()).strip().lower() == "advanced" else "recommended"
        index = self.mode_combo.findData(normalized)
        self.mode_combo.blockSignals(True)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        self.mode_combo.blockSignals(False)
        self.back_to_recommended_button.setVisible(normalized == "advanced")
        if normalized == "advanced":
            self.mode_help_label.setText("Permite seleccionar modelos manualmente. Puede aumentar el costo o causar incompatibilidades.")
        else:
            self.mode_help_label.setText("Creator Intelligence Studio elige una configuracion segura y equilibrada.")

    def _on_mode_changed(self) -> None:
        self._set_mode(str(self.mode_combo.currentData() or "recommended"))

    def _apply_mode_visibility(self) -> None:
        recommended_mode = self._selected_mode() != "advanced"
        self._sync_mode_controls("advanced" if not recommended_mode else "recommended")
        self.guided_panel.setVisible(recommended_mode)
        self.table.setVisible(not recommended_mode)
        self.editor_frame.setVisible(not recommended_mode)
        if not recommended_mode and self._selection_mode() == "recommended":
            compatible_index = self.view_mode_combo.findData("compatible")
            if compatible_index >= 0:
                self.view_mode_combo.blockSignals(True)
                self.view_mode_combo.setCurrentIndex(compatible_index)
                self.view_mode_combo.blockSignals(False)
        if self._startup_refresh_pending:
            return
        if recommended_mode:
            self._refresh_guided_summary()
        else:
            self._refresh_model_combo()

    def _selection_mode(self) -> str:
        return str(self.view_mode_combo.currentData() or "compatible")

    def _refresh_guided_summary(self) -> None:
        provider = self._selected_provider()
        profile_key = self._selected_profile()
        try:
            summary = self.workspace.ai_runtime_guided_configuration_summary(provider, profile_key=profile_key)
        except Exception as exc:
            logger.warning("ai_runtime.guided_summary_refresh_failed provider=%s profile=%s error=%s", provider, profile_key, exc)
            self.profile_hint_label.setText("No se pudo cargar el resumen guiado en este arranque.")
            self.guided_summary_label.setText("Resumen guiado no disponible")
            self.guided_warning_label.setText("La GUI seguira disponible aunque el catalogo no responda.")
            self.guided_roles_table.setRowCount(0)
            return
        profile_label = str(summary.get("profile_label") or profile_key)
        self.profile_hint_label.setText(str(summary.get("profile_description") or ""))
        self.guided_summary_label.setText(
            " · ".join(
                [
                    f"Proveedor: {PROVIDER_LINKS.get(provider, {}).get('label', provider)}",
                    f"Ultima sincronizacion: {_safe_datetime(summary.get('synchronized_at'))}",
                    f"Modelos encontrados: {summary.get('found_count', 0)}",
                    f"Compatibilidad: {summary.get('compatibility_state', 'unknown')}",
                    f"Perfil: {profile_label}",
                    f"Costo relativo: {summary.get('relative_cost_label', '-')}",
                ]
            )
        )
        warnings = summary.get("warnings") or []
        first_setup = summary.get("first_setup_message")
        current_warning = summary.get("current_assignment_warning")
        warning_lines = []
        if current_warning:
            warning_lines.append(str(current_warning))
        if first_setup:
            warning_lines.append(str(first_setup))
        if warnings:
            warning_lines.extend(str(item) for item in warnings)
        self.guided_warning_label.setText("\n".join(warning_lines) if warning_lines else "Configuracion recomendada lista para aplicar.")
        roles = summary.get("roles") or []
        self.guided_roles_table.setRowCount(0)
        for row_index, role in enumerate(roles):
            if not isinstance(role, dict):
                continue
            self.guided_roles_table.insertRow(row_index)
            proposed = role.get("proposed_model") or {}
            proposed_label = "-"
            if isinstance(proposed, dict) and proposed:
                proposed_label = f"{proposed.get('display_name') or proposed.get('model_id')} ({proposed.get('model_id')})"
            alternatives = role.get("alternatives") or []
            alternative_text = ", ".join(
                f"{item.get('display_name') or item.get('model_id')} ({item.get('model_id')})"
                for item in alternatives
                if isinstance(item, dict)
            ) or "-"
            values = [
                role.get("role_label") or role.get("role"),
                proposed_label,
                role.get("confidence"),
                "Si" if role.get("required_now") else "No requerido en la fase actual",
                role.get("reason"),
                alternative_text,
            ]
            for column, value in enumerate(values):
                self.guided_roles_table.setItem(row_index, column, _item(value))
        self.guided_roles_table.resizeColumnsToContents()

    def _apply_guided_configuration(self) -> None:
        provider = self._selected_provider()
        profile_key = self._selected_profile()
        summary = self.workspace.ai_runtime_guided_configuration_summary(provider, profile_key=profile_key)
        details: list[str] = []
        for role in summary.get("roles", []):
            if not isinstance(role, dict):
                continue
            proposal = role.get("proposed_model")
            if isinstance(proposal, dict) and proposal:
                details.append(
                    f"{role.get('role_label')}: {proposal.get('display_name') or proposal.get('model_id')} ({proposal.get('model_id')})"
                )
            else:
                details.append(f"{role.get('role_label')}: sin propuesta")
        summary_text = "\n".join(details) or "No hay propuestas disponibles."
        choice = QMessageBox.question(
            self,
            "AI Runtime",
            f"Resumen de configuracion recomendada ({summary.get('profile_label') or profile_key}):\n\n{summary_text}\n\n¿Aplicar esta configuracion?",
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        result = self.workspace.ai_runtime_apply_recommended_configuration(provider, profile_key=profile_key, replace_existing=True)
        self.refresh()
        _refresh_enclosing_overview(self)
        QMessageBox.information(
            self,
            "AI Runtime",
            f"Configuracion recomendada aplicada. Asignaciones creadas: {result.get('applied_count', 0)}.",
        )

    def _refresh_model_combo(self) -> None:
        provider = self._selected_provider()
        role = self._selected_role()
        try:
            current_assignment = self.workspace.ai_runtime_service.repository.resolve_role_assignment(
                role,
                creator_id=self._selected_creator_scope(),
                provider=provider,
            )
            current_model_id = None
            if current_assignment is not None:
                current_model = self.workspace.ai_runtime_service.repository.get_model_catalog_entry(current_assignment.model_catalog_id)
                if current_model is not None:
                    current_model_id = current_model.model_id
            summary = self.workspace.ai_runtime_list_model_selection(
                provider,
                role,
                query=self.search_edit.text().strip() or None,
                mode=self._selection_mode(),
                show_non_recommended=self.show_non_recommended_checkbox.isChecked(),
                show_all_models=self.show_all_checkbox.isChecked(),
                show_snapshots_and_previews=self.show_snapshots_checkbox.isChecked(),
                selected_model_id=current_model_id,
            )
        except Exception as exc:
            logger.warning("ai_runtime.model_selection_refresh_failed provider=%s role=%s error=%s", provider, role, exc)
            self._model_selection_summary = {}
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.setCurrentIndex(-1)
            self.model_combo.blockSignals(False)
            self.model_hint_label.setText("No se pudieron cargar los modelos en este arranque. La GUI seguira disponible.")
            self.counts_label.setText("Catalogo no disponible")
            self.save_button.setEnabled(False)
            self.model_combo.setEnabled(False)
            self.model_detail.setPlainText("No se pudo cargar el catalogo seguro en este arranque.")
            self.current_assignment_label.setText("Asignacion actual: catalogo no disponible")
            return
        self._model_selection_summary = summary
        models = [item for item in summary.get("items", []) if item.get("is_visible")]

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        selected_index = -1
        for model in models:
            label = (
                f"{model['display_name']} ({model['model_id']}) · "
                f"{model.get('status', '-')} · {model.get('snapshot_or_version') or 'sin snapshot'}"
            )
            index = self.model_combo.count()
            self.model_combo.addItem(label, model)
            if current_model_id is not None and str(model.get("model_id")) == current_model_id:
                selected_index = index
        if selected_index >= 0:
            self.model_combo.setCurrentIndex(selected_index)
        else:
            self.model_combo.setCurrentIndex(-1)
        self.model_combo.blockSignals(False)
        if not models:
            self.model_hint_label.setText(
                f"No hay modelos sincronizados para {PROVIDER_LINKS[provider]['label']}. Configura y valida la credencial, luego pulsa Actualizar catalogo."
            )
        else:
            self.model_hint_label.setText(
                f"{len(models)} modelos visibles para {PROVIDER_LINKS[provider]['label']} y el rol {ROLE_LABELS.get(role, role)}."
            )
        self.counts_label.setText(
            " · ".join(
                [
                    f"Recomendados: {summary.get('recommended_count', 0)}",
                    f"Compatibles: {summary.get('compatible_count', 0)}",
                    f"Desconocidos: {summary.get('unknown_count', 0)}",
                    f"Avanzados: {summary.get('advanced_count', 0)}",
                    f"Catalogo: {summary.get('catalog_count', 0)}",
                    f"Mostrados: {summary.get('visible_count', 0)}",
                ]
            )
        )
        self.save_button.setEnabled(self._selected_model() is not None)
        self.model_combo.setEnabled(bool(models))
        self._update_model_detail(summary)
        self._update_assignment_preview()

    def _update_model_detail(self, summary: dict[str, object]) -> None:
        model = self._selected_model()
        if model is None:
            self.model_detail.setPlainText(
                f"Selecciona un modelo para ver el detalle seguro.\n"
                f"El selector muestra {summary.get('visible_count', 0)} de {summary.get('catalog_count', 0)} modelos."
            )
            return
        detail = str(model.get("detail_text") or "")
        warning = model.get("warning")
        if warning:
            detail = f"{detail}\nAdvertencia: {warning}" if detail else f"Advertencia: {warning}"
        self.model_detail.setPlainText(detail.strip())

    def _on_model_combo_changed(self) -> None:
        self.save_button.setEnabled(self._selected_model() is not None)
        self._update_model_detail(self._model_selection_summary)

    def _resolve_current_assignment(self, role: str) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        service = self.workspace.ai_runtime_service
        try:
            assignment = service.repository.resolve_role_assignment(
                role,
                creator_id=self._selected_creator_scope(),
                provider=self._selected_provider(),
            )
        except Exception as exc:
            logger.warning("ai_runtime.assignment_resolution_failed role=%s error=%s", role, exc)
            return None, None
        if assignment is None:
            return None, None
        try:
            model = service.repository.get_model_catalog_entry(assignment.model_catalog_id)
        except Exception as exc:
            logger.warning(
                "ai_runtime.assignment_model_lookup_failed role=%s catalog_id=%s error=%s",
                role,
                assignment.model_catalog_id,
                exc,
            )
            return assignment.to_dict(), None
        return assignment.to_dict(), model.to_dict() if model is not None else None

    def _update_assignment_preview(self) -> None:
        role = self._selected_role()
        try:
            assignment, model = self._resolve_current_assignment(role)
        except Exception as exc:
            logger.warning("ai_runtime.assignment_preview_refresh_failed role=%s error=%s", role, exc)
            self.current_assignment_label.setText("Asignacion actual: no disponible")
            return
        if assignment is None or model is None:
            self.current_assignment_label.setText("Asignacion actual: sin asignar")
            return
        warning = ""
        if str(model.get("status") or "").lower() in {"deprecated", "unavailable", "blocked"}:
            warning = " (no recomendada)"
        self.current_assignment_label.setText(
            "Asignacion actual: "
            f"{assignment['provider']} / {model['display_name']} / {model.get('snapshot_or_version') or 'sin snapshot'}{warning}"
        )

    def _sync_form_from_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return
        role_item = self.table.item(rows[0].row(), 0)
        provider_item = self.table.item(rows[0].row(), 2)
        model_item = self.table.item(rows[0].row(), 3)
        if role_item is None:
            return
        role = role_item.data(Qt.ItemDataRole.UserRole) or role_item.text()
        index = self.role_combo.findData(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        provider = provider_item.text() if provider_item else "OpenAI"
        provider_index = self.provider_combo.findData(provider.lower())
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        self._refresh_model_combo()
        if model_item is not None and model_item.text():
            for i in range(self.model_combo.count()):
                data = self.model_combo.itemData(i)
                if isinstance(data, dict) and data.get("display_name") == model_item.text():
                    self.model_combo.setCurrentIndex(i)
                    break
        self._update_assignment_preview()

    def _save_assignment(self) -> None:
        model = self._selected_model()
        if model is None:
            QMessageBox.warning(self, "AI Runtime", "Selecciona un modelo valido antes de guardar.")
            return
        role = self._selected_role()
        provider = self._selected_provider()
        try:
            assignment = self.workspace.ai_runtime_assign_role(
                role=role,
                provider=provider,
                model_id=str(model["model_id"]),
                creator_id=self._selected_creator_scope(),
                display_name=str(model.get("display_name") or model["model_id"]),
                is_default=self.default_checkbox.isChecked(),
                is_enabled=self.enabled_checkbox.isChecked(),
                fallback_policy=str(self.fallback_combo.currentData() or "none"),
                quality_level="standard",
                status=str(model.get("status") or "testing"),
                capabilities_json=dict(model.get("capabilities_json") or {}),
                snapshot_or_version=model.get("snapshot_or_version"),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "AI Runtime", str(exc))
            return
        self.refresh()
        _refresh_enclosing_overview(self)
        QMessageBox.information(
            self,
            "AI Runtime",
            f"Asignacion guardada: {assignment['role']} -> {assignment['provider']} / {assignment['model_catalog_id']}",
        )

    def _refresh_catalog(self) -> None:
        provider = self._selected_provider()
        report = self.workspace.ai_runtime_refresh_provider_models(provider)
        self.refresh()
        if report.get("status") == "ok":
            QMessageBox.information(
                self,
                "AI Runtime",
                f"Catalogo sincronizado: encontrados {report.get('found_count', 0)}, compatibles {report.get('compatible_count', 0)}, nuevos {report.get('new_count', 0)}, actualizados {report.get('updated_count', 0)}.",
            )
        else:
            QMessageBox.warning(self, "AI Runtime", str(report.get("message") or "No se pudo sincronizar el catalogo."))

    def refresh(self) -> None:
        creator_id = self._selected_creator_scope()
        selected_role = self._selected_role() if self.role_combo.count() else None
        selected_provider = self._selected_provider() if self.provider_combo.count() else None
        self._seed_role_combo()
        if selected_role is not None:
            role_index = self.role_combo.findData(selected_role)
            if role_index >= 0:
                self.role_combo.blockSignals(True)
                self.role_combo.setCurrentIndex(role_index)
                self.role_combo.blockSignals(False)
        if selected_provider is not None:
            provider_index = self.provider_combo.findData(selected_provider)
            if provider_index >= 0:
                self.provider_combo.blockSignals(True)
                self.provider_combo.setCurrentIndex(provider_index)
                self.provider_combo.blockSignals(False)
        if self.role_combo.count() == 0:
            return
        self._current_creator_id = creator_id
        self.table.setRowCount(0)
        rows = []
        for role, label in ROLE_LABELS.items():
            assignment, model = self._resolve_current_assignment(role)
            rows.append((role, label, assignment, model))
        for row_index, (role, label, assignment, model) in enumerate(rows):
            self.table.insertRow(row_index)
            provider = assignment["provider"] if assignment else "-"
            model_name = model["display_name"] if model else "-"
            status = model["status"] if model else "-"
            capabilities = ", ".join(sorted((model or {}).get("capabilities_json", {}).keys())) if model else "-"
            version = model.get("snapshot_or_version") if model else "-"
            price = _model_price_text(model) if model else "-"
            enabled = "Si" if assignment and assignment.get("is_enabled") else "No"
            fallback = assignment.get("fallback_policy") if assignment else "-"
            values = [role, label, provider, model_name, status, capabilities, version, price, enabled, fallback]
            for column, value in enumerate(values):
                item = _item(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, role)
                self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()
        self._apply_mode_visibility()
        self._refresh_guided_summary()
        self._refresh_model_combo()


class BudgetTab(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        title = QLabel("Presupuesto y consumo")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Lmites editables, gasto calculado, llamadas, errores de facturacion y warnings de pricing.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.currency_edit = QComboBox()
        self.currency_edit.setEditable(True)
        self.currency_edit.addItems(["USD", "MXN", "EUR"])
        self.monthly_limit_edit = QLineEdit()
        self.per_task_limit_edit = QLineEdit()
        self.hard_block_checkbox = QCheckBox("Hard block")
        self.approval_threshold_edit = QDoubleSpinBox()
        self.approval_threshold_edit.setRange(0.0, 100.0)
        self.approval_threshold_edit.setSuffix(" %")
        self.approval_threshold_edit.setDecimals(2)
        self.approval_threshold_edit.setSingleStep(5.0)
        self.fallback_checkbox = QCheckBox("Fallback entre proveedores habilitado")
        self.save_button = QPushButton("Guardar presupuesto")
        self.save_button.clicked.connect(self._save_budget)

        self.monthly_cost_label = QLabel()
        self.provider_costs_label = QLabel()
        self.calls_label = QLabel()
        self.billing_errors_label = QLabel()
        self.warnings_label = QLabel()
        for label in (
            self.monthly_cost_label,
            self.provider_costs_label,
            self.calls_label,
            self.billing_errors_label,
            self.warnings_label,
        ):
            label.setWordWrap(True)

        self.cost_table = QTableWidget(0, 2)
        self.cost_table.setHorizontalHeaderLabels(["Proveedor", "Consumo mensual"])
        self.cost_table.setObjectName("ai_runtime_budget_table")

        form = QFormLayout()
        form.addRow("Moneda", self.currency_edit)
        form.addRow("Limite mensual", self.monthly_limit_edit)
        form.addRow("Limite por tarea", self.per_task_limit_edit)
        form.addRow("Umbral de aprobacion", self.approval_threshold_edit)
        form.addRow("", self.hard_block_checkbox)
        form.addRow("", self.fallback_checkbox)
        form.addRow("", self.save_button)

        summary = QVBoxLayout()
        summary.addWidget(self.monthly_cost_label)
        summary.addWidget(self.provider_costs_label)
        summary.addWidget(self.calls_label)
        summary.addWidget(self.billing_errors_label)
        summary.addWidget(self.warnings_label)
        summary.addWidget(self.cost_table)

        outer = QVBoxLayout(self)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(form)
        outer.addLayout(summary)
        outer.addStretch(1)
        self.refresh()

    def _parse_float(self, text: str) -> float | None:
        text = text.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _save_budget(self) -> None:
        currency = self.currency_edit.currentText().strip() or "USD"
        monthly_limit = self._parse_float(self.monthly_limit_edit.text())
        per_task_limit = self._parse_float(self.per_task_limit_edit.text())
        approval_threshold = self.approval_threshold_edit.value() / 100.0
        self.workspace.ai_runtime_update_budget_policy(
            creator_id=self.workspace.selected_creator_id,
            monthly_limit=monthly_limit,
            per_task_limit=per_task_limit,
            hard_block_enabled=self.hard_block_checkbox.isChecked(),
            currency=currency,
            approval_threshold=approval_threshold,
        )
        self.workspace.ai_runtime_set_runtime_setting(
            "cross_provider_fallback_enabled",
            {"enabled": self.fallback_checkbox.isChecked()},
        )
        self.workspace.ai_runtime_set_runtime_setting(
            "cost_approval_threshold",
            {"value": approval_threshold},
        )
        self.refresh()
        _refresh_enclosing_overview(self)
        QMessageBox.information(self, "AI Runtime", "Presupuesto guardado.")

    def refresh(self) -> None:
        snapshot = self.workspace.ai_runtime_budget_snapshot(self.workspace.selected_creator_id)
        policy = snapshot.get("policy") or {}
        self.currency_edit.setCurrentText(str(policy.get("currency") or "USD"))
        self.monthly_limit_edit.setText("" if policy.get("monthly_limit") is None else str(policy.get("monthly_limit")))
        self.per_task_limit_edit.setText("" if policy.get("per_task_limit") is None else str(policy.get("per_task_limit")))
        self.hard_block_checkbox.setChecked(bool(policy.get("hard_block_enabled", True)))
        approval = snapshot.get("approval_threshold")
        if approval is None:
            approval = policy.get("warning_threshold_90", 0.90)
        try:
            self.approval_threshold_edit.setValue(float(approval) * 100.0)
        except (TypeError, ValueError):
            self.approval_threshold_edit.setValue(90.0)
        self.fallback_checkbox.setChecked(bool(snapshot.get("cross_provider_fallback_enabled", True)))
        self.monthly_cost_label.setText(f"Consumo mensual calculado: {snapshot.get('monthly_cost', 0.0)} {policy.get('currency') or 'USD'}")
        provider_costs = snapshot.get("provider_costs") or {}
        if isinstance(provider_costs, dict) and provider_costs:
            provider_lines = ", ".join(f"{name}: {value}" for name, value in sorted(provider_costs.items()))
        else:
            provider_lines = "Sin consumo por proveedor"
        self.provider_costs_label.setText(f"Consumo por proveedor: {provider_lines}")
        self.calls_label.setText(f"Llamadas registradas: {snapshot.get('calls', 0)}")
        self.billing_errors_label.setText(f"Errores de facturacion: {snapshot.get('billing_errors', 0)}")
        warnings = snapshot.get("warnings") or ()
        if warnings:
            self.warnings_label.setText("Advertencias: " + " | ".join(str(item) for item in warnings))
        else:
            self.warnings_label.setText("Advertencias: ninguna")
        self.cost_table.setRowCount(0)
        for row_index, (provider_name, value) in enumerate(sorted(provider_costs.items())):
            self.cost_table.insertRow(row_index)
            self.cost_table.setItem(row_index, 0, _item(provider_name))
            self.cost_table.setItem(row_index, 1, _item(value))
        self.cost_table.resizeColumnsToContents()


class DiagnosticsTab(QWidget):
    def __init__(
        self,
        workspace: WorkspaceViewModel,
        parent: QWidget | None = None,
        *,
        on_review_budget: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self._on_review_budget = on_review_budget
        self._diagnostic_thread: DiagnosticRunThread | None = None
        self._approval_thread: DiagnosticRunThread | None = None
        self._diagnostic_running = False
        self._approval_running = False
        self._live_refresh_timer = QTimer(self)
        self._live_refresh_timer.setInterval(200)
        self._live_refresh_timer.timeout.connect(self._poll_live_execution_state)
        self._current_execution_id: str | None = None
        self._current_execution_status: str | None = None
        title = QLabel("Diagnostico")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Ejecuta un diagnostico real del AI runtime con salida normalizada y segura.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.provider_combo = QComboBox()
        self.role_combo = QComboBox()
        self.model_line = QLineEdit()
        self.model_line.setReadOnly(True)
        self.cache_combo = QComboBox()
        self.cache_combo.addItem("Use", "use")
        self.cache_combo.addItem("Bypass", "bypass")
        self.cache_combo.addItem("Refresh", "refresh")
        self.run_button = QPushButton("Ejecutar diagnostico")
        self.auto_config_button = QPushButton("Configurar automaticamente")
        self.cancel_active_button = QPushButton("Cancelar ejecucion activa")
        self.run_button.clicked.connect(self._run_diagnostic)
        self.auto_config_button.clicked.connect(self._configure_automatically)
        self.cancel_active_button.clicked.connect(self._cancel_active_execution)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("MutedLabel")

        self.execution_label = QLabel()
        self.provider_label = QLabel()
        self.model_label = QLabel()
        self.role_label = QLabel()
        self.status_label = QLabel()
        self.latency_label = QLabel()
        self.input_tokens_label = QLabel()
        self.output_tokens_label = QLabel()
        self.estimated_cost_label = QLabel()
        self.calculated_cost_label = QLabel()
        self.cache_label = QLabel()
        self.validation_label = QLabel()
        self.error_label = QLabel()
        self.suggested_action_label = QLabel()
        for label in (
            self.execution_label,
            self.provider_label,
            self.model_label,
            self.role_label,
            self.status_label,
            self.latency_label,
            self.input_tokens_label,
            self.output_tokens_label,
            self.estimated_cost_label,
            self.calculated_cost_label,
            self.cache_label,
            self.validation_label,
            self.error_label,
            self.suggested_action_label,
        ):
            label.setWordWrap(True)

        self.provider_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_line())
        self.role_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_line())

        self.approval_group = QFrame()
        self.approval_group.setObjectName("ai_runtime_approval_group")
        approval_layout = QVBoxLayout(self.approval_group)
        self.approval_title = QLabel("Esta ejecucion necesita tu aprobacion.")
        self.approval_title.setObjectName("SectionLabel")
        self.approval_message = QLabel("Esperando tu aprobacion.")
        self.approval_message.setWordWrap(True)
        self.approval_message.setObjectName("MutedLabel")
        self.approval_provider_label = QLabel("-")
        self.approval_model_label = QLabel("-")
        self.approval_role_label = QLabel("-")
        self.approval_reason_label = QLabel("-")
        self.approval_cost_label = QLabel("-")
        self.approval_currency_label = QLabel("-")
        self.approval_policy_label = QLabel("-")
        self.approval_scope_label = QLabel("-")
        self.approval_warning_label = QLabel("-")
        for label in (
            self.approval_provider_label,
            self.approval_model_label,
            self.approval_role_label,
            self.approval_reason_label,
            self.approval_cost_label,
            self.approval_currency_label,
            self.approval_policy_label,
            self.approval_scope_label,
            self.approval_warning_label,
        ):
            label.setWordWrap(True)
        self.approve_button = QPushButton("Aprobar y continuar")
        self.reject_button = QPushButton("Rechazar")
        self.review_budget_button = QPushButton("Revisar presupuesto")
        self.approve_button.clicked.connect(self._approve_and_continue)
        self.reject_button.clicked.connect(self._reject_execution)
        self.review_budget_button.clicked.connect(self._review_budget)
        approval_form = QFormLayout()
        approval_form.addRow("Proveedor", self.approval_provider_label)
        approval_form.addRow("Modelo", self.approval_model_label)
        approval_form.addRow("Rol", self.approval_role_label)
        approval_form.addRow("Motivo", self.approval_reason_label)
        approval_form.addRow("Costo estimado", self.approval_cost_label)
        approval_form.addRow("Moneda", self.approval_currency_label)
        approval_form.addRow("Politica", self.approval_policy_label)
        approval_form.addRow("Alcance", self.approval_scope_label)
        approval_form.addRow("Advertencia", self.approval_warning_label)
        approval_actions = QHBoxLayout()
        approval_actions.addWidget(self.approve_button)
        approval_actions.addWidget(self.reject_button)
        approval_actions.addWidget(self.review_budget_button)
        approval_actions.addStretch(1)
        approval_layout.addWidget(self.approval_title)
        approval_layout.addWidget(self.approval_message)
        approval_layout.addLayout(approval_form)
        approval_layout.addLayout(approval_actions)
        self.approval_group.hide()

        form = QFormLayout()
        form.addRow("Proveedor", self.provider_combo)
        form.addRow("Rol", self.role_combo)
        form.addRow("Modelo resuelto", self.model_line)
        form.addRow("Cache policy", self.cache_combo)
        form.addRow("", self.run_button)
        form.addRow("", self.auto_config_button)
        form.addRow("", self.cancel_active_button)

        result = QFormLayout()
        result.addRow("execution_id", self.execution_label)
        result.addRow("Proveedor", self.provider_label)
        result.addRow("Modelo", self.model_label)
        result.addRow("Rol", self.role_label)
        result.addRow("Estado", self.status_label)
        result.addRow("Latencia", self.latency_label)
        result.addRow("Input tokens", self.input_tokens_label)
        result.addRow("Output tokens", self.output_tokens_label)
        result.addRow("Costo estimado", self.estimated_cost_label)
        result.addRow("Costo calculado", self.calculated_cost_label)
        result.addRow("Cache", self.cache_label)
        result.addRow("Validacion", self.validation_label)
        result.addRow("Error seguro", self.error_label)
        result.addRow("Accion sugerida", self.suggested_action_label)

        self.result_group = QFrame()
        result_layout = QVBoxLayout(self.result_group)
        result_layout.addLayout(result)
        result_layout.addWidget(self.message_label)

        outer = QVBoxLayout(self)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addLayout(form)
        outer.addWidget(self.result_group)
        outer.addWidget(self.approval_group)
        outer.addStretch(1)

        self._seed_combos()
        self.refresh()

    def _current_status(self) -> str:
        return str(self._current_execution_status or "").lower()

    def _has_live_background_task(self) -> bool:
        if not self._current_execution_id:
            return False
        provider = self._selected_provider()
        role = self._selected_role()
        task = self.workspace.ai_runtime_active_diagnostic_task(provider, role)
        if task is not None:
            payload = getattr(task, "payload", {})
            if isinstance(payload, dict) and str(payload.get("execution_id") or "") == self._current_execution_id:
                return True
        return self._current_status() in {"queued", "preparing_context", "awaiting_approval", "running", "validating"}

    def _can_cancel_current_execution(self) -> bool:
        status = self._current_status()
        if status in {"completed", "completed_with_warnings", "failed", "cancelled", "interrupted", "rejected_by_user"}:
            return False
        if self._current_execution_id is None:
            return False
        if status == "awaiting_approval":
            return True
        return self._has_live_background_task() and status in {"queued", "preparing_context", "approved", "running", "validating"}

    def _refresh_cancel_button(self) -> None:
        visible = self._can_cancel_current_execution()
        self.cancel_active_button.setVisible(visible)
        self.cancel_active_button.setEnabled(visible and not self._diagnostic_running and not self._approval_running)

    def _refresh_approval_buttons(self) -> None:
        visible = self._current_execution_id is not None and self._current_status() == "awaiting_approval"
        self.approve_button.setVisible(visible)
        self.reject_button.setVisible(visible)
        self.review_budget_button.setVisible(visible)
        self._set_approval_controls_enabled(visible and not self._diagnostic_running and not self._approval_running)

    def _seed_combos(self) -> None:
        self.provider_combo.blockSignals(True)
        self.role_combo.blockSignals(True)
        self.provider_combo.clear()
        for provider_name, meta in PROVIDER_LINKS.items():
            self.provider_combo.addItem(meta["label"], provider_name)
        self.role_combo.clear()
        for role, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, role)
        self.provider_combo.blockSignals(False)
        self.role_combo.blockSignals(False)
        self._refresh_model_line()

    def _selected_provider(self) -> str:
        return str(self.provider_combo.currentData() or "openai")

    def _selected_role(self) -> str:
        return str(self.role_combo.currentData() or "cheap_structured_model")

    def _refresh_model_line(self) -> None:
        provider = self._selected_provider()
        role = self._selected_role()
        resolved = self.workspace.ai_runtime_service.model_registry.resolve_role(
            role,
            creator_id=self.workspace.selected_creator_id,
            provider=provider,
        )
        if resolved is None:
            self.model_line.setText("Falta configurar el modelo economico estructurado.")
            self.auto_config_button.setVisible(True)
            return
        _, model = resolved
        self.model_line.setText(
            f"{model.display_name} / {model.model_id} / {model.snapshot_or_version or 'sin snapshot'}"
        )
        self.auto_config_button.setVisible(False)

    def _configure_automatically(self) -> None:
        provider = self._selected_provider()
        summary = self.workspace.ai_runtime_guided_configuration_summary(provider, profile_key="equilibrado")
        details = []
        for role in summary.get("roles", []):
            if not isinstance(role, dict):
                continue
            proposal = role.get("proposed_model")
            if isinstance(proposal, dict) and proposal:
                details.append(
                    f"{role.get('role_label')}: {proposal.get('display_name') or proposal.get('model_id')} ({proposal.get('model_id')})"
                )
        choice = QMessageBox.question(
            self,
            "AI Runtime",
            "Falta configurar el modelo economico estructurado.\n\n"
            f"Perfil {summary.get('profile_label') or 'Equilibrado'}:\n"
            + ("\n".join(details) if details else "Sin propuesta disponible.")
            + "\n\n¿Aplicar la configuracion recomendada?",
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        self.workspace.ai_runtime_apply_recommended_configuration(provider, profile_key="equilibrado", replace_existing=True)
        self.refresh()
        _refresh_enclosing_overview(self)

    def _set_running_state(self, running: bool, message: str | None = None) -> None:
        self._diagnostic_running = running
        self.run_button.setEnabled(not running)
        self.provider_combo.setEnabled(not running)
        self.role_combo.setEnabled(not running)
        self.cache_combo.setEnabled(not running)
        self.auto_config_button.setEnabled(not running)
        self._refresh_approval_buttons()
        self._refresh_cancel_button()
        if message is not None:
            self.message_label.setText(message)

    def _set_live_controls_locked(self, locked: bool) -> None:
        self.run_button.setEnabled(not locked)
        self.provider_combo.setEnabled(not locked)
        self.role_combo.setEnabled(not locked)
        self.cache_combo.setEnabled(not locked)
        self.auto_config_button.setEnabled(not locked)

    def _start_live_refresh(self) -> None:
        if not self._live_refresh_timer.isActive():
            self._live_refresh_timer.start()

    def _stop_live_refresh(self) -> None:
        self._live_refresh_timer.stop()

    def _poll_live_execution_state(self) -> None:
        live_threads = (
            (self._diagnostic_thread is not None and self._diagnostic_thread.isRunning())
            or (self._approval_thread is not None and self._approval_thread.isRunning())
            or self._approval_running
        )
        live_status = self._current_status() in {"queued", "preparing_context", "awaiting_approval", "approved", "running", "validating"}
        if not live_threads and not live_status:
            self._stop_live_refresh()
            return
        self.refresh()
        _refresh_enclosing_overview(self)

    def _clear_result_fields(self) -> None:
        self._current_execution_id = None
        self._current_execution_status = None
        self.execution_label.setText("-")
        self.provider_label.setText("-")
        self.model_label.setText("-")
        self.role_label.setText("-")
        self.status_label.setText("-")
        self.latency_label.setText("-")
        self.input_tokens_label.setText("-")
        self.output_tokens_label.setText("-")
        self.estimated_cost_label.setText("-")
        self.calculated_cost_label.setText("-")
        self.cache_label.setText("-")
        self.validation_label.setText("-")
        self.error_label.setText("-")
        self.suggested_action_label.setText("-")
        self.approval_group.hide()
        self.approval_message.setText("Esperando tu aprobacion.")
        self.cancel_active_button.setText("Cancelar ejecucion activa")
        self.cancel_active_button.hide()
        for label in (
            self.approval_provider_label,
            self.approval_model_label,
            self.approval_role_label,
            self.approval_reason_label,
            self.approval_cost_label,
            self.approval_currency_label,
            self.approval_policy_label,
            self.approval_scope_label,
            self.approval_warning_label,
        ):
            label.setText("-")

    def _set_approval_controls_enabled(self, enabled: bool) -> None:
        self.approve_button.setEnabled(enabled)
        self.reject_button.setEnabled(enabled)
        self.review_budget_button.setEnabled(enabled)

    def _show_approval_panel(self, result: dict[str, object]) -> None:
        approval = result.get("provenance") or {}
        approval_details = approval.get("approval") if isinstance(approval, dict) else {}
        if not isinstance(approval_details, dict):
            approval_details = {}
        cost = result.get("cost") or {}
        warnings = result.get("warnings") or ()
        estimated_cost = "-"
        approval_reasons: list[str] = []
        if isinstance(approval_details, dict):
            approval_reasons.extend(str(item) for item in approval_details.get("budget_reasons") or ())
            approval_reasons.extend(str(item) for item in approval_details.get("privacy_reasons") or ())
        if isinstance(cost, dict):
            min_cost = cost.get("estimated_min_cost")
            max_cost = cost.get("estimated_max_cost")
            currency = cost.get("currency") or "USD"
            if min_cost is not None or max_cost is not None:
                estimated_cost = f"{min_cost} - {max_cost}"
                self.approval_currency_label.setText(str(currency))
            else:
                self.approval_currency_label.setText(str(currency))
            self.approval_cost_label.setText(estimated_cost)
        provider_key = str(result.get("provider") or approval_details.get("provider") or "-")
        provider = PROVIDER_LINKS.get(provider_key, {}).get("label") or provider_key
        model = str(result.get("model_id") or approval_details.get("model_id") or "-")
        role = str(result.get("model_role") or approval_details.get("role") or "-")
        reason = "La politica de presupuesto requiere revision."
        if approval_reasons:
            reason = " | ".join(approval_reasons)
        elif isinstance(approval_details, dict) and approval_details.get("estimated_cost_unknown"):
            reason = "El precio todavia no esta verificado para este modelo."
        if isinstance(cost, dict) and cost.get("notes"):
            reason = str(cost.get("notes"))
        self.approval_provider_label.setText(provider)
        self.approval_model_label.setText(model)
        self.approval_role_label.setText(role)
        self.approval_reason_label.setText(reason)
        self.approval_policy_label.setText(str(approval_details.get("policy") or "budget_policy"))
        self.approval_scope_label.setText(str(approval_details.get("scope") or "single_execution"))
        if warnings:
            self.approval_warning_label.setText(" | ".join(str(item) for item in warnings))
        elif approval_details and approval_details.get("estimated_cost_unknown"):
            self.approval_warning_label.setText(
                "Creator Intelligence Studio todavía no tiene un precio verificado para este modelo. La llamada puede generar un cargo en tu cuenta de OpenAI."
            )
        else:
            self.approval_warning_label.setText("-")
        self.approval_group.show()
        self.approval_title.setText("Esta ejecucion necesita tu aprobacion.")
        self.approval_message.setText("Revisa el proveedor, el modelo, el costo estimado y la politica antes de continuar.")
        self._set_approval_controls_enabled(True)
        self._refresh_approval_buttons()
        self._refresh_cancel_button()

    def _hide_approval_panel(self) -> None:
        self.approval_group.hide()
        self._refresh_approval_buttons()
        self._refresh_cancel_button()

    def _friendly_diagnostic_message(self, status: str, error: dict[str, object]) -> str:
        category = str(error.get("category") or "").lower()
        technical_reference = str(error.get("technical_reference") or "").lower()
        safe_message = str(error.get("safe_message") or "").lower()
        if status == "blocked_by_credentials" or category == "authentication_error":
            return "No hay una credencial configurada para este proveedor."
        if category == "authorization_error":
            return "La cuenta no tiene permisos para usar este modelo."
        if category in {"billing_error", "quota_error"}:
            return "OpenAI no pudo completar la solicitud por saldo o cuota."
        if category in {"timeout", "network_error"}:
            return "No se pudo contactar al proveedor. Reintenta en unos minutos."
        if category == "invalid_request" and ("unsupported_parameter" in technical_reference or "max_tokens" in safe_message):
            return "No se pudo completar la solicitud porque la configuración de este modelo necesita actualizarse."
        if status in {"failed", "blocked_by_budget", "blocked_by_privacy", "blocked_by_provider", "blocked_by_model"} or error:
            return "No se pudo completar el diagnóstico."
        return "Diagnóstico completado."

    def _execution_result_from_record(self, execution: dict[str, object]) -> dict[str, object]:
        summary = execution.get("input_summary_json") if isinstance(execution.get("input_summary_json"), dict) else {}
        approval_summary = summary.get("approval_summary") if isinstance(summary, dict) and isinstance(summary.get("approval_summary"), dict) else {}
        estimated = approval_summary.get("estimated_cost_at_approval") if isinstance(approval_summary, dict) else {}
        status = str(execution.get("status") or "-")
        approval_state = str(summary.get("approval_state") or "").lower()
        if status == "awaiting_approval" and approval_state == "approved" and execution.get("approved_at") is not None:
            status = "approved"
        if status == "cancelled" and str(execution.get("error_category") or "").lower() == "interrupted":
            status = "interrupted"
        elif status == "cancelled" and approval_state == "rejected":
            status = "rejected_by_user"
        return {
            "execution_id": execution.get("execution_uuid"),
            "provider": execution.get("provider"),
            "model_id": summary.get("model_id") or execution.get("model_catalog_id"),
            "model_role": execution.get("requested_model_role"),
            "status": status,
            "latency": {"latency_ms": execution.get("latency_ms") or 0},
            "usage": {},
            "cost": {
                "estimated_min_cost": estimated.get("minimum_cost") if isinstance(estimated, dict) else None,
                "estimated_max_cost": estimated.get("maximum_cost") if isinstance(estimated, dict) else None,
                "calculated_cost": None,
                "currency": (estimated.get("currency") if isinstance(estimated, dict) else None) or "USD",
                "notes": summary.get("approval_state") or execution.get("error_message_safe") or "-",
            },
            "cache": {"cache_status": execution.get("cache_status") or "invalidated", "hit_count": 0, "refresh_requested": False},
            "validation": {"status": execution.get("validation_status") or "requires_human_review", "issues": (execution.get("error_message_safe") or "-",)},
            "error": {
                "safe_message": execution.get("error_message_safe") or "-",
                "technical_reference": execution.get("error_category") or "-",
                "suggested_action": execution.get("input_summary_json", {}).get("retry_allowed") and "Reintenta la ejecucion." or "-",
            },
            "provenance": {"approval": approval_summary},
        }

    def _restore_ai_runtime_state(self) -> None:
        task = self.workspace.ai_runtime_active_diagnostic_task(self._selected_provider(), self._selected_role())
        if task is None:
            return
        payload = getattr(task, "payload", {})
        execution_id = str(payload.get("execution_id") or "")
        execution = self.workspace.ai_runtime_get_execution(execution_id) if execution_id else None
        if not execution:
            return
        result = self._execution_result_from_record(execution)
        self._show_result(result)
        status = str(result.get("status") or "").lower()
        if status == "awaiting_approval":
            self._approval_requested(execution_id, result)
        elif status == "approved":
            self._current_execution_id = execution_id
            self._current_execution_status = "approved"
            self._set_running_state(False, "Aprobacion registrada. Preparando diagnostico...")
            self.run_button.setEnabled(False)
            self.provider_combo.setEnabled(True)
            self.role_combo.setEnabled(True)
            self.cache_combo.setEnabled(True)
            self.auto_config_button.setEnabled(True)
            self.message_label.setText("Aprobacion registrada. Preparando diagnostico...")
        elif status == "interrupted":
            self._current_execution_id = execution_id
            self._current_execution_status = "interrupted"
            self._set_running_state(False, "La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.")
            self.run_button.setText("Reintentar")
            self.run_button.setEnabled(True)
            self.cancel_active_button.setEnabled(False)
            self.message_label.setText("La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.")

    def _approval_requested(self, execution_id: str, result: dict[str, object]) -> None:
        self._current_execution_id = execution_id
        self._diagnostic_running = False
        self._set_running_state(False, "Esperando tu aprobacion.")
        self._show_approval_panel(result)
        self.run_button.setEnabled(False)
        self.provider_combo.setEnabled(True)
        self.role_combo.setEnabled(True)
        self.cache_combo.setEnabled(True)
        self.auto_config_button.setEnabled(True)
        self.message_label.setText("Esperando tu aprobacion.")
        self._start_live_refresh()

    def _finalize_diagnostic(self) -> None:
        self._set_running_state(False)
        if not self._approval_running:
            self._set_live_controls_locked(False)

    def shutdown(self) -> None:
        for thread in (self._diagnostic_thread, self._approval_thread):
            if thread is None:
                continue
            if thread.isRunning():
                thread.wait(5000)
        self._diagnostic_thread = None
        self._approval_thread = None
        self._approval_running = False
        self._stop_live_refresh()

    def _diagnostic_finished(self) -> None:
        self._diagnostic_thread = None
        self._approval_thread = None
        self._approval_running = False
        self._set_live_controls_locked(False)
        self._stop_live_refresh()

    def _diagnostic_completed(self, result: object) -> None:
        logger.info("ai_runtime_diagnostic.execution_completed")
        payload = result.to_dict() if hasattr(result, "to_dict") else getattr(result, "__dict__", {})
        payload_dict = payload if isinstance(payload, dict) else {}
        self._show_result(payload_dict)
        status = str(payload_dict.get("status") or "").lower()
        error = payload_dict.get("error") if isinstance(payload_dict.get("error"), dict) else {}
        if status == "awaiting_approval":
            execution_id = str(payload_dict.get("execution_id") or "")
            self._approval_requested(execution_id, payload_dict)
            self.refresh()
            _refresh_enclosing_overview(self)
            return
        self._hide_approval_panel()
        self._finalize_diagnostic()
        self.refresh()
        if status == "blocked_by_credentials" or str(error.get("category") or "").lower() == "authentication_error":
            logger.info("ai_runtime_diagnostic.execution_failed status=%s reason=authentication_error", status)
        elif status in {"failed", "blocked_by_budget", "blocked_by_privacy", "blocked_by_provider", "blocked_by_model"} or payload_dict.get("error"):
            logger.info("ai_runtime_diagnostic.execution_failed status=%s", status)
        _refresh_enclosing_overview(self)
        self.message_label.setText(self._friendly_diagnostic_message(status, error))

    def _diagnostic_failed(self, message: str) -> None:
        logger.info("ai_runtime_diagnostic.execution_failed")
        error = map_error(Exception(message))
        self._hide_approval_panel()
        self._current_execution_status = "failed"
        self.execution_label.setText("-")
        self.provider_label.setText(self._selected_provider())
        self.model_label.setText(_fmt(self.model_line.text()))
        self.role_label.setText(_fmt(ROLE_LABELS.get(self._selected_role(), self._selected_role())))
        self.status_label.setText("failed")
        self.latency_label.setText("-")
        self.input_tokens_label.setText("-")
        self.output_tokens_label.setText("-")
        self.estimated_cost_label.setText("-")
        self.calculated_cost_label.setText("-")
        self.cache_label.setText("-")
        self.validation_label.setText("rejected")
        self.error_label.setText(f"{error.explanation} [{error.technical_code}]")
        self.suggested_action_label.setText(error.recommended_action)
        self._finalize_diagnostic()
        self.refresh()
        _refresh_enclosing_overview(self)
        self.message_label.setText("No se pudo completar el diagnóstico.")

    def _approve_and_continue(self) -> None:
        if not self._current_execution_id or self._approval_running:
            return
        logger.info(
            "ai_runtime_diagnostic.approval_clicked execution_id=%s provider=%s role=%s",
            self._current_execution_id,
            self._selected_provider(),
            self._selected_role(),
        )
        self._approval_running = True
        self._set_approval_controls_enabled(False)
        self._set_live_controls_locked(True)
        self._current_execution_status = "preparing_context"
        self.status_label.setText("preparing_context")
        self.message_label.setText("Registrando aprobacion...")
        self._hide_approval_panel()
        provider = self._selected_provider()
        role = self._selected_role()
        self._approval_thread = DiagnosticRunThread(
            self.workspace,
            provider,
            role,
            str(self.cache_combo.currentData() or "use"),
            approval_execution_id=self._current_execution_id,
        )
        self._approval_thread.result_ready.connect(self._diagnostic_completed)
        self._approval_thread.error_ready.connect(self._diagnostic_failed)
        self._approval_thread.finished.connect(self._diagnostic_finished)
        self._approval_thread.finished.connect(self._approval_thread.deleteLater)
        self._approval_thread.start()
        self._start_live_refresh()

    def _reject_execution(self) -> None:
        if not self._current_execution_id:
            return
        self._set_approval_controls_enabled(False)
        result = self.workspace.ai_runtime_reject_diagnostic_execution(
            self._current_execution_id,
            rejected_by="usuario",
            rejection_reason="El usuario rechazo la ejecucion.",
        )
        try:
            display_result = {
                "execution_id": result.get("execution_uuid") or self._current_execution_id,
                "provider": result.get("provider"),
                "model_id": (result.get("input_summary_json") or {}).get("model_id") if isinstance(result.get("input_summary_json"), dict) else result.get("model_catalog_id"),
                "model_role": result.get("requested_model_role"),
                "status": result.get("status") or "cancelled",
                "latency": {"latency_ms": result.get("latency_ms") or 0},
                "usage": {},
                "cost": {
                    "estimated_min_cost": None,
                    "estimated_max_cost": None,
                    "calculated_cost": None,
                    "currency": "USD",
                    "notes": "La ejecucion fue cancelada y no se realizo ningun cargo.",
                },
                "cache": {"cache_status": result.get("cache_status") or "invalidated", "hit_count": 0, "refresh_requested": False},
                "validation": {"status": result.get("validation_status") or "requires_human_review", "issues": ("La ejecucion fue cancelada y no se realizo ningun cargo.",)},
                "error": {
                    "safe_message": result.get("error_message_safe") or "La ejecucion fue cancelada y no se realizo ningun cargo.",
                    "technical_reference": "cancelled_by_user",
                    "suggested_action": "-",
                },
            }
            self._show_result(display_result)
            self.status_label.setText("cancelled")
            self.calculated_cost_label.setText("Sin cargo")
            self.message_label.setText("La ejecucion fue cancelada y no se realizo ningun cargo.")
        finally:
            self._approval_running = False
            self._hide_approval_panel()
            self._finalize_diagnostic()
            self.refresh()
            _refresh_enclosing_overview(self)
            self.message_label.setText("La ejecucion fue cancelada y no se realizo ningun cargo.")
            self._stop_live_refresh()

    def _cancel_active_execution(self) -> None:
        if not self._current_execution_id:
            return
        status = str(self._current_execution_status or "").lower()
        if status == "awaiting_approval":
            self._reject_execution()
            return
        self._set_approval_controls_enabled(False)
        result = self.workspace.ai_runtime_cancel_diagnostic_execution(
            self._current_execution_id,
            cancelled_by="usuario",
            cancellation_reason="La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.",
        )
        self._show_result(self._execution_result_from_record(result if isinstance(result, dict) else {}))
        self.status_label.setText("interrupted")
        self.run_button.setText("Reintentar")
        self.run_button.setEnabled(True)
        self.message_label.setText("La ejecucion anterior se interrumpio al cerrar la aplicacion. Puedes volver a intentarla.")
        self._current_execution_status = "interrupted"
        self._hide_approval_panel()
        self._finalize_diagnostic()
        self.refresh()
        self._stop_live_refresh()

    def _review_budget(self) -> None:
        if self._on_review_budget is not None:
            self._on_review_budget()
            return
        tabs = self.parentWidget()
        while tabs is not None:
            if hasattr(tabs, "tabs") and hasattr(tabs, "budget_tab"):
                try:
                    tabs.tabs.setCurrentWidget(tabs.budget_tab)
                except Exception:
                    pass
                return
            tabs = tabs.parentWidget()

    def _run_diagnostic(self) -> None:
        if self._diagnostic_thread is not None and self._diagnostic_thread.isRunning():
            self.message_label.setText("El diagnóstico ya está en ejecución.")
            return
        provider = self._selected_provider()
        role = self._selected_role()
        self._restore_ai_runtime_state()
        current_status = str(self._current_execution_status or "").lower()
        if self._current_execution_id:
            current_status = str(self._current_execution_status or "").lower()
            if current_status == "awaiting_approval":
                self.message_label.setText("Esperando tu aprobacion.")
                return
            if current_status in {"approved", "queued", "preparing_context", "running", "validating"}:
                self.message_label.setText("Ya existe un diagnóstico en curso.")
                self.run_button.setEnabled(True)
                self.cancel_active_button.setEnabled(True)
                return
        active_task = self.workspace.ai_runtime_active_diagnostic_task(provider, role)
        if active_task is not None:
            payload = getattr(active_task, "payload", {})
            execution_id = str(payload.get("execution_id") or "")
            execution = self.workspace.ai_runtime_get_execution(execution_id) if execution_id else None
            if execution is not None:
                result = self._execution_result_from_record(execution)
                self._show_result(result)
                if str(result.get("status") or "").lower() == "awaiting_approval":
                    self._approval_requested(execution_id, result)
                else:
                    self._current_execution_id = execution_id
                    self._current_execution_status = str(result.get("status") or "queued")
                    self._set_running_state(False, "Ya existe un diagnóstico en curso.")
                    self.run_button.setEnabled(True)
                    self.cancel_active_button.setEnabled(True)
                    self.message_label.setText("Ya existe un diagnóstico en curso.")
                return
        logger.info(
            "ai_runtime_diagnostic.button_clicked provider=%s role=%s cache_policy=%s",
            provider,
            role,
            str(self.cache_combo.currentData() or "use"),
        )
        provider_status = self.workspace.ai_runtime_provider_status().get(provider, {})
        if not provider_status.get("configured"):
            self.message_label.setText("No hay una credencial configurada para este proveedor.")
        self._clear_result_fields()
        self.status_label.setText("queued")
        self._approval_running = False
        self._set_running_state(True, "Preparando diagnóstico...")
        logger.info(
            "ai_runtime_diagnostic.request_built provider=%s role=%s cache_policy=%s",
            provider,
            role,
            str(self.cache_combo.currentData() or "use"),
        )
        self._diagnostic_thread = DiagnosticRunThread(
            self.workspace,
            provider,
            role,
            str(self.cache_combo.currentData() or "use"),
        )
        self._diagnostic_thread.result_ready.connect(self._diagnostic_completed)
        self._diagnostic_thread.error_ready.connect(self._diagnostic_failed)
        self._diagnostic_thread.finished.connect(self._diagnostic_finished)
        self._diagnostic_thread.finished.connect(self._diagnostic_thread.deleteLater)
        self._diagnostic_thread.start()
        self._start_live_refresh()

    def _show_result(self, result: dict[str, object]) -> None:
        self.execution_label.setText(str(result.get("execution_id") or "-"))
        self.provider_label.setText(_fmt(result.get("provider")))
        self.model_label.setText(_fmt(result.get("model_id")))
        self.role_label.setText(_fmt(result.get("model_role")))
        status = str(result.get("status") or "-")
        self._current_execution_status = status
        self.status_label.setText(_fmt(status))
        latency = result.get("latency") or {}
        if isinstance(latency, dict):
            self.latency_label.setText(f"{latency.get('latency_ms', 0)} ms")
        else:
            self.latency_label.setText("0 ms")
        usage = result.get("usage") or {}
        if isinstance(usage, dict):
            self.input_tokens_label.setText(_fmt(usage.get("input_tokens")))
            self.output_tokens_label.setText(_fmt(usage.get("output_tokens")))
        else:
            self.input_tokens_label.setText("0")
            self.output_tokens_label.setText("0")
        cost = result.get("cost") or {}
        if isinstance(cost, dict):
            estimated_min = cost.get("estimated_min_cost")
            estimated_max = cost.get("estimated_max_cost")
            currency = cost.get("currency") or "USD"
            if estimated_min is None and estimated_max is None:
                self.estimated_cost_label.setText("Precio no verificado")
            else:
                self.estimated_cost_label.setText(f"{estimated_min} - {estimated_max} {currency}")
            calculated_cost = cost.get("calculated_cost")
            notes = str(cost.get("notes") or "")
            if calculated_cost is None or "precio no verificado" in notes.lower() or "unknown" in notes.lower():
                self.calculated_cost_label.setText("No disponible")
            else:
                self.calculated_cost_label.setText(f"{calculated_cost} {currency}")
        cache = result.get("cache") or {}
        if isinstance(cache, dict):
            self.cache_label.setText(
                f"{cache.get('cache_status')} / hits: {cache.get('hit_count', 0)} / policy: {cache.get('refresh_requested')}"
            )
        validation = result.get("validation") or {}
        if isinstance(validation, dict):
            self.validation_label.setText(f"{validation.get('status')} / issues: {', '.join(validation.get('issues') or ()) or '-'}")
        error = result.get("error") or {}
        if isinstance(error, dict):
            technical_reference = str(error.get("technical_reference") or "-")
            safe_message = str(error.get("safe_message") or "-")
            self.error_label.setText(f"{safe_message} [{technical_reference}]")
            self.suggested_action_label.setText(str(error.get("suggested_action") or "-"))
        else:
            self.error_label.setText("-")
            self.suggested_action_label.setText("-")

        if status != "awaiting_approval":
            self._hide_approval_panel()

    def refresh(self) -> None:
        selected_provider = self._selected_provider() if self.provider_combo.count() else None
        selected_role = self._selected_role() if self.role_combo.count() else None
        self._seed_combos()
        if selected_provider is not None:
            provider_index = self.provider_combo.findData(selected_provider)
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
        if selected_role is not None:
            role_index = self.role_combo.findData(selected_role)
            if role_index >= 0:
                self.role_combo.setCurrentIndex(role_index)
        self._refresh_model_line()
        if self._diagnostic_running:
            self.provider_combo.setEnabled(False)
            self.role_combo.setEnabled(False)
            self.cache_combo.setEnabled(False)
            self.auto_config_button.setEnabled(False)
            self.run_button.setEnabled(False)
            self.cancel_active_button.setEnabled(False)
            return
        self._restore_ai_runtime_state()
        current_status = str(self._current_execution_status or "").lower()
        if current_status == "awaiting_approval":
            self.message_label.setText("Esperando tu aprobacion.")
            self._refresh_cancel_button()
            return
        if current_status in {"approved", "queued", "preparing_context", "running", "validating"}:
            self.message_label.setText("Ya existe un diagnóstico en curso.")
            self._refresh_cancel_button()
            return
        self.run_button.setEnabled(True)
        self.provider_combo.setEnabled(True)
        self.role_combo.setEnabled(True)
        self.cache_combo.setEnabled(True)
        self.auto_config_button.setEnabled(True)
        self._refresh_approval_buttons()
        self._refresh_cancel_button()
        if not self.workspace.ai_runtime_provider_status().get(self._selected_provider(), {}).get("configured"):
            self.message_label.setText("No hay una credencial configurada para este proveedor.")
        else:
            self.message_label.setText("Listo para ejecutar diagnóstico.")
class HistoryTab(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        title = QLabel("Historial")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Ejecuciones persistidas sin mostrar secretos, prompts privados ni payloads crudos.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(
            [
                "Fecha",
                "execution_id",
                "task_type",
                "Proveedor",
                "Modelo",
                "Estado",
                "Aprobacion",
                "Actor",
                "Motivo",
                "Costo",
                "Latencia",
                "Cache",
                "Error",
            ]
        )
        self.table.itemSelectionChanged.connect(self._update_detail)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setObjectName("ai_runtime_history_detail")

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.table)
        layout.addWidget(self.detail)
        self.refresh()

    def _approval_view(self, execution: dict[str, object], payloads: list[dict[str, object]]) -> dict[str, str]:
        summary = execution.get("input_summary_json") if isinstance(execution.get("input_summary_json"), dict) else {}
        approval_summary = summary.get("approval_summary") if isinstance(summary, dict) and isinstance(summary.get("approval_summary"), dict) else {}
        for payload in payloads:
            if payload.get("payload_type") != "approval_decision" or not isinstance(payload.get("content_json"), dict):
                continue
            content = payload["content_json"]
            estimated = content.get("estimated_cost_at_decision")
            price_unknown = "Si"
            if isinstance(estimated, dict):
                price_unknown = "Si" if estimated.get("minimum_cost") is None or estimated.get("maximum_cost") is None else "No"
            return {
                "decision": str(content.get("decision") or summary.get("approval_state") or execution.get("status") or "-").lower(),
                "actor": str(content.get("actor") or content.get("approved_by") or content.get("rejected_by") or "-"),
                "reason": str(content.get("reason") or content.get("approval_reason") or "-"),
                "date": str(content.get("approved_at") or content.get("rejected_at") or execution.get("approved_at") or execution.get("updated_at") or "-"),
                "price_unknown": price_unknown,
            }
        approval_state = str(summary.get("approval_state") or "-")
        return {
            "decision": approval_state,
            "actor": str(summary.get("approved_by") or summary.get("rejected_by") or "-"),
            "reason": str(summary.get("approval_reason") or "-"),
            "date": str(summary.get("approved_at") or summary.get("rejected_at") or execution.get("approved_at") or execution.get("updated_at") or "-"),
            "price_unknown": "Si" if isinstance(approval_summary, dict) and bool(approval_summary.get("estimated_cost_unknown")) else "No",
        }

    def _display_status(self, execution: dict[str, object], approval: dict[str, str]) -> str:
        status = str(execution.get("status") or "-")
        decision = approval.get("decision") or "-"
        if status == "awaiting_approval":
            if decision == "approved":
                return "approved"
            if decision == "rejected":
                return "rejected_by_user"
            return "awaiting_approval"
        if status == "cancelled" and str(execution.get("error_category") or "").lower() == "cancelled_by_user":
            return "rejected_by_user"
        return status

    def _cost_display(self, execution: dict[str, object], approval: dict[str, str], usage_cost: float) -> str:
        status = str(execution.get("status") or "")
        summary = execution.get("input_summary_json") if isinstance(execution.get("input_summary_json"), dict) else {}
        approval_summary = summary.get("approval_summary") if isinstance(summary, dict) and isinstance(summary.get("approval_summary"), dict) else {}
        if status == "cancelled" and approval.get("decision") == "rejected" and usage_cost == 0.0:
            return "Sin cargo"
        if status == "awaiting_approval" and usage_cost == 0.0:
            estimated = approval_summary.get("estimated_cost_at_approval") if isinstance(approval_summary, dict) else None
            if isinstance(estimated, dict) and estimated.get("minimum_cost") is None and estimated.get("maximum_cost") is None:
                return "No disponible (precio no verificado)"
            return "Pendiente"
        if approval.get("price_unknown") == "Si" and usage_cost == 0.0:
            return "No disponible"
        return str(usage_cost)

    def refresh(self) -> None:
        executions = self.workspace.ai_runtime_list_executions(self.workspace.selected_creator_id, limit=100)
        usage_records = self.workspace.ai_runtime_list_usage_records()
        usage_by_execution: dict[str, float] = {}
        for record in usage_records:
            execution_id = str(record.get("execution_id") or "")
            usage_by_execution[execution_id] = usage_by_execution.get(execution_id, 0.0) + float(record.get("calculated_cost") or 0.0)
        self.table.setRowCount(0)
        for row_index, execution in enumerate(executions):
            self.table.insertRow(row_index)
            execution_uuid = str(execution.get("execution_uuid") or "")
            summary = execution.get("input_summary_json") if isinstance(execution.get("input_summary_json"), dict) else {}
            model_name = summary.get("model_id") or execution.get("model_catalog_id")
            payloads = self.workspace.ai_runtime_list_payloads(execution_uuid)
            approval = self._approval_view(execution, payloads)
            cost = usage_by_execution.get(execution_uuid, 0.0)
            values = [
                execution.get("created_at"),
                _safe_short_id(execution_uuid),
                execution.get("task_type"),
                execution.get("provider"),
                model_name,
                self._display_status(execution, approval),
                approval.get("date"),
                approval.get("actor"),
                approval.get("reason"),
                self._cost_display(execution, approval, cost),
                f"{execution.get('latency_ms') or 0} ms",
                execution.get("cache_status"),
                execution.get("error_message_safe"),
            ]
            for column, value in enumerate(values):
                item = _item(value)
                if column == 1:
                    item.setData(Qt.ItemDataRole.UserRole, execution_uuid)
                self.table.setItem(row_index, column, item)
        self.table.resizeColumnsToContents()
        self._update_detail()

    def _selected_execution_uuid(self) -> str | None:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 1)
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _update_detail(self) -> None:
        execution_uuid = self._selected_execution_uuid()
        if not execution_uuid:
            self.detail.setPlainText("Selecciona una ejecucion para ver un detalle seguro.")
            return
        execution = self.workspace.ai_runtime_get_execution(execution_uuid)
        if not execution:
            self.detail.setPlainText("Ejecucion no disponible.")
            return
        usage_records = self.workspace.ai_runtime_list_usage_records(execution_uuid)
        payloads = self.workspace.ai_runtime_list_payloads(execution_uuid)
        approval = self._approval_view(execution, payloads)
        summary = execution.get("input_summary_json") if isinstance(execution.get("input_summary_json"), dict) else {}
        safe_lines = [
            f"execution_id: {execution.get('execution_uuid')}",
            f"task_type: {execution.get('task_type')}",
            f"provider: {execution.get('provider')}",
            f"model: {summary.get('model_id') or execution.get('model_catalog_id')}",
            f"status: {self._display_status(execution, approval)}",
            f"validation: {execution.get('validation_status')}",
            f"approval: {approval.get('decision')}",
            f"approval_actor: {approval.get('actor')}",
            f"approval_reason: {approval.get('reason')}",
            f"price_unknown: {approval.get('price_unknown')}",
            f"cache: {execution.get('cache_status')}",
            f"latency_ms: {execution.get('latency_ms')}",
            f"error: {execution.get('error_message_safe') or '-'}",
            f"usage_records: {len(usage_records)}",
            f"payloads: {len(payloads)}",
        ]
        self.detail.setPlainText("\n".join(safe_lines))


class AIRuntimeOverviewView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.setObjectName("ai_runtime_view")

        title = QLabel("AI Runtime")
        title.setObjectName("TitleLabel")
        subtitle = QLabel(
            "Seccion visible para proveedores, modelos y roles, presupuesto, diagnostico e historial."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.tabs = QTabWidget()
        self.tabs.setObjectName("ai_runtime_tabs")
        self.providers_tab = ProvidersTab(workspace)
        self.roles_tab = RolesTab(workspace)
        self.budget_tab = BudgetTab(workspace)
        self.diagnostics_tab = DiagnosticsTab(workspace, on_review_budget=lambda: self.tabs.setCurrentWidget(self.budget_tab))
        self.history_tab = HistoryTab(workspace)
        self.tabs.addTab(self.providers_tab, "Proveedores")
        self.tabs.addTab(self.roles_tab, "Modelos y roles")
        self.tabs.addTab(self.budget_tab, "Presupuesto y consumo")
        self.tabs.addTab(self.diagnostics_tab, "Diagnostico")
        self.tabs.addTab(self.history_tab, "Historial")

        refresh_button = QPushButton("Actualizar todo")
        refresh_button.clicked.connect(self.refresh)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh_button)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addLayout(header)
        layout.addWidget(subtitle)
        layout.addWidget(self.tabs)
        layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

    def refresh(self) -> None:
        self.providers_tab.refresh()
        self.roles_tab.refresh()
        self.budget_tab.refresh()
        self.diagnostics_tab.refresh()
        self.history_tab.refresh()
