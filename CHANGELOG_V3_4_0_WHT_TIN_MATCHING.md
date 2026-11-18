# CETTP V3.4.0 – WHT TIN Matching

## Added
- Dedicated WHT TIN Matching workspace linked from the Tax Compliance navigation.
- Reusable Supplier TIN Master import (CSV/XLSX) with mandatory TIN and agency/business name, optional sole proprietor name, update-by-TIN behaviour and conflict protection.
- Single combined `.xlsx`/`.xlsm` ledger import. Each worksheet is one ledger, identified by GL code 330301–330318 or one of: Medical Reinsurance Premium, GI Reinsurance Premium, Prior Periods, Smart Brokers, Non-Smart Agencies.
- Ten-column ledger structure validation, source row preservation and separate matched-TIN output.
- Name matching against agency and proprietor names; unique scores >=80% auto-match, 60–79% second review, below 60% unmatched. Near-equal candidates with different TINs are held for review.
- Manual review/approval against the Supplier TIN Master.
- Consolidated Excel report with summary, a sheet per imported ledger, Second Review, Unmatched and Supplier TIN Master sheets.
- Additive SQLAlchemy models; existing tables and records are not dropped or reset.

## Operational notes
- New tables are created by the application's existing `db.create_all()` startup call. This is additive and does not alter existing tables.
- Existing deployment, production database migration, Render deployment and live browser testing have not been performed by this package build.
- Use a workbook with each ledger on its own worksheet. Worksheet titles must be a GL code from 330301–330318 or one of the five agreed names. Every ledger sheet must have the agreed ten columns.
- Matching is a suggestion engine, not proof of taxpayer identity. Review ambiguous and second-review cases before using the populated TINs in a WHT return.
