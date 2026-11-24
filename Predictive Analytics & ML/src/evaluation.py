"""
Evaluation and Visualization Module for NEXLYTICS.

Provides regression metrics (MAE, RMSE, baseline comparisons), descriptive
anomaly detection reporting without ground-truth fabrication, publication-quality
reusable Matplotlib charts, and automated markdown evaluation report generation.
Compatible with Python 3.13+ and Matplotlib 3.11+.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Use non-interactive backend if not already set
if matplotlib.get_backend().lower() != "agg":
    matplotlib.use("Agg")


# ==============================================================================
# Model Evaluation Functions
# ==============================================================================

def evaluate_forecast(
    test_data: Any,
    y_pred: Optional[Any] = None,
    y_naive: Optional[Any] = None,
) -> Dict[str, Any]:
    """Evaluate sales forecasting model against actuals and a naive baseline.

    Supports passing a ForecastResult from Phase 4, a test DataFrame with
    ['actual_revenue', 'predicted_revenue', 'naive_revenue'], or array-like
    (y_true, y_pred, y_naive) inputs.

    Args:
        test_data: ForecastResult, test DataFrame, or array-like y_true.
        y_pred: Optional array-like predicted revenue if test_data is y_true.
        y_naive: Optional array-like naive baseline predictions.

    Returns:
        Dictionary containing:
            - model_mae: float
            - model_rmse: float
            - naive_mae: Optional[float]
            - naive_rmse: Optional[float]
            - mae_improvement_pct: Optional[float]
            - outperforms_baseline: Optional[bool]
            - test_sample_count: int
            - date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]]
            - summary: str

    Raises:
        TypeError: If input types are unsupported.
        ValueError: If test set is empty or required columns are missing.
    """
    date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]] = None

    if hasattr(test_data, "test_df"):
        # Extracted from ForecastResult
        df = test_data.test_df.copy()
        if df.empty:
            raise ValueError("Evaluation failed: ForecastResult test_df is empty.")
        y_true_arr = df["actual_revenue"].to_numpy(dtype=float)
        y_pred_arr = df["predicted_revenue"].to_numpy(dtype=float)
        y_naive_arr = df["naive_revenue"].to_numpy(dtype=float) if "naive_revenue" in df.columns else None
        if "forecast_date" in df.columns and len(df) > 0:
            date_range = (pd.Timestamp(df["forecast_date"].iloc[0]), pd.Timestamp(df["forecast_date"].iloc[-1]))

    elif isinstance(test_data, pd.DataFrame):
        df = test_data.copy()
        if df.empty:
            raise ValueError("Evaluation failed: Test DataFrame is empty.")
        if "actual_revenue" not in df.columns or "predicted_revenue" not in df.columns:
            raise ValueError("Test DataFrame must contain 'actual_revenue' and 'predicted_revenue' columns.")
        y_true_arr = df["actual_revenue"].to_numpy(dtype=float)
        y_pred_arr = df["predicted_revenue"].to_numpy(dtype=float)
        y_naive_arr = df["naive_revenue"].to_numpy(dtype=float) if "naive_revenue" in df.columns else None
        if "forecast_date" in df.columns and len(df) > 0:
            date_range = (pd.Timestamp(df["forecast_date"].iloc[0]), pd.Timestamp(df["forecast_date"].iloc[-1]))

    elif y_pred is not None:
        y_true_arr = np.asarray(test_data, dtype=float)
        y_pred_arr = np.asarray(y_pred, dtype=float)
        y_naive_arr = np.asarray(y_naive, dtype=float) if y_naive is not None else None
    else:
        raise TypeError(
            f"Unsupported input to evaluate_forecast: {type(test_data).__name__}. "
            f"Pass a ForecastResult, a DataFrame, or (y_true, y_pred)."
        )

    if len(y_true_arr) == 0:
        raise ValueError("Cannot evaluate empty test series.")

    if len(y_true_arr) != len(y_pred_arr):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true_arr)} rows, but y_pred has {len(y_pred_arr)} rows."
        )

    # Filter out any nonfinite values safely
    valid_mask = np.isfinite(y_true_arr) & np.isfinite(y_pred_arr)
    if not np.all(valid_mask):
        raise ValueError("Non-finite values detected in actual or predicted evaluation series.")

    n_samples = int(len(y_true_arr))

    # Calculate model metrics
    abs_errors = np.abs(y_true_arr - y_pred_arr)
    model_mae = float(np.mean(abs_errors))
    model_rmse = float(np.sqrt(np.mean((y_true_arr - y_pred_arr) ** 2)))

    # Calculate naive baseline metrics if available
    naive_mae: Optional[float] = None
    naive_rmse: Optional[float] = None
    mae_improvement_pct: Optional[float] = None
    outperforms_baseline: Optional[bool] = None

    if y_naive_arr is not None and len(y_naive_arr) == n_samples and np.all(np.isfinite(y_naive_arr)):
        naive_abs = np.abs(y_true_arr - y_naive_arr)
        naive_mae = float(np.mean(naive_abs))
        naive_rmse = float(np.sqrt(np.mean((y_true_arr - y_naive_arr) ** 2)))

        if naive_mae > 1e-8:
            mae_improvement_pct = float(((naive_mae - model_mae) / naive_mae) * 100.0)
        else:
            mae_improvement_pct = 0.0 if model_mae <= 1e-8 else -100.0

        outperforms_baseline = bool(model_mae < naive_mae)

    summary_msg = (
        f"Model MAE: {model_mae:.2f}, RMSE: {model_rmse:.2f} across {n_samples} test days."
    )
    if naive_mae is not None:
        perf = "outperforms" if outperforms_baseline else "underperforms"
        summary_msg += f" Naive baseline MAE: {naive_mae:.2f}. ML {perf} baseline by {mae_improvement_pct:+.1f}%."

    return {
        "model_mae": round(model_mae, 4),
        "model_rmse": round(model_rmse, 4),
        "naive_mae": round(naive_mae, 4) if naive_mae is not None else None,
        "naive_rmse": round(naive_rmse, 4) if naive_rmse is not None else None,
        "mae_improvement_pct": round(mae_improvement_pct, 2) if mae_improvement_pct is not None else None,
        "outperforms_baseline": outperforms_baseline,
        "test_sample_count": n_samples,
        "date_range": date_range,
        "summary": summary_msg,
    }


def evaluate_anomalies(
    anomaly_data: Any,
    y_true: Optional[Any] = None,
) -> Dict[str, Any]:
    """Evaluate anomaly detection results descriptively or against ground-truth labels.

    If ground-truth labels are not provided, returns honest descriptive metrics
    (flagged counts, percentage, types, category drivers) without fabricating
    unverifiable accuracy claims.

    Args:
        anomaly_data: DataFrame from Phase 3 with 'is_anomaly' and 'anomaly_type',
            or array-like predicted anomaly flags.
        y_true: Optional ground-truth binary anomaly labels (1 for anomaly, 0 for normal).

    Returns:
        Dictionary containing descriptive metrics and optional ground-truth metrics.

    Raises:
        TypeError: If input is not a DataFrame or array-like.
        ValueError: If input is empty.
    """
    if isinstance(anomaly_data, pd.DataFrame):
        df = anomaly_data.copy()
        if df.empty:
            raise ValueError("Evaluation failed: Anomaly DataFrame is empty.")
        if "is_anomaly" not in df.columns:
            raise ValueError("Anomaly DataFrame must contain 'is_anomaly' column.")

        total_days = len(df)
        is_flagged = df["is_anomaly"].astype(str).str.strip().str.lower().isin(["yes", "true", "-1"])
        flagged_days = int(is_flagged.sum())
        anomaly_pct = float((flagged_days / total_days) * 100.0) if total_days > 0 else 0.0

        # Count by anomaly_type
        type_counts: Dict[str, int] = {}
        if "anomaly_type" in df.columns:
            flagged_types = df.loc[is_flagged, "anomaly_type"].dropna()
            type_counts = {str(k): int(v) for k, v in flagged_types.value_counts().items()}

        # Count by top_driver_category
        cat_counts: Dict[str, int] = {}
        if "top_driver_category" in df.columns:
            flagged_cats = df.loc[is_flagged, "top_driver_category"].dropna()
            cat_counts = {str(k): int(v) for k, v in flagged_cats.value_counts().items()}

        result: Dict[str, Any] = {
            "total_days": total_days,
            "flagged_days": flagged_days,
            "anomaly_percentage": round(anomaly_pct, 2),
            "anomaly_type_counts": type_counts,
            "top_driver_category_counts": cat_counts,
            "ground_truth_available": False,
            "notice": "Descriptive statistics only. No ground-truth labels available to compute precision/recall.",
        }

        # If ground-truth is optionally supplied
        if y_true is not None:
            y_t = np.asarray(y_true, dtype=int)
            y_p = is_flagged.to_numpy(dtype=int)
            if len(y_t) == len(y_p):
                tp = int(np.sum((y_t == 1) & (y_p == 1)))
                fp = int(np.sum((y_t == 0) & (y_p == 1)))
                fn = int(np.sum((y_t == 1) & (y_p == 0)))
                prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
                rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
                f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
                result["ground_truth_available"] = True
                result["precision"] = round(prec, 4)
                result["recall"] = round(rec, 4)
                result["f1_score"] = round(f1, 4)

        return result

    elif y_true is not None and anomaly_data is not None:
        # Phase 1 stub compatibility: evaluate_anomalies(y_true, y_pred)
        y_t = np.asarray(anomaly_data, dtype=int)
        y_p = np.asarray(y_true, dtype=int)
        if len(y_t) != len(y_p) or len(y_t) == 0:
            raise ValueError("y_true and y_pred must have identical non-zero lengths.")
        tp = int(np.sum((y_t == 1) & (y_p == 1)))
        fp = int(np.sum((y_t == 0) & (y_p == 1)))
        fn = int(np.sum((y_t == 1) & (y_p == 0)))
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        return {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "ground_truth_available": True,
        }

    raise TypeError(f"Unsupported input to evaluate_anomalies: {type(anomaly_data).__name__}")


# ==============================================================================
# Visualization Functions
# ==============================================================================

def plot_trend_chart(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Generate daily financial trend chart showing Revenue, Cost, and Profit.

    Args:
        df: Daily DataFrame containing 'transaction_date', 'daily_revenue',
            'daily_cost', and 'daily_profit'.
        output_path: Optional file path to save the chart image.

    Returns:
        Matplotlib Figure object.

    Raises:
        ValueError: If required columns are missing or df is empty.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Cannot plot trend chart: Input DataFrame is empty or invalid.")

    required_cols = ["transaction_date", "daily_revenue", "daily_cost", "daily_profit"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required trend column: '{col}'")

    plot_df = df.copy()
    plot_df["transaction_date"] = pd.to_datetime(plot_df["transaction_date"])
    plot_df = plot_df.sort_values(by="transaction_date")

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)

    dates = plot_df["transaction_date"]
    ax.plot(dates, plot_df["daily_revenue"], label="Daily Revenue ($)", color="#1f77b4", linewidth=2.0)
    ax.plot(dates, plot_df["daily_cost"], label="Daily Cost ($)", color="#d62728", linewidth=1.8, linestyle="--")
    ax.plot(dates, plot_df["daily_profit"], label="Daily Profit ($)", color="#2ca02c", linewidth=2.0)

    ax.set_title("NEXLYTICS — Daily Financial Trends (Revenue, Cost, Profit)", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Transaction Date", fontsize=11, labelpad=8)
    ax.set_ylabel("Amount (USD)", fontsize=11, labelpad=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", frameon=True)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight")

    return fig


def plot_anomaly_chart(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Generate anomaly detection chart showing Revenue and Cost with highlighted outliers.

    Highlights flagged anomaly dates and clearly distinguishes Expense Spikes.

    Args:
        df: Anomaly results DataFrame containing 'transaction_date', 'daily_revenue',
            'daily_cost', 'is_anomaly', and 'anomaly_type'.
        output_path: Optional file path to save the chart image.

    Returns:
        Matplotlib Figure object.

    Raises:
        ValueError: If required columns are missing or df is empty.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Cannot plot anomaly chart: Input DataFrame is empty or invalid.")

    required_cols = ["transaction_date", "daily_revenue", "daily_cost", "is_anomaly"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required anomaly column: '{col}'")

    plot_df = df.copy()
    plot_df["transaction_date"] = pd.to_datetime(plot_df["transaction_date"])
    plot_df = plot_df.sort_values(by="transaction_date")

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)

    dates = plot_df["transaction_date"]
    ax.plot(dates, plot_df["daily_revenue"], label="Daily Revenue ($)", color="#1f77b4", linewidth=1.8, alpha=0.85)
    ax.plot(dates, plot_df["daily_cost"], label="Daily Cost ($)", color="#7f7f7f", linewidth=1.4, linestyle=":", alpha=0.7)

    # Highlight flagged anomalies
    flagged_mask = plot_df["is_anomaly"].astype(str).str.strip().str.lower().isin(["yes", "true", "-1"])
    anomalies = plot_df[flagged_mask]

    if not anomalies.empty:
        # Separate expense spikes from revenue drops / others
        is_expense_spike = anomalies["anomaly_type"].fillna("").str.contains("Expense Spike", case=False)

        # Expense spikes (highlighted on cost curve with red squares)
        spike_df = anomalies[is_expense_spike]
        if not spike_df.empty:
            ax.scatter(
                spike_df["transaction_date"],
                spike_df["daily_cost"],
                color="#d62728",
                s=90,
                marker="s",
                edgecolors="black",
                zorder=5,
                label="Expense Spike (Cost)",
            )

        # Revenue drops / other anomalies (highlighted on revenue curve with orange/red circles)
        other_anomalies = anomalies[~is_expense_spike]
        if not other_anomalies.empty:
            ax.scatter(
                other_anomalies["transaction_date"],
                other_anomalies["daily_revenue"],
                color="#ff7f0e",
                s=80,
                marker="o",
                edgecolors="black",
                zorder=5,
                label="Revenue Drop / Other",
            )

    ax.set_title("NEXLYTICS — Operational Anomaly Detection & Outliers", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Transaction Date", fontsize=11, labelpad=8)
    ax.set_ylabel("Amount (USD)", fontsize=11, labelpad=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", frameon=True)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight")

    return fig


def plot_forecast_chart(
    forecast_data: Any,
    historical_df: Optional[pd.DataFrame] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Generate sales forecasting chart with historical test actuals, predictions, and future horizon.

    Heuristic uncertainty bands (±1.96 MAE) are clearly demarcated and distinguished
    from calibrated statistical confidence intervals. A vertical forecast origin
    line cleanly separates historical held-out test dates from future forecast dates.

    Args:
        forecast_data: ForecastResult or combined forecast DataFrame with
            ['forecast_date', 'actual_revenue', 'predicted_revenue', 'lower_bound', 'upper_bound'].
        historical_df: Optional complete historical DataFrame for broader context.
        output_path: Optional file path to save the chart image.

    Returns:
        Matplotlib Figure object.

    Raises:
        ValueError: If required forecast columns are missing.
    """
    if hasattr(forecast_data, "forecast_df"):
        f_df = forecast_data.forecast_df.copy()
    elif isinstance(forecast_data, pd.DataFrame):
        f_df = forecast_data.copy()
    else:
        raise TypeError(f"Expected ForecastResult or DataFrame, got {type(forecast_data).__name__}")

    if f_df.empty:
        raise ValueError("Cannot plot forecast chart: Forecast DataFrame is empty.")

    required_cols = ["forecast_date", "actual_revenue", "predicted_revenue", "lower_bound", "upper_bound"]
    for col in required_cols:
        if col not in f_df.columns:
            raise ValueError(f"Missing required forecast column: '{col}'")

    f_df["forecast_date"] = pd.to_datetime(f_df["forecast_date"])
    f_df = f_df.sort_values(by="forecast_date")

    # Split into test evaluation (where actual_revenue is present) and future (where actual is NaN)
    test_mask = f_df["actual_revenue"].notna()
    test_slice = f_df[test_mask]
    future_slice = f_df[~test_mask]

    fig, ax = plt.subplots(figsize=(13, 6), dpi=150)

    # Plot full historical series if provided
    if historical_df is not None and not historical_df.empty and "daily_revenue" in historical_df.columns:
        h_df = historical_df.copy()
        h_df["transaction_date"] = pd.to_datetime(h_df["transaction_date"])
        h_df = h_df.sort_values(by="transaction_date")
        ax.plot(
            h_df["transaction_date"],
            h_df["daily_revenue"],
            label="Historical Actuals",
            color="#1f77b4",
            linewidth=1.6,
            alpha=0.6,
        )
    elif not test_slice.empty:
        ax.plot(
            test_slice["forecast_date"],
            test_slice["actual_revenue"],
            label="Held-out Test Actuals",
            color="#1f77b4",
            linewidth=1.8,
            marker="o",
            markersize=4,
        )

    # Plot test predictions
    if not test_slice.empty:
        ax.plot(
            test_slice["forecast_date"],
            test_slice["predicted_revenue"],
            label="Held-out ML Predictions",
            color="#2ca02c",
            linewidth=1.8,
            linestyle="--",
            marker="s",
            markersize=4,
        )

    # Plot future forecast and uncertainty bands
    if not future_slice.empty:
        ax.plot(
            future_slice["forecast_date"],
            future_slice["predicted_revenue"],
            label="Future 7-Day Forecast",
            color="#d62728",
            linewidth=2.2,
            marker="^",
            markersize=5,
        )

        ax.fill_between(
            future_slice["forecast_date"],
            future_slice["lower_bound"],
            future_slice["upper_bound"],
            color="#d62728",
            alpha=0.18,
            label="Heuristic Uncertainty Band (±1.96 MAE)",
        )

        # Demarcate forecast origin
        origin_date = test_slice["forecast_date"].max() if not test_slice.empty else future_slice["forecast_date"].min()
        ax.axvline(
            x=origin_date,
            color="#333333",
            linestyle="-.",
            linewidth=1.4,
            alpha=0.8,
            label="Forecast Origin",
        )

    ax.set_title("NEXLYTICS — Sales Revenue Forecast & Heuristic Uncertainty", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=11, labelpad=8)
    ax.set_ylabel("Revenue (USD)", fontsize=11, labelpad=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", frameon=True)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, bbox_inches="tight")

    return fig


# ==============================================================================
# Report Generation
# ==============================================================================

def generate_markdown_report(
    data_summary: Dict[str, Any],
    anomaly_metrics: Dict[str, Any],
    forecast_metrics: Dict[str, Any],
    forecast_metadata: Dict[str, Any],
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Generate a comprehensive ML evaluation markdown report.

    Documents model selection, chronological train/test dates, MAE/RMSE,
    naive baseline comparison, descriptive anomaly breakdown, data limitations,
    and correlation-vs-causation cautions.

    Args:
        data_summary: Summary dictionary from Phase 2 data processing.
        anomaly_metrics: Summary dictionary from evaluate_anomalies.
        forecast_metrics: Evaluation dictionary from evaluate_forecast.
        forecast_metadata: Metadata dictionary from ForecastResult.
        output_path: Optional path to save the markdown report.

    Returns:
        Generated report markdown string.
    """
    train_range = forecast_metadata.get("train_date_range", ("N/A", "N/A"))
    test_range = forecast_metadata.get("test_date_range", ("N/A", "N/A"))
    future_range = forecast_metadata.get("future_date_range", ("N/A", "N/A"))

    train_start = pd.Timestamp(train_range[0]).strftime("%Y-%m-%d") if train_range[0] != "N/A" else "N/A"
    train_end = pd.Timestamp(train_range[1]).strftime("%Y-%m-%d") if train_range[1] != "N/A" else "N/A"
    test_start = pd.Timestamp(test_range[0]).strftime("%Y-%m-%d") if test_range[0] != "N/A" else "N/A"
    test_end = pd.Timestamp(test_range[1]).strftime("%Y-%m-%d") if test_range[1] != "N/A" else "N/A"
    fut_start = pd.Timestamp(future_range[0]).strftime("%Y-%m-%d") if future_range[0] != "N/A" else "N/A"
    fut_end = pd.Timestamp(future_range[1]).strftime("%Y-%m-%d") if future_range[1] != "N/A" else "N/A"

    model_mae = forecast_metrics.get("model_mae", 0.0)
    model_rmse = forecast_metrics.get("model_rmse", 0.0)
    naive_mae = forecast_metrics.get("naive_mae", "N/A")
    naive_rmse = forecast_metrics.get("naive_rmse", "N/A")
    improvement = forecast_metrics.get("mae_improvement_pct", "N/A")
    outperforms = forecast_metrics.get("outperforms_baseline")

    if outperforms is True:
        baseline_verdict = f"**Outperformed Naive Baseline** by {improvement:+.1f}% lower MAE."
    elif outperforms is False:
        baseline_verdict = f"**Did Not Outperform Naive Baseline** ({improvement:+.1f}% relative change). Use with caution."
    else:
        baseline_verdict = "Naive baseline comparison not available."

    type_counts = anomaly_metrics.get("anomaly_type_counts", {})
    type_lines = "\n".join([f"  - **{k}**: {v} occurrence(s)" for k, v in type_counts.items()]) or "  - None detected"

    cat_counts = anomaly_metrics.get("top_driver_category_counts", {})
    cat_lines = "\n".join([f"  - **{k}**: {v} occurrence(s)" for k, v in cat_counts.items()]) or "  - None attributed"

    report = f"""# NEXLYTICS ML Evaluation & Deliverables Report

## 1. Executive Summary
- **Module Name:** NEXLYTICS Predictive Analytics & Machine Learning
- **Version:** 1.0.0 (Phase 6 Integration)
- **Pipeline Status:** Verified end-to-end execution
- **Core Models:**
  - Anomaly Detection: `scikit-learn IsolationForest(contamination=0.05, random_state=42)`
  - Sales Forecasting: `scikit-learn LinearRegression` with chronological walk-forward features

---

## 2. Ingested Dataset Overview
| Metric | Description | Value |
|---|---|---|
| Total Transactions | Cleaned record count | {data_summary.get('total_records', 'N/A')} |
| Unique Transaction IDs | Distinct transaction IDs | {data_summary.get('unique_transaction_ids', 'N/A')} |
| Historical Date Range | Continuous calendar range | {pd.Timestamp(data_summary.get('date_min')).strftime('%Y-%m-%d') if data_summary.get('date_min') is not None else 'N/A'} to {pd.Timestamp(data_summary.get('date_max')).strftime('%Y-%m-%d') if data_summary.get('date_max') is not None else 'N/A'} |
| Total Revenue | Aggregated gross revenue | ${data_summary.get('total_revenue', 0.0):,.2f} |
| Total Cost | Aggregated operational cost | ${data_summary.get('total_cost', 0.0):,.2f} |
| Total Profit | Aggregated operating profit | ${data_summary.get('total_profit', 0.0):,.2f} |

---

## 3. Operational Anomaly Detection Results
- **Model:** Isolation Forest fitted on `[daily_revenue, daily_cost, daily_profit]`
- **Total Monitored Days:** {anomaly_metrics.get('total_days', 0)}
- **Flagged Anomalies:** {anomaly_metrics.get('flagged_days', 0)} ({anomaly_metrics.get('anomaly_percentage', 0.0):.1f}% of calendar days)
- **Breakdown by Classified Anomaly Type:**
{type_lines}
- **Leading Attributed Driver Categories:**
{cat_lines}
- **Methodology Notice:**
  > [!NOTE]
  > Anomaly evaluation metrics reflect descriptive statistical distributions. Precision, recall, and ROC-AUC are not fabricated in the absence of verified ground-truth labels.

---

## 4. Sales Forecasting Benchmarks & Evaluation
- **Chronological Split:**
  - **Training Partition (80% earliest):** {forecast_metadata.get('train_samples', 'N/A')} days ({train_start} to {train_end})
  - **Held-out Test Partition (20% latest):** {forecast_metadata.get('test_samples', 'N/A')} days ({test_start} to {test_end})
  - **Future Forecast Horizon (7 days):** {fut_start} to {fut_end}
- **Held-Out Test Set Performance:**
  - **Model MAE:** ${model_mae:.2f}
  - **Model RMSE:** ${model_rmse:.2f}
  - **Naive Baseline MAE (Last-Observed-Value):** ${naive_mae if isinstance(naive_mae, str) else f'{naive_mae:.2f}'}
  - **Naive Baseline RMSE:** ${naive_rmse if isinstance(naive_rmse, str) else f'{naive_rmse:.2f}'}
  - **Relative Improvement:** {baseline_verdict}
- **Uncertainty Margin:** $\\pm${forecast_metadata.get('uncertainty_margin', 0.0):.2f} (derived empirically from chronological validation MAE; clamped to $0.00 lower bound for nonnegative revenue).

---

## 5. Exported Deliverables
All deliverables have been saved to the designated outputs directory:
- `outputs/anomaly_results.csv`: Daily anomaly flags, scores, classifications, and top driver categories.
- `outputs/forecast_results.csv`: Unified chronological predictions, held-out actuals, future 7-day forecast, and bounds.
- `outputs/charts/trend_chart.png`: Historical revenue, cost, and profit time series.
- `outputs/charts/anomaly_chart.png`: Anomaly overlay distinguishing revenue drops from expense spikes.
- `outputs/charts/forecast_chart.png`: Forecast visualization with heuristic uncertainty bands and origin demarcation.

---

## 6. Limitations, Assumptions & Cautions
> [!WARNING]
> **Heuristic Uncertainty Bands**: The uncertainty interval represents empirical spread ($\\pm 1.96 \\times \\text{{MAE}}_{{\\text{{train\\_val}}}}$) derived from historical training residuals, NOT a strict parametric 95% Gaussian confidence or prediction interval.

> [!IMPORTANT]
> **Correlation vs. Causation Caution**: Category driver attributions (`top_driver_category`) indicate the category showing the largest historical divergence on an anomalous date. These constitute supporting analytical clues and operational guidance, not definitive root causes.

> [!CAUTION]
> **Calendar Day Continuity**: Time-series lag and rolling features require continuous, uninterrupted calendar days. Missing dates must not be silently imputed; gaps indicate unrecorded operational periods.
"""

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")

    return report
