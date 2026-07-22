"""Construccion de explicaciones tecnicas para ranking de clips."""

from __future__ import annotations

from typing import Any

from .rule_based_ranker import RankedCandidateDraft


def build_candidate_summary(candidate: RankedCandidateDraft) -> str:
    parts = [
        f"actividad multimodal {candidate.quality_score:.2f}",
        f"score original {candidate.source_score:.2f}",
        f"confianza {candidate.source_confidence:.2f}",
        f"duracion {candidate.duration_seconds:.1f} s",
    ]
    if candidate.overlap_penalty > 0:
        parts.append(f"penalizacion por solapamiento {candidate.overlap_penalty:.2f}")
    if candidate.diversity_score < 0.5:
        parts.append(f"diversidad limitada {candidate.diversity_score:.2f}")
    return " | ".join(parts)


def build_candidate_explanation(candidate: RankedCandidateDraft) -> dict[str, Any]:
    evidence = dict(candidate.explanation)
    explanation = {
        "summary": build_candidate_summary(candidate),
        "rank_score": candidate.rank_score,
        "quality_score": candidate.quality_score,
        "diversity_score": candidate.diversity_score,
        "overlap_penalty": candidate.overlap_penalty,
        "duration_score": candidate.duration_score,
        "opening_score": candidate.opening_score,
        "closing_score": candidate.closing_score,
        "speech_score": candidate.speech_score,
        "visual_score": candidate.visual_score,
        "acoustic_score": candidate.acoustic_score,
        "transition_score": candidate.transition_score,
        "novelty_score": candidate.novelty_score,
        "evidence_strength_score": candidate.evidence_strength_score,
        "evidence": evidence,
        "transcript_text": candidate.transcript_text,
        "scene_index": candidate.scene_index,
        "source_window_start": candidate.source_window_start,
        "source_window_end": candidate.source_window_end,
        "warnings": [],
        "notes": [],
    }
    if candidate.duration_seconds < 3.0:
        explanation["warnings"].append("candidato mas corto que la duracion minima recomendada")
    if candidate.overlap_penalty > 0.5:
        explanation["warnings"].append("solapamiento fuerte con candidatos anteriores")
    return explanation
