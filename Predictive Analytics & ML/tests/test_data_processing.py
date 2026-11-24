"""
Unit tests for NEXLYTICS Data Processing module.

Uses standard Python unittest to avoid unnecessary dependencies.
Tests data loading, column validation, date/numeric parsing, chronological sorting,
daily aggregation, missing calendar date detection, and duplicate ID handling
using small in-memory test fixtures.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_processing import (
    load_dataset,
    validate_transaction_columns,
    validate_and_clean_transactions,
    sort_transactions,
    aggregate_daily_transactions,
    detect_missing_dates,
    preprocess_features,
    REQUIRED_TRANSACTION_COLUMNS,
)


def get_valid_transaction_data() -> pd.DataFrame:
    """Fixture providing a minimal valid transactions DataFrame."""
    return pd.DataFrame(
        {
            "transaction_date": [
                "2026-01-03",
                "2026-01-01",
                "2026-01-01",
                "2026-01-04",
            ],
            "transaction_id": ["TXN_003", "TXN_001", "TXN_002", "TXN_004"],
            "revenue": [300.0, 100.5, 200.0, 150.0],
            "cost": [120.0, 40.5, 80.0, 50.0],
            "profit": [180.0, 60.0, 120.0, 100.0],
            "category": ["Electronics", "Books", "Books", "Electronics"],
        }
    )


class TestLoadDataset(unittest.TestCase):
    """Tests for load_dataset function."""

    def test_file_not_found(self):
        non_existent = Path("non_existent_directory_xyz/file.csv")
        with self.assertRaises(FileNotFoundError) as ctx:
            load_dataset(non_existent)
        self.assertIn("Dataset file not found", str(ctx.exception))

    def test_empty_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_file = Path(tmp_dir) / "empty.csv"
            empty_file.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_dataset(empty_file)
            self.assertIn("empty", str(ctx.exception).lower())

    def test_valid_csv(self):
        df = get_valid_transaction_data()
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_file = Path(tmp_dir) / "valid.csv"
            df.to_csv(csv_file, index=False)
            loaded = load_dataset(csv_file)
            self.assertEqual(len(loaded), len(df))
            self.assertEqual(list(loaded.columns), list(df.columns))


class TestValidateTransactionColumns(unittest.TestCase):
    """Tests for column existence validation."""

    def test_valid_columns(self):
        df = get_valid_transaction_data()
        # Should not raise
        validate_transaction_columns(df)

    def test_missing_columns(self):
        df = get_valid_transaction_data().drop(columns=["revenue", "cost"])
        with self.assertRaises(ValueError) as ctx:
            validate_transaction_columns(df)
        self.assertIn("Missing required transaction columns", str(ctx.exception))
        self.assertIn("revenue", str(ctx.exception))
        self.assertIn("cost", str(ctx.exception))

    def test_invalid_type(self):
        with self.assertRaises(TypeError) as ctx:
            validate_transaction_columns({"transaction_date": []})  # type: ignore
        self.assertIn("Expected pandas DataFrame", str(ctx.exception))


class TestValidateAndCleanTransactions(unittest.TestCase):
    """Tests for date/numeric parsing and schema cleaning."""

    def test_clean_valid_data(self):
        df = get_valid_transaction_data()
        original_copy = df.copy()
        cleaned, summary = validate_and_clean_transactions(df)

        # Ensure original input was preserved and not mutated
        pd.testing.assert_frame_equal(df, original_copy)

        # Check types
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned["transaction_date"]))
        self.assertTrue(pd.api.types.is_float_dtype(cleaned["revenue"]))
        self.assertTrue(pd.api.types.is_float_dtype(cleaned["cost"]))
        self.assertTrue(pd.api.types.is_float_dtype(cleaned["profit"]))

        # Check summary metrics
        self.assertEqual(summary["total_records"], 4)
        self.assertEqual(summary["unique_transaction_ids"], 4)
        self.assertEqual(summary["duplicate_id_count"], 0)
        self.assertEqual(summary["total_revenue"], 750.5)
        self.assertEqual(summary["total_cost"], 290.5)
        self.assertEqual(summary["total_profit"], 460.0)

    def test_invalid_date_rejection(self):
        df = get_valid_transaction_data()
        df.loc[1, "transaction_date"] = "invalid-date-string"
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("Invalid transaction_date format", str(ctx.exception))

    def test_null_date_rejection(self):
        df = get_valid_transaction_data()
        df.loc[2, "transaction_date"] = None
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("null transaction_date", str(ctx.exception))

    def test_non_numeric_revenue_rejection(self):
        df = get_valid_transaction_data()
        df["revenue"] = df["revenue"].astype(object)
        df.loc[0, "revenue"] = "one_hundred"
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("Non-numeric values found in column 'revenue'", str(ctx.exception))

    def test_null_numeric_rejection(self):
        df = get_valid_transaction_data()
        df.loc[0, "cost"] = np.nan
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("Null values found in numeric column 'cost'", str(ctx.exception))

    def test_null_transaction_id_rejection(self):
        df = get_valid_transaction_data()
        df.loc[0, "transaction_id"] = None
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("Missing or null values found in required column 'transaction_id'", str(ctx.exception))

    def test_null_category_rejection(self):
        df = get_valid_transaction_data()
        df.loc[0, "category"] = None
        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df)
        self.assertIn("Missing or null values found in required column 'category'", str(ctx.exception))

    def test_duplicate_transaction_ids_allowed(self):
        df = get_valid_transaction_data()
        df.loc[1, "transaction_id"] = "TXN_001"
        df.loc[2, "transaction_id"] = "TXN_001"  # Duplicate

        cleaned, summary = validate_and_clean_transactions(
            df, allow_duplicate_ids=True
        )
        # Preserves all records without dropping
        self.assertEqual(len(cleaned), 4)
        self.assertEqual(summary["duplicate_id_count"], 2)
        self.assertIn("TXN_001", summary["duplicate_ids"])

    def test_duplicate_transaction_ids_rejected_when_strict(self):
        df = get_valid_transaction_data()
        df.loc[1, "transaction_id"] = "TXN_001"
        df.loc[2, "transaction_id"] = "TXN_001"

        with self.assertRaises(ValueError) as ctx:
            validate_and_clean_transactions(df, allow_duplicate_ids=False)
        self.assertIn("Duplicate transaction_id values detected", str(ctx.exception))


class TestSortTransactions(unittest.TestCase):
    """Tests for chronological sorting."""

    def test_sort_preserves_all_records(self):
        df = get_valid_transaction_data()
        cleaned, _ = validate_and_clean_transactions(df)
        sorted_df = sort_transactions(cleaned)

        self.assertEqual(len(sorted_df), len(cleaned))
        dates = sorted_df["transaction_date"].tolist()
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(sorted_df.iloc[0]["transaction_date"], pd.Timestamp("2026-01-01"))
        self.assertEqual(sorted_df.iloc[-1]["transaction_date"], pd.Timestamp("2026-01-04"))


class TestAggregateDailyTransactions(unittest.TestCase):
    """Tests for daily aggregation metrics."""

    def test_daily_aggregation(self):
        df = get_valid_transaction_data()
        cleaned, _ = validate_and_clean_transactions(df)
        daily = aggregate_daily_transactions(cleaned)

        # Expected 3 distinct dates: 2026-01-01 (2 orders), 2026-01-03 (1 order), 2026-01-04 (1 order)
        self.assertEqual(len(daily), 3)
        expected_cols = [
            "transaction_date",
            "daily_revenue",
            "daily_cost",
            "daily_profit",
            "order_count",
        ]
        self.assertEqual(list(daily.columns), expected_cols)

        # Verify Day 1 aggregation (TXN_001: 100.5 rev / 40.5 cost, TXN_002: 200.0 rev / 80.0 cost)
        day1 = daily[daily["transaction_date"] == pd.Timestamp("2026-01-01")].iloc[0]
        self.assertEqual(day1["daily_revenue"], 300.5)
        self.assertEqual(day1["daily_cost"], 120.5)
        self.assertEqual(day1["daily_profit"], 180.0)
        self.assertEqual(day1["order_count"], 2)


class TestDetectMissingDates(unittest.TestCase):
    """Tests for identifying missing calendar days."""

    def test_missing_calendar_dates_detected(self):
        # Dates present: 2026-01-01, 2026-01-03, 2026-01-05
        # Missing dates should be 2026-01-02 and 2026-01-04
        df = pd.DataFrame(
            {
                "transaction_date": [
                    "2026-01-01",
                    "2026-01-03",
                    "2026-01-05",
                ],
                "revenue": [10.0, 20.0, 30.0],
            }
        )
        missing = detect_missing_dates(df)
        expected_missing = [
            pd.Timestamp("2026-01-02"),
            pd.Timestamp("2026-01-04"),
        ]
        self.assertEqual(missing, expected_missing)

    def test_continuous_dates_have_no_missing(self):
        df = pd.DataFrame(
            {
                "transaction_date": [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                ]
            }
        )
        self.assertEqual(detect_missing_dates(df), [])

    def test_single_or_empty_date(self):
        df_single = pd.DataFrame({"transaction_date": ["2026-01-01"]})
        self.assertEqual(detect_missing_dates(df_single), [])
        df_empty = pd.DataFrame({"transaction_date": []})
        self.assertEqual(detect_missing_dates(df_empty), [])


class TestPreprocessFeaturesPipeline(unittest.TestCase):
    """Tests for the high-level Phase 2 pipeline function."""

    def test_pipeline_with_dataframe(self):
        df = get_valid_transaction_data()
        sorted_df, daily_df, summary = preprocess_features(df)

        # Output validations
        self.assertIsInstance(sorted_df, pd.DataFrame)
        self.assertIsInstance(daily_df, pd.DataFrame)
        self.assertIsInstance(summary, dict)

        # Record preservation
        self.assertEqual(len(sorted_df), len(df))
        # Missing date between Jan 1 and Jan 4 is Jan 2
        self.assertIn(pd.Timestamp("2026-01-02"), summary["missing_calendar_dates"])
        self.assertEqual(summary["missing_calendar_date_count"], 1)


if __name__ == "__main__":
    unittest.main()
