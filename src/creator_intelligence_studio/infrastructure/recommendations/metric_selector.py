from __future__ import annotations


def select_metrics(objective: str, platform: str) -> list[str]:
    if platform == "tiktok" and objective in {"watch_time", "retention", "completion"}:
        return ["public_views", "manual_import_required"]
    return ["views"]
