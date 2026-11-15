# CETTP V3.2.0 – Complete Enhancement

## Included
- Investment WHT Credits: individual investment edit/delete, imported batch deletion, dependent reminder-log cleanup, duplicate checking and interest/WHT recalculation.
- VAT Control Account: selected import batch deletion with scoped removal of associated transaction rows and period balances; audit event retained.
- EFD-to-Invoice: processed invoice history and processed DOCX files stored in the shared CETTP SQLAlchemy database; optional invoice reference, policy and customer fields; invoice-reference linking to cancellation/endorsement cases; case detail and EFD history download links.
- Central Yahoo SMTP configuration used by existing case submission and investment reminder email paths.

## Deployment
Preserve the existing Render service, PostgreSQL database, `DATABASE_URL`, and `SECRET_KEY`. Set the Yahoo App Password only in Render as `MAIL_PASSWORD`. See `README_DEPLOY_EXISTING_RENDER.md`.

## Limitations / validation
Yahoo SMTP delivery requires live Render credentials and recipients and has not been tested from this build environment. EFD legacy SQLite history rows are not automatically imported as processed document binaries; newly processed EFD records are persisted centrally. Existing batch staging remains local draft staging until processing completes; successfully processed invoices are saved to PostgreSQL.
