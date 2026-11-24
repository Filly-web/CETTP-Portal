# CETTP V3.6.8 – Digital Tax Invoice Generator

This release adds the Digital Tax Invoice Generator to the existing Initiator EFD Request workflow.

## User workflow
1. Initiator opens **New Request** and completes the Digital Tax Invoice form.
2. Selects VAT 0% or 18%; CETTP calculates VAT and gross premium from the net amount.
3. Initiator reviews the invoice and downloads the Word preview.
4. Initiator confirms submission. Until confirmation, the request remains a draft and is not visible in the Tax Compliance workplace.
5. Tax Compliance continues using the existing processing workflow and uploads the final processed Word invoice containing the EFD barcode.
6. Initiator downloads the processed Word invoice from the existing request screen.

## Deployment safeguards
- Keep the existing `DATABASE_URL`, `SECRET_KEY`, SMTP settings and other Render environment variables unchanged.
- Do not reset or replace the production PostgreSQL database.
- The additional `digital_tax_invoices` table is created by the existing SQLAlchemy `db.create_all()` startup operation.
- Validate the digital invoice in staging before using it for live requests.

## Important
The existing Tax Compliance processing step still requires the final processed Word document containing the barcode to be uploaded. This release does not claim to automate TRA/EFD barcode issuance or connect to a live TRA service.
