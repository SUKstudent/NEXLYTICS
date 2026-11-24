"""
Unit tests for NEXLYTICS Model Evaluation & Visualization module.

Uses non-interactive Matplotlib backend.
Tests forecast evaluation metrics, naive baseline comparison, descriptive anomaly
detection summaries, chart generation, error handling, and immutability.
"""

from pathlib import Path
import tempfile
import unittest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.evaluation import (
    evaluate_forecast,
    evaluate_anomalies,
    plot_trend_chart,
    plot_anomaly_chart,
    plot_forecast_chart,
)
from src.forecasting import ForecastResult, train_forecast_model


def get_sample_test_df() -> pd.DataFrame:
    """Fixture providing sample held-out test predictions and baseline."""
    dates = pd.date_range("2026-02-01", periods=10, freq="D")
    return pd.DataFrame(
        {
            "forecast_date": dates,
            "actual_revenue": [100.0, 110.0, 105.0, 120.0, 115.0, 130.0, 125.0, 140.0, 135.0, 150.0],
            "predicted_revenue": [102.0, 108.0, 107.0, 118.0, 117.0, 128.0, 127.0, 138.0, 137.0, 148.0],
            "naive_revenue": [95.0] * 10,  # Constant naive baseline
            "lower_bound": [90.0] * 10,
            "upper_bound": [120.0] * 10,
        }
    )


def get_sample_anomaly_df() -> pd.DataFrame:
    """Fixture providing sample anomaly results from Phase 3."""
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    df = pd.DataFrame(
        {
            "transaction_date": dates,
            "daily_revenue": [1000.0] * 20,
            "daily_cost": [400.0] * 20,
            "daily_profit": [600.0] * 20,
            "anomaly_score": [0.1] * 20,
            "anomaly_flag": [1] * 20,
            "is_anomaly": ["No"] * 20,
            "anomaly_type": [None] * 20,
            "top_driver_category": [None] * 20,
        }
    )
    # Inject two anomalies
    df.loc[5, "is_anomaly"] = "Yes"
    df.loc[5, "anomaly_flag"] = -1
    df.loc[5, "anomaly_type"] = "Revenue Drop"
    df.loc[5, "top_driver_category"] = "Electronics"

    df.loc[12, "is_anomaly"] = "Yes"
    df.loc[12, "anomaly_flag"] = -1
    df.loc[12, "anomaly_type"] = "Expense Spike"
    df.loc[12, "top_driver_category"] = "Home"

    return df


class TestEvaluateForecast(unittest.TestCase):
    """Tests for regression metrics and naive baseline comparisons."""

    def test_metrics_calculation_and_baseline_comparison(self):
        df = get_sample_test_df()
        res = evaluate_forecast(df)

        self.assertIn("model_mae", res)
        self.assertIn("model_rmse", res)
        self.assertIn("naive_mae", res)
        self.assertIn("naive_rmse", res)
        self.assertIn("mae_improvement_pct", res)
        self.assertIn("outperforms_baseline", res)

        # Expected model errors: all abs errors are 2.0
        self.assertAlmostEqual(res["model_mae"], 2.0, places=3)
        self.assertAlmostEqual(res["model_rmse"], 2.0, places=3)

        # ML outperforms naive
        self.assertTrue(res["outperforms_baseline"])
        self.assertGreater(res["mae_improvement_pct"], 0.0)
        self.assertEqual(res["test_sample_count"], 10)

    def test_underperforming_baseline_reported_honestly(self):
        # Scenario where model is worse than naive baseline
        dates = pd.date_range("2026-02-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "forecast_date": dates,
                "actual_revenue": [100.0, 100.0, 100.0, 100.0, 100.0],
                "predicted_revenue": [120.0, 130.0, 110.0, 140.0, 120.0],  # Bad predictions
                "naive_revenue": [100.0, 100.0, 100.0, 100.0, 100.0],  # Perfect naive
            }
        )
        res = evaluate_forecast(df)
        self.assertFalse(res["outperforms_baseline"])
        self.assertLess(res["mae_improvement_pct"], 0.0)

    def test_zero_baseline_mae_safety(self):
        # When both model and baseline have 0 error
        res = evaluate_forecast(
            test_data=[100.0, 200.0],
            y_pred=[100.0, 200.0],
            y_naive=[100.0, 200.0],
        )
        self.assertEqual(res["model_mae"], 0.0)
        self.assertEqual(res["naive_mae"], 0.0)
        self.assertEqual(res["mae_improvement_pct"], 0.0)

    def test_input_immutability(self):
        df = get_sample_test_df()
        df_copy = df.copy()
        evaluate_forecast(df)
        pd.testing.assert_frame_equal(df, df_copy)

    def test_empty_or_invalid_inputs(self):
        with self.assertRaises(ValueError):
            evaluate_forecast(pd.DataFrame())

        with self.assertRaises(ValueError):
            evaluate_forecast(test_data=[1.0, 2.0], y_pred=[1.0])  # Length mismatch


