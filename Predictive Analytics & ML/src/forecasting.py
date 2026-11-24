"""
Forecasting Module for NEXLYTICS.

Provides leakage-safe feature engineering, chronological train/test splitting,
recursive walk-forward forecasting, uncertainty intervals, and naive baseline
comparisons for daily sales revenue.
Compatible with Python 3.13+ and scikit-learn LinearRegression.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

REQUIRED_DAILY_COLUMNS: List[str] = ["transaction_date", "daily_revenue"]
FEATURE_NAMES: List[str] = ["day_of_week", "lag_1_revenue", "rolling_7_mean"]
MIN_ROLLING_WINDOW: int = 7
DEFAULT_HORIZON: int = 7
MIN_REQUIRED_DAYS: int = 20  # 7 window days + minimum train (10) + minimum test (3)


@dataclass
class ForecastResult:
    """Structured container for sales forecasting results and metadata.

    Attributes:
        forecast_df: Unified DataFrame containing test evaluation and future predictions
            with columns ['forecast_date', 'actual_revenue', 'predicted_revenue',
            'lower_bound', 'upper_bound', 'naive_revenue'].
        test_df: Test period evaluation DataFrame.
        future_df: Multi-step future forecast DataFrame (actual_revenue is NaN).
        model: Trained scikit-learn LinearRegression estimator.
        metadata: Dictionary containing training parameters, coefficients, metrics,
            and validation uncertainty details.
    """

    forecast_df: pd.DataFrame
    test_df: pd.DataFrame
    future_df: pd.DataFrame
    model: LinearRegression
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_forecasting_data(df: pd.DataFrame) -> None:
    """Validate input time series for sales forecasting.

    Ensures presence of required columns, chronological completeness,
    absence of duplicate dates, absence of nulls/nonfinite values,
    and sufficient historical observation length.

    Args:
        df: Daily aggregated DataFrame.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        ValueError: If columns are missing, values are nonfinite or null,
            dates are duplicated, calendar days are missing, or history is insufficient.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")

    for col in REQUIRED_DAILY_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required forecasting column: '{col}'")

    if len(df) < MIN_REQUIRED_DAYS:
        raise ValueError(
            f"Insufficient history for forecasting: requires at least {MIN_REQUIRED_DAYS} "
            f"consecutive daily observations, got {len(df)}."
        )

    # Validate dates
    raw_dates = pd.to_datetime(df["transaction_date"], errors="coerce")
    if raw_dates.isna().any():
        bad_idx = df.index[raw_dates.isna()].tolist()
        raise ValueError(f"Null or invalid transaction_date at index/indices: {bad_idx}")

    norm_dates = raw_dates.dt.normalize()
    if norm_dates.duplicated().any():
        dupe_dates = norm_dates[norm_dates.duplicated()].unique().tolist()
        raise ValueError(f"Duplicate calendar dates detected in input series: {dupe_dates}")

    # Validate strict chronological order
    if not norm_dates.is_monotonic_increasing:
        raise ValueError("Input DataFrame dates must be sorted in strictly ascending chronological order.")

    # Validate calendar continuity (no missing dates)
    date_diffs = norm_dates.diff().dropna()
    expected_diff = pd.Timedelta(days=1)
    if not (date_diffs == expected_diff).all():
        gap_indices = df.index[1:][date_diffs != expected_diff].tolist()
        raise ValueError(
            f"Incomplete daily series detected. Dates must be continuous consecutive calendar days "
            f"without missing dates. Found discontinuity around row index/indices: {gap_indices}"
        )

    # Validate revenue values
    revenue = pd.to_numeric(df["daily_revenue"], errors="coerce")
    if revenue.isna().any():
        bad_rev = df.index[revenue.isna()].tolist()
        raise ValueError(f"Null, NaN, or non-numeric daily_revenue at index/indices: {bad_rev}")

    if np.isinf(revenue.values).any():
        inf_rev = df.index[np.isinf(revenue.values)].tolist()
        raise ValueError(f"Non-finite (inf/-inf) daily_revenue at index/indices: {inf_rev}")


