# Britam CETTP V3.0.1 – VAT Control Account

This release extends the existing Britam CETTP Tax Compliance Workspace with a VAT Control Account. It preserves the existing cancellation/endorsement case workflow, Premium Register tracking, EFD-to-Invoice utility, TRA tracking and Compliance Calendar.

## VAT Control Account access
1. Sign in through the existing **Tax Compliance Workspace**.
2. Open **VAT Control Account** from the sidebar or Tax Compliance dashboard.
3. Upload the ERP `.xlsx` workbook containing both sheets `330101` (Output VAT) and `330107` (VAT Recoverable).
4. Select an upload batch and reporting month to view the monthly VAT account.
5. Review each transaction's suggested classification. Correct any incorrect category and add a review note.
6. Record any adjustments, imported-service VAT, import VAT or VAT payments not already included in the two ledgers. Attach supporting evidence where available.
7. Record submitted TRA VAT return figures and upload the return evidence to compare the declared net VAT with the ledger-derived movement.
8. Use **Download final VAT account (Excel)** to export the monthly control account and supporting transaction schedules.

## Supported ERP workbook layout
The importer is designed against the supplied ERP Detailed Account Analysis workbook. It requires two worksheets named exactly `330101` and `330107`. It reads the report's monthly sections and the `Accounted Amount` in TZS. It uses the monthly `Period` label for the VAT period, not just the GL date.

## VAT movement sign convention
The sample ERP export records output VAT credit balances in 330101 as negative amounts and recoverable VAT debit balances in 330107 as positive amounts. The control account therefore converts each signed accounted movement into its VAT liability effect by reversing the sign:
- A credit posting to output VAT increases the VAT payable position.
- A debit posting to recoverable VAT reduces the VAT payable position.
- VAT payments posted as debits to 330101 reduce the VAT payable position.

The account starts with the combined opening balance of both ledgers, then adds the classified ERP movements and manual movements. It shows the combined ERP closing balance and reconciliation variance when both ledger closing figures are available.

## Review and statutory control
Automatic classifications are suggestions only. The supplied sample contains manual journals whose descriptions do not clearly identify the VAT nature; those are marked for review. Input tax should only be treated as claimable after review of the relevant tax invoice, business purpose, applicable restrictions and tax period. The module provides registers for increasing/decreasing adjustments, imported services, import VAT and payments, but does not replace professional tax review or the VAT return filing process.

Avoid double counting: if a VAT payment or adjustment is already posted in the imported ERP ledgers, do not enter the same item again as a manual movement.

## Deployment to the existing Render service
- Deploy this package to the existing CETTP repository/service.
- Keep the existing Render service and database attachment.
- Keep the existing `DATABASE_URL`, `SECRET_KEY`, `TAX_ACCESS_CODE` and other environment settings unchanged.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- The existing `db.create_all()` startup call creates the new VAT tables without modifying existing CETTP tables. Back up the production database before deployment as standard operational practice.
- After deployment, check `/health`; the version should report `3.0.1-vat-control`.

The VAT module is part of CETTP and does not include or connect to the separate Fixed Asset Governance / FAR application.
