"""Normalizacion determinista para Creator Corpus."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from .value_objects import TEXT_NORMALIZATION_VERSION

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
_BLANK_LINE_PATTERN = re.compile(r"\n{3,}")


def _normalize_line(line: str) -> str:
    line = _WHITESPACE_PATTERN.sub(" ", line)
    return line.strip(" \t")


def normalize_corpus_text(value: str | None) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    lines = [_normalize_line(line) for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANK_LINE_PATTERN.sub("\n\n", text)
    return text.strip()


def hash_corpus_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_corpus_title(value: str | None) -> str:
    return normalize_corpus_text(value)


def normalize_corpus_language(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_corpus_text(value).replace("_", "-").lower()
    return normalized or None


def normalize_segment_text(value: str | None) -> str:
    return normalize_corpus_text(value)
