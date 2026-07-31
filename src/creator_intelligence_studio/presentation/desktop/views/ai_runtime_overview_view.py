"""Desktop view for AI runtime configuration and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from PySide6.QtCore import Qt, QUrl
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

        self.configure_button = QPushButton("Configurar clave")
        self.replace_button = QPushButton("Reemplazar clave")
        self.delete_button = QPushButton("Eliminar clave")
        self.test_button = QPushButton("Probar conexion")
        self.keys_button = QPushButton("Abrir sitio oficial de claves")
        self.billing_button = QPushButton("Abrir facturacion")
        self.help_button = QPushButton("Ver ayuda")
        self.configure_button.setObjectName(f"{provider_name}_configure_button")
        self.replace_button.setObjectName(f"{provider_name}_replace_button")
        self.delete_button.setObjectName(f"{provider_name}_delete_button")
        self.test_button.setObjectName(f"{provider_name}_test_button")
        self.keys_button.setObjectName(f"{provider_name}_keys_button")
        self.billing_button.setObjectName(f"{provider_name}_billing_button")
        self.help_button.setObjectName(f"{provider_name}_help_button")

        buttons = QGridLayout()
        buttons.addWidget(self.configure_button, 0, 0)
        buttons.addWidget(self.replace_button, 0, 1)
        buttons.addWidget(self.delete_button, 0, 2)
        buttons.addWidget(self.test_button, 1, 0)
        buttons.addWidget(self.keys_button, 1, 1)
        buttons.addWidget(self.billing_button, 1, 2)
        buttons.addWidget(self.help_button, 2, 0, 1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.state_label)
        layout.addWidget(self.mask_label)
        layout.addWidget(self.check_label)
        layout.addWidget(self.enabled_label)
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
        self.configure_button.setEnabled(True)
        self.configure_button.setText("Configurar clave" if not configured else "Reemplazar clave")
        self.replace_button.setEnabled(configured)
        self.delete_button.setEnabled(configured)
        self.test_button.setEnabled(configured)


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

    def _test_provider(self, provider_name: str) -> None:
        diagnostic = self.workspace.ai_runtime_test_provider(provider_name)
        self.refresh()
        if diagnostic.status == "ok":
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
        self.fallback_combo = QComboBox()
        self.enabled_checkbox = QCheckBox("Habilitado")
        self.default_checkbox = QCheckBox("Predeterminado")
        self.save_button = QPushButton("Guardar asignacion")
        self.save_button.clicked.connect(self._save_assignment)
        self.current_assignment_label = QLabel("Asignacion actual: sin seleccionar")
        self.current_assignment_label.setWordWrap(True)
        self.current_assignment_label.setObjectName("MutedLabel")

        self.role_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_combo())
        self.provider_combo.currentIndexChanged.connect(lambda *_: self._refresh_model_combo())

        self.provider_combo.addItem("OpenAI", "openai")
        self.provider_combo.addItem("Anthropic", "anthropic")
        self.fallback_combo.addItem("Sin fallback", "none")
        self.fallback_combo.addItem("Fallback al proveedor", "provider")
        self.fallback_combo.addItem("Fallback entre proveedores", "cross_provider")

        form = QFormLayout()
        form.addRow("Rol", self.role_combo)
        form.addRow("Proveedor", self.provider_combo)
        form.addRow("Modelo", self.model_combo)
        form.addRow("Fallback", self.fallback_combo)
        form.addRow("", self.enabled_checkbox)
        form.addRow("", self.default_checkbox)
        form.addRow("", self.save_button)

        self.editor_frame = QFrame()
        self.editor_frame.setObjectName("MutedPanel")
        editor_layout = QVBoxLayout(self.editor_frame)
        editor_layout.addWidget(self.current_assignment_label)
        editor_layout.addLayout(form)

        outer = QVBoxLayout(self)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addWidget(self.table)
        outer.addWidget(self.editor_frame)

        self._seed_role_combo()
        self.refresh()

    def _seed_role_combo(self) -> None:
        self.role_combo.clear()
        for role, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, role)

    def _selected_role(self) -> str:
        return str(self.role_combo.currentData() or "cheap_structured_model")

    def _selected_provider(self) -> str:
        return str(self.provider_combo.currentData() or "openai")

    def _selected_model(self) -> dict[str, object] | None:
        data = self.model_combo.currentData()
        if isinstance(data, dict):
            return data
        return None

    def _selected_creator_scope(self) -> str | None:
        return self.workspace.selected_creator_id

    def _refresh_model_combo(self) -> None:
        provider = self._selected_provider()
        models = self._selectable_models(provider)
        current_model_id = None
        current_assignment = self.workspace.ai_runtime_service.model_registry.resolve_role(
            self._selected_role(),
            creator_id=self._selected_creator_scope(),
            provider=provider,
        )
        if current_assignment is not None:
            current_model_id = current_assignment[1].model_id

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        selected_index = -1
        for model in models:
            label = f"{model['display_name']} ({model['model_id']}) · {model.get('status', '-')}"
            index = self.model_combo.count()
            self.model_combo.addItem(label, model)
            if current_model_id is not None and str(model.get("model_id")) == current_model_id:
                selected_index = index
        if selected_index >= 0:
            self.model_combo.setCurrentIndex(selected_index)
        elif self.model_combo.count():
            self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)
        self._update_assignment_preview()

    def _selectable_models(self, provider: str) -> list[dict[str, object]]:
        models = list(self.workspace.ai_runtime_list_models(provider))
        return [model for model in models if str(model.get("status") or "").lower() in {"approved", "testing"}]

    def _resolve_current_assignment(self, role: str) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        service = self.workspace.ai_runtime_service
        resolved = service.model_registry.resolve_role(role, creator_id=self._selected_creator_scope())
        if resolved is None:
            return None, None
        assignment, model = resolved
        return assignment.to_dict(), model.to_dict()

    def _update_assignment_preview(self) -> None:
        role = self._selected_role()
        assignment, model = self._resolve_current_assignment(role)
        if assignment is None or model is None:
            self.current_assignment_label.setText("Asignacion actual: sin asignar")
            return
        self.current_assignment_label.setText(
            "Asignacion actual: "
            f"{assignment['provider']} / {model['display_name']} / {model.get('snapshot_or_version') or 'sin snapshot'}"
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
        self.refresh()
        QMessageBox.information(
            self,
            "AI Runtime",
            f"Asignacion guardada: {assignment['role']} -> {assignment['provider']} / {assignment['model_catalog_id']}",
        )

    def refresh(self) -> None:
        creator_id = self._selected_creator_scope()
        selected_role = self._selected_role() if self.role_combo.count() else None
        selected_provider = self._selected_provider() if self.provider_combo.count() else None
        self._seed_role_combo()
        if selected_role is not None:
            role_index = self.role_combo.findData(selected_role)
            if role_index >= 0:
                self.role_combo.setCurrentIndex(role_index)
        if selected_provider is not None:
            provider_index = self.provider_combo.findData(selected_provider)
            if provider_index >= 0:
                self.provider_combo.setCurrentIndex(provider_index)
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
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
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
        self.run_button.clicked.connect(self._run_diagnostic)

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

        form = QFormLayout()
        form.addRow("Proveedor", self.provider_combo)
        form.addRow("Rol", self.role_combo)
        form.addRow("Modelo resuelto", self.model_line)
        form.addRow("Cache policy", self.cache_combo)
        form.addRow("", self.run_button)

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
        outer.addStretch(1)

        self._seed_combos()
        self.refresh()

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
            self.model_line.setText("Sin modelo resuelto")
            return
        _, model = resolved
        self.model_line.setText(
            f"{model.display_name} / {model.model_id} / {model.snapshot_or_version or 'sin snapshot'}"
        )

    def _run_diagnostic(self) -> None:
        provider = self._selected_provider()
        role = self._selected_role()
        provider_status = self.workspace.ai_runtime_provider_status().get(provider, {})
        if not provider_status.get("configured"):
            self.message_label.setText("No hay una credencial configurada para este proveedor.")
        result = self.workspace.run_ai_runtime_diagnostic(
            provider=provider,
            role=role,
            cache_policy=str(self.cache_combo.currentData() or "use"),
        )
        self._show_result(result.to_dict() if hasattr(result, "to_dict") else result)
        self.message_label.setText(
            "No hay una credencial configurada para este proveedor."
            if result.error and result.error.category == "authentication_error"
            else "Diagnostico ejecutado."
        )
        self.refresh()

    def _show_result(self, result: dict[str, object]) -> None:
        self.execution_label.setText(str(result.get("execution_id") or "-"))
        self.provider_label.setText(_fmt(result.get("provider")))
        self.model_label.setText(_fmt(result.get("model_id")))
        self.role_label.setText(_fmt(result.get("model_role")))
        self.status_label.setText(_fmt(result.get("status")))
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
            self.estimated_cost_label.setText(
                f"{cost.get('estimated_min_cost')} - {cost.get('estimated_max_cost')} {cost.get('currency') or 'USD'}"
            )
            self.calculated_cost_label.setText(f"{cost.get('calculated_cost')} {cost.get('currency') or 'USD'}")
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
            self.error_label.setText(str(error.get("safe_message") or "-"))
            self.suggested_action_label.setText(str(error.get("suggested_action") or "-"))
        else:
            self.error_label.setText("-")
            self.suggested_action_label.setText("-")

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
        if not self.workspace.ai_runtime_provider_status().get(self._selected_provider(), {}).get("configured"):
            self.message_label.setText("No hay una credencial configurada para este proveedor.")
        else:
            self.message_label.setText("Listo para ejecutar diagnostico.")


class HistoryTab(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        title = QLabel("Historial")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Ejecuciones persistidas sin mostrar secretos, prompts privados ni payloads crudos.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Fecha",
                "execution_id",
                "task_type",
                "Proveedor",
                "Modelo",
                "Estado",
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
            cost = usage_by_execution.get(execution_uuid, 0.0)
            values = [
                execution.get("created_at"),
                _safe_short_id(execution_uuid),
                execution.get("task_type"),
                execution.get("provider"),
                execution.get("model_catalog_id"),
                execution.get("status"),
                cost,
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
        safe_lines = [
            f"execution_id: {execution.get('execution_uuid')}",
            f"task_type: {execution.get('task_type')}",
            f"provider: {execution.get('provider')}",
            f"model: {execution.get('model_catalog_id')}",
            f"status: {execution.get('status')}",
            f"validation: {execution.get('validation_status')}",
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
        self.diagnostics_tab = DiagnosticsTab(workspace)
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
