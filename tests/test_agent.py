from types import SimpleNamespace as NS

from triage.agent import TOOLS, run_tool, run_triage_agent
from triage.evaluate import ROOT, load_scenario


def block(**kw):
    return NS(**kw)


def tool_use(id, name, **inp):
    return NS(stop_reason="tool_use", content=[block(type="tool_use", id=id, name=name, input=inp)])


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return self.responses[len(self.calls) - 1]


GOOD = dict(summary="Two percent coupons stack", root_cause="apply_coupons subtracts every percent coupon",
            evidence=[dict(file="coupons.py", start_line=13, end_line=13, quote="total -= subtotal_cents * coupon.value // 100")],
            causal_chain=["Loop visits each coupon", "Each percent coupon is subtracted from the same subtotal"],
            confidence="high", verification_steps=["Add a test with two percent coupons"])


def scenario():
    bug, tools, _ = load_scenario(ROOT / "scenarios" / "01_coupon_stacking")
    return bug, tools


def test_agent_investigates_then_submits_grounded_notes():
    bug, tools = scenario()
    client = FakeClient([tool_use("1", "search_code", pattern="coupon"), tool_use("2", "submit_triage", **GOOD)])
    t = run_triage_agent(bug, tools, client, "m")
    assert t.source == "agent" and t.confidence == "high" and t.ungrounded == []
    # the tool result from turn 1 was fed back to the model
    fed_back = client.calls[1]["messages"][-1]["content"][0]
    assert fed_back["tool_use_id"] == "1" and "coupons.py" in fed_back["content"]


def test_fabricated_evidence_is_caught_and_confidence_capped():
    bug, tools = scenario()
    bad = {**GOOD, "evidence": [dict(file="coupons.py", start_line=13, end_line=13, quote="total = best_coupon(subtotal)")]}
    t = run_triage_agent(bug, tools, FakeClient([tool_use("1", "submit_triage", **bad)]), "m")
    assert t.confidence == "low" and "quoted text not found" in t.ungrounded[0]


def test_agent_is_nudged_then_gives_up_without_submitting():
    bug, tools = scenario()
    talk = NS(stop_reason="end_turn", content=[block(type="text", text="I think it's coupons")])
    client = FakeClient([talk, talk])
    t = run_triage_agent(bug, tools, client, "m", max_turns=2)
    assert t.root_cause == "Unknown" and "submit_triage" in client.calls[1]["messages"][-1]["content"][0]["text"]


def test_tool_errors_and_unknown_tools_return_text_not_exceptions():
    _, tools = scenario()
    assert run_tool(tools, "read_file", {"path": "../secret"}).startswith("error:")
    assert run_tool(tools, "nope", {}).startswith("unknown tool")
    assert "start" in run_tool(tools, "read_file", {"path": "catalog.py", "start": 7, "end": 7})


def test_exactly_one_submit_tool_defined():
    assert [t["name"] for t in TOOLS].count("submit_triage") == 1
