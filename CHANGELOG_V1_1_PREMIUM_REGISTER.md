# CETTP V3.2.0 Build Verification

## Static checks completed
- Python source files parsed successfully with `ast`.
- Python source files compiled successfully with `py_compile`.
- All Jinja HTML templates parsed successfully.
- Added route definitions found for VAT import-batch deletion, investment edit/delete and investment imported-batch deletion.
- EFD history model and shared SQLAlchemy persistence routes are present.
- ZIP contents are derived from the uploaded V3.1.0 source project.

## Not verified in this environment
- Full Flask application import and runtime tests could not be run because Flask / Flask-SQLAlchemy dependencies are not installed in the build environment.
- Existing production PostgreSQL schema and records were not accessed.
- Render deployment and Yahoo SMTP delivery were not tested.
- Yahoo App Password must be configured as `MAIL_PASSWORD` in the existing Render service before email delivery can work.

## Deployment safeguards
- No database reset, drop, truncate, or change to `DATABASE_URL` / `SECRET_KEY` is included.
- New EFD records use a new `efd_invoice_records` table created by the existing `db.create_all()` startup.
- VAT batch deletion is scoped to one upload ID and its ledger entries / period balances.
- Investment batch deletion is scoped to the selected batch and its investment reminder logs.
- Existing manually registered investments, other import batches, VAT manual movements, VAT return records, cases, and case attachments are not deleted by these new batch-delete routes.

## Important EFD storage note
Newly processed EFD invoices and their processed DOCX bytes are stored in the shared CETTP SQLAlchemy database.
The pre-existing local SQLite EFD history is not automatically migrated as it contains metadata only and
does not retain the processed DOCX binary. Draft EFD batch staging remains local until successful processing;
successfully processed items are then stored in PostgreSQL.
