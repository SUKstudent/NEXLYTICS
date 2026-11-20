# NEXLYTICS cleaned relational tables

This folder contains eight cleaned CSVs, one per source table. They were kept separate instead of being merged into a single `cleaned_data.csv` because the source tables have different grains (campaign definitions, assignments, product/coupon mappings, demographics, promotional observations, redemptions, and transaction lines). A blind join could multiply rows, discard unmatched records, or mix selected-population and transaction scopes. Join only for a defined analysis after reviewing the data dictionary and relationship evidence.

No original in `Raw-Datasets/` was modified. Exact duplicate removal was limited to `coupon.csv`; its cleaned copy removes only identical full rows. Other tables retain their source row counts.

## Cleaned files

- `campaign_desc_cleaned.csv` — 30 rows; 4 normalized columns.
- `campaign_table_cleaned.csv` — 7,208 rows; 3 normalized columns.
- `causal_data_cleaned.csv` — 36,786,524 rows; 5 normalized columns.
- `coupon_cleaned.csv` — 119,384 rows; 3 normalized columns.
- `coupon_redempt_cleaned.csv` — 2,318 rows; 4 normalized columns.
- `hh_demographic_cleaned.csv` — 801 rows; 8 normalized columns.
- `product_cleaned.csv` — 92,353 rows; 7 normalized columns.
- `transaction_data_cleaned.csv` — 2,595,732 rows; 12 normalized columns.

See `../Docs/data_quality_report.md`, `../Docs/data_dictionary.csv`, and `../Docs/validation_log.txt` for transformations, schema, limitations, and checks.
