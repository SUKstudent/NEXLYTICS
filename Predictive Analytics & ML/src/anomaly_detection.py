"""
Anomaly Detection Module for NEXLYTICS.

Identifies operational outliers, revenue drops, expense spikes, and profit drops
in daily aggregated financial time-series using scikit-learn IsolationForest.
Supports optional category-level attribution from transaction details without
data leakage.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Required daily aggregation columns
REQUIRED_DAILY_COLUMNS: List[str] = [
    "transaction_date",
    "daily_revenue",
    "daily_cost",
    "daily_profit",
]

FEATURE_COLUMNS: List[str] = ["daily_revenue", "daily_cost", "daily_profit"]

# Standard anomaly types
ANOMALY_TYPE_REVENUE_DROP: str = "Revenue Drop"
ANOMALY_TYPE_EXPENSE_SPIKE: str = "Expense Spike"
ANOMALY_TYPE_PROFIT_DROP: str = "Profit Drop"
ANOMALY_TYPE_OTHER: str = "Other Anomaly"


def validate_daily_features(df: pd.DataFrame) -> None:
    """Validate that required daily metrics exist and contain finite, non-null values.

    Args:
        df: Daily aggregated DataFrame.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        ValueError: If required columns are missing, or contain null/non-finite values.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")

    missing_cols = [c for c in REQUIRED_DAILY_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required daily columns: {missing_cols}. Available: {list(df.columns)}"
        )

    # Check transaction_date validity
    if df["transaction_date"].isna().any():
        null_idx = df.index[df["transaction_date"].isna()].tolist()
        raise ValueError(
            f"Null transaction_date values detected at index/indices: {null_idx}"
        )

    # Check numeric columns for null, NaN, and +/- Inf
    for col in FEATURE_COLUMNS:
        series = df[col]
        if series.isna().any():
            null_idx = df.index[series.isna()].tolist()
            raise ValueError(
                f"Null or NaN values detected in daily feature '{col}' at index/indices: {null_idx}"
            )

        # Check non-finite (inf, -inf)
        numeric_series = pd.to_numeric(series, errors="coerce")
        if numeric_series.isna().any():
            bad_idx = df.index[numeric_series.isna()].tolist()
            raise ValueError(
                f"Non-numeric values in daily feature '{col}' at index/indices: {bad_idx}"
            )

        inf_mask = np.isinf(numeric_series.values)
        if inf_mask.any():
            inf_idx = df.index[inf_mask].tolist()
            raise ValueError(
                f"Non-finite (inf/-inf) values in daily feature '{col}' at index/indices: {inf_idx}"
            )


def classify_anomaly(
    current_metrics: Dict[str, float],
    historical_ref: Optional[Dict[str, float]],
) -> str:
    """Classify flagged anomaly using strictly historical reference baselines.

    Avoids data leakage by using only prior observations.

    Args:
        current_metrics: Dictionary with daily_revenue, daily_cost, daily_profit.
        historical_ref: Historical median baselines prior to the current date,
            or None if no prior history exists.

    Returns:
        One of: 'Revenue Drop', 'Expense Spike', 'Profit Drop', 'Other Anomaly'.
    """
    if not historical_ref:
        return ANOMALY_TYPE_OTHER

    ref_rev = historical_ref.get("daily_revenue", 0.0)
    ref_cost = historical_ref.get("daily_cost", 0.0)
    ref_profit = historical_ref.get("daily_profit", 0.0)

    cur_rev = current_metrics["daily_revenue"]
    cur_cost = current_metrics["daily_cost"]
    cur_profit = current_metrics["daily_profit"]

    rev_diff = cur_rev - ref_rev
    cost_diff = cur_cost - ref_cost
    profit_diff = cur_profit - ref_profit

    is_rev_drop = rev_diff < 0
    is_cost_spike = cost_diff > 0
    is_profit_drop = profit_diff < 0

    if is_rev_drop and is_cost_spike:
        # Compare relative percentage deviations
        denom_rev = abs(ref_rev) if abs(ref_rev) > 1e-6 else 1.0
        denom_cost = abs(ref_cost) if abs(ref_cost) > 1e-6 else 1.0
        rev_severity = abs(rev_diff) / denom_rev
        cost_severity = cost_diff / denom_cost
        if rev_severity >= cost_severity:
            return ANOMALY_TYPE_REVENUE_DROP
        else:
            return ANOMALY_TYPE_EXPENSE_SPIKE

    if is_rev_drop:
        return ANOMALY_TYPE_REVENUE_DROP

    if is_cost_spike:
        return ANOMALY_TYPE_EXPENSE_SPIKE

    if is_profit_drop:
        return ANOMALY_TYPE_PROFIT_DROP

    return ANOMALY_TYPE_OTHER


