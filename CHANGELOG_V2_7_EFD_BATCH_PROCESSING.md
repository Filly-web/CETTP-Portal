# V2.7 – EFD Batch Invoice Processing

## Added
- Added a Batch Invoice Processing option to the existing EFD-to-Invoice dashboard.
- Kept the existing Single Invoice Processing form and `/process` route intact.
- Added multi-file `.docx` upload (up to 100 invoices per batch, subject to the existing 40 MB request limit).
- Added per-file TRA verification code and receipt-time entry, generated against the selected file order.
- Added pre-processing checks for missing details, duplicate sanitized filenames, duplicate verification codes, and invalid receipt times. These checks stop the batch before any invoice is processed.
- Reused the existing EFD section and QR generation logic for both single and batch workflows.
- Added ZIP download containing processed invoices, failed source documents (where applicable), and a CSV processing report.
- Successful batch items are recorded in the existing invoice processing history.

## Notes
- Batch processing does not alter the single-invoice workflow or its form fields.
- The current implementation accepts Word `.docx` files only.
- The report is CSV for compatibility with Excel; it includes filename, output filename, EFD code, receipt time, verification URL, result, and error.
- The ZIP is generated for immediate download. Persistent batch archive/history and Excel schedule import are not included in this version.
- Full Flask route/integration tests were not run in this environment because Flask and Flask-WTF are not installed. Python syntax compilation and ZIP integrity checks were run.
