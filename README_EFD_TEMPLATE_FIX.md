# V2.8 – EFD Batch Processing: Add One Invoice at a Time

## Changes
- Replaced multi-file selection with a one-invoice-per-upload workflow.
- Each upload captures its own TRA EFD verification code and receipt time immediately.
- Uploaded invoices are staged in the configured EFD portal data directory and associated with the browser session's batch.
- Added a review table showing each staged invoice and its EFD details.
- Added per-invoice removal and clear-batch actions.
- Added a final action to process all staged invoices and download one ZIP package with processed/failed folders and a CSV report.
- Single-invoice `/process` route and single-invoice dashboard workflow remain unchanged.
- Added a SQLite staging table to the existing EFD history database; no existing history rows are altered.

## Deployment notes
- Keep `EFD_PORTAL_DATA_DIR` / `PORTAL_DATA_DIR` on persistent storage in Render. Staged files are held under `batch_staging/` until the batch is downloaded or cleared.
- The existing `portal_history.db` will automatically create the new `batch_staging` table at startup.
- No change to the main CETTP database or its `DATABASE_URL` is required.
- Batch staging is session-associated. Use the same browser session while building a batch.
