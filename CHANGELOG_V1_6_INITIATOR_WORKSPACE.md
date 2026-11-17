# V1.6 — Initiator workspace and tracking

- Adds a dedicated Initiator dashboard with personal request counters and recent cases.
- Adds a private My Updates inbox with read/unread status and direct links to the related case.
- Creates Initiator notifications when Tax Compliance changes workflow status or adds review notes, including returned-for-clarification and final outcomes.
- Scopes Initiator case listing and exports to records whose Initiator identity matches the email used for the current session.
- Enforces case-level ownership checks for case detail, attachment upload and attachment download routes.
- Adds date-range and overdue filters to the case list; Initiators can filter returned and overdue cases using the existing status/filter controls.
- Tax Compliance retains the broader case register and approval/status controls.

## Notes

- Initiator access remains email-only for the pilot and does not verify email ownership. Do not treat the entered email as authenticated identity in production.
- The existing database initialization (`db.create_all()`) creates the new `initiator_notification` table for new deployments. For production databases, apply an approved migration/initialization process and back up first.
- Draft saving and editing are not yet implemented as a persisted workflow; the dashboard displays a Drafts metric for compatibility but this feature should be completed before presenting drafts as available to users.
- No WHT reconciliation module was added as part of this change.
