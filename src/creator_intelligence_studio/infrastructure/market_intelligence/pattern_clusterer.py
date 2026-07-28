"""Agrupacion simple de patrones observados."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import json_loads, normalize_text


def cluster_patterns(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        topics = json_loads(item.get("topic_labels_json"), [])
        formats = json_loads(item.get("format_labels_json"), [])
        topic_key = normalize_text(topics[0] if topics else item.get("title") or "").lower()
        format_key = normalize_text(formats[0] if formats else item.get("content_type") or "").lower()
        clusters[(topic_key, format_key)].append(item)
    results: list[dict[str, Any]] = []
    for (topic_key, format_key), cluster_items in clusters.items():
        results.append(
            {
                "canonical_name": topic_key or format_key or "pattern",
                "pattern_type": "format" if format_key else "topic",
                "sample_size": len(cluster_items),
                "supporting_count": len(cluster_items),
                "contradicting_count": 0,
                "items": cluster_items,
            }
        )
    return results

