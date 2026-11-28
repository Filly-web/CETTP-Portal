# CETTP V3.7.5 – Total Premium Alignment Fix

## Change
- Vertically align the Total Premium amount in the right-hand amount cell with the Total Premium label at the bottom of the left-hand cell.
- Retain right alignment within the amount column and preserve the existing table borders, row layout, VAT calculations, EFD footer placement, and one-page invoice layout.

## Validation
- Python syntax compilation passed.
- Digital invoice DOCX generation test passed.
- Verified the Total Premium amount cell uses bottom vertical alignment.
- Converted test invoice to PDF; output was one page.
- Full Flask application, live Render, PostgreSQL, email delivery, and TRA integration were not tested in this build environment.
