"""Vista general de Market and Trend Intelligence."""

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


class MarketSectionView(QWidget):
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
        self.table = QTableWidget(0, len(fields))
        self.table.setHorizontalHeaderLabels(fields)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.text if self._text_mode else self.table)
        self.refresh()

    def refresh(self) -> None:
        try:
            rows = self._loader(self.workspace)
        except Exception as exc:  # pragma: no cover - gui fallback
            rows = [{"error": str(exc)}]
        if self._text_mode:
            self.text.setPlainText(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            return
        self.table.setRowCount(0)
        if not rows:
            return
        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            for column, field in enumerate(self._fields):
                value = row.get(field, "")
                display = value.value if hasattr(value, "value") else value
                self.table.setItem(row_index, column, QTableWidgetItem("" if display is None else str(display)))
        self.table.resizeColumnsToContents()


class MarketOverviewView(QWidget):
    def __init__(self, workspace: WorkspaceViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.title_label = QLabel("Market and Trend Intelligence")
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel("Evidencia, tendencias, patrones y oportunidades revisables sin automatizar recomendaciones finales.")
        self.subtitle_label.setObjectName("MutedLabel")
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.tabs = QTabWidget()
        self.sources_view = MarketSourcesView(workspace)
        self.competitor_view = CompetitorLibraryView(workspace)
        self.external_content_view = ExternalContentView(workspace)
        self.trend_signals_view = TrendSignalsView(workspace)
        self.topic_landscape_view = TopicLandscapeView(workspace)
        self.format_patterns_view = FormatPatternsView(workspace)
        self.saturation_view = SaturationView(workspace)
        self.creator_fit_view = CreatorFitView(workspace)
        self.opportunity_candidates_view = OpportunityCandidatesView(workspace)
        self.research_history_view = ResearchHistoryView(workspace)
        self.market_privacy_view = MarketPrivacyView(workspace)
        self.tabs.addTab(self.sources_view, "Sources")
        self.tabs.addTab(self.competitor_view, "Competitors")
        self.tabs.addTab(self.external_content_view, "External Content")
        self.tabs.addTab(self.trend_signals_view, "Trend Signals")
        self.tabs.addTab(self.topic_landscape_view, "Topic Landscape")
        self.tabs.addTab(self.format_patterns_view, "Format Patterns")
        self.tabs.addTab(self.saturation_view, "Saturation")
        self.tabs.addTab(self.creator_fit_view, "Creator Fit")
        self.tabs.addTab(self.opportunity_candidates_view, "Opportunities")
        self.tabs.addTab(self.research_history_view, "Research History")
        self.tabs.addTab(self.market_privacy_view, "Privacy")
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.summary)
        layout.addWidget(self.tabs)
        self.refresh()

    def refresh(self) -> None:
        market_service = self.workspace.market_service
        if market_service is None or self.workspace.selected_creator_id is None:
            self.summary.setPlainText("No hay creador activo o el servicio de mercado no esta disponible.")
            return
        overview = market_service.build_overview(self.workspace.selected_creator_id)
        self.summary.setPlainText(json.dumps([row.to_dict() for row in overview], ensure_ascii=False, indent=2, default=lambda value: value.value if hasattr(value, "value") else str(value)))
        for view in (
            self.sources_view,
            self.competitor_view,
            self.external_content_view,
            self.trend_signals_view,
            self.topic_landscape_view,
            self.format_patterns_view,
            self.saturation_view,
            self.creator_fit_view,
            self.opportunity_candidates_view,
            self.research_history_view,
            self.market_privacy_view,
        ):
            view.refresh()


class MarketSourcesView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Market Sources",
            subtitle="Fuentes manuales y oficiales permitidas.",
            fields=["name", "source_type", "platform", "access_method", "trust_level", "permission_status", "enabled"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_market_sources(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class CompetitorLibraryView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Competitor Library",
            subtitle="Referentes, comparables y anti-referencias revisables.",
            fields=["market_entity_id", "relationship_type", "approval_status", "monitoring_status", "copying_risk_level", "relevance_reason"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_competitor_profiles(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class ExternalContentView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="External Content",
            subtitle="Publicaciones externas observadas o importadas manualmente.",
            fields=["platform", "content_type", "title", "published_at", "language", "region", "source_url"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_external_content_items(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class TrendSignalsView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Trend Signals",
            subtitle="Señales de crecimiento, declive, persistencia y saturación.",
            fields=["platform", "signal_type", "direction", "lifecycle_stage", "sample_size", "confidence_level", "status"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_trend_signals(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class TopicLandscapeView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Topic Landscape",
            subtitle="Mapa de mercados y subtemas definidos por el creador.",
            fields=["canonical_name", "display_name", "market_id", "topic_type", "status", "description"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_market_topics(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class FormatPatternsView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Format Patterns",
            subtitle="Patrones de formato observados sin copiar identidades ni assets completos.",
            fields=["canonical_name", "pattern_type", "sample_size", "supporting_count", "contradicting_count", "confidence_level"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_patterns(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class SaturationView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Saturation",
            subtitle="Señales de saturación y presión competitiva.",
            fields=["platform", "signal_type", "saturation_level", "sample_size", "direction", "confidence_level"],
            loader=lambda ws: [
                {
                    "platform": item.platform.value if hasattr(item.platform, "value") else item.platform,
                    "signal_type": item.signal_type.value if hasattr(item.signal_type, "value") else item.signal_type,
                    "saturation_level": item.saturation_level.value if hasattr(item.saturation_level, "value") else item.saturation_level,
                    "sample_size": item.sample_size,
                    "direction": item.direction.value if hasattr(item.direction, "value") else item.direction,
                    "confidence_level": item.confidence_level.value if hasattr(item.confidence_level, "value") else item.confidence_level,
                }
                for item in (ws.market_service.list_trend_signals(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])
            ],
        )


class CreatorFitView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Creator Fit",
            subtitle="Compatibilidad de las señales externas con la identidad del creador.",
            fields=["target_type", "target_id", "overall_fit", "brand_fit", "audience_fit", "copying_risk", "confidence_level"],
            loader=lambda ws: [
                {
                    "target_type": item.target_type,
                    "target_id": item.target_id,
                    "overall_fit": item.overall_fit,
                    "brand_fit": item.brand_fit,
                    "audience_fit": item.audience_fit,
                    "copying_risk": item.copying_risk,
                    "confidence_level": item.confidence_level.value if hasattr(item.confidence_level, "value") else item.confidence_level,
                }
                for item in (ws.market_service.list_fit_evaluations(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])
            ],
        )


class OpportunityCandidatesView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Opportunity Candidates",
            subtitle="Candidatos revisables para la siguiente fase.",
            fields=["title", "opportunity_type", "urgency", "freshness_status", "creator_fit", "copying_risk", "status"],
            loader=lambda ws: [item.to_dict() for item in (ws.market_service.list_opportunity_candidates(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])],
        )


class ResearchHistoryView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Research History",
            subtitle="Consultas, corridas y snapshots historicos.",
            fields=["id", "platform", "query_text", "status", "created_at"],
            loader=lambda ws: [
                {"id": item.id, "platform": item.platform, "query_text": item.query_text, "status": item.status, "created_at": item.created_at}
                for item in (ws.market_service.list_research_queries(ws.selected_creator_id) if ws.market_service and ws.selected_creator_id else [])
            ],
        )


class MarketPrivacyView(MarketSectionView):
    def __init__(self, workspace: WorkspaceViewModel) -> None:
        super().__init__(
            workspace,
            title="Privacy",
            subtitle="Garantias de solo lectura, sin scraping ni escritura remota.",
            fields=["item", "value"],
            loader=lambda ws: [
                {"item": "Read-only", "value": "No publica, no sube, no edita ni borra contenido remoto."},
                {"item": "Sources", "value": "Fuentes manuales y APIs oficiales permitidas."},
                {"item": "Data", "value": "Evidencia, tendencias, patrones, fit y oportunidades revisables."},
                {"item": "Limits", "value": "No scraping, no Research API, no LLM, no ML."},
            ],
        )
