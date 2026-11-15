from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from rca import agent, analysis, loaders
from rca.engine import investigate
from rca.models import Change, Incident, LogEvent, MetricPoint

EX = Path(__file__).resolve().parent.parent / "examples"
START = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)
END = START + timedelta(minutes=30)


def sample() -> Incident:
    return Incident(START, END, loaders.load_logs(EX / "logs.jsonl"), loaders.load_metrics(EX / "metrics.csv"),
                    loaders.load_changes(EX / "changes.json"))


def test_signature_groups_variable_parts():
    a = analysis.signature("Timeout after 30000 ms for user 17 id 0xAB12")
    b = analysis.signature("Timeout after 5000 ms for user 99 id 0xFF")
    assert a == b


def test_sample_incident_ranks_pool_change_first():
    r = investigate(sample())
    assert r.suspects[0].change.id == "d93b5a7"
    assert r.confidence == "high"
    assert r.suspects[0].score > r.suspects[1].score + 0.15


def test_background_noise_is_not_flagged():
    spikes = analysis.error_spikes(sample().logs, START, END)
    assert all("email" not in s.service for s in spikes)
    assert len(spikes) == 1 and spikes[0].is_new


def test_existing_error_needs_3x_rate_increase():
    def ev(minute, n):
        return [LogEvent(START + timedelta(minutes=minute, seconds=i), "ERROR", "svc", f"boom {i}") for i in range(n)]
    base = [LogEvent(START - timedelta(minutes=30, seconds=-i), "ERROR", "svc", "boom 1") for i in range(10)]
    steady = base + ev(1, 5)          # 5 in 30 min vs 10 in 60 min: ~same rate
    assert analysis.error_spikes(steady, START, END) == []
    jump = base + ev(1, 40)
    assert len(analysis.error_spikes(jump, START, END)) == 1


def test_metric_anomaly_needs_baseline_and_threshold():
    flat = [MetricPoint(START - timedelta(minutes=i + 1), "m", 100.0) for i in range(10)]
    ok = flat + [MetricPoint(START + timedelta(minutes=1), "m", 104.0)]
    assert analysis.metric_anomalies(ok, START, END) == []
    bad = flat + [MetricPoint(START + timedelta(minutes=1), "m", 500.0)]
    assert analysis.metric_anomalies(bad, START, END)[0].metric == "m"
    assert analysis.metric_anomalies(flat[:3] + bad[-1:], START, END) == []  # too little baseline


def test_changes_after_onset_or_outside_lookback_are_ignored():
    spikes = analysis.error_spikes(sample().logs, START, END)
    changes = [Change("late", START + timedelta(hours=1), "x", "pool connection"),
               Change("old", START - timedelta(days=3), "x", "pool connection")]
    assert analysis.suspect_changes(changes, START, spikes, []) == []


def test_no_correlated_change_reports_low_confidence():
    inc = sample()
    inc.changes = [Change("x1", START - timedelta(hours=20), "dev", "Update docs", ("docs/a.md",))]
    r = investigate(inc)
    assert r.confidence == "low"
    assert "No change correlates" in r.to_markdown()


def test_agent_loop_runs_tools_and_returns_final_text():
    calls = []

    def block(**kw):
        return SimpleNamespace(**kw)

    responses = [
        SimpleNamespace(stop_reason="tool_use", content=[block(type="tool_use", id="t1", name="get_suspect_changes", input={})]),
        SimpleNamespace(stop_reason="end_turn", content=[block(type="text", text="Root cause: change d93b5a7")]),
    ]

    class Client:
        messages = SimpleNamespace(create=lambda **kw: (calls.append(kw), responses[len(calls) - 1])[1])

    out = agent.run_agent(sample(), Client(), "test-model")
    assert "d93b5a7" in out
    tool_result = calls[1]["messages"][-1]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and "d93b5a7" in tool_result["content"]


def test_search_logs_tool_and_bad_regex():
    inc = sample()
    assert "pool" in agent.run_tool(inc, "search_logs", {"pattern": "pool", "limit": 2})
    assert "invalid regex" in agent.run_tool(inc, "search_logs", {"pattern": "("})
    assert "unknown tool" in agent.run_tool(inc, "nope", {})
