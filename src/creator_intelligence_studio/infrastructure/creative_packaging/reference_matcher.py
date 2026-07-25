"""Emparejamiento determinista de referencias."""

from __future__ import annotations

from collections.abc import Iterable


def match_reference_assets(
    references: Iterable[dict[str, object]],
    *,
    reference_type: str | None = None,
    purpose: str | None = None,
    platform: str | None = None,
) -> list[dict[str, object]]:
    result = []
    for reference in references:
        if reference_type and reference.get("reference_type") != reference_type:
            continue
        if purpose and purpose not in str(reference.get("reference_purpose") or ""):
            continue
        if platform and reference.get("platform") not in (None, platform):
            continue
        result.append(dict(reference))
    return result

