"""What-if simulation: Python does the math, the LLM (or a template) only explains it."""


def run_what_if_simulation(current_revenue, current_cost, price_change_pct=0.0, cost_change_pct=0.0):
    """Linear-scaling projection. Inputs are plain numbers; changes are in percent (e.g. 10 = +10%)."""
    for name, v in [("current_revenue", current_revenue), ("current_cost", current_cost),
                    ("price_change_pct", price_change_pct), ("cost_change_pct", cost_change_pct)]:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise TypeError(f"{name} must be a number, got {type(v).__name__}")
    if current_revenue < 0 or current_cost < 0:
        raise ValueError("current_revenue and current_cost must be >= 0")
    if price_change_pct <= -100 or cost_change_pct <= -100:
        raise ValueError("change percentages must be greater than -100")

    new_revenue = current_revenue * (1 + price_change_pct / 100)
    new_cost = current_cost * (1 + cost_change_pct / 100)
    new_profit = new_revenue - new_cost
    old_profit = current_revenue - current_cost

    def margin(rev, profit):
        return round(profit / rev * 100, 2) if rev else None

    return {
        "current_profit": round(old_profit, 2),
        "projected_revenue": round(new_revenue, 2),
        "projected_cost": round(new_cost, 2),
        "projected_profit": round(new_profit, 2),
        "profit_change": round(new_profit - old_profit, 2),
        "current_margin_pct": margin(current_revenue, old_profit),
        "projected_margin_pct": margin(new_revenue, new_profit),
        "disclaimer": "Estimated projection based on linear scaling. Actual market elasticity may vary.",
    }


def template_explanation(result, price_change_pct, cost_change_pct):
    """Rule-based explanation, used as the fallback when the LLM is unavailable."""
    direction = "increase" if result["profit_change"] >= 0 else "decrease"
    text = (f"With a price change of {price_change_pct}% and a cost change of {cost_change_pct}%, "
            f"projected profit is {result['projected_profit']} "
            f"(a {direction} of {abs(result['profit_change'])}).")
    if result["projected_margin_pct"] is not None:
        text += f" Projected margin is {result['projected_margin_pct']}%."
    if result["projected_profit"] < 0:
        text += " Warning: this scenario results in a loss."
    return text + " " + result["disclaimer"]


def explain_simulation(result, price_change_pct, cost_change_pct, use_llm=True):
    """LLM explains the trade-offs using only the computed numbers; falls back to the template."""
    if use_llm:
        try:
            from ai_insights import call_llm_json, numbers_are_grounded
            payload = {"inputs": {"price_change_pct": price_change_pct, "cost_change_pct": cost_change_pct},
                       "result": result}
            data = call_llm_json(
                "You are a business advisor. Explain the operational trade-offs of this scenario using ONLY "
                "the numbers provided. Return JSON: {\"explanation\": str, \"risks\": [str, str]}.",
                str(payload))
            if numbers_are_grounded(str(data), payload):
                return {"source": "llm", **data}
        except Exception:
            pass
    return {"source": "template", "explanation": template_explanation(result, price_change_pct, cost_change_pct)}
