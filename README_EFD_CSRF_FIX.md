# EFD invoice generation – CSRF fix and CETTP return link

This package fixes the `Bad Request: The CSRF token is missing` error when processing an invoice in the EFD-to-Invoice Portal.

## What changed
1. The EFD invoice form now submits the CSRF token required by the application's global Flask-WTF CSRF protection.
2. The EFD dashboard and processing history page now have a **Back to CETTP Portal** link.
3. The EFD processing route remains CSRF-protected; security has not been disabled.

## Deploy to the existing Render service
1. Back up your current database and source repository.
2. Extract this ZIP and copy its contents to the root of the existing `Filly-web/SmartCETTP` repository, preserving the `templates/` and `static/` folders.
3. Commit and push the changes to the existing branch.
4. Keep the existing Render service and environment variables, especially `DATABASE_URL`, `SECRET_KEY`, and `EFD_PORTAL_DATA_DIR`, unchanged.
5. Redeploy the existing service. The build command should remain `pip install -r requirements.txt`; the start command should remain `gunicorn app:app` if `app.py` exposes `app`.
6. After deployment, open `/efd-invoice/` afresh, upload a `.docx`, enter the TRA verification code and receipt time, then process the invoice. The form will include a fresh CSRF token from that page load.

Do not add `@csrf.exempt` to the EFD processing route and do not disable global CSRF protection.
