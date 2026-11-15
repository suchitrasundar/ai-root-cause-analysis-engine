"""LLM agent mode: Claude investigates by calling the deterministic analysis tools.

Requires `pip install anthropic` and ANTHROPIC_API_KEY. The model may only state what the tools returned.
"""
from __future__ import annotations

import dataclasses
import json
import re
from typing import Any

from . import analysis
from .models import Incident

SYSTEM = (
    "You are an on-call engineer investigating a production incident. Use the tools to gather evidence "
    "before concluding. Only state facts that appear in tool results, cite change ids, and say plainly when "
    "evidence is weak or ambiguous. Correlation with a change is not proof; recommend how to verify."
)

TOOLS = [
    {"name": "get_error_spikes", "description": "Error/warn log signatures that spiked or are new during the incident window.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_metric_anomalies", "description": "Metrics that deviate strongly from their pre-incident baseline.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_suspect_changes", "description": "Recent code/config changes ranked by timing and overlap with the evidence.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "search_logs", "description": "Regex search over log messages (case-insensitive), most recent first.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "limit": {"type": "integer"}},
                      "required": ["pattern"]}},
]


def _dump(obj: Any) -> str:
    def conv(o):
        return dataclasses.asdict(o) if dataclasses.is_dataclass(o) else str(o)
    return json.dumps(obj, default=conv, indent=1)


def run_tool(incident: Incident, name: str, args: dict) -> str:
    spikes = analysis.error_spikes(incident.logs, incident.start, incident.end)
    anomalies = analysis.metric_anomalies(incident.metrics, incident.start, incident.end)
    if name == "get_error_spikes":
        return _dump(spikes)
    if name == "get_metric_anomalies":
        return _dump(anomalies)
    if name == "get_suspect_changes":
        onset = analysis.find_onset(spikes, anomalies, incident.start)
        return _dump(analysis.suspect_changes(incident.changes, onset, spikes, anomalies))
    if name == "search_logs":
        try:
            rx = re.compile(args["pattern"], re.IGNORECASE)
        except re.error as e:
            return f"invalid regex: {e}"
        hits = [e for e in reversed(incident.logs) if rx.search(e.message)][: int(args.get("limit", 20))]
        return _dump(hits)
    return f"unknown tool: {name}"


def run_agent(incident: Incident, client, model: str, max_turns: int = 8) -> str:
    """Tool-use loop. `client` is an anthropic.Anthropic instance (or anything with .messages.create)."""
    messages: list[dict] = [{"role": "user", "content": (
        f"Investigate the incident between {incident.start.isoformat()} and {incident.end.isoformat()}. "
        "Give a root cause hypothesis, supporting evidence, confidence, and how to verify.")}]
    for _ in range(max_turns):
        resp = client.messages.create(model=model, max_tokens=1500, system=SYSTEM, tools=TOOLS, messages=messages)
        calls = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not calls:
            return "".join(b.text for b in resp.content if b.type == "text")
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": c.id, "content": run_tool(incident, c.name, c.input)} for c in calls]})
    return "Stopped: reached the maximum number of investigation turns without a final answer."
