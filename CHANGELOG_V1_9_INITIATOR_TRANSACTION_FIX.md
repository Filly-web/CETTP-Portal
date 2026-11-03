# V1.9 – Initiator submission transaction fix

- Corrected Initiator-side WTForms validation: the Initiator name is derived from the email-only session and is no longer incorrectly rejected when the hidden name field is absent from the submitted form.
- Kept the Initiator name requirement for Tax Compliance submissions.
- Made case creation, attachment persistence, audit logging and the Tax Compliance in-app notification part of one database transaction. If any part fails, the transaction rolls back and a server-side exception is logged.
- Kept the existing email-only Initiator entry, mandatory cancelled invoice/EFD attachment, existing workflow, database URL and environment-variable configuration.