def identify_top_driver_category(
    anomaly_date: pd.Timestamp,
    anomaly_type: str,
    transactions_df: Optional[pd.DataFrame],
) -> Optional[str]:
    """Identify the category driving an anomaly on a given date from transaction details.

    Compares category performance on the anomaly date against historical
    daily averages strictly before that date (avoiding data leakage).
    Treats findings as supporting clues, not proven causes.

    Args:
        anomaly_date: Date of the flagged anomaly.
        anomaly_type: Classification string of the anomaly.
        transactions_df: Cleaned transaction-level DataFrame (Phase 2 output).

    Returns:
        Name of top driver category or None if context is missing or undetermined.
    """
    if transactions_df is None or transactions_df.empty:
        return None

    required_cols = ["transaction_date", "category", "revenue", "cost", "profit"]
    if any(col not in transactions_df.columns for col in required_cols):
        return None

    # Filter transactions on the target date
    target_dates = pd.to_datetime(transactions_df["transaction_date"]).dt.normalize()
    norm_anomaly_date = pd.to_datetime(anomaly_date).normalize()

    day_txns = transactions_df[target_dates == norm_anomaly_date]
    if day_txns.empty:
        return None

    # Historical transactions strictly prior to the anomaly date
    hist_txns = transactions_df[target_dates < norm_anomaly_date]

    # Aggregate current day by category
    day_cat = day_txns.groupby("category", as_index=False).agg(
        day_revenue=("revenue", "sum"),
        day_cost=("cost", "sum"),
        day_profit=("profit", "sum"),
    )

    if hist_txns.empty:
        # If no prior history, attribute to the largest contributor on that day
        if anomaly_type == ANOMALY_TYPE_EXPENSE_SPIKE:
            return str(day_cat.sort_values(by="day_cost", ascending=False).iloc[0]["category"])
        else:
            return str(day_cat.sort_values(by="day_revenue", ascending=False).iloc[0]["category"])

    # Compute historical daily average per category
    hist_days_count = hist_txns["transaction_date"].dt.normalize().nunique()
    hist_days_count = max(hist_days_count, 1)

    hist_cat = hist_txns.groupby("category", as_index=False).agg(
        hist_revenue=("revenue", lambda s: s.sum() / hist_days_count),
        hist_cost=("cost", lambda s: s.sum() / hist_days_count),
        hist_profit=("profit", lambda s: s.sum() / hist_days_count),
    )

    merged = pd.merge(day_cat, hist_cat, on="category", how="outer").fillna(0.0)

    # Attribution logic based on anomaly classification
    if anomaly_type == ANOMALY_TYPE_REVENUE_DROP:
        # Largest negative deviation in revenue (baseline > current)
        merged["rev_drop"] = merged["hist_revenue"] - merged["day_revenue"]
        worst = merged.sort_values(by="rev_drop", ascending=False).iloc[0]
        if worst["rev_drop"] > 0:
            return str(worst["category"])

    elif anomaly_type == ANOMALY_TYPE_EXPENSE_SPIKE:
        # Largest positive deviation in cost (current > baseline)
        merged["cost_spike"] = merged["day_cost"] - merged["hist_cost"]
        worst = merged.sort_values(by="cost_spike", ascending=False).iloc[0]
        if worst["cost_spike"] > 0:
            return str(worst["category"])

    elif anomaly_type == ANOMALY_TYPE_PROFIT_DROP:
        # Largest negative deviation in profit (baseline > current)
        merged["profit_drop"] = merged["hist_profit"] - merged["day_profit"]
        worst = merged.sort_values(by="profit_drop", ascending=False).iloc[0]
        if worst["profit_drop"] > 0:
            return str(worst["category"])

    # Fallback to category with highest total activity volume on that day
    merged["total_impact"] = merged["day_revenue"] + merged["day_cost"]
    top_cat = merged.sort_values(by="total_impact", ascending=False).iloc[0]["category"]
    return str(top_cat) if pd.notna(top_cat) else None


