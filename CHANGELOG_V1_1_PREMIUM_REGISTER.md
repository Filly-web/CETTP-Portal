# CETTP V3.0.0 – Build verification

## Checks completed
- `app.py` and `efd_portal.py` passed Python syntax compilation.
- The `base.html`, `dashboard.html` and `tax_vat_control.html` Jinja templates compiled successfully.
- New VAT Control Account template links were checked against the route function names in `app.py`.
- The VAT ledger parser was executed against the supplied `330101.xlsx` sample workbook without changing or including the workbook in this deployment package.
- The parser detected 215 transaction rows in sheet 330101 and 823 transaction rows in sheet 330107, across 12 monthly reporting periods and 24 account-period opening balance records.
- For months where the ERP supplied numeric closing balances, opening balance plus monthly movement rolled forward to the reported closing balance within TZS 1.00 rounding tolerance.
- Supplier payment descriptions in 330107 were not automatically classified as VAT payments; the 330107 entries were treated as input VAT unless their description identified another VAT category.

## Not completed
- A live Flask application/database integration test was not run in this build environment because Flask and Flask-SQLAlchemy were not installed and package installation was unavailable.
- No connection was made to the production Render service or production database.
- No production data or environment settings were changed.

## Deployment verification required
After deployment to the existing Render service, confirm `/health` returns `3.0.0-vat-control`, then upload a test copy of the ERP workbook and check the monthly control account before importing a production ledger batch.
