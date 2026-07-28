from __future__ import annotations


def build_alternatives(blocked: bool) -> list[str]:
    return ["lower_risk_alternative", "do_nothing_alternative"] if blocked else ["lower_effort_alternative"]
