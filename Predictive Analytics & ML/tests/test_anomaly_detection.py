"""
Unit tests for NEXLYTICS Anomaly Detection module.

Uses standard Python unittest.
Tests schema validation, IsolationForest anomaly detection, classification rules,
category driver attribution, reproducibility, and edge cases (empty data, constant values,
insufficient history, nonfinite values).
"""

import unittest
import numpy as np
import pandas as pd

from src.anomaly_detection import (
    validate_daily_features,
    classify_anomaly,
    identify_top_driver_category,
    detect_anomalies,
    REQUIRED_DAILY_COLUMNS,
    ANOMALY_TYPE_REVENUE_DROP,
    ANOMALY_TYPE_EXPENSE_SPIKE,
    ANOMALY_TYPE_PROFIT_DROP,
    ANOMALY_TYPE_OTHER,
)


def get_synthetic_daily_data(n_days: int = 40, seed: int = 42) -> pd.DataFrame:
    """Helper fixture generating small in-memory daily time-series with injected anomalies."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n_days, freq="D")

    # Baseline daily pattern
    revenue = rng.normal(loc=1000.0, scale=30.0, size=n_days)
    cost = rng.normal(loc=400.0, scale=15.0, size=n_days)
    profit = revenue - cost

    df = pd.DataFrame(
        {
            "transaction_date": dates,
            "daily_revenue": revenue,
            "daily_cost": cost,
            "daily_profit": profit,
        }
    )

    # Inject specific anomalies if there are sufficient days:
    if n_days > 25:
        # Day 15: Severe Revenue Drop
        df.loc[15, "daily_revenue"] = 200.0
        df.loc[15, "daily_profit"] = df.loc[15, "daily_revenue"] - df.loc[15, "daily_cost"]

        # Day 25: Massive Expense Spike
        df.loc[25, "daily_cost"] = 1500.0
        df.loc[25, "daily_profit"] = df.loc[25, "daily_revenue"] - df.loc[25, "daily_cost"]

    return df


def get_synthetic_transactions(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Helper generating matching transaction details for category attribution."""
    records = []
    txn_id = 1
    for _, row in daily_df.iterrows():
        dt = row["transaction_date"]
        rev = row["daily_revenue"]
        cst = row["daily_cost"]

        # Split into two categories: Electronics (70%) and Home (30%) on normal days
        # On Day 15 (Revenue Drop), Electronics drops heavily
        if dt == pd.Timestamp("2026-01-16"):  # Day 15
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Electronics",
                "revenue": 50.0,
                "cost": cst * 0.5,
                "profit": 50.0 - (cst * 0.5),
            })
            txn_id += 1
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Home",
                "revenue": 150.0,
                "cost": cst * 0.5,
                "profit": 150.0 - (cst * 0.5),
            })
            txn_id += 1
        elif dt == pd.Timestamp("2026-01-26"):  # Day 25 (Expense Spike in Electronics)
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Electronics",
                "revenue": rev * 0.7,
                "cost": cst * 0.8,
                "profit": (rev * 0.7) - (cst * 0.8),
            })
            txn_id += 1
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Home",
                "revenue": rev * 0.3,
                "cost": cst * 0.2,
                "profit": (rev * 0.3) - (cst * 0.2),
            })
            txn_id += 1
        else:
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Electronics",
                "revenue": rev * 0.7,
                "cost": cst * 0.6,
                "profit": (rev * 0.7) - (cst * 0.6),
            })
            txn_id += 1
            records.append({
                "transaction_date": dt,
                "transaction_id": f"TX_{txn_id}",
                "category": "Home",
                "revenue": rev * 0.3,
                "cost": cst * 0.4,
                "profit": (rev * 0.3) - (cst * 0.4),
            })
            txn_id += 1

    return pd.DataFrame(records)


class TestValidateDailyFeatures(unittest.TestCase):
    """Tests for schema and value validity in daily metrics."""

    def test_valid_schema(self):
        df = get_synthetic_daily_data(10)
        # Should not raise
        validate_daily_features(df)

    def test_missing_column(self):
        df = get_synthetic_daily_data(10).drop(columns=["daily_profit"])
        with self.assertRaises(ValueError) as ctx:
            validate_daily_features(df)
        self.assertIn("Missing required daily columns", str(ctx.exception))
        self.assertIn("daily_profit", str(ctx.exception))

    def test_null_dates(self):
        df = get_synthetic_daily_data(10)
        df.loc[2, "transaction_date"] = None
        with self.assertRaises(ValueError) as ctx:
            validate_daily_features(df)
        self.assertIn("Null transaction_date", str(ctx.exception))

    def test_nan_values(self):
        df = get_synthetic_daily_data(10)
        df.loc[3, "daily_revenue"] = np.nan
        with self.assertRaises(ValueError) as ctx:
            validate_daily_features(df)
        self.assertIn("Null or NaN values detected in daily feature 'daily_revenue'", str(ctx.exception))

    def test_inf_values(self):
        df = get_synthetic_daily_data(10)
        df.loc[1, "daily_cost"] = np.inf
        with self.assertRaises(ValueError) as ctx:
            validate_daily_features(df)
        self.assertIn("Non-finite (inf/-inf) values in daily feature 'daily_cost'", str(ctx.exception))

    def test_non_dataframe_type(self):
        with self.assertRaises(TypeError) as ctx:
            validate_daily_features([1, 2, 3])  # type: ignore
        self.assertIn("Expected pandas DataFrame", str(ctx.exception))


