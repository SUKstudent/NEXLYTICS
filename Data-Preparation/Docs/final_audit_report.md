# NEXLYTICS final data engineering audit

## Verdict

**Original audit: PASS WITH WARNINGS. Follow-up: PASS for the two requested corrections.**

The original audit below describes the pre-correction state. The follow-up section records the targeted changes and their revalidation.

The original audit was read-only and did not execute cleaning or notebook cells.

## Audit checklist

| Area | Status | Evidence and result |
|---|---|---|
| Raw source inventory and audit read-only behavior | PASS | All eight expected source CSVs were read from `Raw-Datasets/`. The audit did not write to source files or execute the pipeline. |
| Byte-for-byte proof that raw files are unchanged | WARNING | The cleaning code writes to `Processed/` and `Docs/`, and no evidence of raw edits was found. However, no baseline cryptographic hashes were recorded, so this audit cannot independently prove byte-for-byte source immutability. |
| Eight cleaned CSVs exist and are readable | PASS | All expected files in `Processed/` were opened and parsed. |
| Actual row/column counts and source reconciliation | PASS | Counts match the source profiles and are independently confirmed below. |
| Exact duplicate removal in `coupon.csv` | PASS | Independently counted 5,164 exact full-row duplicates in the source. `coupon_cleaned.csv` has 119,384 rows and exactly matches source `drop_duplicates(keep="first")` after resetting the expected row index. |
| No unexpected loss in the other seven tables | PASS | Each source and cleaned output was compared in ordered 100,000-row chunks after only the documented transformations. No chunk had a content mismatch; source and output row counts match. |
| Column names and column preservation | PASS | Every cleaned header matches the documented lowercase snake_case normalization, with the original number and order of columns preserved. |
| Identifier and numeric values | PASS | Ordered row comparisons found no parsed numeric or identifier value changes. A lexical-format exception for `TRANS_TIME` is described below. |
| Missing-value and whitespace policy | PASS | Product whitespace-only fields independently reconcile to the cleaned missing counts. No unintended missing cells or remaining whitespace-only output text values were found. Other special labels and zero values remain unchanged. |
| Memory-efficient large-file handling | PASS | The cleaning script and notebook use 100,000-row chunks for large files. The audit independently compared the large source/output pairs in chunks; only the comparatively small coupon table was loaded as a whole for exact deduplication. |
| Notebook validity and workflow | PASS | `data_cleaning.ipynb` is valid JSON, uses notebook format 4.5, has 11 cells (5 code cells), and every code cell compiles. It contains source loading/profile checks, cleaning/export, validation-log checks, and before/after comparison. The pipeline was not run during this audit. |
| Notebook schema/execution-state verification | WARNING | The optional `nbformat` package was unavailable, so its validator could not be run. All notebook cells are unexecuted and have no saved outputs; their code was syntax-checked but not executed to avoid rewriting outputs. |
| Notebook overwrite behavior | WARNING | The export cell calls `run_cleaning_pipeline(allow_overwrite=True)`. Running that cell can regenerate and overwrite the named Phase 3 deliverables. The script itself defaults to refusing overwrites, but the notebook explicitly opts in. |
| `data_quality_report.md` accuracy | PASS | Reported source/final row counts, column counts, duplicate removal, product whitespace counts, and missing-value totals match the files and independent checks. It documents unresolved domain meanings and limitations. |
| Report disclosure of `TRANS_TIME` lexical change | WARNING | The report generally warns that numeric CSV formatting may change and that original lexical formatting remains in raw data, but it does not call out the observed zero-padding change and its count specifically. |
| `data_dictionary.csv` coverage and schema | PASS | It has 46 unique table/column entries, exactly covering the 4, 3, 5, 3, 4, 8, 7, and 12 columns in the eight respective tables. No description is blank. Types agree with the profiled data. |
| Dictionary descriptions | PASS | Descriptions avoid asserting unverified code meanings, units, date origins, or rules. They identify unknown definitions as unconfirmed. The claimed unique household/product identifiers were independently checked and are unique and non-null in their respective cleaned tables. |
| `validation_log.txt` claims | PASS | It records all eight outputs, row reconciliation, checks, an overall PASS, and successful publication. No `FAIL` entries are present. Its figures agree with the independent checks. |
| Validation-log duplicate/hash limitation | WARNING | The log discloses use of 64-bit Pandas row hashes and theoretical collision risk. This audit directly compared all output rows with their expected source transformations, but did not independently recompute whole-file exact duplicate counts for the seven non-coupon source tables using a separate external-sort method. |
| README and separate-table rationale | PASS | `Processed/README.md` correctly explains why the related tables remain separate and accurately lists their cleaned row and column counts. No merged `cleaned_data.csv` is required or present. |
| Cleaning and supporting scripts | PASS | `clean_dataset.py`, `inspect_dataset.py`, and `assess_data_quality.py` are present and compile. The cleaning script writes outputs outside `Raw-Datasets/`; its chunking, deduplication, and validation behavior is consistent with the deliverables. The Phase 1/2 reports and metrics are present as supporting evidence. |

## Source-to-cleaned reconciliation

