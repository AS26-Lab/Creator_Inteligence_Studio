"""Planificador de exportacion para ranking de clips."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from creator_intelligence_studio.domain.clip_ranking.entities import ClipRankingRun, RankedClipCandidate


def clip_export_suffix(format_name: str) -> str:
    normalized = format_name.strip().lower()
    if normalized == "json":
        return "json"
    if normalized == "csv":
        return "csv"
    if normalized == "edl":
        return "edl"
    raise ValueError("Formato de exportacion no soportado.")


def build_clip_export(run: ClipRankingRun, candidates: list[RankedClipCandidate], format_name: str) -> tuple[str, str]:
    normalized = format_name.strip().lower()
    if normalized == "json":
        payload = {
            "ranking_run": run.to_dict(),
            "candidates": [candidate.to_dict() for candidate in candidates],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2), "json"
    if normalized == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "rank_position",
            "start_seconds",
            "end_seconds",
            "duration_seconds",
            "candidate_type",
            "rank_score",
            "review_status",
            "rating",
            "tags",
            "note",
        ])
        for candidate in candidates:
            writer.writerow([
                candidate.rank_position,
                f"{candidate.adjusted_start_seconds:.3f}",
                f"{candidate.adjusted_end_seconds:.3f}",
                f"{candidate.duration_seconds:.3f}",
                candidate.candidate_type,
                f"{candidate.rank_score:.4f}",
                candidate.review_status.value,
                "" if candidate.user_rating is None else candidate.user_rating,
                ",".join(candidate.tags),
                candidate.user_note or "",
            ])
        return buffer.getvalue(), "csv"
    if normalized == "edl":
        lines = ["TITLE: Creator Intelligence Studio Clip Plan"]
        for candidate in candidates:
            lines.append(
                f"{candidate.rank_position:03d} {candidate.adjusted_start_seconds:.3f} {candidate.adjusted_end_seconds:.3f} {candidate.candidate_type} | {candidate.user_note or candidate.explanation.get('summary', '')}"
            )
        return "\n".join(lines) + "\n", "edl"
    raise ValueError("Formato de exportacion no soportado.")
