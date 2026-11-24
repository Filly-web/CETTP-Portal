# CETTP V3.7.2 – One-Page Digital Invoice and In-System EFD Processing

## Digital invoice layout
- Reduced the vertical gap between the insured address and Customer ID.
- Removed unused blank paragraphs and the empty trailing template table while preserving the logo/image anchor.
- Normalized the TAX INVOICE heading and compacted paragraph/table spacing.
- Applied compact A4 page margins and non-splitting table rows.
- Limited the invoice description to 300 characters to support the one-page layout.
- Kept the unused VAT calculation section removed according to the selected 0% or 18% VAT rate.

## Digital invoice processing
- Tax Compliance can complete a digital invoice directly from its CETTP request detail page.
- Verification code and receipt time are mandatory for completion and the receipt time is normalized to HH:MM:SS.
- CETTP generates the final Word document from the stored digital invoice and embeds EFD verification details and a QR code; no processed Word upload is required for digital invoices.
- The generated final Word document is stored in the existing processed-file fields and remains downloadable by the Initiator.
- Completion email notification and EFD request audit entry are retained.

## Manual invoice processing
- Manual invoice requests retain the existing workflow: Tax Compliance enters verification code/time and uploads the processed Word invoice containing its QR code.
- The existing manual upload, amendment, rejection and download workflow is preserved.

## QR-code note
The QR code is generated using the existing CETTP EFD Portal verification URL convention (`https://verify.tra.go.tz/{verification_code}_{HHMMSS}`). CETTP does not issue a TRA verification code or independently verify the receipt with TRA; Tax Compliance must enter the actual details from the TRA receipt and confirm them before completion.

## Database and deployment
- No new database columns or tables are introduced.
- No production records are deleted or reset.
- Existing PostgreSQL configuration and Render environment variables are retained.
- Deploy over the existing V3.7.1 source and retain the current production database.
