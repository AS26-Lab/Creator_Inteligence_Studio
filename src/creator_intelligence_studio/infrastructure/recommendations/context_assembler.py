from __future__ import annotations

from creator_intelligence_studio.domain.recommendations.services import build_recommendation_fingerprint


def assemble_context(payload: object) -> dict[str, object]:
    return {"source_fingerprint": build_recommendation_fingerprint(payload), "payload": payload}
