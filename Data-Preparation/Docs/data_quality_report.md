# NEXLYTICS data quality and cleaning report

## Scope

Eight related tables were cleaned independently. The original `Raw-Datasets/` files were not changed. No tables were merged, no imputations or outlier removals were made, and numeric day/week/time codes were not converted to dates.

Phase 1 and Phase 2 inspection profiles were reused for original row counts, parser-null counts, blank/whitespace counts, duplicate counts, types, and identifier checks. Pandas processed large files in 100,000-row chunks.

## Cleaning actions and before/after comparison

| Table | Source rows | Source columns | Source parser nulls | Source blank/whitespace text | Source exact duplicates | Rows removed | Final rows | Final columns | Cleaned missing cells |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `campaign_desc.csv` | 30 | 4 | 0 | 0 | 0 | 0 | 30 | 4 | 0 |
| `campaign_table.csv` | 7,208 | 3 | 0 | 0 | 0 | 0 | 7,208 | 3 | 0 |
| `causal_data.csv` | 36,786,524 | 5 | 0 | 0 | 0 | 0 | 36,786,524 | 5 | 0 |
| `coupon.csv` | 124,548 | 3 | 0 | 0 | 5,164 | 5,164 | 119,384 | 3 | 0 |
| `coupon_redempt.csv` | 2,318 | 4 | 0 | 0 | 0 | 0 | 2,318 | 4 | 0 |
| `hh_demographic.csv` | 801 | 8 | 0 | 0 | 0 | 0 | 801 | 8 | 0 |
| `product.csv` | 92,353 | 7 | 0 | 30,652 | 0 | 0 | 92,353 | 7 | 30,652 |
| `transaction_data.csv` | 2,595,732 | 12 | 0 | 0 | 0 | 0 | 2,595,732 | 12 | 0 |

### Transformations applied

- Every header was normalized to lowercase snake_case; the original-to-cleaned mapping is recorded in `data_dictionary.csv`.
- Leading/trailing whitespace was trimmed from profiled text columns. Text values that became empty after trimming were written as CSV missing cells; labels such as `Unknown`, `None/Unknown`, and `N/A DEOD SPRAY/GEL DEOD` were preserved as text.
- `coupon.csv` alone had exact full-row duplicates removed from the cleaned copy. The original remains unchanged.
- Source-profiled numeric/text dtypes were applied consistently while reading, except `transaction_data.TRANS_TIME`, which is stored as text to preserve its observed representation. No date conversion, identifier recoding, unit scaling, imputation, row filtering, or outlier treatment was applied.
- CSV serialization can normalize lexical formatting in numeric columns (for example, float-profiled values may be written with decimal notation). `TRANS_TIME` is an explicit text exception to preserve its source form. Numeric values and canonical rows were round-trip validated; use `Raw-Datasets/` when original byte-level representation is required.

## Per-table actions and headers

- `campaign_desc.csv` → `campaign_desc_cleaned.csv`: 0 exact rows removed; 30 final rows. Header mapping: `DESCRIPTION` → `description`, `CAMPAIGN` → `campaign`, `START_DAY` → `start_day`, `END_DAY` → `end_day`.
- `campaign_table.csv` → `campaign_table_cleaned.csv`: 0 exact rows removed; 7,208 final rows. Header mapping: `DESCRIPTION` → `description`, `household_key` → `household_key`, `CAMPAIGN` → `campaign`.
- `causal_data.csv` → `causal_data_cleaned.csv`: 0 exact rows removed; 36,786,524 final rows. Header mapping: `PRODUCT_ID` → `product_id`, `STORE_ID` → `store_id`, `WEEK_NO` → `week_no`, `display` → `display`, `mailer` → `mailer`.
- `coupon.csv` → `coupon_cleaned.csv`: 5,164 exact rows removed; 119,384 final rows. Header mapping: `COUPON_UPC` → `coupon_upc`, `PRODUCT_ID` → `product_id`, `CAMPAIGN` → `campaign`.
- `coupon_redempt.csv` → `coupon_redempt_cleaned.csv`: 0 exact rows removed; 2,318 final rows. Header mapping: `household_key` → `household_key`, `DAY` → `day`, `COUPON_UPC` → `coupon_upc`, `CAMPAIGN` → `campaign`.
- `hh_demographic.csv` → `hh_demographic_cleaned.csv`: 0 exact rows removed; 801 final rows. Header mapping: `AGE_DESC` → `age_desc`, `MARITAL_STATUS_CODE` → `marital_status_code`, `INCOME_DESC` → `income_desc`, `HOMEOWNER_DESC` → `homeowner_desc`, `HH_COMP_DESC` → `hh_comp_desc`, `HOUSEHOLD_SIZE_DESC` → `household_size_desc`, `KID_CATEGORY_DESC` → `kid_category_desc`, `household_key` → `household_key`.
- `product.csv` → `product_cleaned.csv`: 0 exact rows removed; 92,353 final rows. Header mapping: `PRODUCT_ID` → `product_id`, `MANUFACTURER` → `manufacturer`, `DEPARTMENT` → `department`, `BRAND` → `brand`, `COMMODITY_DESC` → `commodity_desc`, `SUB_COMMODITY_DESC` → `sub_commodity_desc`, `CURR_SIZE_OF_PRODUCT` → `curr_size_of_product`.
- `transaction_data.csv` → `transaction_data_cleaned.csv`: 0 exact rows removed; 2,595,732 final rows. Header mapping: `household_key` → `household_key`, `BASKET_ID` → `basket_id`, `DAY` → `day`, `PRODUCT_ID` → `product_id`, `QUANTITY` → `quantity`, `SALES_VALUE` → `sales_value`, `STORE_ID` → `store_id`, `RETAIL_DISC` → `retail_disc`, `TRANS_TIME` → `trans_time`, `WEEK_NO` → `week_no`, `COUPON_DISC` → `coupon_disc`, `COUPON_MATCH_DISC` → `coupon_match_disc`.

