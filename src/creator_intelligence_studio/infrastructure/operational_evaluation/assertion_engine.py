"""Assertions tecnicas para evaluacion operativa."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.operational_evaluation.value_objects import (
    OperationalEvaluationAssertionSeverity,
)


@dataclass(frozen=True, slots=True)
class AssertionResult:
    name: str
    passed: bool
    severity: OperationalEvaluationAssertionSeverity
    expected: dict[str, object]
    actual: dict[str, object]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value,
            "expected": dict(self.expected),
            "actual": dict(self.actual),
            "message": self.message,
        }


def assert_condition(
    name: str,
    condition: bool,
    *,
    severity: OperationalEvaluationAssertionSeverity = OperationalEvaluationAssertionSeverity.ERROR,
    expected: dict[str, object] | None = None,
    actual: dict[str, object] | None = None,
    message: str | None = None,
) -> AssertionResult:
    return AssertionResult(
        name=name,
        passed=condition,
        severity=severity,
        expected=expected or {},
        actual=actual or {},
        message=message or ("OK" if condition else "Assertion fallida"),
    )
