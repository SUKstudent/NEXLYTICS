"""
Integration tests for the complete NEXLYTICS ML Pipeline.

Tests end-to-end execution from CLI entry point and run_pipeline function,
verifying output files, CSV schemas, chart generation, markdown report creation,
error handling for missing calendar dates, and temporary artifact cleanup.
"""

from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from run_pipeline import run_pipeline


def generate_temp_transactions_csv(csv_path: Path, n_days: int = 35) -> Path:
    """Helper writing a temporary synthetic transaction CSV for integration testing."""
    dates = pd.date_range("2026-01-01", periods=n_days, freq="D")
    records = []
    txn_id = 1

    for i, d in enumerate(dates):
        dow = d.day_of_week if hasattr(d, "day_of_week") else d.dayofweek
        rev = 500.0 + (i * 2.5) + (20.0 if dow == 5 else 0.0)
        cst = rev * 0.4
        prof = rev - cst

        # Add 2 transactions per day across 2 categories
        records.append({
            "transaction_date": d.strftime("%Y-%m-%d"),
            "transaction_id": f"TX_{txn_id}",
            "revenue": round(rev * 0.6, 2),
            "cost": round(cst * 0.6, 2),
            "profit": round(prof * 0.6, 2),
            "category": "Electronics",
        })
        txn_id += 1

        records.append({
            "transaction_date": d.strftime("%Y-%m-%d"),
            "transaction_id": f"TX_{txn_id}",
            "revenue": round(rev * 0.4, 2),
            "cost": round(cst * 0.4, 2),
            "profit": round(prof * 0.4, 2),
            "category": "Home",
        })
        txn_id += 1

    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False)
    return csv_path


class TestEndToEndPipelineIntegration(unittest.TestCase):
    """End-to-end tests for run_pipeline execution."""

    def test_pipeline_execution_and_deliverables(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_csv = tmp_path / "raw_txns.csv"
            out_dir = tmp_path / "test_outputs"
            report_file = tmp_path / "test_report.md"

            generate_temp_transactions_csv(input_csv, n_days=35)

            # Execute pipeline
            result = run_pipeline(
                input_path=input_csv,
                output_dir=out_dir,
                report_path=report_file,
                horizon=7,
            )

            self.assertEqual(result["status"], "success")

            # Check CSV deliverables
            anomaly_csv = out_dir / "anomaly_results.csv"
            forecast_csv = out_dir / "forecast_results.csv"
            self.assertTrue(anomaly_csv.is_file())
            self.assertTrue(forecast_csv.is_file())

            # Check Chart deliverables
            trend_png = out_dir / "charts" / "trend_chart.png"
            anomaly_png = out_dir / "charts" / "anomaly_chart.png"
            forecast_png = out_dir / "charts" / "forecast_chart.png"
            self.assertTrue(trend_png.is_file())
            self.assertTrue(anomaly_png.is_file())
            self.assertTrue(forecast_png.is_file())

            # Check Report deliverable
            self.assertTrue(report_file.is_file())
            report_text = report_file.read_text(encoding="utf-8")
            self.assertIn("# NEXLYTICS ML Evaluation & Deliverables Report", report_text)
            self.assertIn("Held-Out Test Set Performance", report_text)

            # Validate anomaly_results.csv schema
            df_anom = pd.read_csv(anomaly_csv)
            expected_anom_cols = [
                "transaction_date",
                "daily_revenue",
                "daily_cost",
                "is_anomaly",
                "anomaly_type",
                "top_driver_category",
            ]
            for col in expected_anom_cols:
                self.assertIn(col, df_anom.columns)
            self.assertEqual(len(df_anom), 35)

            # Validate forecast_results.csv schema
            df_fc = pd.read_csv(forecast_csv)
            expected_fc_cols = [
                "forecast_date",
                "actual_revenue",
                "predicted_revenue",
                "lower_bound",
                "upper_bound",
            ]
            for col in expected_fc_cols:
                self.assertIn(col, df_fc.columns)

            # Check that exactly 7 future rows have null actual_revenue
            future_rows = df_fc[df_fc["actual_revenue"].isna()]
            self.assertEqual(len(future_rows), 7)

            # Check that held-out test rows have non-null actual_revenue
            test_rows = df_fc[df_fc["actual_revenue"].notna()]
            self.assertGreater(len(test_rows), 0)

            # Verify forecast dates are strictly in ascending order
            fc_dates = pd.to_datetime(df_fc["forecast_date"])
            self.assertTrue(fc_dates.is_monotonic_increasing)

    def test_pipeline_fails_on_missing_calendar_dates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_csv = tmp_path / "gapped_txns.csv"
            out_dir = tmp_path / "test_outputs"

            generate_temp_transactions_csv(input_csv, n_days=35)
            # Inject a missing calendar day gap by removing all records for day index 15
            df = pd.read_csv(input_csv)
            dates = sorted(df["transaction_date"].unique())
            gapped_date = dates[15]
            df_gapped = df[df["transaction_date"] != gapped_date].reset_index(drop=True)
            df_gapped.to_csv(input_csv, index=False)

            with self.assertRaises(ValueError) as ctx:
                run_pipeline(input_path=input_csv, output_dir=out_dir)
            self.assertIn("Incomplete daily series detected", str(ctx.exception))
            self.assertIn("missing calendar date", str(ctx.exception).lower())

    def test_pipeline_fails_on_missing_column(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_csv = tmp_path / "bad_txns.csv"
            out_dir = tmp_path / "test_outputs"

            generate_temp_transactions_csv(input_csv, n_days=30)
            df = pd.read_csv(input_csv).drop(columns=["cost"])
            df.to_csv(input_csv, index=False)

            with self.assertRaises(ValueError) as ctx:
                run_pipeline(input_path=input_csv, output_dir=out_dir)
            self.assertIn("Missing required transaction columns", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
