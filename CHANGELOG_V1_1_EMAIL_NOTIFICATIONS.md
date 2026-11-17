# Central Yahoo SMTP service (V3.3.0). Keep SMTP_PASSWORD secret; do not commit real credentials.
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=temporarytin2026@yahoo.com
SMTP_PASSWORD=replace-with-Yahoo-generated-App-Password
SMTP_FROM=temporarytin2026@yahoo.com
SMTP_TIMEOUT=15

# Approved notification recipient(s), comma or semicolon separated.
CETTP_TAX_COMPLIANCE_EMAIL=
# Optional separate recipient for Investment WHT reminders.
CETTP_INVESTMENT_WHT_EMAIL=
# Optional email test recipient.
CETTP_EMAIL_TEST_TO=

# Public CETTP URL, without a trailing slash
CETTP_BASE_URL=https://your-approved-cettp-host

# Existing application secrets (set strong production values)
SECRET_KEY=replace-with-a-long-random-secret
TAX_ACCESS_CODE=replace-with-approved-strong-access-code

# Existing PostgreSQL connection (Render normally injects DATABASE_URL)
# DATABASE_URL=postgresql://user:password@host:5432/database
