# V1.7 – Initiator email username login

- Initiators enter their work email as the username only; no password, OTP, or verification code is requested.
- CSRF protection is exempted only on the Initiator email-entry endpoint to avoid the reported missing-token error.
- Tax Compliance login remains protected by CSRF.
- This pilot mode does not verify ownership of the email address; anyone who knows an email can enter it.
- No database configuration or existing case data changes are included.
