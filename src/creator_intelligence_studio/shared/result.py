"""Resultado operativo simple."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Contenedor pequeno para exito o error."""

    ok: bool
    value: T | None = None
    error: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def success(cls, value: T | None = None, warnings: tuple[str, ...] = ()) -> "Result[T]":
        return cls(ok=True, value=value, warnings=warnings)

    @classmethod
    def failure(cls, error: str, warnings: tuple[str, ...] = ()) -> "Result[T]":
        return cls(ok=False, error=error, warnings=warnings)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "value": self.value,
            "error": self.error,
            "warnings": list(self.warnings),
        }

