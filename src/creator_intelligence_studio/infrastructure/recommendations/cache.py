from __future__ import annotations


class RecommendationCache:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value: object) -> None:
        self._store[key] = value
