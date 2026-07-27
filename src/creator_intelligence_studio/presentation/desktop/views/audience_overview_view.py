"""Vista principal del modelo de audiencia."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
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


class AudienceOverviewView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace

        self.refresh_button = QPushButton("Actualizar")
        self.build_button = QPushButton("Construir modelo")
        self.refresh_button.clicked.connect(self.refresh)
        self.build_button.clicked.connect(self._build_model)

        self.tabs = QTabWidget()
        self.overview_tab = QWidget()
        self.signals_tab = QWidget()
        self.new_returning_tab = QWidget()
        self.segments_tab = QWidget()
        self.affinities_tab = QWidget()
        self.journeys_tab = QWidget()
        self.platform_roles_tab = QWidget()
        self.content_roles_tab = QWidget()
        self.contradictions_tab = QWidget()
        self.history_tab = QWidget()

        for widget, label in [
            (self.overview_tab, "Overview"),
            (self.signals_tab, "Signals"),
            (self.new_returning_tab, "New vs Returning"),
            (self.segments_tab, "Segments"),
            (self.affinities_tab, "Affinities"),
            (self.journeys_tab, "Journeys"),
            (self.platform_roles_tab, "Platform Roles"),
            (self.content_roles_tab, "Content Roles"),
            (self.contradictions_tab, "Contradictions"),
            (self.history_tab, "History"),
        ]:
            self.tabs.addTab(widget, label)

        self._build_overview_tab()
        self._build_signals_tab()
        self._build_new_returning_tab()
        self._build_segments_tab()
        self._build_affinities_tab()
        self._build_journeys_tab()
        self._build_platform_roles_tab()
        self._build_content_roles_tab()
        self._build_contradictions_tab()
        self._build_history_tab()

        title = QLabel("Audience Model")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Modelo local, trazable y agregado de audiencia observada.")
        subtitle.setObjectName("MutedLabel")
        self.creator_label = QLabel("Creador activo: ninguno")
        self.creator_label.setObjectName("MutedLabel")
        self.status_label = QLabel("Sin perfil construido.")
        self.status_label.setObjectName("MutedLabel")

        header = QHBoxLayout()
        header.addWidget(self.creator_label)
        header.addWidget(self.status_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        header.addWidget(self.build_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(header)
        layout.addWidget(self.tabs)

        self.refresh()

    def _build_overview_tab(self) -> None:
        self.profile_confidence = QLabel("-")
        self.profile_period = QLabel("-")
        self.available_platforms = QLabel("-")
        self.available_signals = QLabel("-")
        self.missing_signals = QLabel("-")
        self.new_returning_summary = QLabel("-")
        self.acquisition_summary = QLabel("-")
        self.conversion_summary = QLabel("-")
        self.loyalty_summary = QLabel("-")
        self.warnings_summary = QLabel("-")
        grid = QGridLayout(self.overview_tab)
        labels = [
            ("Profile confidence", self.profile_confidence),
            ("Period", self.profile_period),
            ("Available platforms", self.available_platforms),
            ("Available signals", self.available_signals),
            ("Missing signals", self.missing_signals),
            ("New/Returning", self.new_returning_summary),
            ("Acquisition", self.acquisition_summary),
            ("Conversion", self.conversion_summary),
            ("Loyalty", self.loyalty_summary),
            ("Warnings", self.warnings_summary),
        ]
        for index, (label, value) in enumerate(labels):
            row = index // 2
            col = (index % 2) * 2
            grid.addWidget(QLabel(label), row, col)
            grid.addWidget(value, row, col + 1)

    def _build_signals_tab(self) -> None:
        self.signals_empty = EmptyStateWidget("Sin señales", "Construye el modelo para ver señales normalizadas.")
        self.signals_table = QTableWidget(0, 9)
        self.signals_table.setHorizontalHeaderLabels(["Signal", "Platform", "Period", "Value", "Unit", "Dimensions", "Source", "Quality", "Warning"])
        layout = QVBoxLayout(self.signals_tab)
        layout.addWidget(self.signals_empty)
        layout.addWidget(self.signals_table)

    def _build_new_returning_tab(self) -> None:
        self.new_returning_text = QLabel("Sin datos.")
        self.new_returning_text.setObjectName("MutedLabel")
        layout = QVBoxLayout(self.new_returning_tab)
        layout.addWidget(self.new_returning_text)

    def _build_segments_tab(self) -> None:
        self.segments_table = QTableWidget(0, 10)
        self.segments_table.setHorizontalHeaderLabels(["Name", "Type", "Definition", "Scope", "Platform", "Sample", "Evidence", "Contradictions", "Confidence", "Status"])
        layout = QVBoxLayout(self.segments_tab)
        layout.addWidget(self.segments_table)

    def _build_affinities_tab(self) -> None:
        self.affinities_table = QTableWidget(0, 7)
        self.affinities_table.setHorizontalHeaderLabels(["Target", "Type", "Basis", "Support", "Contradict", "Confidence", "Status"])
        layout = QVBoxLayout(self.affinities_tab)
        layout.addWidget(self.affinities_table)

    def _build_journeys_tab(self) -> None:
        self.journeys_table = QTableWidget(0, 6)
        self.journeys_table.setHorizontalHeaderLabels(["Entry", "Steps", "Possible conversion", "Evidence", "Limitations", "Review"])
        layout = QVBoxLayout(self.journeys_tab)
        layout.addWidget(self.journeys_table)

    def _build_platform_roles_tab(self) -> None:
        self.platform_roles_table = QTableWidget(0, 8)
        self.platform_roles_table.setHorizontalHeaderLabels(["Platform", "Discovery", "Depth", "Conversion", "Loyalty", "Community", "Evidence", "Confidence"])
        layout = QVBoxLayout(self.platform_roles_tab)
        layout.addWidget(self.platform_roles_table)

    def _build_content_roles_tab(self) -> None:
        self.content_roles_table = QTableWidget(0, 6)
        self.content_roles_table.setHorizontalHeaderLabels(["Publication", "Role", "Metrics", "Evidence", "Warnings", "Id"])
        self.content_roles_table.setColumnHidden(5, True)
        layout = QVBoxLayout(self.content_roles_tab)
        layout.addWidget(self.content_roles_table)

    def _build_contradictions_tab(self) -> None:
        self.contradictions_table = QTableWidget(0, 5)
        self.contradictions_table.setHorizontalHeaderLabels(["Conflict", "Period", "Platform", "Possible explanation", "Status"])
        layout = QVBoxLayout(self.contradictions_tab)
        layout.addWidget(self.contradictions_table)

    def _build_history_tab(self) -> None:
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Version", "Status", "Created", "Fingerprint", "Summary"])
        layout = QVBoxLayout(self.history_tab)
        layout.addWidget(self.history_table)

    def _build_model(self) -> None:
        creator_id = self.workspace.selected_creator_id
        if not creator_id:
            QMessageBox.information(self, "Audience Model", "Selecciona un creador.")
            return
        result = self.workspace.build_audience_model(str(creator_id))
        QMessageBox.information(self, "Audience Model", f"Modelo construido: {result.run.status.value}")
        self.refresh()

    def refresh(self) -> None:
        creator_id = self.workspace.selected_creator_id
        self.creator_label.setText(f"Creador activo: {creator_id or 'ninguno'}")
        if not creator_id:
            self._clear()
            return
        profile = self.workspace.get_audience_profile(str(creator_id))
        signals = self.workspace.list_audience_signals(str(creator_id))
        segments = self.workspace.list_audience_segments(str(creator_id))
        affinities = self.workspace.list_audience_affinities(str(creator_id))
        journeys = self.workspace.list_audience_journeys(str(creator_id))
        history = self.workspace.list_audience_profile_history(str(creator_id))
        if profile is None:
            self.status_label.setText("Sin perfil construido.")
        else:
            self.status_label.setText(f"Perfil v{profile.profile_version} | {profile.status.value} | {profile.confidence_level.value}")
        self.profile_confidence.setText("" if profile is None else profile.confidence_level.value)
        self.profile_period.setText("" if not history else f"v{history[0].profile_version}")
        platforms = sorted({signal.platform for signal in signals})
        self.available_platforms.setText(", ".join(platforms) if platforms else "-")
        self.available_signals.setText(str(len(signals)))
        missing = sorted({signal.signal_key for signal in signals if signal.quality_status == "metric_not_available"})
        self.missing_signals.setText(", ".join(missing) if missing else "-")
        self.new_returning_summary.setText(self._build_new_returning_summary(signals))
        self.acquisition_summary.setText(self._build_acquisition_summary(signals))
        self.conversion_summary.setText(self._build_conversion_summary(signals))
        self.loyalty_summary.setText(self._build_loyalty_summary(signals))
        warnings = sorted({signal.quality_status for signal in signals if signal.quality_status not in {"ok", "completed"}})
        self.warnings_summary.setText(", ".join(warnings) if warnings else "-")
        self._refresh_signals(signals)
        self._refresh_segments(segments)
        self._refresh_affinities(affinities)
        self._refresh_journeys(journeys)
        self._refresh_platform_roles(str(creator_id))
        self._refresh_content_roles(str(creator_id))
        self._refresh_contradictions(signals)
        self._refresh_history(history)

    def _clear(self) -> None:
        for table in (
            self.signals_table,
            self.segments_table,
            self.affinities_table,
            self.journeys_table,
            self.platform_roles_table,
            self.content_roles_table,
            self.contradictions_table,
            self.history_table,
        ):
            table.setRowCount(0)

    def _build_new_returning_summary(self, signals) -> str:
        new_values = [float(signal.numeric_value) for signal in signals if signal.signal_key == "new_viewers" and signal.numeric_value is not None]
        returning_values = [float(signal.numeric_value) for signal in signals if signal.signal_key == "returning_viewers" and signal.numeric_value is not None]
        if not new_values and not returning_values:
            return "metric_not_available"
        return f"new={sum(new_values):.0f} | returning={sum(returning_values):.0f}" if returning_values else f"new={sum(new_values):.0f} | returning=metric_not_available"

    def _build_acquisition_summary(self, signals) -> str:
        keys = ("search_views", "suggested_views", "browse_views", "shorts_feed_views", "external_views", "direct_views")
        values = {key: sum(float(signal.numeric_value or 0) for signal in signals if signal.signal_key == key) for key in keys}
        active = [f"{key}={int(value)}" for key, value in values.items() if value]
        return ", ".join(active) if active else "-"

    def _build_conversion_summary(self, signals) -> str:
        keys = ("subscribers_gained", "followers_gained", "profile_visits", "traffic_to_longform")
        values = {key: sum(float(signal.numeric_value or 0) for signal in signals if signal.signal_key == key) for key in keys}
        active = [f"{key}={int(value)}" for key, value in values.items() if value]
        return ", ".join(active) if active else "-"

    def _build_loyalty_summary(self, signals) -> str:
        values = [float(signal.numeric_value or 0) for signal in signals if signal.signal_key == "returning_viewers"]
        if not values:
            return "metric_not_available"
        return f"returning_viewers={int(sum(values))}"

    def _refresh_signals(self, signals) -> None:
        self.signals_table.setRowCount(0)
        if not signals:
            self.signals_empty.show()
            return
        self.signals_empty.hide()
        for row, signal in enumerate(signals):
            self.signals_table.insertRow(row)
            values = [
                signal.signal_key,
                signal.platform,
                f"{signal.period_start or ''} -> {signal.period_end or ''}",
                signal.numeric_value if signal.numeric_value is not None else signal.text_value,
                signal.unit or "",
                signal.dimensions_json,
                signal.source_type,
                signal.quality_status,
                signal.warning_codes_json,
            ]
            for column, value in enumerate(values):
                self.signals_table.setItem(row, column, _item(value))
        self.signals_table.resizeColumnsToContents()

    def _refresh_segments(self, segments) -> None:
        self.segments_table.setRowCount(0)
        for row, segment in enumerate(segments):
            self.segments_table.insertRow(row)
            values = [
                segment.name,
                segment.segment_type.value,
                segment.description,
                segment.scope.value,
                segment.platform or "",
                segment.supporting_signal_count,
                segment.topic or "",
                segment.contradicting_signal_count,
                segment.confidence_level.value,
                segment.status.value,
            ]
            for column, value in enumerate(values):
                self.segments_table.setItem(row, column, _item(value))
        self.segments_table.resizeColumnsToContents()

    def _refresh_affinities(self, affinities) -> None:
        self.affinities_table.setRowCount(0)
        for row, affinity in enumerate(affinities):
            self.affinities_table.insertRow(row)
            values = [
                f"{affinity.target_key}:{affinity.target_value}",
                affinity.affinity_type,
                affinity.segment_id or "",
                affinity.supporting_example_count,
                affinity.contradicting_example_count,
                affinity.confidence_level.value,
                affinity.status.value,
            ]
            for column, value in enumerate(values):
                self.affinities_table.setItem(row, column, _item(value))
        self.affinities_table.resizeColumnsToContents()

    def _refresh_journeys(self, journeys) -> None:
        self.journeys_table.setRowCount(0)
        for row, journey in enumerate(journeys):
            self.journeys_table.insertRow(row)
            evidence = json.loads(journey.evidence_json) if journey.evidence_json else {}
            limitations = json.loads(journey.limitations_json) if journey.limitations_json else []
            steps = self.workspace.list_audience_journey_steps(journey.id)
            values = [
                f"{journey.entry_platform or ''} -> {journey.next_step_type or ''}",
                str(len(steps)),
                journey.conversion_type or "",
                json.dumps(evidence, ensure_ascii=False),
                ", ".join(limitations) if limitations else "",
                journey.status.value,
            ]
            for column, value in enumerate(values):
                self.journeys_table.setItem(row, column, _item(value))
        self.journeys_table.resizeColumnsToContents()

    def _refresh_platform_roles(self, creator_id: str) -> None:
        roles = self.workspace.list_audience_platform_roles(creator_id)
        self.platform_roles_table.setRowCount(0)
        for row, (platform, payload) in enumerate(sorted(roles.items())):
            self.platform_roles_table.insertRow(row)
            values = [
                platform,
                payload.get("discovery", ""),
                payload.get("depth", ""),
                payload.get("conversion", ""),
                payload.get("loyalty", ""),
                payload.get("community", ""),
                ", ".join(payload.get("evidence", [])),
                payload.get("confidence", ""),
            ]
            for column, value in enumerate(values):
                self.platform_roles_table.setItem(row, column, _item(value))
        self.platform_roles_table.resizeColumnsToContents()

    def _refresh_content_roles(self, creator_id: str) -> None:
        roles = self.workspace.list_audience_content_roles(creator_id)
        publications = self.workspace.list_analytics_publications(creator_id)
        self.content_roles_table.setRowCount(0)
        for row, publication in enumerate(publications):
            payload = roles.get(publication.id, {})
            self.content_roles_table.insertRow(row)
            values = [
                publication.title,
                payload.get("role", ""),
                json.dumps(payload.get("metrics", {}), ensure_ascii=False),
                ", ".join(payload.get("evidence", [])),
                ", ".join(payload.get("warnings", [])),
                publication.id,
            ]
            for column, value in enumerate(values):
                self.content_roles_table.setItem(row, column, _item(value))
        self.content_roles_table.resizeColumnsToContents()

    def _refresh_contradictions(self, signals) -> None:
        self.contradictions_table.setRowCount(0)
        platform_conflicts = []
        for signal in signals:
            if signal.signal_key == "completion_rate" and signal.numeric_value is not None and signal.numeric_value < 0.25:
                platform_conflicts.append((signal.platform, "high_views_low_completion"))
        for row, (platform, conflict) in enumerate(platform_conflicts):
            self.contradictions_table.insertRow(row)
            values = [conflict, "-", platform, "mixed_window or outlier_dominated", "unresolved"]
            for column, value in enumerate(values):
                self.contradictions_table.setItem(row, column, _item(value))
        self.contradictions_table.resizeColumnsToContents()

    def _refresh_history(self, history) -> None:
        self.history_table.setRowCount(0)
        for row, snapshot in enumerate(history):
            self.history_table.insertRow(row)
            values = [
                snapshot.profile_version,
                snapshot.status.value,
                snapshot.created_at.isoformat(),
                snapshot.source_fingerprint[:16],
                snapshot.snapshot_json[:120],
            ]
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, _item(value))
        self.history_table.resizeColumnsToContents()
