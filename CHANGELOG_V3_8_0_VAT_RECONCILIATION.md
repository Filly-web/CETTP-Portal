# CETTP V3.8.0 – VAT Reconciliation

## Overview
Replaces the Tax & Reconciliation sidebar's generic **VAT & WHT** entry with a dedicated **VAT Reconciliation** workspace. The prior generic VAT/WHT reconciliation route and data remain available for legacy records; a link to legacy WHT reconciliation is provided from the new VAT page.

## Included
- New PostgreSQL tables `vat_recon_batches` and `vat_recon_transactions`, created through the application's existing `db.create_all()` startup mechanism. No existing table is dropped or altered.
- Separate period-based imports for AIMS premium, AIMS commission, EFDMS fiscal transactions, GL output VAT/sales, GL input VAT and TRA VAT return summary.
- CSV/XLSX import using a standard template with transaction reference, transaction date, counterparty, TIN, category, VAT rate, taxable value, VAT amount and gross amount.
- SHA-256 duplicate-file prevention, batch history and controlled batch deletion.
- Source totals for transaction count, taxable value, VAT and gross value.
- AIMS premium/commission to EFDMS reference matching, with missing-record and amount/VAT variance identification.
- VAT arithmetic checks where the imported row explicitly contains a VAT rate.
- CSV export of the period's exception register.
- Existing VAT Control Account, WHT TIN matching, Investment WHT and legacy WHT reconciliation retained.

## Matching and control limitations
- AIMS/EFDMS matching uses normalized transaction references; it does not force matches based on amount or customer name alone.
- GL and VAT-return imports are currently summarized by source and are not automatically reconciled to individual AIMS/EFDMS transactions.
- VAT arithmetic checks only test the supplied rate and values. The application does not independently determine legal VAT classification, input-tax deductibility or exemption/zero-rating eligibility.
- No TRA filing, accounting journal posting or external TRA verification is performed.
- Tax Compliance must review exceptions and source mappings before relying on the results.

## Data and deployment
- Existing PostgreSQL records and tables are preserved.
- New tables are additive; no destructive migration or database reset is required.
- Keep existing Render environment variables and database configuration unchanged.
