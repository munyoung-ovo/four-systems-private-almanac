from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class CalendarType(str, Enum):
    SOLAR = "solar"
    LUNAR = "lunar"
    UNKNOWN = "unknown"

class TimePrecision(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"

class EvidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PARTIAL = "partial"
    BLOCKED = "blocked"

@dataclass(slots=True)
class CalculationProfile:
    calendar_type: CalendarType = CalendarType.SOLAR
    is_true_solar_time: bool = False
    time_precision: TimePrecision = TimePrecision.UNKNOWN
    is_leap_month: bool = False  # 专供农历使用，标记是否为闰月

    longitude: float | None = None
    latitude: float | None = None
    timezone: str | float | None = None

    confidence_score: float = 0.5
    evidence_level: EvidenceLevel = EvidenceLevel.MEDIUM
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.calendar_type = CalendarType(self.calendar_type)
        self.time_precision = TimePrecision(self.time_precision)
        self.evidence_level = EvidenceLevel(self.evidence_level)
        self.confidence_score = max(0.0, min(1.0, float(self.confidence_score)))

    def add_warning(self, warning: str) -> None:
        text = warning.strip()
        if text and text not in self.warnings:
            self.warnings.append(text)

    def to_dict(self) -> dict[str, object]:
        return {
            "calendar_type": self.calendar_type.value,
            "is_true_solar_time": self.is_true_solar_time,
            "time_precision": self.time_precision.value,
            "is_leap_month": self.is_leap_month,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "timezone": self.timezone,
            "confidence_score": self.confidence_score,
            "evidence_level": self.evidence_level.value,
            "warnings": list(self.warnings),
        }
