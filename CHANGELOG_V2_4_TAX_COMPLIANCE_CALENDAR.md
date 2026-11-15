# CETTP v1.8 – Initiator submission fix

- Fixed Initiator case submission validation. The Initiator name field is hidden for Initiators, but was still marked required by WTForms; this caused `validate_on_submit()` to reject the form before saving the case or creating a Tax Compliance notification.
- The application now populates the required Initiator name field from the email-only login session before validation.
- Tax Compliance submissions continue to use the name entered in the form.
- No database schema, database URL, hosting configuration, or WHT functionality was changed.
