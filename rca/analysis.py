"""Deterministic evidence-gathering tools. The LLM agent calls these; the engine also runs them directly."""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import Change, LogEvent, MetricPoint

BAD_LEVELS = {"WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}
_TOKEN = re.compile(r"[a-z][a-z0-9]{2,}")
_STOP = {"the", "and", "for", "from", "after", "with", "update", "fix", "add", "change", "service", "file", "src", "main", "java", "py"}


def signature(message: str) -> str:
    """Collapse variable parts (ids, numbers, hex) so repeated errors group together."""
    s = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<uuid>", message.lower())
    s = re.sub(r"0x[0-9a-f]+", "<hex>", s)
    s = re.sub(r"\d+", "<n>", s)
    return s.strip()


def tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower().replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ")) if t not in _STOP}


@dataclass
class Spike:
    signature: str
    service: str
    baseline_count: int
    incident_count: int
    first_seen: datetime
    example: str
    is_new: bool


@dataclass
class MetricAnomaly:
    metric: str
    baseline_mean: float
    peak: float
    z_score: float
    first_anomalous: datetime


@dataclass
class SuspectChange:
    change: Change
    score: float
    timing_score: float
    overlap_score: float
    matched_terms: list[str]
    hours_before_onset: float


def error_spikes(logs: list[LogEvent], start: datetime, end: datetime, baseline: timedelta = timedelta(hours=1),
                 min_incident_count: int = 3) -> list[Spike]:
    base: dict[tuple[str, str], int] = {}
    inc: dict[tuple[str, str], list[LogEvent]] = {}
    for e in logs:
        if e.level not in BAD_LEVELS:
            continue
        key = (e.service, signature(e.message))
        if start - baseline <= e.ts < start:
            base[key] = base.get(key, 0) + 1
        elif start <= e.ts <= end:
            inc.setdefault(key, []).append(e)
    window_ratio = max((end - start) / baseline, 1e-9)
    spikes = []
    for key, events in inc.items():
        b = base.get(key, 0)
        # compare per-unit-time rates so differently sized windows are comparable
        if len(events) < min_incident_count:
            continue
        if b > 0 and len(events) / window_ratio < 3 * b:  # existing error: require a 3x rate increase
            continue
        spikes.append(Spike(key[1], key[0], b, len(events), events[0].ts, events[0].message, b == 0))
    return sorted(spikes, key=lambda s: (-s.is_new, -s.incident_count))


def metric_anomalies(metrics: list[MetricPoint], start: datetime, end: datetime, z_threshold: float = 3.0) -> list[MetricAnomaly]:
    by_metric: dict[str, list[MetricPoint]] = {}
    for p in metrics:
        by_metric.setdefault(p.metric, []).append(p)
    out = []
    for name, pts in by_metric.items():
        base = [p.value for p in pts if p.ts < start]
        during = [p for p in pts if start <= p.ts <= end]
        if len(base) < 5 or not during:
            continue
        mean = statistics.fmean(base)
        std = max(statistics.pstdev(base), abs(mean) * 0.05, 1e-6)  # floor avoids infinite z on flat series
        flagged = [(abs(p.value - mean) / std, p) for p in during]
        flagged = [(z, p) for z, p in flagged if z >= z_threshold]
        if not flagged:
            continue
        peak_z, peak_p = max(flagged, key=lambda x: x[0])
        out.append(MetricAnomaly(name, mean, peak_p.value, round(peak_z, 1), min(p.ts for _, p in flagged)))
    return sorted(out, key=lambda a: -a.z_score)


def find_onset(spikes: list[Spike], anomalies: list[MetricAnomaly], fallback: datetime) -> datetime:
    times = [s.first_seen for s in spikes if s.is_new] + [a.first_anomalous for a in anomalies]
    return min(times) if times else fallback


def suspect_changes(changes: list[Change], onset: datetime, spikes: list[Spike], anomalies: list[MetricAnomaly],
                    lookback: timedelta = timedelta(hours=24)) -> list[SuspectChange]:
    evidence_terms: set[str] = set()
    for s in spikes:
        evidence_terms |= tokens(s.signature) | tokens(s.service)
    for a in anomalies:
        evidence_terms |= tokens(a.metric)
    results = []
    for c in changes:
        if not (onset - lookback <= c.ts <= onset):
            continue
        hours = (onset - c.ts).total_seconds() / 3600
        timing = math.exp(-hours / 6)  # recent changes are more suspicious
        change_terms = tokens(c.title) | {t for f in c.files for t in tokens(f)}
        matched = sorted(change_terms & evidence_terms)
        overlap = min(1.0, len(matched) / 3)
        results.append(SuspectChange(c, round(0.4 * timing + 0.6 * overlap, 3), round(timing, 3), round(overlap, 3), matched, round(hours, 2)))
    return sorted(results, key=lambda r: -r.score)
