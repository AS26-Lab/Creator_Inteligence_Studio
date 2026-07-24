"""Normalizacion de fechas para importaciones de analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class DateNormalizationResult:
    value: datetime | None
    inferred_timezone: bool
    warning_codes: tuple[str, ...]


def normalize_timezone_name(timezone_name: str | None) -> str:
    return timezone_name.strip() if timezone_name and timezone_name.strip() else "UTC"


def normalize_date(value, *, timezone_name: str | None = None) -> DateNormalizationResult:
    if value is None:
        return DateNormalizationResult(None, False, ("invalid_date",))
    zone_name = normalize_timezone_name(timezone_name)
    if zone_name.upper() == "UTC":
        tz = timezone.utc
    else:
        try:
            tz = ZoneInfo(zone_name)
        except Exception:
            return DateNormalizationResult(None, False, ("invalid_timezone",))
    warnings: list[str] = []
    inferred_timezone = False
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
        inferred_timezone = True
        warnings.append("inferred_timezone")
    else:
        text = str(value).strip()
        if not text:
            return DateNormalizationResult(None, False, ("invalid_date",))
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for candidate in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(text, candidate)
                except ValueError:
                    continue
                inferred_timezone = True
                warnings.append("inferred_timezone")
                break
            else:
                return DateNormalizationResult(None, False, ("invalid_date",))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
        inferred_timezone = True
        warnings.append("inferred_timezone")
    return DateNormalizationResult(dt.astimezone(timezone.utc), inferred_timezone, tuple(dict.fromkeys(warnings)))
