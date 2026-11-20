# V3.5.3 – Optional EFD Return Fields and VAT Import Batch Delete

## EFD Invoice Request
- EFD Verification Code and Receipt Time are no longer required when Tax Compliance returns a processed invoice to the initiator.
- Processed Word invoice remains mandatory.
- Optional verification code/time are stored if supplied and included in the completion email only when present.

## VAT Control Account
- Added a Tax Compliance-only POST action to delete a selected ERP VAT import batch.
- The selected upload, its imported ledger transaction rows, and monthly period balances are deleted.
- Manual VAT movements and saved TRA return records are preserved.
- The action writes an audit record and includes a confirmation prompt in the UI.

## Validation
- Python syntax compilation checked for app.py, efd_portal.py, and calendar_reminders.py.
- ZIP integrity and Jinja template parsing are checked during packaging.
- Live PostgreSQL/Render deployment and production data behavior are not tested here.
