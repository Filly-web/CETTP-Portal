# CETTP V3.0.1 – VAT Control Account

## Location
The VAT Control Account is a Tax Compliance Workspace tool. It is available from the Tax Compliance sidebar and the Tax Compliance dashboard. It is not a separate portal and is not integrated with the Fixed Asset Governance (FAR) application.

## ERP ledger import
- Accepts an `.xlsx` ERP Detailed Account Analysis workbook containing both worksheets named `330101` and `330107`.
- Reads the monthly `Period`, opening balance, closing balance (where the ERP report provides a numeric value), and transaction rows.
- Imports GL date, transaction number, transaction date, creation date, posting date, document number, batch, supplier/customer, source, transaction type, transaction description, entered amount/currency, accounted amount/currency and initiator.
- Uses the report's monthly Period section for tax-period allocation. This is deliberate because some GL dates in the sample are in a prior calendar month while appearing in a later monthly ERP reporting section.
- Retains the original uploaded workbook in the application database and stores a SHA-256 fingerprint to block an exact duplicate upload. New versions are retained as separate batches; earlier batches are not overwritten.

## VAT account and classification
- Calculates the VAT liability effect as the negative of the signed TZS accounted amount from the ERP ledger. This matches the sample's sign convention: 330101 output VAT credit balances are negative and 330107 recoverable VAT debit balances are positive.
- Automatically suggests classifications for output VAT, input VAT, VAT payments, increasing/decreasing adjustments, imported-services VAT and import VAT credits.
- Restricts automatic payment classification to 330101 so ordinary supplier payment descriptions in 330107 are not misidentified as payments to TRA.
- Leaves ambiguous manual VAT journals as `Unclassified – review required`. Unclassified movements remain separately visible in the account until Tax Compliance reviews them.
- Allows Tax Compliance to reclassify each ledger row and record a review note. The reviewer and review timestamp are retained.
- Allows manual movements for increasing/decreasing adjustments, imported-service output/input VAT, import VAT credit, VAT payments, refunds and other increases/decreases. Supporting documents can be attached.
- Provides a TRA VAT return register for output tax, input tax, adjustments, declared net payable/(credit), submission date, return reference and supporting evidence.
- Generates a monthly VAT control account, a monthly movement summary and an Excel export with VAT Control Account, ERP Transactions, Manual Movements, TRA VAT Returns and VAT Audit Trail worksheets.

## Important controls
- A payment already captured in 330101 should not be entered again as a manual payment. Manual payments are for amounts not represented in the imported ledger.
- Excluded non-VAT postings are shown separately and create a visible reconciliation difference against the combined ERP closing balances; they are not silently removed from the source history.
- The application does not automatically decide whether input VAT is legally allowable. Tax Compliance must review invoice validity, restrictions, tax period, imported-service treatment, adjustments and supporting evidence before using the output for a return or TRA audit.
- The system compares calculated closing balances with combined ERP closing balances where both ledger closing figures are numeric. The ERP sample masks some 330101 monthly closing balances with `*****`; those months are marked as unavailable rather than guessed.
- The application creates new VAT tables through the existing `db.create_all()` startup process. It does not alter existing CETTP tables, change the database URL, require a database migration, or change Render service configuration.

## Database tables added
- `vat_ledger_upload`
- `vat_ledger_entry`
- `vat_ledger_period_balance`
- `vat_manual_movement`
- `vat_return_record`
- `vat_audit_log`

## Version
`3.0.1-vat-control`
