# NEXLYTICS ML Evaluation & Deliverables Report

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
| Total Transactions | Cleaned record count | 80 |
| Unique Transaction IDs | Distinct transaction IDs | 80 |
| Historical Date Range | Continuous calendar range | 2026-01-01 to 2026-02-09 |
| Total Revenue | Aggregated gross revenue | $44,500.00 |
| Total Cost | Aggregated operational cost | $20,025.00 |
| Total Profit | Aggregated operating profit | $24,475.00 |

---

## 3. Operational Anomaly Detection Results
- **Model:** Isolation Forest fitted on `[daily_revenue, daily_cost, daily_profit]`
- **Total Monitored Days:** 40
- **Flagged Anomalies:** 2 (5.0% of calendar days)
- **Breakdown by Classified Anomaly Type:**
  - **Expense Spike**: 2 occurrence(s)
- **Leading Attributed Driver Categories:**
  - **Electronics**: 2 occurrence(s)
- **Methodology Notice:**
  > [!NOTE]
  > Anomaly evaluation metrics reflect descriptive statistical distributions. Precision, recall, and ROC-AUC are not fabricated in the absence of verified ground-truth labels.

---

## 4. Sales Forecasting Benchmarks & Evaluation
- **Chronological Split:**
  - **Training Partition (80% earliest):** 26 days (2026-01-08 to 2026-02-02)
  - **Held-out Test Partition (20% latest):** 7 days (2026-02-03 to 2026-02-09)
  - **Future Forecast Horizon (7 days):** 2026-02-10 to 2026-02-16
- **Held-Out Test Set Performance:**
  - **Model MAE:** $27.75
  - **Model RMSE:** $31.98
  - **Naive Baseline MAE (Last-Observed-Value):** $34.29
  - **Naive Baseline RMSE:** $51.41
  - **Relative Improvement:** **Outperformed Naive Baseline** by +19.1% lower MAE.
- **Uncertainty Margin:** $\pm$55.31 (derived empirically from chronological validation MAE; clamped to $0.00 lower bound for nonnegative revenue).

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
> **Heuristic Uncertainty Bands**: The uncertainty interval represents empirical spread ($\pm 1.96 \times \text{MAE}_{\text{train\_val}}$) derived from historical training residuals, NOT a strict parametric 95% Gaussian confidence or prediction interval.

> [!IMPORTANT]
> **Correlation vs. Causation Caution**: Category driver attributions (`top_driver_category`) indicate the category showing the largest historical divergence on an anomalous date. These constitute supporting analytical clues and operational guidance, not definitive root causes.

> [!CAUTION]
> **Calendar Day Continuity**: Time-series lag and rolling features require continuous, uninterrupted calendar days. Missing dates must not be silently imputed; gaps indicate unrecorded operational periods.
