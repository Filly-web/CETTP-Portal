# Initiator email-only access (pilot)

- Initiators enter an email address without a password.
- The email is stored in the session and recorded as the initiator identity on new cases.
- Initiator name is read-only in the case form to keep attribution consistent.
- Basic email format validation is applied.
- Tax Compliance access behavior is unchanged.

## Security limitation
Email-only access does not authenticate or verify the person. Anyone can enter another person's email address. This should be limited to a controlled pilot and should not be treated as secure production access. Add verified email/SSO or password authentication before handling sensitive production records.
