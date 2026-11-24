"""
Unit tests for NEXLYTICS Sales Forecasting module.

Tests feature leakage prevention, chronological 80/20 splitting, recursive walk-forward,
uncertainty interval computation, naive baseline comparison, calendar continuity enforcement,
configurable forecast horizons, and edge-case validation.
"""

import unittest
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.forecasting import (
    validate_forecasting_data,
    build_lag_features,
    train_forecast_model,
    generate_forecast,
    ForecastResult,
    MIN_REQUIRED_DAYS,
    FEATURE_NAMES,
)


def get_synthetic_continuous_series(n_days: int = 50, seed: int = 42) -> pd.DataFrame:
    """Fixture providing continuous daily revenue without missing calendar dates."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n_days, freq="D")
    trend = np.linspace(500.0, 800.0, n_days)
    weekly_pattern = np.array([20.0, -10.0, -5.0, 15.0, 30.0, 60.0, -40.0])
    seasonal = np.array([weekly_pattern[d.day_of_week if hasattr(d, "day_of_week") else d.dayofweek] for d in dates])
    noise = rng.normal(0, 10.0, n_days)

    revenue = np.maximum(50.0, trend + seasonal + noise)
    return pd.DataFrame(
        {
            "transaction_date": dates,
            "daily_revenue": np.round(revenue, 2),
            "daily_cost": np.round(revenue * 0.4, 2),
            "daily_profit": np.round(revenue * 0.6, 2),
        }
    )


class TestValidateForecastingData(unittest.TestCase):
    """Tests for input validation and calendar continuity."""

    def test_valid_input(self):
        df = get_synthetic_continuous_series(30)
        # Should not raise
        validate_forecasting_data(df)

    def test_missing_column(self):
        df = get_synthetic_continuous_series(30).drop(columns=["daily_revenue"])
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df)
        self.assertIn("Missing required forecasting column: 'daily_revenue'", str(ctx.exception))

    def test_short_history_rejection(self):
        df = get_synthetic_continuous_series(MIN_REQUIRED_DAYS - 5)
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df)
        self.assertIn("Insufficient history for forecasting", str(ctx.exception))

    def test_duplicate_dates_rejection(self):
        df = get_synthetic_continuous_series(30)
        df.loc[5, "transaction_date"] = df.loc[4, "transaction_date"]
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df)
        self.assertIn("Duplicate calendar dates detected", str(ctx.exception))

    def test_missing_calendar_dates_rejection(self):
        df = get_synthetic_continuous_series(30)
        # Drop day index 10 to create a non-consecutive gap
        df_gapped = df.drop(index=[10]).reset_index(drop=True)
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df_gapped)
        self.assertIn("Incomplete daily series detected", str(ctx.exception))
        self.assertIn("missing dates", str(ctx.exception).lower())

    def test_null_and_inf_revenue_rejection(self):
        df = get_synthetic_continuous_series(30)
        df_null = df.copy()
        df_null.loc[3, "daily_revenue"] = np.nan
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df_null)
        self.assertIn("Null, NaN, or non-numeric", str(ctx.exception))

        df_inf = df.copy()
        df_inf.loc[4, "daily_revenue"] = np.inf
        with self.assertRaises(ValueError) as ctx:
            validate_forecasting_data(df_inf)
        self.assertIn("Non-finite (inf/-inf)", str(ctx.exception))


class TestFeatureEngineering(unittest.TestCase):
    """Tests for leakage-safe lag and rolling feature creation."""

    def test_lag_and_rolling_leakage_safety(self):
        df = get_synthetic_continuous_series(30)
        usable = build_lag_features(df)

        # Usable df drops first 7 window rows
        self.assertEqual(len(usable), len(df) - 7)
        self.assertTrue(all(f in usable.columns for f in FEATURE_NAMES))

        # Check that lag_1 matches previous row's daily_revenue
        # For the first usable row (original row index 7):
        expected_lag_1 = df.iloc[6]["daily_revenue"]
        self.assertAlmostEqual(usable.iloc[0]["lag_1_revenue"], expected_lag_1, places=2)

        # Check rolling 7 mean of original rows 0..6
        expected_rolling_7 = df.iloc[0:7]["daily_revenue"].mean()
        self.assertAlmostEqual(usable.iloc[0]["rolling_7_mean"], expected_rolling_7, places=2)

        # Verify current-day revenue is NOT leaked into lag or rolling
        self.assertNotEqual(usable.iloc[0]["lag_1_revenue"], usable.iloc[0]["daily_revenue"])


class TestTrainForecastModel(unittest.TestCase):
    """Tests for model training, walk-forward evaluation, and forecasting."""

    def test_chronological_split_and_results(self):
        df = get_synthetic_continuous_series(45)
        result = train_forecast_model(df)

        self.assertIsInstance(result, ForecastResult)
        self.assertIsInstance(result.model, LinearRegression)

        # Check metadata
        meta = result.metadata
        self.assertGreater(meta["train_samples"], 0)
        self.assertGreater(meta["test_samples"], 0)
        # 80/20 split check
        total_usable = meta["train_samples"] + meta["test_samples"]
        self.assertEqual(meta["train_samples"], int(np.floor(0.80 * total_usable)))

        # Chronological boundary check: max(train) < min(test)
        self.assertLess(meta["train_date_range"][1], meta["test_date_range"][0])

    def test_output_schema_and_bounds(self):
        df = get_synthetic_continuous_series(45)
        result = train_forecast_model(df, config={"horizon": 7})

        expected_cols = [
            "forecast_date",
            "actual_revenue",
            "predicted_revenue",
            "lower_bound",
            "upper_bound",
            "naive_revenue",
        ]
        self.assertEqual(list(result.forecast_df.columns), expected_cols)
        self.assertEqual(list(result.test_df.columns), expected_cols)
        self.assertEqual(list(result.future_df.columns), expected_cols)

        # Test period has non-null actuals
        self.assertTrue(result.test_df["actual_revenue"].notna().all())
        # Future forecast has null actuals
        self.assertTrue(result.future_df["actual_revenue"].isna().all())

        # Bounds check: lower_bound <= predicted_revenue <= upper_bound
        for _, row in result.forecast_df.iterrows():
            self.assertLessEqual(row["lower_bound"], row["predicted_revenue"] + 1e-4)
            self.assertGreaterEqual(row["upper_bound"], row["predicted_revenue"] - 1e-4)
            # Lower bound clamped to 0 for nonnegative revenue
            self.assertGreaterEqual(row["lower_bound"], 0.0)

    def test_recursive_forecast_length(self):
        df = get_synthetic_continuous_series(45)
        result_7 = train_forecast_model(df, config={"horizon": 7})
        self.assertEqual(len(result_7.future_df), 7)

        result_14 = train_forecast_model(df, config={"horizon": 14})
        self.assertEqual(len(result_14.future_df), 14)

    def test_naive_baseline_presence(self):
        df = get_synthetic_continuous_series(45)
        result = train_forecast_model(df)

        self.assertTrue(result.test_df["naive_revenue"].notna().all())
        self.assertTrue(result.future_df["naive_revenue"].notna().all())
        # Check that naive baseline is positive
        self.assertGreater(result.metadata["naive_baseline_test_value"], 0)
        self.assertGreater(result.metadata["naive_baseline_future_value"], 0)

    def test_reproducibility(self):
        df = get_synthetic_continuous_series(40)
        r1 = train_forecast_model(df)
        r2 = train_forecast_model(df)

        pd.testing.assert_frame_equal(r1.forecast_df, r2.forecast_df)
        self.assertEqual(r1.metadata["coefficients"], r2.metadata["coefficients"])

    def test_generate_forecast_wrapper(self):
        df = get_synthetic_continuous_series(40)
        result = train_forecast_model(df, config={"horizon": 7})

        future = generate_forecast(result, horizon=7)
        self.assertEqual(len(future), 7)
        self.assertTrue(future["actual_revenue"].isna().all())


if __name__ == "__main__":
    unittest.main()
