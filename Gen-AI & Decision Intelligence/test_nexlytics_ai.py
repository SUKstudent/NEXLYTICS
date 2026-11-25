import pytest
from what_if_simulation import run_what_if_simulation
from decision_readiness import evaluate_decision_readiness
from experiment_designer import design_experiment, decide
from ai_insights import numbers_are_grounded, generate_business_insight


def test_simulation_math():
    r = run_what_if_simulation(1000, 800, 10, -5)
    assert r["projected_revenue"] == 1100.0
    assert r["projected_cost"] == 760.0
    assert r["projected_profit"] == 340.0
    assert r["profit_change"] == 140.0
    assert r["projected_margin_pct"] == 30.91


def test_simulation_zero_and_invalid():
    assert run_what_if_simulation(0, 0, 10, 10)["projected_margin_pct"] is None
    with pytest.raises(ValueError):
        run_what_if_simulation(100, 50, -100, 0)
    with pytest.raises(TypeError):
        run_what_if_simulation("100", 50, 0, 0)


def test_readiness_grades():
    assert evaluate_decision_readiness(1000, 0.01, 1)["grade"] == "HIGH READINESS"
    assert evaluate_decision_readiness(100, 0.01, 1)["grade"] == "MEDIUM READINESS"
    low = evaluate_decision_readiness(100, 0.10, 10, 0.4)
    assert low["grade"].startswith("LOW") and low["score"] == 0 and len(low["warnings"]) == 4


def test_experiment_rules():
    bp = design_experiment("10% discount", "slow-moving SKUs", 15, 50000, 20.0, 14)
    assert decide(bp, 18, 19.5, 14)[0] == "SCALE"
    assert decide(bp, 5, 19.5, 14)[0] == "MODIFY"
    assert decide(bp, -2, 19.5, 14)[0] == "STOP"
    assert decide(bp, 20, 15.0, 14)[0] == "STOP"
    assert decide(bp, 20, 19.5, 5)[0] == "EXTEND"


def test_number_grounding():
    src = {"kpis": {"profit_change_pct": -12.0, "revenue": 50000}}
    assert numbers_are_grounded("Profit fell 12% on revenue of 50,000", src)
    assert not numbers_are_grounded("Profit fell 15%", src)


def test_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = generate_business_insight({"revenue": 100}, "none")
    assert r["source"] == "template" and "fallback_reason" in r
