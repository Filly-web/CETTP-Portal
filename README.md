# V2.5 – Compliance Calendar workspace integration and deadline scheduling

## Changes
- Removed the standalone Tax Compliance Calendar service card from the public portal landing page.
- Removed the calendar from the global sidebar. Tax Compliance officers now open it from the **Tax Compliance Tools** card on the Tax Compliance Workspace dashboard.
- Added automatic, duplicate-safe generation of recurring deadlines for the current and following calendar year:
  - WHT, PAYE and SDL returns: 7th of each month.
  - VAT return: 20th of each month.
  - Corporate income tax annual return: 30 June each year.
  - Corporate income tax provisional return: 31 March each year.
  - Corporate income tax instalment payments: 31 March, 30 June, 30 September and 31 December each year.
- Recurring dates are schedule-controlled. Officers can update assignment, status, filing/completion date, payment amount, control number, notes and evidence, but cannot change the scheduled due date.
- Added one-time manual deadline categories for Tax Audit, Tax Objection, Tax Appeal, Demand Notice, TRA Verification and other matters.
- Added milestone/activity choices including notification received, information request, response to information request, response to audit findings, exit meeting, objection filing, appeal filing, demand notice response, hearing and follow-up.
- Existing deadline, audit and attachment tables are reused; no database schema migration is introduced.

## Important
- The schedule follows the dates supplied by the user. Tax Compliance should validate statutory applicability and dates against current TRA requirements before relying on them.
- Recurring records are generated when the calendar is first opened after deployment. The generator is idempotent and will not create duplicate recurring records for the same obligation, activity, period and due date.
- Existing database URL and Render service configuration should remain unchanged. Back up the production database before deployment.
