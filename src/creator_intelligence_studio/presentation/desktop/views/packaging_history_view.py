"""Vista de historial de packaging creativo."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class PackagingHistoryView(QWidget):
    """Muestra historial de versiones, decisiones y enlaces de experimentos."""

    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.brand_profiles_table = QTableWidget(0, 5)
        self.brand_profiles_table.setHorizontalHeaderLabels(["Version", "Estado", "Resumen", "Creado", "ID"])
        self.brand_profiles_table.setColumnHidden(4, True)
        self.decision_table = QTableWidget(0, 5)
        self.decision_table.setHorizontalHeaderLabels(["Decision", "Target", "Motivo", "Fecha", "ID"])
        self.decision_table.setColumnHidden(4, True)
        self.link_table = QTableWidget(0, 5)
        self.link_table.setHorizontalHeaderLabels(["Asset", "Experimento", "Assignment", "Creado", "ID"])
        self.link_table.setColumnHidden(4, True)
        self.title_versions_table = QTableWidget(0, 6)
        self.title_versions_table.setHorizontalHeaderLabels(["Titulo", "Plataforma", "Version", "Seleccionado", "Aprobacion", "ID"])
        self.title_versions_table.setColumnHidden(5, True)
        self.thumbnail_versions_table = QTableWidget(0, 6)
        self.thumbnail_versions_table.setHorizontalHeaderLabels(["Miniatura", "Plataforma", "Version", "Seleccionada", "Aprobacion", "ID"])
        self.thumbnail_versions_table.setColumnHidden(5, True)

        title = QLabel("Packaging History")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Historial trazable de versiones, decisiones y enlaces.")
        subtitle.setObjectName("MutedLabel")

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(QLabel("Brand profiles"))
        layout.addWidget(self.brand_profiles_table)
        layout.addWidget(QLabel("Title versions"))
        layout.addWidget(self.title_versions_table)
        layout.addWidget(QLabel("Thumbnail versions"))
        layout.addWidget(self.thumbnail_versions_table)
        layout.addWidget(QLabel("Decisions"))
        layout.addWidget(self.decision_table)
        layout.addWidget(QLabel("Experiment links"))
        layout.addWidget(self.link_table)

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if creator_id is None:
            for table in (
                self.brand_profiles_table,
                self.decision_table,
                self.link_table,
                self.title_versions_table,
                self.thumbnail_versions_table,
            ):
                table.setRowCount(0)
            return

        self.brand_profiles_table.setRowCount(0)
        self.decision_table.setRowCount(0)
        self.link_table.setRowCount(0)
        self.title_versions_table.setRowCount(0)
        self.thumbnail_versions_table.setRowCount(0)

        for row_index, profile in enumerate(self.workspace.list_packaging_brand_profiles(creator_id)):
            self.brand_profiles_table.insertRow(row_index)
            values = [
                profile.profile_version,
                profile.status.value,
                profile.brand_summary[:120],
                profile.created_at.isoformat(),
                profile.id,
            ]
            for column, value in enumerate(values):
                self.brand_profiles_table.setItem(row_index, column, _item(value))

        for asset in self.workspace.list_packaging_assets(creator_id):
            for title_version in self.workspace.list_packaging_title_versions(asset.id):
                row_index = self.title_versions_table.rowCount()
                self.title_versions_table.insertRow(row_index)
                values = [
                    title_version.title_text,
                    title_version.platform,
                    title_version.version_number,
                    "si" if title_version.is_selected else "no",
                    title_version.creator_approval_status,
                    title_version.id,
                ]
                for column, value in enumerate(values):
                    self.title_versions_table.setItem(row_index, column, _item(value))
            for thumbnail_version in self.workspace.list_packaging_thumbnail_versions(asset.id):
                row_index = self.thumbnail_versions_table.rowCount()
                self.thumbnail_versions_table.insertRow(row_index)
                values = [
                    thumbnail_version.image_path or thumbnail_version.source_type,
                    thumbnail_version.platform,
                    thumbnail_version.version_number,
                    "si" if thumbnail_version.is_selected else "no",
                    thumbnail_version.creator_approval_status,
                    thumbnail_version.id,
                ]
                for column, value in enumerate(values):
                    self.thumbnail_versions_table.setItem(row_index, column, _item(value))
            for link in self.workspace.list_packaging_experiment_links(asset.id):
                row_index = self.link_table.rowCount()
                self.link_table.insertRow(row_index)
                values = [asset.asset_type.value, link.experiment_id, link.assignment_id or "", link.created_at.isoformat(), link.id]
                for column, value in enumerate(values):
                    self.link_table.setItem(row_index, column, _item(value))

        for decision in self.workspace.list_packaging_decisions(creator_id):
            row_index = self.decision_table.rowCount()
            self.decision_table.insertRow(row_index)
            values = [
                decision.decision.value,
                f"{decision.target_type}:{decision.target_id}",
                decision.reason or "",
                decision.decided_at.isoformat(),
                decision.id,
            ]
            for column, value in enumerate(values):
                self.decision_table.setItem(row_index, column, _item(value))

        for table in (
            self.brand_profiles_table,
            self.decision_table,
            self.link_table,
            self.title_versions_table,
            self.thumbnail_versions_table,
        ):
            table.resizeColumnsToContents()
