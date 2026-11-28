# V3.8.3 – EFD report deletion and large-upload reliability

## EFD monthly reports
- Extended report-batch deletion to both `admin` and `tax` roles at the server route.
- Added explicit delete confirmation in the upload-history table.
- Delete removes the selected batch rows and parent batch in one transaction. If the removed batch was current, the most recent remaining batch for the same period/source is restored as current.
- Kept replacement restricted to CETTP Admin (`admin`) and retained the explicit replacement checkbox requirement.

## Large TRA/AIMS uploads
- Increased the EFD endpoint file limit to 35 MiB, below the application's 40 MiB request limit.
- Changed bulk row insertion to chunks of 250 while retaining a single transaction across all chunks. Any failure rolls back the complete upload.
- Added row-count consistency check and structured server-side diagnostics. User-facing messages no longer expose raw database/driver exception details.

## Online-uploaded EFD invoices
- Exposed permanent deletion to both Administrator and Tax Compliance on the EFD request detail page and workplace list.
- The existing server-side deletion removes original and processed binary attachments with the request, plus digital invoice data, EFD request audit rows and related request email-log rows.
- Added deletion of standalone EFD Portal processing-history entries for Administrator and Tax Compliance. This is history-only: the standalone portal streams processed DOCX files to download and does not persist those output files.

## Data/deployment safety
- No schema migration is required.
- No production database reset, drop, truncate, or URL change.
- No notification-related files or behavior intentionally changed.
- CETTP Admin remains the only role allowed to replace an existing monthly TRA/AIMS batch.
