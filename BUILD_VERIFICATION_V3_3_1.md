# V3.3.2 build verification

## Passed
- Python source compilation (`compileall`).
- Jinja2 parsing for all 22 HTML templates.
- `cancellation_tracker.html` contains exactly one `scripts` block.
- ZIP integrity check (`testzip`) passed; 78 files included.
- The PostgreSQL migration and deployment instructions are included.

## Not run / blocked
- Existing pytest suite could not be collected because Flask is not installed
  in the packaging runtime (`ModuleNotFoundError: No module named 'flask'`).
- No live PostgreSQL migration, Render deployment, full Flask integration
  test, or Yahoo SMTP connectivity test was performed.

## V3.3.2 migration behavior
- Application startup now runs a safe, idempotent migration after `db.create_all()`.
- The database user needs ALTER TABLE and CREATE INDEX permissions for the one table/index repair.
- A manual SQL fallback remains in `migrations/V3_3_1_add_portal_email_logs_module.sql`.
- No production database changes are made by generating this ZIP; the migration runs only when the deployed application starts.
