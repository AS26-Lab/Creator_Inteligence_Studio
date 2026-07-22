"""Shim de arranque para ejecutar el paquete sin instalarlo."""

from __future__ import annotations

from pathlib import Path
from typing import Final

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SRC_PACKAGE_DIR = _PACKAGE_ROOT.parent / "src" / "creator_intelligence_studio"

if _SRC_PACKAGE_DIR.is_dir():
    __path__.append(str(_SRC_PACKAGE_DIR))  # type: ignore[name-defined]

from ._metadata import APP_NAME, VERSION  # noqa: E402

__all__: Final = ["APP_NAME", "VERSION", "__version__"]

__version__: Final[str] = VERSION

