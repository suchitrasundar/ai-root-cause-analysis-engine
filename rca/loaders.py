"""Load logs (JSON lines), metrics (CSV: ts,metric,value) and changes (JSON list)."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Change, LogEvent, MetricPoint


def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_logs(path: str | Path) -> list[LogEvent]:
    events = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        events.append(LogEvent(parse_ts(row["ts"]), row["level"].upper(), row.get("service", "unknown"), row["message"]))
    return sorted(events, key=lambda e: e.ts)


def load_metrics(path: str | Path) -> list[MetricPoint]:
    with open(path, newline="") as f:
        points = [MetricPoint(parse_ts(r["ts"]), r["metric"], float(r["value"])) for r in csv.DictReader(f)]
    return sorted(points, key=lambda p: p.ts)


def load_changes(path: str | Path) -> list[Change]:
    rows = json.loads(Path(path).read_text())
    return sorted(
        (Change(r["id"], parse_ts(r["ts"]), r.get("author", "unknown"), r["title"], tuple(r.get("files", []))) for r in rows),
        key=lambda c: c.ts,
    )
