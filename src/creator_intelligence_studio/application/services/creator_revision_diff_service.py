"""Deterministic revision diffing for creator edits."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import difflib
import re


_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n", re.MULTILINE)
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CreatorRevisionDiffSummary:
    algorithm_version: str
    before_characters: int
    after_characters: int
    before_words: int
    after_words: int
    before_paragraphs: int
    after_paragraphs: int
    insertions: int
    deletions: int
    replacements: int
    changed_ratio: float
    net_character_delta: int
    net_word_delta: int
    length_direction: str
    prefix_changed: bool
    suffix_changed: bool
    diff_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "algorithm_version": self.algorithm_version,
            "before_characters": self.before_characters,
            "after_characters": self.after_characters,
            "before_words": self.before_words,
            "after_words": self.after_words,
            "before_paragraphs": self.before_paragraphs,
            "after_paragraphs": self.after_paragraphs,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "replacements": self.replacements,
            "changed_ratio": self.changed_ratio,
            "net_character_delta": self.net_character_delta,
            "net_word_delta": self.net_word_delta,
            "length_direction": self.length_direction,
            "prefix_changed": self.prefix_changed,
            "suffix_changed": self.suffix_changed,
            "diff_hash": self.diff_hash,
        }


class CreatorRevisionDiffService:
    ALGORITHM_VERSION = "creator-text-diff-v1"

    @staticmethod
    def _normalize(text: str | None) -> str:
        value = "" if text is None else str(text)
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        return value.strip()

    @classmethod
    def summarize(cls, before_text: str | None, after_text: str | None) -> CreatorRevisionDiffSummary:
        before = cls._normalize(before_text)
        after = cls._normalize(after_text)
        before_words = [token for token in _WHITESPACE.split(before) if token] if before else []
        after_words = [token for token in _WHITESPACE.split(after) if token] if after else []
        before_paragraphs = [para for para in _PARAGRAPH_SPLIT.split(before) if para.strip()] if before else []
        after_paragraphs = [para for para in _PARAGRAPH_SPLIT.split(after) if para.strip()] if after else []
        matcher = difflib.SequenceMatcher(a=before_words, b=after_words)
        insertions = deletions = replacements = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                insertions += j2 - j1
            elif tag == "delete":
                deletions += i2 - i1
            elif tag == "replace":
                replacements += max(i2 - i1, j2 - j1)
        prefix_changed = not after.startswith(before[: min(len(before), len(after))]) if before and after else before != after
        suffix_changed = not after.endswith(before[max(0, len(before) - min(len(before), len(after))):]) if before and after else before != after
        net_word_delta = len(after_words) - len(before_words)
        net_character_delta = len(after) - len(before)
        if net_word_delta > 0:
            length_direction = "longer"
        elif net_word_delta < 0:
            length_direction = "shorter"
        else:
            length_direction = "stable"
        total_tokens = max(len(before_words), len(after_words), 1)
        changed_ratio = min(1.0, (insertions + deletions + replacements) / total_tokens)
        digest = sha256(
            "|".join(
                [
                    cls.ALGORITHM_VERSION,
                    before,
                    after,
                    str(insertions),
                    str(deletions),
                    str(replacements),
                ]
            ).encode("utf-8")
        ).hexdigest()
        return CreatorRevisionDiffSummary(
            algorithm_version=cls.ALGORITHM_VERSION,
            before_characters=len(before),
            after_characters=len(after),
            before_words=len(before_words),
            after_words=len(after_words),
            before_paragraphs=len(before_paragraphs),
            after_paragraphs=len(after_paragraphs),
            insertions=insertions,
            deletions=deletions,
            replacements=replacements,
            changed_ratio=changed_ratio,
            net_character_delta=net_character_delta,
            net_word_delta=net_word_delta,
            length_direction=length_direction,
            prefix_changed=prefix_changed,
            suffix_changed=suffix_changed,
            diff_hash=digest,
        )

