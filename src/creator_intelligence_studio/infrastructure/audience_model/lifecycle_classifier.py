"""Clasificador local de ciclo de vida."""

from __future__ import annotations

from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudiencePlatformRole
from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudienceContentRole
from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudiencePlatformRole


def classify_platform_role(*, discovery: float, depth: float, conversion: float, loyalty: float, community: float, experimentation: float) -> AudiencePlatformRole:
    scores = {
        AudiencePlatformRole.DISCOVERY: discovery,
        AudiencePlatformRole.DEPTH: depth,
        AudiencePlatformRole.CONVERSION: conversion,
        AudiencePlatformRole.LOYALTY: loyalty,
        AudiencePlatformRole.COMMUNITY: community,
        AudiencePlatformRole.EXPERIMENTATION: experimentation,
    }
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered or ordered[0][1] <= 0:
        return AudiencePlatformRole.UNCLEAR
    if len(ordered) > 1 and ordered[0][1] - ordered[1][1] < 0.15:
        return AudiencePlatformRole.MIXED
    return ordered[0][0]


def classify_content_role(*, acquisition: float, engagement: float, conversion: float, loyalty: float, authority: float, community: float, bridge: float) -> AudienceContentRole:
    scores = {
        AudienceContentRole.ACQUISITION: acquisition,
        AudienceContentRole.ENGAGEMENT: engagement,
        AudienceContentRole.CONVERSION: conversion,
        AudienceContentRole.LOYALTY: loyalty,
        AudienceContentRole.AUTHORITY: authority,
        AudienceContentRole.COMMUNITY: community,
        AudienceContentRole.BRIDGE_CONTENT: bridge,
    }
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered or ordered[0][1] <= 0:
        return AudienceContentRole.UNCLEAR
    if len(ordered) > 1 and ordered[0][1] - ordered[1][1] < 0.15:
        return AudienceContentRole.UNCLEAR
    return ordered[0][0]

