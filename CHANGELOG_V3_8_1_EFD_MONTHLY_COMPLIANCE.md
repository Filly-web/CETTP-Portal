# CETTP V3.8.1 – Monthly EFD Compliance Reconciliation and Admin EFD Deletion

## New EFD Compliance Check
- Added a dedicated EFD Compliance Check workspace for Tax Compliance and CETTP Admin.
- Users select a reporting month (YYYY-MM) and upload the AIMS report and TRA receipt report as separate monthly batches.
- AIMS verification codes are detected by the `TaxEfdCode` header. TRA verification codes are detected by the `RCTVNUM` header (the uploaded TRA sample places this field in column G; column F is `Z#`).
- Reconciles verification codes in both directions: AIMS codes not found in TRA and TRA codes not found in AIMS.
- Flags duplicate verification codes in either source, AIMS transactions without a verification code, and cancelled-policy / cancellation-transaction rows.
- Identifies cancelled AIMS rows whose verification code still appears in the TRA listing for manual confirmation of cancellation/adjustment evidence.
- Flags Bankassurance channel rows without an EFD code for manual confirmation against integrated bank EFD machines and TRA records. No direct bank-machine API connection is included.
- Provides a monthly status, prior-period selection and Excel exception export.
- Prevents duplicate source/month uploads. CETTP Admin can explicitly replace or delete a monthly batch; superseded upload versions remain in the month’s upload history.

## Admin-only permanent EFD request deletion
- Restricted permanent deletion of EFD requests to CETTP Admin only.
- Admin can permanently delete requests even after Tax Compliance has processed and returned the invoice.
- Purges the request, embedded original/processed invoice files, request-specific EFD audit rows and associated EFD request email-log rows.
- No application-level deletion audit record is created, in line with the requested permanent-deletion behaviour. Infrastructure backups may retain copies until their normal expiry.

## Data and deployment safeguards
- Added `efd_recon_batches` and `efd_recon_rows` tables through the existing `db.create_all()` startup mechanism. This is additive; no existing business tables are dropped or reset.
- Existing VAT reconciliation, WHT, cancellation tracking, users, permissions and other workflows are retained.
- Keep the existing PostgreSQL `DATABASE_URL`, `SECRET_KEY`, SMTP settings and Render service configuration.

## Known limitations / review points
- Matching is based on normalized EFD verification code. Policy number, amount, customer and date are retained as supporting context where the source supplies them; they are not used to force a match.
- The TRA report sample contains receipt verification codes and listing details, but does not provide a reliable policy-level cancellation status. Cancelled EFD cases therefore require human review against TRA cancellation/adjustment evidence.
- Bankassurance validation is an exception queue only; the module does not query bank EFD machines or TRA APIs.
- Runtime integration against the live Render/PostgreSQL service, email delivery, and bank/TRA systems must be tested in staging before production use.
