# CETTP v2.1 — EFD-to-Invoice Portal Integration

- Added EFD-to-Invoice as a third option on the pre-login service selection page.
- Mounted the existing EFD invoice processing utility under `/efd-invoice/` using a Flask Blueprint to avoid route collisions with CETTP.
- Preserved Initiator and Tax Compliance workflows and case-edit/resubmission features.
- Added `python-docx` and `qrcode[pil]` dependencies.
- EFD processing history remains in its own SQLite database, configurable through `EFD_PORTAL_DATA_DIR`; configure persistent storage for durable history on Render.
- EFD utility currently has no role login; access should be restricted to approved internal users.
