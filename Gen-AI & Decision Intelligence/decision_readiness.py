"""Decision Readiness Passport: transparent HIGH / MEDIUM / LOW grade for data reliability."""


def evaluate_decision_readiness(row_count, missing_pct, days_since_last_update, forecast_mape=None):
    """
    row_count: number of rows behind the analysis
    missing_pct: fraction of missing cells, 0-1 (e.g. 0.07 = 7%)
    days_since_last_update: age of the data in days
    forecast_mape: optional forecast error as a fraction (e.g. 0.18 = 18%), from Tauz's model
    Returns dict with score, grade, and a list of every penalty applied (fully transparent).
    """
    if not 0 <= missing_pct <= 1:
        raise ValueError("missing_pct must be a fraction between 0 and 1")
    if row_count < 0 or days_since_last_update < 0:
        raise ValueError("row_count and days_since_last_update must be >= 0")

    score = 100
    warnings = []

    if row_count < 500:
        score -= 30
        warnings.append(f"Low sample size ({row_count} rows, need 500+). -30")
    if missing_pct > 0.05:
        score -= 25
        warnings.append(f"High missing data ({round(missing_pct * 100, 1)}%, limit 5%). -25")
    if days_since_last_update > 3:
        score -= 20
        warnings.append(f"Data is {days_since_last_update} days old (limit 3). -20")
    if forecast_mape is not None:
        if forecast_mape > 0.30:
            score -= 25
            warnings.append(f"High forecast error (MAPE {round(forecast_mape * 100, 1)}%, limit 30%). -25")
        elif forecast_mape > 0.15:
            score -= 10
            warnings.append(f"Moderate forecast error (MAPE {round(forecast_mape * 100, 1)}%, limit 15%). -10")

    score = max(score, 0)
    if score >= 80:
        grade = "HIGH READINESS"
    elif score >= 50:
        grade = "MEDIUM READINESS"
    else:
        grade = "LOW READINESS (Proceed with caution)"
    return {"score": score, "grade": grade, "warnings": warnings}


def readiness_from_dataframe(df, date_col=None, forecast_mape=None, today=None):
    """Convenience helper for Kadambini's cleaned pandas tables."""
    import pandas as pd
    rows = len(df)
    missing = float(df.isna().sum().sum() / df.size) if df.size else 1.0
    days = 0
    if date_col:
        today = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
        days = max((today - pd.to_datetime(df[date_col]).max()).days, 0)
    return evaluate_decision_readiness(rows, missing, days, forecast_mape)
