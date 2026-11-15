# Central CETTP notification recipients (comma or semicolon separated)
CETTP_TAX_COMPLIANCE_EMAIL=
CETTP_INVESTMENT_WHT_EMAIL=

# Central Yahoo SMTP sender. Set MAIL_PASSWORD only in Render environment variables.
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=temporarytin2026@yahoo.com
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=temporarytin2026@yahoo.com

# Daily scheduled reminder endpoint protection
INVESTMENT_WHT_CRON_TOKEN=replace-with-a-long-random-token

# Public CETTP URL, without a trailing slash
CETTP_BASE_URL=https://your-approved-cettp-host

# Existing application secrets (set strong production values)
SECRET_KEY=replace-with-a-long-random-secret
TAX_ACCESS_CODE=replace-with-approved-strong-access-code

# Existing PostgreSQL connection (Render normally injects DATABASE_URL)
# DATABASE_URL=postgresql://user:password@host:5432/database
