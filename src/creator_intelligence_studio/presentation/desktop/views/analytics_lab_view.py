"""Vista de Analytics Lab."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
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


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class AnalyticsLabView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        self.tabs = QTabWidget()
        self.overview_tab = QWidget()
        self.publications_tab = QWidget()
        self.cohorts_tab = QWidget()
        self.comparisons_tab = QWidget()
        self.findings_tab = QWidget()
        self.reports_tab = QWidget()
        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.publications_tab, "Publications")
        self.tabs.addTab(self.cohorts_tab, "Cohorts")
        self.tabs.addTab(self.comparisons_tab, "Comparisons")
        self.tabs.addTab(self.findings_tab, "Findings")
        self.tabs.addTab(self.reports_tab, "Weekly Reports")

        self._build_overview_tab()
        self._build_publications_tab()
        self._build_cohorts_tab()
        self._build_comparisons_tab()
        self._build_findings_tab()
        self._build_reports_tab()

        title = QLabel("Analytics Lab")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Capa estadistica y comparativa trazable sobre las publicaciones disponibles.")
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

    def _build_overview_tab(self) -> None:
        self.overview_counts = {
            "publications": QLabel("0"),
            "cohorts": QLabel("0"),
            "analyses": QLabel("0"),
            "findings": QLabel("0"),
        }
        grid = QGridLayout(self.overview_tab)
        grid.addWidget(QLabel("Publicaciones"), 0, 0)
        grid.addWidget(self.overview_counts["publications"], 0, 1)
        grid.addWidget(QLabel("Cohortes"), 0, 2)
        grid.addWidget(self.overview_counts["cohorts"], 0, 3)
        grid.addWidget(QLabel("Corridas"), 1, 0)
        grid.addWidget(self.overview_counts["analyses"], 1, 1)
        grid.addWidget(QLabel("Findings"), 1, 2)
        grid.addWidget(self.overview_counts["findings"], 1, 3)
        self.recent_findings_table = QTableWidget(0, 5)
        self.recent_findings_table.setHorizontalHeaderLabels(["Tipo", "Titulo", "Confianza", "Estado", "Cohorte"])
        grid.addWidget(self.recent_findings_table, 2, 0, 1, 4)

    def _build_publications_tab(self) -> None:
        self.publications_table = QTableWidget(0, 8)
        self.publications_table.setHorizontalHeaderLabels(
            ["Titulo", "Plataforma", "Tipo", "Fecha", "Duracion", "Vistas", "Completion", "Warnings"]
        )
        self.publications_empty = EmptyStateWidget(
            "No hay publicaciones normalizadas todavia.",
            "Importa datos de Analytics Data Foundation para habilitar comparaciones.",
        )
        layout = QVBoxLayout(self.publications_tab)
        layout.addWidget(self.publications_empty)
        layout.addWidget(self.publications_table)

    def _build_cohorts_tab(self) -> None:
        self.cohorts_table = QTableWidget(0, 6)
        self.cohorts_table.setHorizontalHeaderLabels(["Nombre", "Plataforma", "Tipo", "Publicaciones", "Calidad", "Id"])
        self.cohorts_table.setColumnHidden(5, True)
        self.cohort_name = QLineEdit()
        self.cohort_name.setPlaceholderText("Cohorte nueva")
        self.cohort_description = QLineEdit()
        self.cohort_description.setPlaceholderText("Descripcion")
        self.cohort_platform = QLineEdit()
        self.cohort_platform.setPlaceholderText("Platform opcional")
        self.cohort_content_type = QLineEdit()
        self.cohort_content_type.setPlaceholderText("content_type opcional")
        self.cohort_create_button = QPushButton("Crear cohorte")
        self.cohort_analyze_button = QPushButton("Analizar seleccion")
        self.cohort_create_button.clicked.connect(self._create_cohort)
        self.cohort_analyze_button.clicked.connect(self._analyze_selected_cohort)
        controls = QGridLayout()
        controls.addWidget(QLabel("Nombre"), 0, 0)
        controls.addWidget(self.cohort_name, 0, 1)
        controls.addWidget(QLabel("Descripcion"), 0, 2)
        controls.addWidget(self.cohort_description, 0, 3)
        controls.addWidget(QLabel("Plataforma"), 1, 0)
        controls.addWidget(self.cohort_platform, 1, 1)
        controls.addWidget(QLabel("Tipo"), 1, 2)
        controls.addWidget(self.cohort_content_type, 1, 3)
        controls.addWidget(self.cohort_create_button, 2, 0)
        controls.addWidget(self.cohort_analyze_button, 2, 1)
        layout = QVBoxLayout(self.cohorts_tab)
        layout.addLayout(controls)
        layout.addWidget(self.cohorts_table)

    def _build_comparisons_tab(self) -> None:
        self.compare_publication_combo = QComboBox()
        self.compare_cohort_combo = QComboBox()
        self.compare_button = QPushButton("Comparar")
        self.analysis_combo = QComboBox()
        self.analysis_load_button = QPushButton("Cargar corrida")
        self.comparison_table = QTableWidget(0, 7)
        self.comparison_table.setHorizontalHeaderLabels(
            ["Metrica", "Observado", "Media cohorte", "Mediana", "Percentil", "Estado", "Warnings"]
        )
        self.comparison_detail = QLabel("Selecciona una corrida para ver comparaciones.")
        self.comparison_detail.setObjectName("MutedLabel")
        self.compare_button.clicked.connect(self._compare_publication)
        self.analysis_load_button.clicked.connect(self._load_selected_analysis)
        controls = QGridLayout()
        controls.addWidget(QLabel("Publicacion"), 0, 0)
        controls.addWidget(self.compare_publication_combo, 0, 1)
        controls.addWidget(QLabel("Cohorte"), 0, 2)
        controls.addWidget(self.compare_cohort_combo, 0, 3)
        controls.addWidget(self.compare_button, 0, 4)
        controls.addWidget(QLabel("Corrida"), 1, 0)
        controls.addWidget(self.analysis_combo, 1, 1, 1, 3)
        controls.addWidget(self.analysis_load_button, 1, 4)
        layout = QVBoxLayout(self.comparisons_tab)
        layout.addLayout(controls)
        layout.addWidget(self.comparison_detail)
        layout.addWidget(self.comparison_table)

    def _build_findings_tab(self) -> None:
        self.findings_table = QTableWidget(0, 6)
        self.findings_table.setHorizontalHeaderLabels(["Tipo", "Titulo", "Confianza", "Estado", "Evidencia", "Id"])
        self.findings_table.setColumnHidden(5, True)
        self.finding_confirm_button = QPushButton("Confirmar")
        self.finding_reject_button = QPushButton("Rechazar")
        self.finding_confirm_button.clicked.connect(self._confirm_selected_finding)
        self.finding_reject_button.clicked.connect(self._reject_selected_finding)
        actions = QHBoxLayout()
        actions.addWidget(self.finding_confirm_button)
        actions.addWidget(self.finding_reject_button)
        actions.addStretch(1)
        layout = QVBoxLayout(self.findings_tab)
        layout.addLayout(actions)
        layout.addWidget(self.findings_table)

    def _build_reports_tab(self) -> None:
        self.report_start = QLineEdit()
        self.report_start.setPlaceholderText("YYYY-MM-DD")
        self.report_end = QLineEdit()
        self.report_end.setPlaceholderText("YYYY-MM-DD")
        self.report_generate_button = QPushButton("Generar reporte")
        self.report_load_button = QPushButton("Abrir reporte")
        self.report_export_button = QPushButton("Exportar JSON")
        self.report_combo = QComboBox()
        self.report_summary = QLabel("Sin reportes.")
        self.report_summary.setObjectName("MutedLabel")
        self.reports_table = QTableWidget(0, 6)
        self.reports_table.setHorizontalHeaderLabels(["Titulo", "Periodo", "Estado", "Findings", "Warnings", "Id"])
        self.reports_table.setColumnHidden(5, True)
        self.report_items_table = QTableWidget(0, 6)
        self.report_items_table.setHorizontalHeaderLabels(["Titulo", "Seccion", "Tipo", "Indice", "Finding", "Id"])
        self.report_items_table.setColumnHidden(5, True)
        self.report_generate_button.clicked.connect(self._generate_report)
        self.report_load_button.clicked.connect(self._load_selected_report)
        self.report_export_button.clicked.connect(self._export_selected_report)
        controls = QGridLayout()
        controls.addWidget(QLabel("Desde"), 0, 0)
        controls.addWidget(self.report_start, 0, 1)
        controls.addWidget(QLabel("Hasta"), 0, 2)
        controls.addWidget(self.report_end, 0, 3)
        controls.addWidget(self.report_generate_button, 0, 4)
        controls.addWidget(QLabel("Reporte"), 1, 0)
        controls.addWidget(self.report_combo, 1, 1, 1, 3)
        controls.addWidget(self.report_load_button, 1, 4)
        controls.addWidget(self.report_export_button, 1, 5)
        layout = QVBoxLayout(self.reports_tab)
        layout.addLayout(controls)
        layout.addWidget(self.report_summary)
        layout.addWidget(self.reports_table)
        layout.addWidget(self.report_items_table)

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        if not creator_id:
            self._clear_all()
            return
        publications = self.workspace.list_analytics_publications(creator_id)
        cohorts = self.workspace.list_analytics_lab_cohorts(creator_id)
        analyses = self.workspace.list_analytics_lab_analysis_runs(creator_id)
        findings = self.workspace.list_analytics_lab_findings(creator_id)
        reports = self.workspace.list_analytics_lab_reports(creator_id)
        self.overview_counts["publications"].setText(str(len(publications)))
        self.overview_counts["cohorts"].setText(str(len(cohorts)))
        self.overview_counts["analyses"].setText(str(len(analyses)))
        self.overview_counts["findings"].setText(str(len(findings)))
        self._refresh_publications(publications)
        self._refresh_cohorts(cohorts)
        self._refresh_comparisons(publications, cohorts, analyses)
        self._refresh_findings(findings)
        self._refresh_reports(reports)

    def _clear_all(self) -> None:
        for table in (
            self.recent_findings_table,
            self.publications_table,
            self.cohorts_table,
            self.comparison_table,
            self.findings_table,
            self.reports_table,
            self.report_items_table,
        ):
            table.setRowCount(0)
        self.publications_empty.show()
        self.report_summary.setText("Sin reportes.")
        self.comparison_detail.setText("Selecciona una corrida para ver comparaciones.")

    def _refresh_publications(self, publications) -> None:
        self.publications_table.setRowCount(0)
        if not publications:
            self.publications_empty.show()
            return
        self.publications_empty.hide()
        for row, publication in enumerate(publications):
            latest = self.workspace.get_analytics_latest_metrics(publication.id)
            snapshot = next(iter(latest.values()), None)
            warnings = []
            if latest.get("completion_rate") is None:
                warnings.append("missing_completion")
            self.publications_table.insertRow(row)
            values = [
                publication.title,
                publication.platform,
                publication.content_type.value,
                publication.published_at.isoformat(),
                "" if publication.duration_seconds is None else publication.duration_seconds,
                "" if latest.get("views") is None or latest["views"].numeric_value is None else latest["views"].numeric_value,
                "" if latest.get("completion_rate") is None or latest["completion_rate"].numeric_value is None else latest["completion_rate"].numeric_value,
                ", ".join(warnings),
            ]
            for column, value in enumerate(values):
                self.publications_table.setItem(row, column, _item(value))
        self.publications_table.resizeColumnsToContents()

    def _refresh_cohorts(self, cohorts) -> None:
        self.cohorts_table.setRowCount(0)
        self.compare_cohort_combo.clear()
        for row, cohort in enumerate(cohorts):
            self.cohorts_table.insertRow(row)
            values = [
                cohort.name,
                cohort.platform or "",
                cohort.content_type or "",
                len(self.workspace.list_analytics_publications(cohort.creator_id, filters={"platform": cohort.platform})),
                "sistema" if cohort.is_system else "usuario",
                cohort.id,
            ]
            for column, value in enumerate(values):
                item = _item(value)
                self.cohorts_table.setItem(row, column, item)
            self.compare_cohort_combo.addItem(cohort.name, cohort.id)
        self.cohorts_table.resizeColumnsToContents()

    def _refresh_comparisons(self, publications, cohorts, analyses) -> None:
        self.compare_publication_combo.clear()
        for publication in publications:
            self.compare_publication_combo.addItem(publication.title, publication.id)
        self.analysis_combo.clear()
        for analysis in analyses:
            label = f"{analysis.run_type.value} · {analysis.status.value} · {analysis.created_at.isoformat()}"
            self.analysis_combo.addItem(label, analysis.id)
        self.comparison_table.setRowCount(0)
        if self.analysis_combo.count() == 0:
            self.comparison_detail.setText("Selecciona una cohorte y ejecuta una comparacion.")
            return
        self._load_selected_analysis()

    def _refresh_findings(self, findings) -> None:
        self.findings_table.setRowCount(0)
        self.recent_findings_table.setRowCount(0)
        for row, finding in enumerate(findings):
            self.findings_table.insertRow(row)
            values = [
                finding.finding_type.value,
                finding.title,
                finding.confidence_level.value,
                finding.status.value,
                finding.evidence_json[:80],
                finding.id,
            ]
            for column, value in enumerate(values):
                self.findings_table.setItem(row, column, _item(value))
        recent = list(findings[:10])
        for row, finding in enumerate(recent):
            self.recent_findings_table.insertRow(row)
            values = [
                finding.finding_type.value,
                finding.title,
                finding.confidence_level.value,
                finding.status.value,
                finding.cohort_id or "",
            ]
            for column, value in enumerate(values):
                self.recent_findings_table.setItem(row, column, _item(value))
        self.findings_table.resizeColumnsToContents()
        self.recent_findings_table.resizeColumnsToContents()

    def _refresh_reports(self, reports) -> None:
        self.reports_table.setRowCount(0)
        self.report_combo.clear()
        for row, report in enumerate(reports):
            self.reports_table.insertRow(row)
            values = [
                report.title,
                f"{report.period_start} → {report.period_end}",
                report.status.value,
                report.finding_count,
                report.warning_count,
                report.id,
            ]
            for column, value in enumerate(values):
                self.reports_table.setItem(row, column, _item(value))
            self.report_combo.addItem(report.title, report.id)
        if reports:
            self.report_summary.setText(f"{len(reports)} reportes disponibles.")
        else:
            self.report_summary.setText("Sin reportes.")
        self.reports_table.resizeColumnsToContents()

    def _selected_cohort_id(self) -> str | None:
        row = self.cohorts_table.currentRow()
        if row < 0:
            return self.compare_cohort_combo.currentData()
        item = self.cohorts_table.item(row, 5)
        return item.text() if item else None

    def _selected_finding_id(self) -> str | None:
        row = self.findings_table.currentRow()
        if row < 0:
            return None
        item = self.findings_table.item(row, 5)
        return item.text() if item else None

    def _selected_report_id(self) -> str | None:
        row = self.reports_table.currentRow()
        if row < 0:
            return self.report_combo.currentData()
        item = self.reports_table.item(row, 5)
        return item.text() if item else None

    def _create_cohort(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "Analytics Lab", "Selecciona un creador.")
            return
        name = self.cohort_name.text().strip() or "Cohorte manual"
        cohort = self.workspace.create_analytics_lab_cohort(
            creator_id=str(creator_id),
            name=name,
            description=self.cohort_description.text().strip() or "Cohorte creada desde la GUI.",
            platform=self.cohort_platform.text().strip() or None,
            content_type=self.cohort_content_type.text().strip() or None,
        )
        self.cohort_name.clear()
        self.cohort_description.clear()
        self.cohort_platform.clear()
        self.cohort_content_type.clear()
        QMessageBox.information(self, "Analytics Lab", f"Cohorte creada: {cohort.name}")
        self.refresh()

    def _analyze_selected_cohort(self) -> None:
        cohort_id = self._selected_cohort_id()
        if not cohort_id:
            QMessageBox.information(self, "Analytics Lab", "Selecciona una cohorte.")
            return
        run = self.workspace.analyze_analytics_lab_cohort(cohort_id)
        QMessageBox.information(self, "Analytics Lab", f"Corrida completada: {run.status.value}")
        self.refresh()

    def _compare_publication(self) -> None:
        publication_id = self.compare_publication_combo.currentData()
        cohort_id = self.compare_cohort_combo.currentData()
        if not publication_id or not cohort_id:
            QMessageBox.information(self, "Analytics Lab", "Selecciona publicacion y cohorte.")
            return
        run = self.workspace.compare_analytics_publication(str(publication_id), str(cohort_id))
        QMessageBox.information(self, "Analytics Lab", f"Comparacion completada: {run.status.value}")
        self.refresh()

    def _load_selected_analysis(self) -> None:
        run_id = self.analysis_combo.currentData()
        if not run_id:
            return
        detail = self.workspace.get_analytics_lab_analysis_detail(str(run_id))
        comparisons = detail.get("comparisons", [])
        self.comparison_table.setRowCount(0)
        for row, comparison in enumerate(comparisons):
            self.comparison_table.insertRow(row)
            warnings = comparison.get("warning_codes_json", "")
            values = [
                comparison.get("metric_key"),
                comparison.get("observed_value"),
                comparison.get("cohort_mean"),
                comparison.get("cohort_median"),
                comparison.get("percentile"),
                comparison.get("comparison_status"),
                warnings,
            ]
            for column, value in enumerate(values):
                self.comparison_table.setItem(row, column, _item(value))
        run = detail.get("run", {})
        self.comparison_detail.setText(
            f"Corrida {run.get('run_type', '')} | {run.get('status', '')} | publicaciones: {run.get('publication_count', 0)}"
        )
        self.comparison_table.resizeColumnsToContents()

    def _confirm_selected_finding(self) -> None:
        finding_id = self._selected_finding_id()
        if not finding_id:
            return
        self.workspace.confirm_analytics_lab_finding(str(finding_id))
        self.refresh()

    def _reject_selected_finding(self) -> None:
        finding_id = self._selected_finding_id()
        if not finding_id:
            return
        self.workspace.reject_analytics_lab_finding(str(finding_id))
        self.refresh()

    def _generate_report(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "Analytics Lab", "Selecciona un creador.")
            return
        period_start = self.report_start.text().strip()
        period_end = self.report_end.text().strip()
        if not period_start or not period_end:
            QMessageBox.information(self, "Analytics Lab", "Completa el periodo.")
            return
        report = self.workspace.generate_analytics_lab_weekly_report(str(creator_id), period_start, period_end)
        QMessageBox.information(self, "Analytics Lab", f"Reporte generado: {report.status.value}")
        self.refresh()

    def _load_selected_report(self) -> None:
        report_id = self._selected_report_id()
        if not report_id:
            return
        detail = self.workspace.get_analytics_lab_report_detail(str(report_id))
        report = detail.get("report", {})
        items = detail.get("items", [])
        self.report_summary.setText(
            f"{report.get('title', 'Reporte')} | {report.get('status', '')} | findings: {report.get('finding_count', 0)}"
        )
        self.report_items_table.setRowCount(0)
        for row, item in enumerate(items):
            self.report_items_table.insertRow(row)
            values = [
                item.get("title"),
                item.get("section"),
                item.get("item_type"),
                item.get("item_index"),
                item.get("finding_id"),
                item.get("id"),
            ]
            for column, value in enumerate(values):
                self.report_items_table.setItem(row, column, _item(value))
        self.report_items_table.resizeColumnsToContents()

    def _export_selected_report(self) -> None:
        report_id = self._selected_report_id()
        if not report_id:
            QMessageBox.information(self, "Analytics Lab", "Selecciona un reporte.")
            return
        path = self.workspace.export_analytics_lab_report(str(report_id), "json")
        if path is None:
            QMessageBox.information(self, "Analytics Lab", "El reporte no tiene salida disponible.")
            return
        QMessageBox.information(self, "Analytics Lab", f"Reporte exportado en: {path}")
