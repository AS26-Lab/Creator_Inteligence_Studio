from __future__ import annotations


def build_explanation(summary: str, *, facts: list[str], inferences: list[str], hypotheses: list[str]) -> dict[str, object]:
    return {"summary": summary, "facts": facts, "inferences": inferences, "hypotheses": hypotheses}
