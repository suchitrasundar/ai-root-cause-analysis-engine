# AI Root Cause Analysis Engine

An agent that investigates a production incident by correlating **logs**, **metrics** and **recent code changes**, then ranks the changes most likely to have caused it. A deterministic analysis pipeline does the evidence gathering; an optional Claude tool-use agent calls the same tools and writes the investigation.

## How it works

1. **Error spikes** – log errors are grouped by normalized signature (ids and numbers collapsed). A signature is flagged if it is new in the incident window, or its rate rose at least 3x over the baseline.
2. **Metric anomalies** – each metric is compared with its pre-incident baseline (z-score, with a floor so flat series don't produce infinite scores).
3. **Onset** – the earliest new error or anomalous metric point.
4. **Suspect changes** – changes in the 24 hours before onset are scored: 40% recency (exponential decay), 60% overlap between the change (title, file paths) and the evidence terms (error text, service, metric names).
5. **Report** – likely cause, confidence (high / medium / low), and the evidence. When no change correlates, it says so rather than guessing.

## Usage

```bash
python examples/generate_sample.py      # synthetic incident: a pool-size change causes connection timeouts
python -m rca.cli --logs examples/logs.jsonl --metrics examples/metrics.csv \
  --changes examples/changes.json --start 2026-11-10T14:00:00Z --end 2026-11-10T14:30:00Z
```

Agent mode (optional): `pip install anthropic`, set `ANTHROPIC_API_KEY`, add `--agent`. The model can call `get_error_spikes`, `get_metric_anomalies`, `get_suspect_changes` and `search_logs`, and is instructed to state only what the tools return.

Input formats: logs are JSON lines (`ts, level, service, message`), metrics are CSV (`ts, metric, value`), changes are a JSON list (`id, ts, author, title, files`).

## Limitations

- The bundled example is **synthetic**. The engine has not been evaluated on real production incidents.
- Ranking is a heuristic. Correlation in time and wording is not proof of causation, and the report says to verify by reverting or testing.
- It does not read traces or diffs, and it only sees the logs, metrics and changes you give it. Causes outside code changes (traffic, infrastructure, dependencies) are reported as "no strong correlation".
- Agent mode has been tested with a mocked client only, not against the live API.

## Tests

```bash
python -m pytest -q
```
