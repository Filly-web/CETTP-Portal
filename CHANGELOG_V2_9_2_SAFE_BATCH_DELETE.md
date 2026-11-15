# V2.4 – Tax Compliance Calendar & Monitoring

- Added a Tax Compliance Calendar service option and Tax Compliance sidebar navigation.
- Added manual creation and editing of separate filing/payment obligations, due dates, periods, assigned officers, status, completion dates, payment amounts and control numbers.
- Added dashboard counts for due in seven days, due today, overdue, payment pending and completed.
- Added document evidence uploads stored in the application database, CSV export, and per-obligation audit history.
- Added overdue status calculation without overwriting the saved workflow status.

## Deployment and database
The app's existing startup `db.create_all()` will create the three new calendar tables on startup without dropping or replacing existing tables. Existing `DATABASE_URL`, Render service, and EFD portal configuration are unchanged. Back up the production database before deployment.

## Important
This release does not hard-code statutory due dates or automatically create future periods. Tax Compliance must enter and validate each deadline against current TRA/statutory requirements. Filing and payment dates should be separate obligations where they differ. Reminders are currently visible through the dashboard counters and overdue labels; background email/push reminders are not included in this first release.
