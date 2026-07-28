"""Vista de Opportunity and Recommendation Engine Foundation."""

from __future__ import annotations

import json
from typing import Any, Callable

from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def _item(value: object) -> QTableWidgetItem:
    return QTableWidgetItem("" if value is None else str(value))


class _RecommendationSectionView(QWidget):
    def __init__(
        self,
        workspace: WorkspaceViewModel,
        *,
        title: str,
        subtitle: str,
        fields: list[str],
        loader: Callable[[WorkspaceViewModel], list[dict[str, Any]]],
        text_mode: bool = False,
    ) -> None:
        super().__init__()
        self.workspace = workspace
        self._fields = fields
        self._loader = loader
        self._text_mode = text_mode
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("MutedLabel")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.table = QTableWidget(0, len(fields))
        self.table.setHorizontalHeaderLabels(fields)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.text if text_mode else self.table)
        self.refresh()

    def refresh(self) -> None:
        service = self.workspace.recommendation_service
        creator_id = self.workspace.selected_creator_id
        if service is None or creator_id is None:
            if self._text_mode:
                self.text.setPlainText("No hay creador activo o el servicio no esta disponible.")
            else:
                self.table.setRowCount(0)
            return
        try:
            rows = self._loader(self.workspace)
        except Exception as exc:  # pragma: no cover - gui fallback
            rows = [{"error": str(exc)}]
        if self._text_mode:
            self.text.setPlainText(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            return
        self.table.setRowCount(0)
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            for column, field in enumerate(self._fields):
                value = row.get(field, "")
                if hasattr(value, "value"):
                    value = value.value
                self.table.setItem(row_index, column, _item(value))
        self.table.resizeColumnsToContents()


class RecommendationRequestsView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Requests",
            subtitle="Solicitudes de recomendacion y su estado.",
            fields=["request_type", "objective_type", "status", "time_horizon", "market_id", "id"],
            loader=lambda ws: [item.to_dict() for item in (ws.recommendation_service.list_requests(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])],
        )


class RecommendationCandidatesView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Prioritized",
            subtitle="Recomendaciones priorizadas con explicacion y riesgo.",
            fields=["title", "recommendation_type", "objective_type", "priority_level", "confidence_level", "freshness_status", "copying_risk"],
            loader=lambda ws: [item.to_dict() for item in (ws.recommendation_service.list_recommendations(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])],
        )


class RecommendationEvidenceView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Evidence",
            subtitle="Cadena de procedencia, hechos, inferencias e hipotesis.",
            fields=["source_domain", "evidence_type", "evidence_strength", "evidence_quality", "supports_recommendation", "description"],
            loader=lambda ws: [
                evidence.to_dict()
                for candidate in (ws.recommendation_service.list_recommendations(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])
                for evidence in (ws.recommendation_service.list_evidence(candidate.id) if ws.recommendation_service else [])
            ],
        )


class RecommendationRisksView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Risks",
            subtitle="Riesgos, mitigaciones y condiciones bloqueantes.",
            fields=["risk_type", "severity", "likelihood", "impact", "blocking", "description"],
            loader=lambda ws: [
                risk.to_dict()
                for candidate in (ws.recommendation_service.list_recommendations(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])
                for risk in (ws.recommendation_service.list_risks(candidate.id) if ws.recommendation_service else [])
            ],
        )


class RecommendationAlternativesView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Alternatives",
            subtitle="Alternativas de menor riesgo, menor esfuerzo o mayor aprendizaje.",
            fields=["alternative_type", "title", "reason", "confidence_level"],
            loader=lambda ws: [
                alternative.to_dict()
                for candidate in (ws.recommendation_service.list_recommendations(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])
                for alternative in (ws.recommendation_service.list_alternatives(candidate.id) if ws.recommendation_service else [])
            ],
        )


class RecommendationReviewView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Review",
            subtitle="Revisiones humanas, decisiones y feedback persistido.",
            fields=["decision", "previous_status", "new_status", "reason", "reviewer"],
            loader=lambda ws: [
                review.to_dict()
                for candidate in (ws.recommendation_service.list_recommendations(ws.selected_creator_id) if ws.recommendation_service and ws.selected_creator_id else [])
                for review in (ws.recommendation_service.list_reviews(candidate.id) if ws.recommendation_service else [])
            ],
        )


