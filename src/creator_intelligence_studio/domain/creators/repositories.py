"""Contratos de persistencia para creadores."""

from __future__ import annotations

from typing import Protocol

from creator_intelligence_studio.domain.creators.entities import Creator


class CreatorRepository(Protocol):
    """Operaciones para almacenar creadores."""

    def create(self, creator: Creator) -> Creator: ...

    def list(self) -> list[Creator]: ...

    def get_by_id(self, creator_id: str) -> Creator | None: ...

    def get_by_slug(self, slug: str) -> Creator | None: ...

    def archive(self, creator_id: str) -> Creator | None: ...

