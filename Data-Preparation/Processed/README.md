# NEXLYTICS — Cleaned Relational Tables

This folder contains six cleaned CSV tables prepared from the original source datasets. The tables are maintained separately because they represent different data grains and purposes, including campaign definitions, campaign assignments, coupon mappings, coupon redemptions, household demographics, and product information.

Keeping the tables separate avoids unintended row multiplication, loss of unmatched records, or mixing different data scopes during joins. Relationships should be established only for specific analytical requirements after reviewing the data dictionary and relationship evidence.

The original source files remain unchanged. Exact duplicate removal was limited to `coupon.csv`, where only identical full rows were removed from the cleaned output. The other tables retain their original row counts.

## Cleaned Tables

| File | Rows | Columns |
|---|---:|---:|
| `campaign_desc_cleaned.csv` | 30 | 4 |
| `campaign_table_cleaned.csv` | 7,208 | 3 |
| `coupon_cleaned.csv` | 119,384 | 3 |
| `coupon_redempt_cleaned.csv` | 2,318 | 4 |
| `hh_demographic_cleaned.csv` | 801 | 8 |
| `product_cleaned.csv` | 92,353 | 7 |

## Documentation

Refer to the following files in `../Docs/` for additional information:

- `data_quality_report.md` — data quality findings and cleaning details.
- `data_dictionary.csv` — column definitions and schema reference.
- `validation_log.txt` — validation checks and recorded results.

These cleaned tables are prepared for the subsequent Business Analysis phase of NEXLYTICS.
