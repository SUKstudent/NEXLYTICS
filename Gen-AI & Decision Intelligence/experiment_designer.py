"""AI Business Experiment Designer: turns a recommendation into a structured micro-test."""


def design_experiment(action, target, expected_lift_pct, baseline_revenue, baseline_margin_pct,
                      duration_days=14, min_margin_pct=None):
    """Build a test blueprint. All numbers come from the analytics stage, none are invented."""
    if duration_days < 7:
        duration_days = 7  # at least one full weekly cycle
    min_margin = baseline_margin_pct - 2 if min_margin_pct is None else min_margin_pct
    return {
        "hypothesis": f"{action} on {target} will increase revenue by {expected_lift_pct}%.",
        "target_group": f"{target} (test)",
        "baseline_group": f"{target} historical control weeks (same length, same season if possible)",
        "duration_days": duration_days,
        "success_metric": {"name": "gross_profit", "baseline_revenue": baseline_revenue,
                           "target_lift_pct": expected_lift_pct},
        "guardrail_metric": {"name": "net_margin_pct", "baseline": baseline_margin_pct,
                             "minimum_allowed": min_margin},
        "decision_rules": {
            "SCALE": "lift >= target and margin >= minimum_allowed",
            "MODIFY": "0 < lift < target and margin >= minimum_allowed",
            "STOP": "lift <= 0 or margin < minimum_allowed",
            "EXTEND": "result inconclusive (too few days or too little data)",
        },
    }


def decide(blueprint, observed_lift_pct, observed_margin_pct, days_run):
    """Return SCALE / MODIFY / STOP / EXTEND plus the reason."""
    target = blueprint["success_metric"]["target_lift_pct"]
    min_margin = blueprint["guardrail_metric"]["minimum_allowed"]
    if observed_margin_pct < min_margin:
        return "STOP", f"Margin {observed_margin_pct}% fell below guardrail {min_margin}%."
    if days_run < blueprint["duration_days"]:
        return "EXTEND", f"Only {days_run} of {blueprint['duration_days']} planned days completed."
    if observed_lift_pct >= target:
        return "SCALE", f"Lift {observed_lift_pct}% met target {target}% with margin intact."
    if observed_lift_pct > 0:
        return "MODIFY", f"Lift {observed_lift_pct}% is positive but below target {target}%."
    return "STOP", f"Lift {observed_lift_pct}% is not positive."
