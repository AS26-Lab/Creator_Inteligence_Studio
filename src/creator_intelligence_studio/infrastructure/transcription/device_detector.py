"""Deteccion del backend de transcripcion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionBackendInfo

from .cuda_runtime_loader import discover_cuda_runtime_locations
from .faster_whisper_engine import FasterWhisperEngine
from .model_manager import TranscriptionModelManager


@dataclass(frozen=True, slots=True)
class TranscriptionDeviceDetector:
    """Coordina la verificacion del backend y del caché de modelos."""

    model_manager: TranscriptionModelManager

    def verify_backend(self) -> TranscriptionBackendInfo:
        engine = FasterWhisperEngine(self.model_manager)
        return engine.verify_backend()

    def verify_model_cache(self, model_name: str):
        return self.model_manager.get_model_status(model_name)


