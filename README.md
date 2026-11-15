# AI Bug Triage Agent

An agent that triages a bug report: it investigates a codebase with read-only tools and writes notes on the likely root cause, why it happens, the evidence, its confidence and how to verify. Every cited line is checked against the real code, and unsupported claims cap the confidence at "low".

All code, bugs and data in this repo are **synthetic**. The sample app is an invented bookshop.

## How it works

```
bug report ──► agent loop (Claude + tools) ──► submit_triage ──► grounding check ──► triage notes
                 list_files, read_file, search_code,
                 get_recent_changes, search_logs
```

- **Agent** (`triage/agent.py`): Claude investigates, then submits structured notes: summary, root cause, evidence (file, lines, exact quote), causal chain, confidence, verification steps, missing information.
- **Grounding** (`triage/grounding.py`): rejects evidence whose file, line range or quote does not exist.
- **Baseline** (`triage/baseline.py`): offline, no LLM. Ranks files from stack-trace frames, keyword overlap and recent changes. Points at the likely file but cannot explain why.
- **Incident correlation** (`rca/`): an earlier module that ranks recent changes against error spikes and metric anomalies from logs and metrics. See `examples/`.

Build steps and design decisions: [docs/BUILD_STEPS.md](docs/BUILD_STEPS.md).

## Try it

```bash
pip install -r requirements.txt
python -m triage.evaluate                       # baseline on the 4 planted-bug scenarios
python -m triage.cli --bug scenarios/02_checkout_keyerror/bug.md --repo sample_app \
  --changes scenarios/02_checkout_keyerror/changes.json --logs scenarios/02_checkout_keyerror/logs.jsonl

pip install anthropic && export ANTHROPIC_API_KEY=...
python -m triage.cli --agent --bug scenarios/01_coupon_stacking/bug.md --repo sample_app \
  --changes scenarios/01_coupon_stacking/changes.json
python -m pytest -q
```

## Scenarios (planted bugs in `sample_app/`)

| Scenario | Symptom | Cause |
|---|---|---|
| 01 | Two percentage coupons stack (35% off) | `apply_coupons` subtracts every percent coupon; policy allows one |
| 02 | Every checkout raises `KeyError` | stock keys stored lowercase, lookups normalized to uppercase |
| 03 | Catalog pages show 9 books, not 10 | slice end is `start + per_page - 1` |
| 04 | Evening sales appear on the next day's report | groups by UTC date instead of store time |

## Results and limitations

- Baseline finds the right file in 4/4 scenarios. This is a tiny, easy benchmark (small app, descriptive file names), so treat it as a sanity check, not evidence of general accuracy.
- Triage notes are hypotheses to verify, not diagnoses. The agent only sees the files, logs and changes it is given.
