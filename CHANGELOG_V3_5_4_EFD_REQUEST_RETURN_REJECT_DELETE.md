# CETTP V3.5.4 — EFD Request Return, Rejection and Deletion Controls

## Changes
- Tax Compliance can return a submitted EFD invoice request for amendment with a mandatory comment.
- Initiators can edit the customer name and optionally replace the Word invoice only when the request is in `Returned for Amendment`, then resubmit under the same reference.
- Tax Compliance can reject a request with a mandatory reason. Rejected requests cannot be resubmitted; initiators must raise a new request if needed.
- Tax Compliance can soft-delete a request with confirmation. Deleted requests are excluded from the active workplace queue but remain in the database for audit and can still appear in the initiator's own history.
- Added EFD request audit records for return, rejection, soft deletion and initiator resubmission.
- Return/rejection/resubmission notifications are attempted using the portal's existing central email service. Notification failures are shown to the user.
- Verification code and receipt time remain optional when returning the processed invoice; the processed Word invoice remains mandatory.

## Preservation
- No production records are deleted by these changes. Request deletion is a status change (`Deleted`) with an audit record.
- Changes are limited to the EFD request workflow.

## Validation
- Python syntax compilation passed for app.py, efd_portal.py and calendar_reminders.py.
- Jinja parsing passed for all 27 HTML templates.
- Live database, SMTP, Render deployment and end-to-end browser testing were not performed.

## Source baseline note
This package was built from the user-uploaded V3.5.2 Email Audit Resilience Fix archive. It does not contain other changes that may be present in the separately discussed V3.5.3 package, such as VAT imported Excel batch deletion. Please use the actual V3.5.3 source package as the baseline if those features must be carried forward into the combined release.
