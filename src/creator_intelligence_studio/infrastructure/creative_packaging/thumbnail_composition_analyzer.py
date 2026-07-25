"""Analisis local y explicable de miniaturas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.domain.creative_packaging.thumbnail_types import (
    ThumbnailAnalysisMetric,
    ThumbnailAnalysisResult,
    ThumbnailReviewStatus,
)


def _luma(frame: np.ndarray) -> np.ndarray:
    rgb = frame.astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def analyze_thumbnail_pixels(
    pixels: np.ndarray | None,
    *,
    width: int | None,
    height: int | None,
    platform: str | None = None,
    brand_palette: list[str] | None = None,
    approved_patterns: list[dict[str, object]] | None = None,
    rejected_patterns: list[dict[str, object]] | None = None,
) -> ThumbnailAnalysisResult:
    if pixels is None or width is None or height is None:
        metrics = (
            ThumbnailAnalysisMetric("width", float(width) if width is not None else None, None, "px", "high", ("missing_thumbnail",)),
            ThumbnailAnalysisMetric("height", float(height) if height is not None else None, None, "px", "high", ("missing_thumbnail",)),
        )
        return ThumbnailAnalysisResult(
            dimensions=(width or 0, height or 0) if width and height else None,
            metrics=metrics,
            warnings=("missing_thumbnail",),
            recommendation_status=ThumbnailReviewStatus.INSUFFICIENT_CONTEXT.value,
            summary="Miniatura no disponible para analisis.",
        )
    luma = _luma(pixels)
    brightness = float(np.mean(luma) / 255.0)
    contrast = float(np.std(luma) / 255.0)
    gx = np.abs(np.diff(luma, axis=1))
    gy = np.abs(np.diff(luma, axis=0))
    sharpness = float((np.mean(gx) + np.mean(gy)) / 255.0)
    hist, _ = np.histogram(luma, bins=32, range=(0.0, 255.0), density=True)
    entropy = float(-np.sum(hist * np.log2(hist + 1e-9)))
    edge_density = float(np.mean((gx > np.percentile(gx, 75)) if gx.size else np.array([0.0])) + np.mean((gy > np.percentile(gy, 75)) if gy.size else np.array([0.0]))) / 2.0 if (gx.size and gy.size) else 0.0
    thirds = [
        luma[: height // 3 or 1, : width // 3 or 1],
        luma[: height // 3 or 1, width // 3 : 2 * width // 3 or width],
        luma[: height // 3 or 1, 2 * width // 3 :],
        luma[height // 3 : 2 * height // 3 or height, : width // 3 or 1],
        luma[height // 3 : 2 * height // 3 or height, width // 3 : 2 * width // 3 or width],
        luma[height // 3 : 2 * height // 3 or height, 2 * width // 3 :],
        luma[2 * height // 3 :, : width // 3 or 1],
        luma[2 * height // 3 :, width // 3 : 2 * width // 3 or width],
        luma[2 * height // 3 :, 2 * width // 3 :],
    ]
    region_means = [float(np.mean(region) / 255.0) for region in thirds if region.size]
    dominant_region_count = len([value for value in region_means if value >= brightness])
    text_region_estimate = 1.0 if edge_density > 0.2 and contrast > 0.1 else 0.0
    subject_centrality = float(np.mean(luma[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4]) / 255.0)
    safe_area_warnings = []
    if platform in {"youtube_short", "instagram_reel", "tiktok"} and (width / height) > 1.2:
        safe_area_warnings.append("wrong_aspect_ratio")
    palette_similarity = 0.0
    if brand_palette:
        palette_similarity = min(1.0, 0.15 * len(brand_palette))
    composition_similarity = 0.0
    if approved_patterns:
        composition_similarity = min(1.0, 0.1 * len(approved_patterns))
    similarity_warning = "copying_risk" if rejected_patterns else None
    visual_density = min(1.0, float((edge_density + contrast + sharpness) / 3.0))
    probable_focus_region = "center" if subject_centrality >= brightness else "periphery"
    warnings = tuple(
        flag
        for flag in [
            *safe_area_warnings,
            similarity_warning,
            "low_contrast" if contrast < 0.08 else None,
            "blurry_frame" if sharpness < 0.04 else None,
            "too_many_elements_estimate" if dominant_region_count > 5 else None,
            "text_density_high_estimate" if text_region_estimate > 0.5 else None,
        ]
        if flag
    )
    recommendation_status = ThumbnailReviewStatus.READY_TO_USE.value
    if "copying_risk" in warnings:
        recommendation_status = ThumbnailReviewStatus.NOT_RECOMMENDED.value
    elif "low_contrast" in warnings or "blurry_frame" in warnings:
        recommendation_status = ThumbnailReviewStatus.TECHNICALLY_WEAK.value
    metrics = (
        ThumbnailAnalysisMetric("width", float(width), None, "px", "high"),
        ThumbnailAnalysisMetric("height", float(height), None, "px", "high"),
        ThumbnailAnalysisMetric("aspect_ratio", float(width / float(height)), None, "ratio", "high"),
        ThumbnailAnalysisMetric("file_size_bytes", None, None, "bytes", "low"),
        ThumbnailAnalysisMetric("brightness", brightness, None, "ratio", "high"),
        ThumbnailAnalysisMetric("contrast", contrast, None, "ratio", "high"),
        ThumbnailAnalysisMetric("sharpness", sharpness, None, "ratio", "medium"),
        ThumbnailAnalysisMetric("entropy", entropy, None, "score", "medium"),
        ThumbnailAnalysisMetric("edge_density", edge_density, None, "ratio", "medium"),
        ThumbnailAnalysisMetric("dominant_region_count", float(dominant_region_count), None, "count", "medium"),
        ThumbnailAnalysisMetric("text_region_estimate", text_region_estimate, None, "score", "low"),
        ThumbnailAnalysisMetric("subject_centrality", subject_centrality, None, "ratio", "medium"),
        ThumbnailAnalysisMetric("palette_similarity", palette_similarity, None, "score", "low"),
        ThumbnailAnalysisMetric("composition_similarity", composition_similarity, None, "score", "low"),
        ThumbnailAnalysisMetric("visual_density", visual_density, None, "score", "medium"),
    )
    summary = f"Miniatura {width}x{height} con brillo {brightness:.2f} y contraste {contrast:.2f}."
    return ThumbnailAnalysisResult(
        dimensions=(width, height),
        metrics=metrics,
        warnings=warnings,
        recommendation_status=recommendation_status,
        summary=summary,
    )

