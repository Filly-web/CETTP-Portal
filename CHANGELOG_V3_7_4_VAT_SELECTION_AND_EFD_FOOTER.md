# CETTP V3.7.4 – VAT Selection Consistency and EFD Footer Position

## Changes
- Both repeated premium calculation sections now use the VAT rate selected by the Initiator.
- Both rows display the same VAT label and matching net amount, VAT amount, and gross premium.
- The Total Premium continues to reflect the selected VAT treatment.
- The generated EFD verification block (verification code, receipt time and QR code) is placed below the invoice at the designated bottom position after the Exchange Rate line.
- The EFD block is removed from the bank-details table cell to avoid the previous incorrect placement.
- The manual invoice processing workflow is unchanged.

## Verification
- Python syntax compilation passed.
- Generated sample invoices tested at 0% and 18% VAT; both repeated rows matched the selected rate.
- Processed Word output includes the EFD details and QR below the Exchange Rate line.
- Both generated sample outputs converted to one-page PDFs using LibreOffice.
- ZIP integrity check passed.

Live Render, PostgreSQL, email delivery and TRA verification were not tested.
