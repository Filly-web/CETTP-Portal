# V2.6 – Month-specific compliance calendar and separate TRA/ZRA VAT

- Compliance Calendar now defaults to the current month and displays only deadlines due within that month.
- Added previous/next month navigation. Month and year selections are retained when filtering by tax type or status.
- Dashboard counters (due in 7 days, due today, overdue, payment pending and completed) are calculated only from obligations in the selected month.
- Monthly VAT obligations are generated separately as TRA VAT Return and ZRA VAT Return, both due on the 20th.
- Existing system-generated generic VAT Return records are upgraded in place to TRA VAT Return to avoid duplicate TRA VAT rows; ZRA VAT is added as a separate obligation.
- Manual deadlines remain visible in the month in which their due date falls.
- No new database tables or migrations are introduced.
