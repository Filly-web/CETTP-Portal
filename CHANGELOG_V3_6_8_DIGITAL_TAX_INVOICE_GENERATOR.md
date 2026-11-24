# CETTP V3.6.8 – Digital Tax Invoice Generator

## Added
- Initiators can create a Digital Tax Invoice in CETTP without uploading a manually completed Word invoice.
- Captures insured/customer details, invoice reference, agent, cover type, debit note number, invoice description, preparer and manager details.
- Requires selection of VAT rate: 0% or 18%.
- Calculates VAT and gross premium from the entered net amount.
- Generates a Word invoice from the supplied Britam sample template, removes demonstration highlights, and displays only the selected VAT calculation section.
- Provides an HTML review screen and downloadable Word preview before request creation.
- Saves the invoice as a draft until the initiator confirms submission to Tax Compliance.
- Stores digital invoice data in a new `digital_tax_invoices` table linked to the existing EFD invoice request. Existing request records and production data are not reset.
- Existing Tax Compliance processing and processed-Word upload workflow remains in place for the final invoice containing the EFD barcode.

## Deployment
- Deploy the complete ZIP using the existing Render service and PostgreSQL database.
- `db.create_all()` creates the additional digital invoice table on startup; no existing table is dropped or reset.
- No new environment variables are required.

## Validation
- Python syntax compilation passed.
- Source ZIP and embedded Word template archive integrity checked.
- Full Flask runtime, database migration, browser workflow and live EFD/barcode integration were not executable in the build environment because Flask is not installed there. Perform staging validation before production deployment.
