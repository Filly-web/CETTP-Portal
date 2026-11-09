# CETTP v2.2 – EFD CSRF and Return Navigation Fix

## Fixes
- Added the Flask-WTF CSRF token as a hidden field in the EFD invoice processing form. This allows the globally enabled CSRF protection in `app.py` to validate the POST request to `/efd-invoice/process`.
- Added a prominent **Back to CETTP Portal** link on the EFD dashboard and processing-history page. Both links return to the CETTP home page (`/`).
- Kept the existing EFD invoice processing route protected by CSRF; no global CSRF exemption was introduced.
- Kept the existing CETTP and EFD routes, dependencies, and database configuration unchanged.

## Deployment
Replace the application files from this package in the existing repository and redeploy the existing Render service. Keep the current `DATABASE_URL`, `SECRET_KEY`, and EFD persistent-storage environment settings unchanged. The CSRF fix relies on the existing Flask session and secret key; users should load a fresh EFD dashboard page before submitting an invoice after deployment.

## Validation
Python syntax compilation and ZIP integrity were checked. A live Flask request test was not possible in the build environment because Flask dependencies are not installed there.
