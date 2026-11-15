# Build walkthrough

The project was built in six steps, one commit each (`git log --oneline`). Each step can be checked on its own.

| Step | What was built | How to check it |
|---|---|---|
| 1 | Synthetic bookshop app with four planted bugs, plus a bug report, change list, logs and known root cause for each (`sample_app/`, `scenarios/`) | `pytest tests/test_baseline.py::test_planted_bugs_really_reproduce` proves each bug really happens |
| 2 | Read-only investigation tools (`triage/tools.py`): list/read/search code, recent changes, search logs. File access is confined to the repo root | `pytest tests/test_tools.py` includes path-traversal attempts |
| 3 | Grounding check (`triage/grounding.py`): every cited file, line range and quote must exist in the code, otherwise confidence is capped at low | `pytest tests/test_grounding.py` |
| 4 | Offline baseline triager (traceback frames, keyword overlap, recent changes) and an evaluation harness | `python -m triage.evaluate` |
| 5 | Claude tool-use agent (`triage/agent.py`): investigates with the tools, then must call `submit_triage`; output is grounded before it is returned | `pytest tests/test_agent.py` (fake client) |
| 6 | CLI, README, CI | `python -m triage.cli ...` and the GitHub Actions run |

## Design decisions

- **Why a grounding check:** an LLM can write a convincing but wrong explanation. Forcing it to quote exact lines, and verifying them in code, makes unsupported claims visible instead of trusted.
- **Why a baseline:** it works without an API key and gives the agent a number to beat. It is deliberately simple and cannot explain *why* a bug happens.
- **Why synthetic data:** the project uses only an invented bookshop app and invented bug reports. No employer or customer code, bugs or data is used.
- **Bugs found while building:** the baseline initially guessed a file from recent changes alone for an unrelated report (a test caught it; changes now only boost files the report already points to). A wrong line number in a test fixture was rejected by the grounding check.

## Not yet done

- The Claude agent has not been run against the live API; it is tested with a scripted fake client. Running `--agent` on the four scenarios and recording accuracy is the next step.
- The benchmark is four scenarios in a tiny app. A 4/4 baseline score says little about real codebases.
