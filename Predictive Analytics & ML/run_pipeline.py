"""
NEXLYTICS ML End-to-End Execution Pipeline.

CLI Entry Point that coordinates:
1. Data loading and transaction schema validation (Phase 2)
2. Daily calendar aggregation and continuity verification (Phase 2)
3. Outlier and operational anomaly detection (Phase 3)
4. Multi-step sales revenue forecasting (Phase 4)
5. Model evaluation and naive baseline comparison (Phase 5)
6. Visualization generation and deliverable export (Phase 5/6)
7. Dynamic evaluation markdown report generation (Phase 6)
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union

import pandas as pd

from src.data_processing import (
    load_dataset,
    validate_and_clean_transactions,
    aggregate_daily_transactions,
    detect_missing_dates,
)
from src.anomaly_detection import detect_anomalies
from src.forecasting import train_forecast_model, DEFAULT_HORIZON
from src.evaluation import (
    evaluate_forecast,
    evaluate_anomalies,
    plot_trend_chart,
    plot_anomaly_chart,
    plot_forecast_chart,
    generate_markdown_report,
)


def run_pipeline(
    input_path: Union[str, Path],
    output_dir: Union[str, Path] = "outputs",
    report_path: Optional[Union[str, Path]] = "reports/ml_evaluation_report.md",
    horizon: int = DEFAULT_HORIZON,
) -> Dict[str, Any]:
    """Execute the full NEXLYTICS ML pipeline end-to-end.

    Args:
        input_path: Path to raw transaction CSV file.
        output_dir: Directory where CSV and chart deliverables are saved.
        report_path: Optional path to save the generated markdown evaluation report.
        horizon: Forecast horizon steps in days (default: 7).

    Returns:
        Dictionary containing execution summary, metrics, and generated file paths.

    Raises:
        FileNotFoundError: If input_path does not exist.
        ValueError: If validation, calendar continuity, or history requirements fail.
    """
    in_file = Path(input_path)
    out_dir = Path(output_dir)
    out_charts = out_dir / "charts"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_charts.mkdir(parents=True, exist_ok=True)

    print(f"[1/7] Loading dataset from: {in_file}")
    raw_df = load_dataset(in_file)

    print("[2/7] Cleaning transactions and validating schema...")
    cleaned_txns, data_summary = validate_and_clean_transactions(raw_df, allow_duplicate_ids=True)
    print(f"      Verified {data_summary['total_records']} records ({data_summary['unique_transaction_ids']} unique IDs).")

    print("[3/7] Aggregating daily metrics and verifying calendar continuity...")
    daily_df = aggregate_daily_transactions(cleaned_txns)

    # Check for missing calendar dates
    missing_dates = detect_missing_dates(daily_df)
    if missing_dates:
        sample_missing = [d.strftime("%Y-%m-%d") for d in missing_dates[:5]]
        raise ValueError(
            f"Incomplete daily series detected: {len(missing_dates)} missing calendar date(s) found "
            f"between {daily_df['transaction_date'].min().strftime('%Y-%m-%d')} and "
            f"{daily_df['transaction_date'].max().strftime('%Y-%m-%d')}. "
            f"Sample missing dates: {sample_missing}. Continuous daily sequence required."
        )

    print(f"      Aggregated {len(daily_df)} consecutive calendar days.")

    print("[4/7] Running IsolationForest anomaly detection...")
    anomaly_results = detect_anomalies(daily_df, transactions_df=cleaned_txns)
    anomaly_eval = evaluate_anomalies(anomaly_results)
    print(f"      Flagged {anomaly_eval['flagged_days']} anomalous day(s) ({anomaly_eval['anomaly_percentage']}%).")

    print(f"[5/7] Training LinearRegression forecasting model (Horizon: {horizon} days)...")
    forecast_result = train_forecast_model(daily_df, config={"horizon": horizon})
    forecast_eval = evaluate_forecast(forecast_result)
    print(f"      Model MAE: ${forecast_eval['model_mae']:.2f} (Naive Baseline: ${forecast_eval['naive_mae']:.2f}).")

    print("[6/7] Exporting deliverables and charts...")
    # 1. Anomaly Results CSV
    # Ensure PDF required fields are present
    anomaly_csv_path = out_dir / "anomaly_results.csv"
    anomaly_results.to_csv(anomaly_csv_path, index=False)
    print(f"      -> {anomaly_csv_path}")

    # 2. Forecast Results CSV
    forecast_csv_path = out_dir / "forecast_results.csv"
    forecast_export_cols = [
        "forecast_date",
        "actual_revenue",
        "predicted_revenue",
        "lower_bound",
        "upper_bound",
    ]
    if "naive_revenue" in forecast_result.forecast_df.columns:
        forecast_export_cols.append("naive_revenue")

    forecast_result.forecast_df[forecast_export_cols].to_csv(forecast_csv_path, index=False)
    print(f"      -> {forecast_csv_path}")

    # 3. Charts
    trend_chart_path = out_charts / "trend_chart.png"
    anomaly_chart_path = out_charts / "anomaly_chart.png"
    forecast_chart_path = out_charts / "forecast_chart.png"

    fig1 = plot_trend_chart(daily_df, output_path=trend_chart_path)
    import matplotlib.pyplot as plt
    plt.close(fig1)
    print(f"      -> {trend_chart_path}")

    fig2 = plot_anomaly_chart(anomaly_results, output_path=anomaly_chart_path)
    plt.close(fig2)
    print(f"      -> {anomaly_chart_path}")

    fig3 = plot_forecast_chart(forecast_result, historical_df=daily_df, output_path=forecast_chart_path)
    plt.close(fig3)
    print(f"      -> {forecast_chart_path}")

    # 4. Evaluation Report Markdown
    rep_path = Path(report_path) if report_path else None
    if rep_path:
        print(f"[7/7] Generating evaluation report at: {rep_path}")
        generate_markdown_report(
            data_summary=data_summary,
            anomaly_metrics=anomaly_eval,
            forecast_metrics=forecast_eval,
            forecast_metadata=forecast_result.metadata,
            output_path=rep_path,
        )
        print(f"      -> {rep_path}")

    print("\n=== NEXLYTICS ML Pipeline Completed Successfully ===")
    return {
        "status": "success",
        "data_summary": data_summary,
        "anomaly_eval": anomaly_eval,
        "forecast_eval": forecast_eval,
        "deliverables": {
            "anomaly_results_csv": str(anomaly_csv_path),
            "forecast_results_csv": str(forecast_csv_path),
            "trend_chart_png": str(trend_chart_path),
            "anomaly_chart_png": str(anomaly_chart_path),
            "forecast_chart_png": str(forecast_chart_path),
            "evaluation_report_md": str(rep_path) if rep_path else None,
        },
    }


def main() -> None:
    """CLI parser and runner."""
    parser = argparse.ArgumentParser(
        description="NEXLYTICS ML — End-to-End Predictive Analytics Pipeline"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=str,
        help="Path to raw transaction CSV file (must include required transaction columns).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="outputs",
        type=str,
        help="Directory to save output CSVs and charts (default: outputs).",
    )
    parser.add_argument(
        "--report-path",
        "-r",
        default="reports/ml_evaluation_report.md",
        type=str,
        help="Path to save evaluation markdown report (default: reports/ml_evaluation_report.md).",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=DEFAULT_HORIZON,
        help=f"Future forecast horizon in days (default: {DEFAULT_HORIZON}).",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            input_path=args.input,
            output_dir=args.output_dir,
            report_path=args.report_path,
            horizon=args.horizon,
        )
    except Exception as exc:
        print(f"\n[ERROR] Pipeline execution failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
