# NEXLYTICS — Predictive Analytics & Machine Learning Engine

Welcome to the **NEXLYTICS ML** module. This repository provides an end-to-end, production-ready machine learning pipeline for financial telemetry, operational anomaly detection, multi-step sales forecasting, and automated deliverables generation.

---

## 1. Project Architecture & Directory Layout

```text
NEXLYTICS-ML/
├── data/                             # Raw transaction storage (local data excluded by .gitignore)
├── notebooks/
│   └── ml_analysis.ipynb             # Structured exploratory, modeling, & visualization notebook
├── outputs/                          # Generated hackathon deliverables
│   ├── anomaly_results.csv           # Operational anomaly detection results
│   ├── forecast_results.csv          # 7-day revenue forecast and evaluation series
│   └── charts/                       # Publication-ready visualization figures
│       ├── trend_chart.png           # Daily revenue, cost, and profit trends
│       ├── anomaly_chart.png         # Anomaly overlay distinguishing expense spikes
│       └── forecast_chart.png        # Sales forecast with heuristic uncertainty bands
├── reports/
│   └── ml_evaluation_report.md       # Comprehensive evaluation and benchmark report
├── src/
│   ├── __init__.py                   # Package initializer
│   ├── data_processing.py            # Ingestion, validation, sorting, daily aggregation
│   ├── anomaly_detection.py          # Isolation Forest and category attribution engine
│   ├── forecasting.py                # Walk-forward linear regression and future forecasting
│   └── evaluation.py                 # Error metrics, naive benchmarks, charts, report generator
├── tests/
│   ├── __init__.py                   # Test package marker
│   ├── test_data_processing.py       # Unit tests for data processing & validation
│   ├── test_anomaly_detection.py     # Unit tests for anomaly detection & attribution
│   ├── test_forecasting.py           # Unit tests for sales forecasting & feature safety
│   ├── test_evaluation.py            # Unit tests for metrics, baseline, and charts
│   └── test_integration.py           # End-to-end pipeline integration tests
├── run_pipeline.py                   # Minimal CLI entry point
├── requirements.txt                  # Locked Python 3.13 dependencies
├── .gitignore                        # Git ignore rules (allows deliverable CSVs/charts)
└── README.md                         # Project documentation and team guide
```

---

## 2. Environment Setup

### Prerequisites
- Python 3.13+ (tested on Python 3.13.12)
- Existing virtual environment (`.venv`)

### Activation & Installation
Activate the existing virtual environment and verify installed dependencies:

```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install / verify requirements
pip install -r requirements.txt
```

---

## 3. Expected Transaction CSV Schema

The input CSV provided to the pipeline must contain the following six columns:

| Column Name | Type | Description |
|---|---|---|
| `transaction_date` | Date / String (`YYYY-MM-DD`) | Date of transaction. Must be parseable to calendar day. |
| `transaction_id` | String / Numeric | Unique identifier for the transaction record. |
| `revenue` | Float / Numeric | Gross revenue generated. Non-negative numeric value. |
| `cost` | Float / Numeric | Cost of goods sold / operational expense. Non-negative numeric value. |
| `profit` | Float / Numeric | Net operating profit (`revenue - cost`). |
| `category` | String | Commercial product or service category (e.g., `Electronics`, `Books`). |

> [!IMPORTANT]
> **Calendar Continuity Requirement:** The pipeline aggregates transactions into daily summaries. Historical observations must form a continuous sequence of consecutive calendar days without missing dates. If unrecorded date gaps exist, the pipeline fails with a descriptive error message rather than silently imputing data.

---

## 4. CLI Entry Point Usage

Run the complete pipeline end-to-end using `run_pipeline.py`:

```bash
# Basic run with input dataset and default outputs directory ('outputs/')
python run_pipeline.py --input path/to/transactions.csv

# Custom output directory and custom 14-day forecast horizon
python run_pipeline.py --input path/to/transactions.csv --output-dir custom_outputs --horizon 14

# Custom report path
python run_pipeline.py --input path/to/transactions.csv --report-path reports/my_custom_report.md
```

### CLI Arguments
- `--input`, `-i`: (Required) Path to the input transaction CSV file.
- `--output-dir`, `-o`: (Optional) Directory to save output CSVs and charts (default: `outputs`).
- `--report-path`, `-r`: (Optional) File path for the generated markdown report (default: `reports/ml_evaluation_report.md`).
- `--horizon`: (Optional) Number of days for the future sales forecast (default: `7`).

