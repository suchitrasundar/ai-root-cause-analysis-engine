from __future__ import annotations

from dataclasses import dataclass, field

CONFIDENCE_LEVELS = ("low", "medium", "high")


@dataclass
class Evidence:
    file: str
    start_line: int
    end_line: int
    quote: str


@dataclass
class Triage:
    summary: str
    root_cause: str
    evidence: list[Evidence] = field(default_factory=list)
    causal_chain: list[str] = field(default_factory=list)
    confidence: str = "low"
    verification_steps: list[str] = field(default_factory=list)
    component: str = ""
    missing_info: list[str] = field(default_factory=list)
    ungrounded: list[str] = field(default_factory=list)  # problems found by the grounding check
    source: str = "agent"

    @classmethod
    def from_dict(cls, d: dict, source: str = "agent") -> "Triage":
        conf = d.get("confidence", "low")
        return cls(
            summary=d.get("summary", ""),
            root_cause=d.get("root_cause", ""),
            evidence=[Evidence(e.get("file", ""), int(e.get("start_line", 0)), int(e.get("end_line", 0)), e.get("quote", ""))
                      for e in d.get("evidence", [])],
            causal_chain=list(d.get("causal_chain", [])),
            confidence=conf if conf in CONFIDENCE_LEVELS else "low",
            verification_steps=list(d.get("verification_steps", [])),
            component=d.get("component", ""),
            missing_info=list(d.get("missing_info", [])),
            source=source,
        )

    def to_markdown(self) -> str:
        out = [f"# Triage notes ({self.source})", "", f"**Summary:** {self.summary}", "",
               f"**Likely root cause:** {self.root_cause}", f"**Confidence:** {self.confidence}",
               f"**Component:** {self.component or 'unknown'}", "", "## Why it happens"]
        out += [f"{i}. {s}" for i, s in enumerate(self.causal_chain, 1)] or ["- not provided"]
        out += ["", "## Evidence (checked against the code)"]
        out += [f"- `{e.file}` lines {e.start_line}-{e.end_line}: `{e.quote}`" for e in self.evidence] or ["- none"]
        if self.ungrounded:
            out += ["", "## Ungrounded claims (confidence capped at low)"] + [f"- {p}" for p in self.ungrounded]
        out += ["", "## How to verify"] + ([f"- {s}" for s in self.verification_steps] or ["- not provided"])
        if self.missing_info:
            out += ["", "## Missing information"] + [f"- {s}" for s in self.missing_info]
        return "\n".join(out)