class RecommendationHistoryView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="History",
            subtitle="Runs, snapshots, outcomes and reports.",
            fields=["kind", "title", "status", "created_at", "id"],
            loader=lambda ws: self._history_loader(ws),
        )

    def _history_loader(self, ws: WorkspaceViewModel) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if ws.recommendation_service is None or ws.selected_creator_id is None:
            return rows
        for run in ws.recommendation_service.list_runs(ws.selected_creator_id):
            rows.append({"kind": "run", "title": run.request_id or run.context_snapshot_id, "status": run.status.value, "created_at": run.created_at, "id": run.id})
        for report in ws.recommendation_service.list_reports(ws.selected_creator_id):
            rows.append({"kind": "report", "title": report.report_type, "status": "stored", "created_at": report.created_at, "id": report.id})
        return rows


class RecommendationSettingsView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Settings",
            subtitle="Pesos, frescura, umbrales y preferencias de forma comprensible.",
            fields=["key", "value"],
            loader=lambda ws: [
                {"key": "require_human_review", "value": True},
                {"key": "allow_automatic_approval", "value": False},
                {"key": "include_do_not_pursue", "value": True},
                {"key": "include_research_first", "value": True},
                {"key": "show_numeric_scores", "value": False},
            ],
        )


class RecommendationPrivacyView(_RecommendationSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Privacy",
            subtitle="No tokens, no publication, no scraping, no PII de audiencia.",
            fields=["key", "value"],
            loader=lambda ws: [
                {"key": "read_only", "value": True},
                {"key": "no_scraping", "value": True},
                {"key": "no_llm", "value": True},
                {"key": "no_ml", "value": True},
                {"key": "no_remote_execution", "value": True},
            ],
        )


class RecommendationsOverviewView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.title_label = QLabel("Recommendations")
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel("Base trazable para convertir evidencia en recomendaciones revisables sin ejecucion automatica.")
        self.subtitle_label.setObjectName("MutedLabel")
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.tabs = QTabWidget()
        self.requests_view = RecommendationRequestsView(workspace)
        self.candidates_view = RecommendationCandidatesView(workspace)
        self.evidence_view = RecommendationEvidenceView(workspace)
        self.risks_view = RecommendationRisksView(workspace)
        self.alternatives_view = RecommendationAlternativesView(workspace)
        self.review_view = RecommendationReviewView(workspace)
        self.history_view = RecommendationHistoryView(workspace)
        self.settings_view = RecommendationSettingsView(workspace)
        self.privacy_view = RecommendationPrivacyView(workspace)
        self.tabs.addTab(self.requests_view, "Requests")
        self.tabs.addTab(self.candidates_view, "Prioritized")
        self.tabs.addTab(self.evidence_view, "Evidence")
        self.tabs.addTab(self.risks_view, "Risks")
        self.tabs.addTab(self.alternatives_view, "Alternatives")
        self.tabs.addTab(self.review_view, "Review")
        self.tabs.addTab(self.history_view, "History")
        self.tabs.addTab(self.settings_view, "Settings")
        self.tabs.addTab(self.privacy_view, "Privacy")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.summary)
        layout.addWidget(self.tabs)
        self.refresh()

    def refresh(self) -> None:
        service = self.workspace.recommendation_service
        creator_id = self.workspace.selected_creator_id
        if service is None or creator_id is None:
            self.summary.setPlainText("No hay creador activo o el servicio de recomendaciones no esta disponible.")
            return
        overview = service.build_overview(creator_id)
        self.summary.setPlainText(json.dumps(overview, ensure_ascii=False, indent=2, default=str))
        for view in (
            self.requests_view,
            self.candidates_view,
            self.evidence_view,
            self.risks_view,
            self.alternatives_view,
            self.review_view,
            self.history_view,
            self.settings_view,
            self.privacy_view,
        ):
            view.refresh()