---

## 5. Output Deliverables Description

Running the pipeline produces the following standardized artifacts in `outputs/`:

1. **`outputs/anomaly_results.csv`**:
   - `transaction_date`: Calendar date.
   - `daily_revenue`: Total daily revenue.
   - `daily_cost`: Total daily cost.
   - `is_anomaly`: Binary flag (`Yes` or `No`).
   - `anomaly_type`: Classification (`Revenue Drop`, `Expense Spike`, `Profit Drop`, `Other Anomaly`, or blank for normal days).
   - `top_driver_category`: Attributed category showing the largest historical divergence (supporting analytical clue).
   - Additional preserved fields: `daily_profit`, `anomaly_score`, `anomaly_flag`.

2. **`outputs/forecast_results.csv`**:
   - `forecast_date`: Calendar date.
   - `actual_revenue`: Ground-truth revenue for held-out test rows; empty (`NaN`) for future forecast rows.
   - `predicted_revenue`: Recursive walk-forward prediction from `LinearRegression`.
   - `lower_bound`: Lower bound of the heuristic uncertainty band (clamped to `0.0`).
   - `upper_bound`: Upper bound of the heuristic uncertainty band.
   - `naive_revenue`: Last-observed-revenue baseline prediction.

3. **`outputs/charts/`**:
   - `trend_chart.png`: Visualizes daily financial trends (Revenue, Cost, Profit).
   - `anomaly_chart.png`: Highlights operational outliers, explicitly distinguishing Expense Spikes on the cost curve.
   - `forecast_chart.png`: Historical test actuals, predictions, 7-day future forecast, heuristic uncertainty band ($\pm 1.96 \text{ MAE}$), and forecast origin demarcation.

4. **`reports/ml_evaluation_report.md`**:
   - Complete technical and business evaluation report detailing model selection, chronological partitions, MAE/RMSE comparisons against the naive baseline, descriptive anomaly counts, and risk cautions.

---

## 6. Integration Guide for Teammates

### For Naveen (Backend / API Integration)
1. **Executing the ML Engine from Backend Services:**
   - Execute `run_pipeline.py` as a subprocess or import `run_pipeline` directly in Python:
     ```python
     from run_pipeline import run_pipeline

     summary = run_pipeline(input_path="data/transactions.csv", output_dir="outputs")
     print(summary["forecast_eval"]["model_mae"])
     ```
2. **Consuming Output Data in Database / REST Endpoints:**
   - Ingest `outputs/anomaly_results.csv` into the anomaly feed table. Filter by `is_anomaly == "Yes"` to trigger real-time notification alerts.
   - Ingest `outputs/forecast_results.csv` for the sales dashboard endpoint. Future forecast records are identified where `actual_revenue` is null or where `forecast_date > forecast_origin`.
3. **Error Handling:**
   - Any validation error (e.g. missing columns, date discontinuities, insufficient history $< 20$ days) raises a `ValueError` with clear exit code `1`. Ensure your worker catches stderr to display informative API responses.

### For Hasan (Frontend / Dashboard Integration)
1. **Displaying Charts & Visualizations:**
   - Serve static images directly from `outputs/charts/`:
     - `outputs/charts/trend_chart.png` -> Financial overview card
     - `outputs/charts/anomaly_chart.png` -> Outlier detection tab
     - `outputs/charts/forecast_chart.png` -> Predictive revenue widget
2. **Rendering Dynamic Tables & Cards:**
   - **Anomalies Table:** Display `transaction_date`, `daily_revenue`, `daily_cost`, and `anomaly_type`. Use badge colors for anomaly types (`Expense Spike` in red, `Revenue Drop` in orange). Render `top_driver_category` as supporting operational context.
   - **Sales Forecast:** Plot `predicted_revenue` against `actual_revenue`. Render `lower_bound` and `upper_bound` as a shaded band labeled **"Heuristic Uncertainty Band (±1.96 MAE)"**. Do NOT label this as a strict 95% confidence interval.
   - **Forecast Origin Line:** Ensure the UI visually distinguishes historical evaluation dates from future projections.

---

## 7. Running Tests & Quality Verification

Run the comprehensive unit and integration test suite:

```bash
# Run all 60+ tests using unittest
python -m unittest discover -s tests -v
```

All tests execute on small in-memory fixtures without modifying local files or creating permanent dummy datasets.
