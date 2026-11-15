# CETTP V2.0 – Case Editing and Returned Request Resubmission

- Tax Compliance can edit submitted case details, including policy number, customer/insured name and TIN, request type, effective date, reason, product, branch, underwriter, invoice number and financial amounts.
- Initiators can edit only cases in `Returned for Clarification` and resubmit them to `Under Tax Review`.
- Initiator ownership checks remain enforced; an initiator cannot edit another initiator's case.
- Case changes are recorded in the existing audit history.
- Resubmission creates an in-app notification for Tax Compliance. Tax Compliance edits trigger an initiator notification.
- Existing attachments remain attached. Editing does not require uploading the cancelled invoice/EFD again, but additional supporting documents can be added.
- No database schema change is required; the existing case fields and notification tables are reused.