class TestClassifyAnomaly(unittest.TestCase):
    """Tests for anomaly classification logic and historical baseline comparisons."""

    def test_revenue_drop_classification(self):
        ref = {"daily_revenue": 1000.0, "daily_cost": 400.0, "daily_profit": 600.0}
        cur = {"daily_revenue": 200.0, "daily_cost": 400.0, "daily_profit": -200.0}
        self.assertEqual(classify_anomaly(cur, ref), ANOMALY_TYPE_REVENUE_DROP)

    def test_expense_spike_classification(self):
        ref = {"daily_revenue": 1000.0, "daily_cost": 400.0, "daily_profit": 600.0}
        cur = {"daily_revenue": 1000.0, "daily_cost": 1500.0, "daily_profit": -500.0}
        self.assertEqual(classify_anomaly(cur, ref), ANOMALY_TYPE_EXPENSE_SPIKE)

    def test_profit_drop_classification(self):
        ref = {"daily_revenue": 1000.0, "daily_cost": 400.0, "daily_profit": 600.0}
        # Revenue slightly lower, cost slightly higher, but both within margin while profit tanked
        cur = {"daily_revenue": 1000.0, "daily_cost": 400.0, "daily_profit": 100.0}
        self.assertEqual(classify_anomaly(cur, ref), ANOMALY_TYPE_PROFIT_DROP)

    def test_other_anomaly_without_history(self):
        cur = {"daily_revenue": 5000.0, "daily_cost": 200.0, "daily_profit": 4800.0}
        self.assertEqual(classify_anomaly(cur, None), ANOMALY_TYPE_OTHER)


class TestDetectAnomaliesPipeline(unittest.TestCase):
    """Tests for the detect_anomalies function."""

    def test_output_schema_and_columns(self):
        df = get_synthetic_daily_data(35)
        results = detect_anomalies(df)

        required_for_csv = [
            "transaction_date",
            "daily_revenue",
            "daily_cost",
            "is_anomaly",
            "anomaly_type",
            "top_driver_category",
        ]
        for col in required_for_csv:
            self.assertIn(col, results.columns)

        # Preserved additional fields
        self.assertIn("daily_profit", results.columns)
        self.assertIn("anomaly_score", results.columns)
        self.assertIn("anomaly_flag", results.columns)

    def test_labels_and_values(self):
        df = get_synthetic_daily_data(35)
        results = detect_anomalies(df)

        # anomaly_flag must be in {1, -1}
        self.assertTrue(set(results["anomaly_flag"].unique()).issubset({1, -1}))
        # is_anomaly must be in {'Yes', 'No'}
        self.assertTrue(set(results["is_anomaly"].unique()).issubset({"Yes", "No"}))
        # Consistency between flag and is_anomaly
        for _, row in results.iterrows():
            if row["anomaly_flag"] == -1:
                self.assertEqual(row["is_anomaly"], "Yes")
                self.assertTrue(pd.notna(row["anomaly_type"]))
            else:
                self.assertEqual(row["is_anomaly"], "No")
                # Normal days must NEVER be labeled as anomalous
                self.assertTrue(pd.isna(row["anomaly_type"]) or row["anomaly_type"] is None)
                self.assertTrue(pd.isna(row["top_driver_category"]) or row["top_driver_category"] is None)

    def test_reproducibility(self):
        df = get_synthetic_daily_data(35)
        res1 = detect_anomalies(df, config={"random_state": 42})
        res2 = detect_anomalies(df, config={"random_state": 42})

        pd.testing.assert_frame_equal(res1, res2)

    def test_optional_category_context(self):
        df = get_synthetic_daily_data(35)
        txns = get_synthetic_transactions(df)
        results = detect_anomalies(df, transactions_df=txns)

        anomalies = results[results["is_anomaly"] == "Yes"]
        self.assertGreater(len(anomalies), 0)
        # Check that anomalies have a string top_driver_category or None, never arbitrary numbers
        for _, row in anomalies.iterrows():
            if row["top_driver_category"] is not None:
                self.assertIn(row["top_driver_category"], ["Electronics", "Home"])

    def test_missing_category_context(self):
        df = get_synthetic_daily_data(35)
        results = detect_anomalies(df, transactions_df=None)
        # Without transaction details, top_driver_category must be None
        self.assertTrue(results["top_driver_category"].isna().all())

    def test_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=REQUIRED_DAILY_COLUMNS)
        results = detect_anomalies(empty_df)
        self.assertTrue(results.empty)
        self.assertIn("transaction_date", results.columns)
        self.assertIn("is_anomaly", results.columns)

    def test_insufficient_history(self):
        df = get_synthetic_daily_data(3)
        results = detect_anomalies(df, config={"min_history_samples": 5})
        self.assertEqual(len(results), 3)
        # All must be marked normal when history is insufficient
        self.assertTrue((results["is_anomaly"] == "No").all())
        self.assertTrue(results["anomaly_type"].isna().all())

    def test_constant_valued_features(self):
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        const_df = pd.DataFrame(
            {
                "transaction_date": dates,
                "daily_revenue": [100.0] * 10,
                "daily_cost": [50.0] * 10,
                "daily_profit": [50.0] * 10,
            }
        )
        results = detect_anomalies(const_df)
        self.assertEqual(len(results), 10)
        self.assertTrue((results["is_anomaly"] == "No").all())


if __name__ == "__main__":
    unittest.main()
