---
name: grounded-bug-triage
description: Triage a bug report, stack trace, failing test or error log by investigating the codebase and writing root-cause notes where every claim cites real, verified lines of code. Use when the user pastes a bug, error, traceback or incident and asks what is causing it, why it happens, where to look, or to triage/debug it before fixing.
---

# Grounded Bug Triage

Produce triage notes for a bug: the likely root cause, why it happens, the evidence, a confidence level and how to verify. The defining rule: **every piece of evidence quotes real lines from the repository, and a script checks those quotes before the notes are shown.** Ungrounded claims force confidence down to `low`.

Triage comes before fixing. Do not edit source files during triage unless the user asks for a fix afterwards.

## Workflow

### 1. Read the report
Extract: the symptom, any stack-trace frames (file + line), error messages, IDs or values mentioned (e.g. `ISBN-0042`), when it started ("since the last deploy") and the environment.

### 2. Investigate (read-only)
Work from the most specific clue outward:
1. **Stack frames first.** Open each frame's file at the reported line, then read the surrounding function.
2. **Search for the values and names** in the error (keys, messages, function names) across the code.
3. **Follow the data.** For the failing value, find where it is written and where it is read. Mismatches between the two (casing, units, time zones, off-by-one, null handling) are the most common root causes.
4. **Check recent changes** when the report says it started recently: `git log -n 20 --stat`, then `git log -p -n 5 -- <file>` for suspect files.
5. **Check logs** if the user supplied them or the repo has them.

Read a file before you cite it. Note the exact line numbers as you read.

### 3. Draft the notes as JSON
Write `triage.json` in a scratch location (not inside the user's source tree; use the system temp dir or `.triage/` if the user prefers it in-repo):

```json
{
  "summary": "One sentence: what breaks and for whom.",
  "root_cause": "The specific defect, in plain words.",
  "evidence": [
    {"file": "src/inventory.py", "start_line": 13, "end_line": 13,
     "quote": "STOCK[sku.lower()] = qty",
     "why": "Stock is stored under lowercase keys."}
  ],
  "causal_chain": ["step from the code ...", "... to the observed symptom"],
  "confidence": "high | medium | low",
  "verification_steps": ["A concrete check or test that would confirm it."],
  "alternatives": ["Other explanations considered and why they were ruled out or not."],
  "missing_info": ["What extra data would raise confidence."]
}
```

Rules for evidence:
- `file` is relative to the repository root.
- `quote` is copied exactly from the lines in the range (whitespace differences are tolerated). Keep it short: the line or two that matter.
- Cite at least one line for the root cause and one for each important link in the causal chain.

Choosing confidence:
- **high**: the causal chain is fully supported by cited code and explains every symptom.
- **medium**: the code supports it, but a step relies on an assumption (runtime data, config, environment).
- **low**: plausible but unconfirmed, or two explanations fit equally well. Say which two.

### 4. Verify grounding (required)
Run:

```bash
python <skill-dir>/scripts/verify_evidence.py triage.json --repo <repo-root>
```

- Exit 0: all evidence is grounded.
- Exit 1: the script lists each problem (missing file, line range out of bounds, quote not found) and rewrites `confidence` to `low` in the JSON. **Fix the citations by re-reading the files**, then run it again. Only if a claim genuinely cannot be grounded, keep it out of the evidence and mention it under `missing_info`.

Never present notes that have not passed this check, and never raise confidence that the script capped.

### 5. Present the notes
Show the user a readable version (not raw JSON):

```
## Triage: <summary>
**Confidence:** <level>   **Grounding:** passed (<n> citations verified)

**Root cause:** ...

**Why it happens**
1. ...
2. ...

**Evidence**
- `file:line` — `quote` — why it matters

**How to verify**
- ...

**Other explanations considered** / **Missing information**
- ...
```

Then offer one next step: write a failing test that reproduces it, or propose a fix.

## Pitfalls
- Don't stop at the line that throws. The throwing line is usually the symptom; the root cause is where the bad value was produced.
- Don't cite code you haven't opened, and don't infer line numbers from a stack trace without reading the file (the file may have changed since the trace).
- If the stack trace's line numbers don't match the current code, say so: the deployed version may differ from the checked-out one.
- If nothing in the repo explains the bug, say that plainly with `low` confidence and list what to collect next. A clear "not found, here's what to check" beats a confident guess.
