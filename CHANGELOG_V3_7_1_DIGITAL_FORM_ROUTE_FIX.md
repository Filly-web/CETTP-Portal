# CETTP V3.7.1 – Digital Invoice Form Route Fix

- Added the missing authenticated GET endpoint `efd_request_digital_form` at `/efd-requests/digital/new`.
- Replaced the accidentally duplicated choice-screen markup in `efd_request_digital_form.html` with the actual digital invoice entry form.
- The form posts to the existing digital preview endpoint and includes the required invoice fields, VAT rate selection (0%/18%), net premium, manager name and CSRF token.
- Preserved the manual invoice upload route and existing processing workflow.

The reported 500 was caused by the missing Flask endpoint. The template linked to `efd_request_digital_form`, but the application had only the preview, preview-download, submit and confirm endpoints.
