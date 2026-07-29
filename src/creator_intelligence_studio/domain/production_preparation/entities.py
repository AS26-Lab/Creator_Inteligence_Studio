"""Entidades persistidas para production preparation."""

from __future__ import annotations

from typing import Any


class ProductionRecord:
    """Registro generico con acceso por atributos y serializacion estable."""

    def __init__(self, **data: Any) -> None:
        self.__dict__.update(data)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, value in self.__dict__.items():
            payload[key] = _serialize(value)
        return payload

    def __repr__(self) -> str:  # pragma: no cover - depuracion
        return f"ProductionRecord({self.to_dict()!r})"


def _serialize(value: Any) -> object:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value

