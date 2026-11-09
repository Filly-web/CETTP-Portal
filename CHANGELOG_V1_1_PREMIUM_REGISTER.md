# Notification recipient(s), comma or semicolon separated. Leave blank until approved recipients are configured.
CETTP_TAX_COMPLIANCE_EMAIL=

# Microsoft 365 SMTP submission — obtain approved values from Britam IT
M365_SMTP_HOST=smtp.office365.com
M365_SMTP_PORT=587
M365_SMTP_USERNAME=approved-sender@example.com
M365_SMTP_PASSWORD=replace-with-secret-from-secure-environment
M365_SMTP_FROM=approved-sender@example.com

# Public CETTP URL, without a trailing slash
CETTP_BASE_URL=https://your-approved-cettp-host

# Existing application secrets (set strong production values)
SECRET_KEY=replace-with-a-long-random-secret

# Existing CETTP Tax Compliance shared access gate (use a strong, unique value)
TAX_ACCESS_CODE=replace-with-approved-strong-access-code

# Existing PostgreSQL connection (Render normally injects DATABASE_URL)
# DATABASE_URL=postgresql://user:password@host:5432/database
