# CETTP V3.6.7 — Automated User Access Email

## Added
- User account creation sends a credential email to the registered work email.
- Email contains the portal link, email address, role-specific PIN/password, and requested signature.
- Credential reset also sends the newly assigned credential to the user.
- SMTP failure does not undo account creation or credential reset; status is shown to the operator.

## Render configuration
Retain existing SMTP variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` (and optional SMTP TLS settings).
Optional: `CETTP_PORTAL_URL=https://cettp-portal.onrender.com/`.

No database reset is required. Email delivery requires SMTP credentials to be configured and is not live-tested in this build environment.
