"""
Data Processing Module for NEXLYTICS.

Handles CSV loading, schema validation, type conversions, sorting,
daily aggregation, and missing calendar date detection for transaction data.
Compatible with Python 3.13+ and Pandas 3.x.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

# Standard required columns for transaction data
REQUIRED_TRANSACTION_COLUMNS: List[str] = [
    "transaction_date",
    "transaction_id",
    "revenue",
    "cost",
    "profit",
    "category",
]

NUMERIC_COLUMNS: List[str] = ["revenue", "cost", "profit"]


def load_dataset(file_path: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
    """Load raw dataset from disk or storage into a Pandas DataFrame.

    Args:
        file_path: Path to the target CSV file.
        **kwargs: Optional parser arguments passed to pd.read_csv.

    Returns:
        Loaded pandas DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist at file_path.
        ValueError: If file cannot be parsed or is empty/corrupt.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found at: {file_path}")

    try:
        df = pd.read_csv(path, **kwargs)
    except pd.errors.EmptyDataError as err:
        raise ValueError(f"Dataset file is empty: {file_path}") from err
    except pd.errors.ParserError as err:
        raise ValueError(f"Failed to parse CSV file at {file_path}: {err}") from err
    except Exception as err:
        raise ValueError(f"Error reading CSV file at {file_path}: {err}") from err

    if df.empty:
        raise ValueError(f"Dataset file loaded as empty DataFrame: {file_path}")

    return df


def validate_transaction_columns(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
) -> None:
    """Validate that required transaction columns are present in the DataFrame.

    Args:
        df: Input DataFrame to check.
        required_columns: List of column names that must be present.
            Defaults to REQUIRED_TRANSACTION_COLUMNS.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        ValueError: If any required columns are missing from df.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")

    if required_columns is None:
        required_columns = REQUIRED_TRANSACTION_COLUMNS

    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required transaction columns: {missing_cols}. "
            f"Available columns: {list(df.columns)}"
        )


def validate_and_clean_transactions(
    df: pd.DataFrame,
    allow_duplicate_ids: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Clean and validate transaction DataFrame safely.

    Converts dates and numeric fields safely, checks for missing/invalid
    values, and gathers validation metrics without dropping records silently.

    Args:
        df: Raw transaction DataFrame.
        allow_duplicate_ids: If False, raises ValueError on duplicate transaction_id.
            If True, logs duplicates in summary without dropping rows.

    Returns:
        Tuple containing:
            - Cleaned and type-converted DataFrame (copy).
            - Validation summary dictionary.

    Raises:
        ValueError: If required columns are missing, dates/numerics cannot be parsed,
            required values are null, or duplicate IDs exist when allow_duplicate_ids=False.
    """
    validate_transaction_columns(df)

    # Work on an isolated copy to preserve original input
    cleaned_df = df.copy()

    # 1. Validate and convert transaction_date
    raw_dates = cleaned_df["transaction_date"]
    if raw_dates.isna().any():
        null_indices = cleaned_df.index[raw_dates.isna()].tolist()
        raise ValueError(
            f"Found null transaction_date values at row index/indices: {null_indices}"
        )

    parsed_dates = pd.to_datetime(raw_dates, errors="coerce")
    invalid_date_mask = parsed_dates.isna()
    if invalid_date_mask.any():
        invalid_rows = cleaned_df.index[invalid_date_mask].tolist()
        invalid_vals = raw_dates.loc[invalid_date_mask].tolist()
        raise ValueError(
            f"Invalid transaction_date format at row index/indices {invalid_rows}: {invalid_vals}"
        )

    # Normalize dates to calendar day (timestamp with 00:00:00)
    cleaned_df["transaction_date"] = parsed_dates.dt.normalize()

    # 2. Validate transaction_id and category
    for col in ["transaction_id", "category"]:
        if cleaned_df[col].isna().any():
            null_rows = cleaned_df.index[cleaned_df[col].isna()].tolist()
            raise ValueError(
                f"Missing or null values found in required column '{col}' at rows: {null_rows}"
            )

    # 3. Check duplicate transaction IDs
    duplicate_mask = cleaned_df.duplicated(subset=["transaction_id"], keep=False)
    duplicate_ids = (
        cleaned_df.loc[duplicate_mask, "transaction_id"].unique().tolist()
    )
    if duplicate_ids and not allow_duplicate_ids:
        raise ValueError(
            f"Duplicate transaction_id values detected: {duplicate_ids}"
        )

    # 4. Validate and convert numeric fields safely
    for col in NUMERIC_COLUMNS:
        raw_vals = cleaned_df[col]
        if raw_vals.isna().any():
            null_rows = cleaned_df.index[raw_vals.isna()].tolist()
            raise ValueError(
                f"Null values found in numeric column '{col}' at row index/indices: {null_rows}"
            )

        numeric_vals = pd.to_numeric(raw_vals, errors="coerce")
        invalid_num_mask = numeric_vals.isna()
        if invalid_num_mask.any():
            invalid_rows = cleaned_df.index[invalid_num_mask].tolist()
            invalid_raw = raw_vals.loc[invalid_num_mask].tolist()
            raise ValueError(
                f"Non-numeric values found in column '{col}' at row index/indices {invalid_rows}: {invalid_raw}"
            )

        cleaned_df[col] = numeric_vals.astype(float)

    # Compile validation summary
    summary: Dict[str, Any] = {
        "total_records": len(cleaned_df),
        "unique_transaction_ids": int(cleaned_df["transaction_id"].nunique()),
        "duplicate_id_count": int(duplicate_mask.sum()),
        "duplicate_ids": duplicate_ids,
        "date_min": cleaned_df["transaction_date"].min(),
        "date_max": cleaned_df["transaction_date"].max(),
        "categories": sorted(cleaned_df["category"].dropna().unique().tolist()),
        "total_revenue": float(cleaned_df["revenue"].sum()),
        "total_cost": float(cleaned_df["cost"].sum()),
        "total_profit": float(cleaned_df["profit"].sum()),
    }

    return cleaned_df, summary


