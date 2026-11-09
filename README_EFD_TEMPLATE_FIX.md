# V2.8 – Email notification recipient configuration

- Configured `fillyrichard98@gmail.com` as the default Tax Compliance notification recipient.
- Kept Gmail as a recipient only; the existing Microsoft 365 SMTP account remains the sender.
- Retained comma/semicolon-separated multiple recipient support through `CETTP_TAX_COMPLIANCE_EMAIL`.
- No Gmail password, SMTP secret, database migration, or database URL change is introduced.
- Existing notification behavior remains: an email is attempted after a new Initiator cancellation/endorsement request is successfully saved.
- Microsoft 365 sender credentials must be supplied securely in the existing Render environment by an authorized administrator.