class TestEvaluateAnomalies(unittest.TestCase):
    """Tests for descriptive anomaly evaluation."""

    def test_descriptive_metrics_without_ground_truth(self):
        df = get_sample_anomaly_df()
        res = evaluate_anomalies(df)

        self.assertEqual(res["total_days"], 20)
        self.assertEqual(res["flagged_days"], 2)
        self.assertEqual(res["anomaly_percentage"], 10.0)
        self.assertFalse(res["ground_truth_available"])
        self.assertIn("Revenue Drop", res["anomaly_type_counts"])
        self.assertIn("Expense Spike", res["anomaly_type_counts"])
        self.assertEqual(res["anomaly_type_counts"]["Revenue Drop"], 1)
        self.assertEqual(res["anomaly_type_counts"]["Expense Spike"], 1)
        self.assertEqual(res["top_driver_category_counts"]["Electronics"], 1)

    def test_with_ground_truth_labels(self):
        df = get_sample_anomaly_df()
        y_true = [0] * 20
        y_true[5] = 1  # Matches row 5 (TP)
        # Row 12 is flagged in df but 0 in y_true (FP)
        res = evaluate_anomalies(df, y_true=y_true)

        self.assertTrue(res["ground_truth_available"])
        self.assertIn("precision", res)
        self.assertIn("recall", res)
        self.assertIn("f1_score", res)
        self.assertEqual(res["recall"], 1.0)  # 1/1
        self.assertEqual(res["precision"], 0.5)  # 1/2


class TestVisualizations(unittest.TestCase):
    """Tests for chart generation functions and saving."""

    def test_plot_trend_chart(self):
        dates = pd.date_range("2026-01-01", periods=15, freq="D")
        df = pd.DataFrame(
            {
                "transaction_date": dates,
                "daily_revenue": [500.0] * 15,
                "daily_cost": [200.0] * 15,
                "daily_profit": [300.0] * 15,
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "charts" / "trend.png"
            fig = plot_trend_chart(df, output_path=out_file)
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 1000)
            plt.close(fig)

    def test_plot_anomaly_chart(self):
        df = get_sample_anomaly_df()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "charts" / "anomaly.png"
            fig = plot_anomaly_chart(df, output_path=out_file)
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 1000)
            plt.close(fig)

    def test_plot_forecast_chart(self):
        # Build test and future slices
        dates_test = pd.date_range("2026-02-01", periods=5, freq="D")
        dates_future = pd.date_range("2026-02-06", periods=7, freq="D")

        f_df = pd.DataFrame(
            {
                "forecast_date": list(dates_test) + list(dates_future),
                "actual_revenue": [100.0] * 5 + [np.nan] * 7,
                "predicted_revenue": [102.0] * 5 + [105.0] * 7,
                "lower_bound": [90.0] * 12,
                "upper_bound": [120.0] * 12,
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "charts" / "forecast.png"
            fig = plot_forecast_chart(f_df, output_path=out_file)
            self.assertIsInstance(fig, plt.Figure)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 1000)
            plt.close(fig)

    def test_chart_errors_on_empty_df(self):
        with self.assertRaises(ValueError):
            plot_trend_chart(pd.DataFrame())

        with self.assertRaises(ValueError):
            plot_anomaly_chart(pd.DataFrame())

        with self.assertRaises(ValueError):
            plot_forecast_chart(pd.DataFrame())


if __name__ == "__main__":
    unittest.main()