def sort_transactions(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
) -> pd.DataFrame:
    """Sort transactions chronologically without silently dropping records.

    Preserves all records and performs a stable sort by date_column.

    Args:
        df: Input transactions DataFrame.
        date_column: Column name to sort chronologically by.

    Returns:
        Sorted pandas DataFrame with preserved length and reset index.

    Raises:
        ValueError: If date_column is not present in df.
    """
    if date_column not in df.columns:
        raise ValueError(f"Sort column '{date_column}' not found in DataFrame.")

    initial_len = len(df)
    sorted_df = df.sort_values(
        by=[date_column],
        kind="mergesort",  # stable sort
    ).reset_index(drop=True)

    if len(sorted_df) != initial_len:
        raise RuntimeError(
            f"Record count mismatch after sorting: expected {initial_len}, got {len(sorted_df)}"
        )

    return sorted_df


def aggregate_daily_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transactions by calendar day into daily metrics.

    Produces a summary DataFrame with columns:
    ['transaction_date', 'daily_revenue', 'daily_cost', 'daily_profit', 'order_count'].

    Args:
        df: Validated transaction DataFrame containing 'transaction_date',
            'revenue', 'cost', and 'profit'.

    Returns:
        Aggregated daily DataFrame sorted chronologically.

    Raises:
        ValueError: If required aggregation columns are missing.
    """
    required = ["transaction_date", "revenue", "cost", "profit"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Cannot aggregate daily transactions. Missing columns: {missing}"
        )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "transaction_date",
                "daily_revenue",
                "daily_cost",
                "daily_profit",
                "order_count",
            ]
        )

    # Ensure transaction_date is normalized to calendar day
    daily_dates = pd.to_datetime(df["transaction_date"]).dt.normalize()

    agg_df = (
        df.assign(_calendar_date=daily_dates)
        .groupby("_calendar_date", as_index=False)
        .agg(
            daily_revenue=("revenue", "sum"),
            daily_cost=("cost", "sum"),
            daily_profit=("profit", "sum"),
            order_count=("revenue", "count"),
        )
        .rename(columns={"_calendar_date": "transaction_date"})
        .sort_values(by="transaction_date")
        .reset_index(drop=True)
    )

    return agg_df


def detect_missing_dates(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
) -> List[pd.Timestamp]:
    """Detect missing calendar dates between min and max date in DataFrame.

    Identifies gaps in the continuous daily timeline without automatically
    filling or interpolating records.

    Args:
        df: Transaction or aggregated DataFrame.
        date_column: Name of the datetime column.

    Returns:
        List of missing calendar dates as pd.Timestamp instances.

    Raises:
        ValueError: If date_column is missing from df.
    """
    if date_column not in df.columns:
        raise ValueError(f"Date column '{date_column}' not found in DataFrame.")

    if df.empty or len(df[date_column].dropna()) < 2:
        return []

    parsed_dates = pd.to_datetime(df[date_column]).dt.normalize()
    min_date = parsed_dates.min()
    max_date = parsed_dates.max()

    expected_range = pd.date_range(start=min_date, end=max_date, freq="D")
    present_dates = pd.DatetimeIndex(parsed_dates.unique())

    missing = expected_range.difference(present_dates)
    return [pd.Timestamp(d) for d in missing]


def preprocess_features(
    data: Any,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Clean, validate, sort, aggregate, and inspect date continuity for transaction data.

    Serves as the high-level Phase 2 pipeline function that produces:
    1. Validated and sorted transaction-level DataFrame.
    2. Daily aggregated time-series DataFrame.
    3. Comprehensive validation summary including missing calendar days.

    Args:
        data: Raw transaction DataFrame or file path (str/Path).
        config: Optional configuration dictionary. Supported keys:
            - 'allow_duplicate_ids' (bool, default True)
            - 'date_column' (str, default 'transaction_date')

    Returns:
        Tuple of:
            - cleaned_transactions_df (pd.DataFrame)
            - daily_aggregated_df (pd.DataFrame)
            - validation_summary (Dict[str, Any])

    Raises:
        TypeError: If input data is neither a DataFrame nor a path.
        ValueError: On schema or validation errors.
    """
    config = config or {}
    allow_duplicate_ids = config.get("allow_duplicate_ids", True)

    if isinstance(data, (str, Path)):
        raw_df = load_dataset(data)
    elif isinstance(data, pd.DataFrame):
        raw_df = data
    else:
        raise TypeError(
            f"Expected pd.DataFrame or file path, got {type(data).__name__}"
        )

    # 1. Clean and validate
    cleaned_df, summary = validate_and_clean_transactions(
        raw_df, allow_duplicate_ids=allow_duplicate_ids
    )

    # 2. Chronological sort (preserves all records)
    sorted_df = sort_transactions(cleaned_df)

    # 3. Daily aggregation
    daily_df = aggregate_daily_transactions(sorted_df)

    # 4. Missing calendar date detection
    missing_dates = detect_missing_dates(daily_df)
    summary["missing_calendar_dates"] = missing_dates
    summary["missing_calendar_date_count"] = len(missing_dates)

    return sorted_df, daily_df, summary