def detect_anomalies(
    data: Any,
    transactions_df: Optional[pd.DataFrame] = None,
    model_type: str = "isolation_forest",
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Detect anomalies in daily financial metrics using IsolationForest.

    Produces a DataFrame with anomaly flags, Yes/No labels, interpretable
    anomaly scores, anomaly types, and optional category driver attribution.

    Anomaly Score Interpretation:
        Defined as `-decision_function(X)`. Higher scores represent greater
        degree of anomalousness / outlier severity. Positive scores (> 0)
        correspond to detected outliers where decision_function < 0.

    Args:
        data: Daily aggregated DataFrame containing 'transaction_date',
            'daily_revenue', 'daily_cost', and 'daily_profit'.
        transactions_df: Optional cleaned transaction details from Phase 2
            to identify category drivers without data leakage.
        model_type: Anomaly detection algorithm ('isolation_forest').
        config: Hyperparameters dictionary. Supported keys:
            - 'contamination' (float, default 0.05)
            - 'random_state' (int, default 42)
            - 'min_history_samples' (int, default 5)

    Returns:
        DataFrame containing:
            - transaction_date
            - daily_revenue
            - daily_cost
            - daily_profit
            - anomaly_score (float, higher = more anomalous)
            - anomaly_flag (int, -1 for anomaly, 1 for inlier)
            - is_anomaly (str, 'Yes' / 'No')
            - anomaly_type (Optional[str], 'Revenue Drop'/'Expense Spike'/'Profit Drop'/'Other Anomaly'/None)
            - top_driver_category (Optional[str])

    Raises:
        TypeError: If data is not a pandas DataFrame.
        ValueError: If required columns are missing or contain nonfinite values.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(data).__name__}")

    output_columns = [
        "transaction_date",
        "daily_revenue",
        "daily_cost",
        "daily_profit",
        "anomaly_score",
        "anomaly_flag",
        "is_anomaly",
        "anomaly_type",
        "top_driver_category",
    ]

    # Handle empty DataFrame gracefully
    if data.empty:
        return pd.DataFrame(columns=output_columns)

    # Validate input schema and values
    validate_daily_features(data)

    config = config or {}
    contamination = float(config.get("contamination", 0.05))
    random_state = int(config.get("random_state", 42))
    min_history_samples = int(config.get("min_history_samples", 5))

    # Sort chronologically to prevent temporal data leakage
    df = data.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.normalize()
    df = df.sort_values(by="transaction_date").reset_index(drop=True)

    n_samples = len(df)

    # Handle insufficient history gracefully
    if n_samples < min_history_samples:
        result_df = df.copy()
        result_df["anomaly_score"] = 0.0
        result_df["anomaly_flag"] = 1
        result_df["is_anomaly"] = "No"
        result_df["anomaly_type"] = None
        result_df["top_driver_category"] = None
        return result_df[output_columns]

    X = df[FEATURE_COLUMNS].to_numpy(dtype=float)

    # Check if features are constant
    is_constant = np.all(np.isclose(X, X[0, :], atol=1e-8))
    if is_constant:
        result_df = df.copy()
        result_df["anomaly_score"] = 0.0
        result_df["anomaly_flag"] = 1
        result_df["is_anomaly"] = "No"
        result_df["anomaly_type"] = None
        result_df["top_driver_category"] = None
        return result_df[output_columns]

    # Fit IsolationForest
    # Clamp contamination to valid range for small n_samples if necessary
    clamped_contamination = min(max(contamination, 0.01), 0.5)

    model = IsolationForest(
        contamination=clamped_contamination,
        random_state=random_state,
        n_estimators=100,
    )
    model.fit(X)

    # -1 = anomaly, 1 = normal
    flags = model.predict(X)

    # Interpretable anomaly score: -decision_function(X) -> higher means more anomalous
    scores = -model.decision_function(X)

    df["anomaly_flag"] = flags
    df["is_anomaly"] = np.where(flags == -1, "Yes", "No")
    df["anomaly_score"] = np.round(scores, 4)

    # Classify anomalies and attribute category drivers
    anomaly_types: List[Optional[str]] = []
    top_categories: List[Optional[str]] = []

    for i in range(n_samples):
        row = df.iloc[i]
        if row["is_anomaly"] == "Yes":
            # Historical reference using strictly prior dates (no future leakage)
            if i > 0:
                prior_df = df.iloc[:i]
                hist_ref = {
                    "daily_revenue": float(prior_df["daily_revenue"].median()),
                    "daily_cost": float(prior_df["daily_cost"].median()),
                    "daily_profit": float(prior_df["daily_profit"].median()),
                }
            else:
                hist_ref = None

            cur_metrics = {
                "daily_revenue": float(row["daily_revenue"]),
                "daily_cost": float(row["daily_cost"]),
                "daily_profit": float(row["daily_profit"]),
            }

            a_type = classify_anomaly(cur_metrics, hist_ref)
            top_cat = identify_top_driver_category(
                anomaly_date=row["transaction_date"],
                anomaly_type=a_type,
                transactions_df=transactions_df,
            )

            anomaly_types.append(a_type)
            top_categories.append(top_cat)
        else:
            # Never label normal days as anomalous
            anomaly_types.append(None)
            top_categories.append(None)

    df["anomaly_type"] = pd.Series(anomaly_types, dtype=object)
    df["top_driver_category"] = pd.Series(top_categories, dtype=object)

    return df[output_columns]
