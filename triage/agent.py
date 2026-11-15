"""LLM triage agent: Claude investigates with read-only tools, then must call submit_triage.

The submission is checked by the grounding validator, so every cited line must exist in the code.
Needs `pip install anthropic` and ANTHROPIC_API_KEY (the client is injected, so tests use a fake).
"""
from __future__ import annotations

import json
from typing import Any

from .grounding import apply_grounding
from .models import Triage
from .tools import RepoTools

SYSTEM = (
    "You are a senior engineer triaging a bug report. Investigate the codebase with the tools before concluding: "
    "follow stack traces into the code, search for related functions, read the relevant files, and check recent "
    "changes. Then call submit_triage exactly once. Rules: every evidence item must quote real lines you read "
    "(file, line range, exact text); explain the causal chain from the code to the symptom; if the evidence is "
    "weak or two explanations fit, say so and lower your confidence; list what extra information would help. "
    "Never invent files, lines or behaviour."
)

_NOARGS = {"type": "object", "properties": {}}
TOOLS = [
    {"name": "list_files", "description": "List source files in the repository.", "input_schema": _NOARGS},
    {"name": "read_file", "description": "Read a file with line numbers (optionally a line range).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start": {"type": "integer"},
                                                       "end": {"type": "integer"}}, "required": ["path"]}},
    {"name": "search_code", "description": "Case-insensitive regex search across the code; returns file:line: text.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "get_recent_changes", "description": "Recent changes, optionally only those touching a given file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "search_logs", "description": "Search application log messages by regex, most recent first.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "submit_triage", "description": "Submit the final triage notes. Call once, when done.",
     "input_schema": {"type": "object", "properties": {
         "summary": {"type": "string"},
         "root_cause": {"type": "string"},
         "evidence": {"type": "array", "items": {"type": "object", "properties": {
             "file": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"},
             "quote": {"type": "string"}}, "required": ["file", "start_line", "end_line", "quote"]}},
         "causal_chain": {"type": "array", "items": {"type": "string"}},
         "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
         "verification_steps": {"type": "array", "items": {"type": "string"}},
         "component": {"type": "string"},
         "missing_info": {"type": "array", "items": {"type": "string"}}},
         "required": ["summary", "root_cause", "evidence", "causal_chain", "confidence", "verification_steps"]}},
]


def run_tool(tools: RepoTools, name: str, args: dict) -> str:
    try:
        if name == "list_files":
            out: Any = tools.list_files()
        elif name == "read_file":
            out = tools.read_file(args["path"], int(args.get("start", 1)), args.get("end"))
        elif name == "search_code":
            out = tools.search_code(args["pattern"])
        elif name == "get_recent_changes":
            out = tools.recent_changes(args.get("path"))
        elif name == "search_logs":
            out = tools.search_logs(args["pattern"])
        else:
            return f"unknown tool: {name}"
    except Exception as e:  # tool errors go back to the model so it can correct itself
        return f"error: {e}"
    return out if isinstance(out, str) else json.dumps(out, indent=1)


def run_triage_agent(bug_text: str, tools: RepoTools, client, model: str, max_turns: int = 12) -> Triage:
    messages: list[dict] = [{"role": "user", "content": f"Bug report:\n\n{bug_text}"}]
    for _ in range(max_turns):
        resp = client.messages.create(model=model, max_tokens=2000, system=SYSTEM, tools=TOOLS, messages=messages)
        calls = [b for b in resp.content if b.type == "tool_use"]
        submit = next((c for c in calls if c.name == "submit_triage"), None)
        if submit:
            return apply_grounding(Triage.from_dict(submit.input, source="agent"), tools)
        messages.append({"role": "assistant", "content": resp.content})
        if calls:
            results = [{"type": "tool_result", "tool_use_id": c.id, "content": run_tool(tools, c.name, c.input)} for c in calls]
        else:
            results = [{"type": "text", "text": "Please finish by calling submit_triage."}]
        messages.append({"role": "user", "content": results})
    return Triage("Agent did not finish.", "Unknown", confidence="low", source="agent",
                  missing_info=[f"No submit_triage call within {max_turns} turns."])
