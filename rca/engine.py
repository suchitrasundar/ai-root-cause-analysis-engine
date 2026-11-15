"""Deterministic investigation pipeline: spikes + metric anomalies -> onset -> ranked suspect changes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import analysis
from .models import Incident


@dataclass
class Report:
    onset: datetime
    spikes: list[analysis.Spike]
    anomalies: list[analysis.MetricAnomaly]
    suspects: list[analysis.SuspectChange]

    @property
    def confidence(self) -> str:
        if not self.suspects:
            return "none"
        top = self.suspects[0].score
        runner_up = self.suspects[1].score if len(self.suspects) > 1 else 0.0
        if top >= 0.6 and top - runner_up >= 0.15:
            return "high"
        return "medium" if top >= 0.4 else "low"

    def to_markdown(self) -> str:
        lines = [f"# Incident analysis", f"Onset (earliest new error or metric anomaly): {self.onset.isoformat()}", ""]
        lines.append("## Likely cause")
        if self.suspects and self.confidence != "low":
            top = self.suspects[0]
            lines.append(f"Change `{top.change.id}` ({top.change.title}) by {top.change.author}, "
                         f"{top.hours_before_onset}h before onset. Confidence: **{self.confidence}**. "
                         "This is a correlation, not proof: verify by reverting or testing the change.")
        else:
            lines.append("No change correlates strongly with the incident. Check infrastructure, dependencies and traffic.")
        lines += ["", "## Error spikes"]
        lines += [f"- [{s.service}] x{s.incident_count} (baseline {s.baseline_count}{', new' if s.is_new else ''}): {s.example}" for s in self.spikes] or ["- none"]
        lines += ["", "## Metric anomalies"]
        lines += [f"- {a.metric}: baseline mean {a.baseline_mean:.1f}, peak {a.peak:.1f} (z={a.z_score})" for a in self.anomalies] or ["- none"]
        lines += ["", "## Suspect changes (ranked)"]
        for s in self.suspects:
            lines.append(f"- `{s.change.id}` score {s.score} (timing {s.timing_score}, overlap {s.overlap_score}; "
                         f"matched: {', '.join(s.matched_terms) or 'none'}): {s.change.title}")
        if not self.suspects:
            lines.append("- none in the lookback window")
        return "\n".join(lines)


def investigate(incident: Incident) -> Report:
    spikes = analysis.error_spikes(incident.logs, incident.start, incident.end)
    anomalies = analysis.metric_anomalies(incident.metrics, incident.start, incident.end)
    onset = analysis.find_onset(spikes, anomalies, incident.start)
    suspects = analysis.suspect_changes(incident.changes, onset, spikes, anomalies)
    return Report(onset, spikes, anomalies, suspects)
