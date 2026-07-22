"""Infraestructura para herramientas multimedia externas."""

from .ffmpeg_client import build_thumbnail_path, generate_initial_thumbnail
from .ffmpeg_locator import MediaToolLocator, discover_media_tools
from .ffprobe_client import FFprobeClient, FFprobeError, FFprobeTimeoutError
from .parsers import parse_ffprobe_json

__all__ = [
    "FFprobeClient",
    "FFprobeError",
    "FFprobeTimeoutError",
    "MediaToolLocator",
    "build_thumbnail_path",
    "discover_media_tools",
    "generate_initial_thumbnail",
    "parse_ffprobe_json",
]
