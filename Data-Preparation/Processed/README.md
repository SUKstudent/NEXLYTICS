# NEXLYTICS — Cleaned Relational Tables

This folder contains cleaned datasets prepared from the original source tables. The tables are maintained separately because they represent different data grains and purposes, including campaign definitions, campaign assignments, product and coupon mappings, household demographics, promotional observations, coupon redemptions, and transaction records.

Keeping the tables separate avoids unintended row multiplication, loss of unmatched records, or mixing different data scopes during joins. Relationships should be established only when required for a specific analysis, using the data dictionary and verified relationship evidence.

The original files in `Raw-Datasets/` remain unchanged. Exact duplicate removal was limited to `coupon.csv`, where only identical full rows were removed from the cleaned output. The other tables retain their original row counts.

## Cleaned Tables

| File | Rows | Columns |
|---|---:|---:|
| `campaign_desc_cleaned.csv` | 30 | 4 |
| `campaign_table_cleaned.csv` | 7,208 | 3 |
| `coupon_cleaned.csv` | 119,384 | 3 |
| `coupon_redempt_cleaned.csv` | 2,318 | 4 |
| `hh_demographic_cleaned.csv` | 801 | 8 |
| `product_cleaned.csv` | 92,353 | 7 |

## Locally Retained Datasets

The following large cleaned datasets are excluded from this repository due to file size limitations but remain preserved locally:

- `causal_data_cleaned.csv` — 36,786,524 rows; 5 columns.
- `transaction_data_cleaned.csv` — 2,595,732 rows; 12 columns.

These files have been cleaned and validated as part of the data preparation process; they have not been deleted.

## Documentation

Refer to the following files in `../Docs/` for additional information:

- `data_quality_report.md` — data quality findings and cleaning details.
- `data_dictionary.csv` — column definitions and schema reference.
- `validation_log.txt` — validation checks and recorded results.

This folder contains the repository-accessible cleaned datasets for the subsequent Business Analysis phase.
