from datetime import datetime, timezone

from sample_app import cart, catalog, coupons, inventory, models, reports
from triage.baseline import keywords, triage_baseline
from triage.evaluate import ROOT, evaluate, load_scenario


def test_planted_bugs_really_reproduce():
    two = [models.Coupon("A", "percent", 20), models.Coupon("B", "percent", 15)]
    assert coupons.apply_coupons(10000, two) == 6500          # policy says 8000
    assert len(catalog.paginate(list(range(30)), 1)) == 9      # should be 10
    late = models.Order(1, 500, datetime(2026, 11, 10, 1, 0, tzinfo=timezone.utc))  # 5pm Pacific on Nov 9
    assert list(reports.daily_revenue([late])) == [datetime(2026, 11, 10).date()]
    inventory.load_stock([("ISBN-0042", 3)])
    try:
        cart.checkout([("ISBN-0042", 1, 1000)], [])
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_keywords_stem_and_drop_stopwords():
    assert "coupon" in keywords("Coupons were applied twice") and "were" not in keywords("these were applied")


def test_baseline_hits_every_scenario_with_grounded_evidence():
    results = evaluate(triage_baseline)
    assert len(results) == 4
    assert all(r["hit"] and r["grounded"] for r in results), results


def test_traceback_pins_the_deepest_frame():
    bug, tools, _ = load_scenario(ROOT / "scenarios" / "02_checkout_keyerror")
    t = triage_baseline(bug, tools)
    assert t.evidence[0].file == "inventory.py" and t.evidence[0].start_line == 22
    assert "reserve" in t.root_cause and t.source == "baseline"


def test_unknown_bug_returns_low_confidence_not_a_guess():
    _, tools, _ = load_scenario(ROOT / "scenarios" / "01_coupon_stacking")
    t = triage_baseline("# Weird\nxyzzy plugh", tools)
    assert t.confidence == "low" and t.root_cause == "Unknown"