def build_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create leakage-safe lag and rolling features for daily revenue.

    Uses shift(1) to ensure features at date t access only observations strictly
    prior to date t.

    Features created:
        - day_of_week: Day of week integer (0=Monday, 6=Sunday)
        - lag_1_revenue: Revenue at t-1 via shift(1)
        - rolling_7_mean: 7-day rolling average of revenue ending at t-1 via shift(1).rolling(7)

    Args:
        df: Validated daily DataFrame with 'transaction_date' and 'daily_revenue'.

    Returns:
        DataFrame containing original data plus feature columns, with initial NaN
        window rows dropped.
    """
    out = df.copy()
    out["transaction_date"] = pd.to_datetime(out["transaction_date"]).dt.normalize()

    # Feature 1: day_of_week
    if hasattr(out["transaction_date"].dt, "day_of_week"):
        out["day_of_week"] = out["transaction_date"].dt.day_of_week.astype(float)
    else:
        out["day_of_week"] = out["transaction_date"].dt.dayofweek.astype(float)

    # Feature 2: lag_1_revenue
    out["lag_1_revenue"] = out["daily_revenue"].shift(1).astype(float)

    # Feature 3: rolling_7_mean using shift(1) to avoid current-day leakage
    out["rolling_7_mean"] = (
        out["daily_revenue"].shift(1).rolling(window=MIN_ROLLING_WINDOW, min_periods=MIN_ROLLING_WINDOW).mean()
    )

    # Drop the first 7 rows that do not have full rolling history
    usable_df = out.dropna(subset=FEATURE_NAMES).reset_index(drop=True)
    return usable_df


def _predict_step(
    model: LinearRegression,
    date: pd.Timestamp,
    lag_1: float,
    rolling_7: float,
    clamp_nonnegative: bool = True,
) -> float:
    """Predict single step with LinearRegression and apply conservative negative policy.

    Policy:
        If historical revenue is nonnegative, negative model predictions are
        clamped to 0.0 because negative revenue is not physically/economically
        meaningful in transaction records.
    """
    dow = float(date.day_of_week if hasattr(date, "day_of_week") else date.dayofweek)
    df_step = pd.DataFrame(
        [[dow, float(lag_1), float(rolling_7)]],
        columns=FEATURE_NAMES,
    )
    raw_pred = float(model.predict(df_step)[0])
    if clamp_nonnegative:
        return max(0.0, raw_pred)
    return raw_pred


def _compute_training_uncertainty(
    train_df: pd.DataFrame,
    clamp_nonnegative: bool = True,
) -> float:
    """Compute MAE uncertainty margin using training-only chronological validation.

    Splits the training observations chronologically (earliest 75% for fitting,
    latest 25% for recursive evaluation) to prevent test-set leakage.

    Returns:
        MAE uncertainty margin (1.96 * validation MAE).
    """
    n_train = len(train_df)
    sub_split = int(np.floor(0.75 * n_train))
    sub_split = max(sub_split, MIN_ROLLING_WINDOW + 2)

    sub_train = train_df.iloc[:sub_split]
    sub_val = train_df.iloc[sub_split:]

    if len(sub_val) < 2:
        # Fallback to in-sample residual MAE if sub-split is too small
        m = LinearRegression().fit(train_df[FEATURE_NAMES], train_df["daily_revenue"])
        preds = m.predict(train_df[FEATURE_NAMES])
        if clamp_nonnegative:
            preds = np.maximum(0.0, preds)
        mae = float(mean_absolute_error(train_df["daily_revenue"], preds))
        return max(1.96 * mae, 1e-4)

    # Fit sub-model on sub_train
    sub_model = LinearRegression().fit(sub_train[FEATURE_NAMES], sub_train["daily_revenue"])

    # Walk-forward recursive evaluation on sub_val
    history_rev = list(sub_train["daily_revenue"].values[-MIN_ROLLING_WINDOW:])
    sub_preds: List[float] = []

    for i in range(len(sub_val)):
        val_date = sub_val.iloc[i]["transaction_date"]
        lag_1 = history_rev[-1]
        rolling_7 = float(np.mean(history_rev[-MIN_ROLLING_WINDOW:]))

        pred = _predict_step(sub_model, val_date, lag_1, rolling_7, clamp_nonnegative)
        sub_preds.append(pred)
        history_rev.append(pred)

    val_mae = float(mean_absolute_error(sub_val["daily_revenue"], sub_preds))
    return max(1.96 * val_mae, 1e-4)


def train_forecast_model(
    data: Any,
    target_column: str = "daily_revenue",
    config: Optional[Dict[str, Any]] = None,
) -> ForecastResult:
    """Train LinearRegression forecasting pipeline on daily revenue.

    Chronologically splits data into earliest 80% train and latest 20% test.
    Performs recursive walk-forward prediction on the test set, compares
    against a naive last-observed-value baseline, computes training-only
    uncertainty margins, and generates a multi-step future forecast.

    Args:
        data: Validated daily DataFrame from Phase 2.
        target_column: Target column to forecast ('daily_revenue').
        config: Configuration parameters:
            - 'horizon' (int, default 7): Future forecast days.
            - 'clamp_nonnegative' (bool, default True): Clamp negative predictions to 0.

    Returns:
        ForecastResult object containing unified forecast DataFrame,
        test evaluation DataFrame, future forecast DataFrame, fitted model,
        and evaluation metadata.

    Raises:
        ValueError: On data validation or schema errors.
    """
    validate_forecasting_data(data)

    config = config or {}
    horizon = int(config.get("horizon", DEFAULT_HORIZON))
    clamp_nonnegative = bool(config.get("clamp_nonnegative", True))

    # Build leakage-safe features
    usable_df = build_lag_features(data)
    n_usable = len(usable_df)

    # Chronological 80/20 train/test split without shuffling
    train_size = int(np.floor(0.80 * n_usable))
    train_df = usable_df.iloc[:train_size].copy().reset_index(drop=True)
    test_df = usable_df.iloc[train_size:].copy().reset_index(drop=True)

    if len(test_df) < 1:
        raise ValueError("Test set is empty after 80/20 chronological split.")

    # Fit final model on 80% training data
    model = LinearRegression()
    model.fit(train_df[FEATURE_NAMES], train_df[target_column])

    # Compute training-only uncertainty margin
    uncertainty_margin = _compute_training_uncertainty(train_df, clamp_nonnegative)

    # Naive baseline for test set: last observed revenue in the training set
    naive_baseline_test = float(train_df["daily_revenue"].iloc[-1])

    # 1. Walk-forward recursive prediction across test set
    # Maintain a sliding history of the last 7 observed/predicted revenues
    test_history = list(train_df["daily_revenue"].values[-MIN_ROLLING_WINDOW:])
    test_preds: List[float] = []

    for i in range(len(test_df)):
        cur_date = test_df.iloc[i]["transaction_date"]
        lag_1 = test_history[-1]
        rolling_7 = float(np.mean(test_history[-MIN_ROLLING_WINDOW:]))

        pred = _predict_step(model, cur_date, lag_1, rolling_7, clamp_nonnegative)
        test_preds.append(pred)
        # Update history with prediction recursively (no test actual leakage)
        test_history.append(pred)

    test_eval_df = pd.DataFrame(
        {
            "forecast_date": test_df["transaction_date"],
            "actual_revenue": test_df["daily_revenue"].astype(float),
            "predicted_revenue": np.round(test_preds, 4),
            "lower_bound": np.maximum(0.0 if clamp_nonnegative else -np.inf, np.round(np.array(test_preds) - uncertainty_margin, 4)),
            "upper_bound": np.round(np.array(test_preds) + uncertainty_margin, 4),
            "naive_revenue": naive_baseline_test,
        }
    )

    # 2. Genuine multi-step future forecast beyond last observed date
    last_observed_date = pd.to_datetime(usable_df["transaction_date"].iloc[-1])
    last_observed_revenue = float(usable_df["daily_revenue"].iloc[-1])
    future_history = list(usable_df["daily_revenue"].values[-MIN_ROLLING_WINDOW:])

    future_dates: List[pd.Timestamp] = []
    future_preds: List[float] = []

    for step in range(1, horizon + 1):
        f_date = last_observed_date + pd.Timedelta(days=step)
        f_lag_1 = future_history[-1]
        f_rolling_7 = float(np.mean(future_history[-MIN_ROLLING_WINDOW:]))

        f_pred = _predict_step(model, f_date, f_lag_1, f_rolling_7, clamp_nonnegative)
        future_dates.append(f_date)
        future_preds.append(f_pred)
        future_history.append(f_pred)

    future_forecast_df = pd.DataFrame(
        {
            "forecast_date": future_dates,
            "actual_revenue": np.nan,  # Null for future
            "predicted_revenue": np.round(future_preds, 4),
            "lower_bound": np.maximum(0.0 if clamp_nonnegative else -np.inf, np.round(np.array(future_preds) - uncertainty_margin, 4)),
            "upper_bound": np.round(np.array(future_preds) + uncertainty_margin, 4),
            "naive_revenue": last_observed_revenue,
        }
    )

    # Unified DataFrame combining test evaluation and future forecast
    combined_forecast_df = pd.concat([test_eval_df, future_forecast_df], ignore_index=True)

    metadata: Dict[str, Any] = {
        "model_type": "LinearRegression",
        "coefficients": {name: float(coef) for name, coef in zip(FEATURE_NAMES, model.coef_)},
        "intercept": float(model.intercept_),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "train_date_range": (train_df["transaction_date"].min(), train_df["transaction_date"].max()),
        "test_date_range": (test_df["transaction_date"].min(), test_df["transaction_date"].max()),
        "future_date_range": (future_dates[0], future_dates[-1]),
        "uncertainty_margin": float(uncertainty_margin),
        "naive_baseline_test_value": naive_baseline_test,
        "naive_baseline_future_value": last_observed_revenue,
        "horizon": horizon,
        "clamp_nonnegative": clamp_nonnegative,
    }

    return ForecastResult(
        forecast_df=combined_forecast_df,
        test_df=test_eval_df,
        future_df=future_forecast_df,
        model=model,
        metadata=metadata,
    )


def generate_forecast(
    model: Any,
    horizon: int = DEFAULT_HORIZON,
    **kwargs: Any,
) -> pd.DataFrame:
    """Generate forward-looking predictions for a given horizon.

    Supports calling with an existing ForecastResult object or model object.
    If a ForecastResult is provided and matches the horizon, returns future_df.
    Otherwise runs forecast pipeline with provided data.

    Args:
        model: ForecastResult or trained model.
        horizon: Forecast horizon steps.
        **kwargs: Additional parameters including 'data' or 'config'.

    Returns:
        DataFrame containing future forecast schema:
            ['forecast_date', 'actual_revenue', 'predicted_revenue',
            'lower_bound', 'upper_bound', 'naive_revenue']
    """
    if isinstance(model, ForecastResult):
        if model.metadata.get("horizon") == horizon:
            return model.future_df
        # If horizon differs, re-run with original data if provided in kwargs
        if "data" in kwargs:
            res = train_forecast_model(kwargs["data"], config={"horizon": horizon})
            return res.future_df
        return model.future_df

    if "data" in kwargs:
        res = train_forecast_model(kwargs["data"], config={"horizon": horizon})
        return res.future_df

    raise ValueError("generate_forecast requires a ForecastResult or 'data' argument in kwargs.")
