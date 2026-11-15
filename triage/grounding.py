"""Grounding check: every piece of evidence must exist in the code, or the notes are downgraded.

This is the main guardrail against hallucinated explanations: the model must quote real lines.
"""
from __future__ import annotations

from .models import Triage
from .tools import RepoTools


def _norm(text: str) -> str:
    return " ".join(text.split())


def check_evidence(triage: Triage, tools: RepoTools) -> list[str]:
    problems = []
    if not triage.evidence:
        problems.append("no evidence cited")
    for e in triage.evidence:
        label = f"{e.file}:{e.start_line}-{e.end_line}"
        try:
            lines = tools.file_lines(e.file)
        except (FileNotFoundError, ValueError):
            problems.append(f"{label}: file not found in repository")
            continue
        if not (1 <= e.start_line <= e.end_line <= len(lines)):
            problems.append(f"{label}: line range outside the file ({len(lines)} lines)")
            continue
        if not e.quote.strip() or _norm(e.quote) not in _norm(" ".join(lines[e.start_line - 1:e.end_line])):
            problems.append(f"{label}: quoted text not found in those lines")
    return problems


def apply_grounding(triage: Triage, tools: RepoTools) -> Triage:
    """Record problems and cap confidence at 'low' if any evidence is not grounded."""
    triage.ungrounded = check_evidence(triage, tools)
    if triage.ungrounded:
        triage.confidence = "low"
    return triage
