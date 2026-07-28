from __future__ import annotations


def build_report_payload(*, creator_id: str, report_type: str, recommendations: list[dict[str, object]]) -> dict[str, object]:
    return {"creator_id": creator_id, "report_type": report_type, "recommendations": recommendations}
