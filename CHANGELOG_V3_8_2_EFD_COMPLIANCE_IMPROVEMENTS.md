# CETTP V3.8.2 – EFD Compliance Improvements

## Changes
- Reworked AIMS/TRA ingestion to use sequential `iter_rows(values_only=True)` iteration in OpenPyXL read-only mode; removed per-row worksheet indexing and `max_row` iteration.
- Header detection is bounded to the first 30 rows and uses normalized header names. TRA verification matching is keyed specifically to `RCTVNUM` (not `Z#`).
- Skips empty rows, retains populated exception rows even when their verification code is blank, limits retained raw data to reconciliation-relevant columns, closes workbooks, and returns actionable errors for invalid files.
- Reads uploads with a 25 MB bounded stream and bulk-inserts parsed rows in one transaction. Existing digest duplicate checks and current/superseded batch history remain.
- Adds matched-code amount comparisons when both source amounts are available, plus reporting-period date checks where dates can be interpreted.
- Allows Tax Compliance and Admin to permanently delete processed EFD requests; deletion removes the request's original/processed binary attachments, digital invoice record, EFD request audit rows, and associated portal email logs in one database transaction. Initiators remain blocked server-side.
- Adds additive PostgreSQL indexes for monthly batch/source lookups and batch/code reconciliation.

## Deployment
1. Back up the PostgreSQL database before deployment.
2. Deploy the complete release package using the existing Render service and existing environment variables.
3. Run `migrations/V3_8_2_efd_compliance_indexes.sql` against the existing PostgreSQL database. The statements are idempotent and do not drop or truncate data.
4. Confirm the existing Render start command and environment variables remain unchanged.

## Validation
- Syntax compilation and automated regression tests are recorded in `TEST_RESULTS_V3_8_2.md`.
- Real production AIMS/TRA sample files and a Render production-sized upload were not included with the supplied baseline; therefore end-to-end runtime against those exact files and Render timeout behaviour must be verified after deployment.