## Missing-value changes

Phase 2 found no parser-recognized null cells. Whitespace-only text was measured separately. The following product cells were normalized to missing values; no rows were dropped:

- `product.csv.DEPARTMENT`: 15 whitespace-only source cells.
- `product.csv.COMMODITY_DESC`: 15 whitespace-only source cells.
- `product.csv.SUB_COMMODITY_DESC`: 15 whitespace-only source cells.
- `product.csv.CURR_SIZE_OF_PRODUCT`: 30,607 whitespace-only source cells.
- Literal categories such as `Unknown` and `None/Unknown` were preserved. Missing counts in the output correspond only to profiled source nulls and text cells made blank by whitespace trimming.

## Duplicate reconciliation

- `campaign_desc.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `campaign_table.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `causal_data.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `coupon.csv`: 5,164 source exact duplicates; 5,164 removed; 0 exact duplicates in cleaned output.
- `coupon_redempt.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `hh_demographic.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `product.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.
- `transaction_data.csv`: 0 source exact duplicates; 0 removed; 0 exact duplicates in cleaned output.

## Issues preserved for future analysis

- No unmatched household, product, campaign, store, week, or coupon identifiers were removed. Phase 2 showed differing table scopes and incomplete demographic coverage; these are not automatically errors.
- Zero quantities, zero sales, large quantities, positive retail discounts, and discount sign patterns were preserved.
- Numeric `DAY`, `START_DAY`, `END_DAY`, and `WEEK_NO` codes were preserved as numbers. `transaction_data.TRANS_TIME` is stored as text and retains the original four-character source representation.
- Raw `TRANS_TIME` was profiled in chunks: all 2,595,732 values have four digits and fall within the numeric ranges 00–23 and 00–59; 165,055 begin with zero, and no values were outside the checked shape/ranges. This is format evidence only, not confirmation of a time interpretation or time zone. No padding was applied; source text was retained as-is, with no date/time conversion.
- CSV files do not embed column types. Load `trans_time` as text (for example, `dtype={"trans_time": "string"}` in Pandas) so a reader does not infer a number and discard leading zeroes in memory.
- Sentinel-like category labels and empty strings outside the whitespace-only normalization rule were not replaced.
- The `coupon.csv` cleaned copy has fewer rows by the exact duplicate count; the original and duplicate-group details remain available in the prior Phase 2 report.

## Limitations and unresolved concerns

- No local table-level data dictionary was available. Grain, units, day/week/time origins, demographic selection rules, and discount/quantity conventions need owner confirmation.
- Unique tuple tests describe this extract only and are not declared database constraints.
- Whitespace-only product size fields may mean not applicable or unavailable; their business interpretation is unresolved.
- Hash-based global duplicate and round-trip checks use 64-bit Pandas row hashes, with theoretical collision risk.
- CSV numeric lexical formatting may differ from the source even where parsed numeric values and dtypes round-trip correctly; use `Raw-Datasets/` if original byte-level representation is required.
- The project guide's exact names for its five deliverables were not present; the Phase 2 report contains a clearly labeled proposed mapping.

Validation details and per-check results are in `validation_log.txt`.
