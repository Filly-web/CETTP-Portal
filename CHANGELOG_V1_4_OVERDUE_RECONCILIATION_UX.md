# V3.3.1 build verification

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

## Deployment requirement
Run `migrations/V3_3_1_add_portal_email_logs_module.sql` against the existing
production PostgreSQL database after taking a backup and before deploying.
No production database changes are made by generating this ZIP.
