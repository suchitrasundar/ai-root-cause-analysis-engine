from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogEvent:
    ts: datetime
    level: str
    service: str
    message: str


@dataclass(frozen=True)
class MetricPoint:
    ts: datetime
    metric: str
    value: float


@dataclass(frozen=True)
class Change:
    id: str
    ts: datetime
    author: str
    title: str
    files: tuple[str, ...] = ()


@dataclass
class Incident:
    start: datetime
    end: datetime
    logs: list[LogEvent] = field(default_factory=list)
    metrics: list[MetricPoint] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
