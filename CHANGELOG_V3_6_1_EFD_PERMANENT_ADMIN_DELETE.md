# CETTP V3.6.1 — EFD Permanent Admin Deletion

- Changes Tax Compliance/admin EFD request deletion from soft-delete to permanent database deletion.
- Permanently removes the EFD request row, including embedded original and processed Word invoice file data.
- Deletes request-specific `EFDRequestAudit` entries.
- Deletes request-specific central `PortalEmailLog` rows for module `efd_invoice_requests`.
- Removes the deletion comment field and replaces it with explicit irreversible-action warning and confirmation.
- Return, Reject, and Amendment workflows remain unchanged.
- Permission remains restricted to the Tax Compliance role (`role == tax`).
- Uses a transaction; rolls back if any deletion fails.

## Validation
- Python compilation passed for `app.py`, `efd_portal.py`, and `calendar_reminders.py`.
- Jinja parse passed for 30 templates.
- ZIP integrity checked after packaging.
- No live PostgreSQL, Render, browser, or production test performed.

## Scope note
The deletion is permanent from the application database perspective. External backups, infrastructure logs, or database snapshots managed outside CETTP are not controlled by this application and may retain historical copies according to their own retention policies.