| Table | Source rows | Source columns | Cleaned rows | Cleaned columns | Rows removed |
|---|---:|---:|---:|---:|---:|
| `campaign_desc.csv` | 30 | 4 | 30 | 4 | 0 |
| `campaign_table.csv` | 7,208 | 3 | 7,208 | 3 | 0 |
| `causal_data.csv` | 36,786,524 | 5 | 36,786,524 | 5 | 0 |
| `coupon.csv` | 124,548 | 3 | 119,384 | 3 | 5,164 exact duplicate rows |
| `coupon_redempt.csv` | 2,318 | 4 | 2,318 | 4 | 0 |
| `hh_demographic.csv` | 801 | 8 | 801 | 8 | 0 |
| `product.csv` | 92,353 | 7 | 92,353 | 7 | 0 |
| `transaction_data.csv` | 2,595,732 | 12 | 2,595,732 | 12 | 0 |

The independent comparison normalized source headers as documented, trimmed profiled text fields, and represented whitespace-only text as missing. For the seven non-coupon tables, every ordered chunk matched its cleaned counterpart. For coupon, the source deduplicated with `keep="first"` matched the cleaned file exactly after accounting for the new sequential row index.

The independently measured product missing cells are: `department` 15, `commodity_desc` 15, `sub_commodity_desc` 15, and `curr_size_of_product` 30,607, for 30,652 total. These agree with the report, dictionary, and validation log. No rows were removed from product.

## Findings requiring attention

| Severity | Finding and evidence | Recommended action |
|---|---|---|
| Medium | **`TRANS_TIME` zero-padding is not retained in the cleaned CSV.** A raw-text scan found 165,055 of 2,595,732 values (6.359%) represented with leading zeros. For example, raw `0946` is cleaned as `946`. All parsed numeric values still match, no calendar/time conversion occurred, and the original raw CSV remains the source for the lexical form. The field’s format and meaning are not confirmed. | Before treating or displaying this field as a clock value, ask the dataset/domain owner whether its fixed-width text representation is meaningful. If it is, preserve it as text or apply an owner-confirmed formatting rule in a future approved revision. |
| Low | **Notebook export cell permits overwriting.** `data_cleaning.ipynb` calls the pipeline with `allow_overwrite=True`; rerunning it replaces named Phase 3 outputs. | Make the overwrite behavior explicit to anyone using the notebook; review outputs/backups before intentionally rerunning the export cell. |
| Low | **Raw byte identity cannot be established from a baseline.** The audit found no evidence that raw inputs were edited, but initial hashes are unavailable. | For future phases, record cryptographic hashes of raw inputs and verify them after processing. |
| Low | **Notebook validation was static.** The notebook was not executed, and the optional `nbformat` validator was unavailable. | If notebook execution is needed later, do so in a controlled environment after reviewing its overwrite-enabled export cell; install/use `nbformat` as part of that separate validation if required. |

## Deliverable assessment

- **Cleaned CSVs:** All eight expected files exist; their row and column counts reconcile. Seven are unchanged in row count and match their documented source transformations. Coupon has exactly 5,164 identical full rows removed, and no other values differ.
- **`data_cleaning.ipynb`:** Valid JSON notebook structure with a complete executable workflow. Cells were not run as part of this read-only audit. The export cell is overwrite-enabled.
- **`data_quality_report.md`:** Figures and documented missing/duplicate transformations match the data. Add a specific note about `TRANS_TIME` padding in any future approved documentation revision.
- **`data_dictionary.csv`:** 46/46 columns represented, with no blank descriptions; unresolved domain meanings are appropriately qualified.
- **`validation_log.txt`:** Recorded pass claims and row counts agree with the audit. It appropriately discloses hash-based validation limitations.
- **`Processed/README.md` and scripts:** Rationale for retaining the eight relational tables is accurate. The cleaning script is consistent with actual outputs and does not target raw files for writing.

## Handoff recommendation at time of original audit

**Safe to hand off with warnings.** Use the cleaned tables for analyses that depend on numeric `TRANS_TIME` values only after noting that their original leading-zero formatting was not retained. Keep `Raw-Datasets/` as the immutable source of record for any format-sensitive use. Do not rerun the notebook export cell unless overwriting the existing Phase 3 deliverables is intentional.

## Follow-up correction and revalidation — 2026-11-20

The two requested issues have been addressed without rerunning the full cleaning pipeline:

- Raw `transaction_data.csv.TRANS_TIME` was scanned in 100,000-row chunks. All 2,595,732 values are four ASCII digits and fall within the numeric ranges 00–23 and 00–59; 165,055 begin with zero, and no unusual values were found. These are format checks only and do not establish time semantics.
- `transaction_data_cleaned.csv` alone was regenerated and validated. Its `trans_time` column is now text, all four-character values match the raw source in row order, numeric row counts and the other 11 columns are unchanged, and the original 165,055 leading-zero forms are restored. No values were padded or converted to date/time objects.
- `clean_dataset.py` now applies the evidenced text type, validates source-to-output `TRANS_TIME` text directly, records format/range counts and unusual-value examples, and generates matching report/dictionary/log content. `data_cleaning.ipynb` includes the chunked source profile and loads the preview column as text.
- The notebook export cell now defaults to `ALLOW_OVERWRITE = False`; explicit opt-in is required. The script rejects write destinations inside `Raw-Datasets/`.
- The existing-output preflight rejects the default overwrite attempt and accepts explicit opt-in without writing files. The raw-destination guard also rejects a path under `Raw-Datasets/`.

The two requested warnings are resolved. Overall handoff remains **PASS WITH WARNINGS** only for audit-level limitations from the original review (no baseline source checksums and no optional `nbformat` validator); no other tables or cleaning rules were changed.
