# CETTP V2.3 — EFD Template Namespace Fix

## Issue
The EFD history route rendered `history.html`, which could resolve to CETTP's case-history template. That template expects a `case` variable and caused `jinja2.exceptions.UndefinedError: 'case' is undefined`.

## Fix
- EFD history explicitly renders `efd_portal/history.html`.
- EFD dashboard explicitly renders `efd_portal/index.html`.
- The EFD processing history query and its records are unchanged.
- CSRF protection and the Back to CETTP Portal navigation remain in place.

## Deployment
Update the existing repository/service with the ZIP contents. Keep the existing Render service, database URL, and environment variables unchanged. Back up existing data first. Verify the EFD dashboard, history, invoice generation, Initiator login, and Tax Compliance login after deployment.
