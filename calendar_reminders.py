"""Daily Tax Compliance Calendar reminder runner. Configure as a Render Cron Job."""
from datetime import date
from app import app, db, TaxDeadline, TaxDeadlineAudit, _central_send_email

RECIPIENT = "faugusti@britam.co.tz"


def run():
    today = date.today()
    with app.app_context():
        due_items = TaxDeadline.query.filter(
            TaxDeadline.status.notin_(["Completed", "Not Applicable"])
        ).all()
        sent = 0
        for item in due_items:
            days_left = (item.due_date - today).days
            if not 0 <= days_left <= 5:
                continue
            # Dedupe one reminder per deadline per day. Changes to due date naturally reset schedule.
            key = f"deadline={item.id};due={item.due_date.isoformat()};days={days_left};date={today.isoformat()}"
            already = TaxDeadlineAudit.query.filter_by(deadline_id=item.id, action="Reminder Email Sent", details=key).first()
            if already:
                continue
            subject = f"Tax Compliance Deadline Reminder: {item.obligation} - {days_left} day(s) remaining"
            body = (
                f"Tax Compliance Calendar reminder\n\nObligation: {item.obligation}\nTax Type: {item.tax_type}\n"
                f"Activity: {item.activity}\nPeriod: {item.period}\nDue Date: {item.due_date:%d %B %Y}\n"
                f"Days Remaining: {days_left}\nStatus: {item.status}\nAssigned To: {item.assigned_to or 'Unassigned'}\n\n"
                "Please ensure the obligation is filed by the deadline. This reminder stops once the item is marked Completed or Not Applicable."
            )
            ok, _err = _central_send_email("tax_calendar", f"deadline_reminder_{days_left}d", subject, body, recipients=[RECIPIENT], reference_id=item.id)
            if ok:
                db.session.add(TaxDeadlineAudit(deadline_id=item.id, actor="SYSTEM - CALENDAR REMINDER", action="Reminder Email Sent", details=key))
                db.session.commit(); sent += 1
        print(f"Calendar reminder run: {today.isoformat()}, sent={sent}")

if __name__ == "__main__":
    run()
