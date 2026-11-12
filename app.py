import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SelectField, DateField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from flask_migrate import Migrate
from sqlalchemy import or_, func, delete
from werkzeug.utils import secure_filename
from io import BytesIO
import csv, io, smtplib, ssl, logging, hashlib, hmac
from email.message import EmailMessage
from decimal import Decimal, InvalidOperation
from sqlalchemy import UniqueConstraint
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("cettp.notifications")
database_url = os.environ.get("DATABASE_URL", "sqlite:///cettp.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024  # 40 MB total request size
ALLOWED_ATTACHMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "doc", "docx", "csv"}
MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024  # 12 MB per file
ATTACHMENT_CATEGORIES = [
    ("cancelled_invoice_efd", "Cancelled invoice / EFD (mandatory at initiation)"),
    ("original_invoice", "Original invoice / supporting invoice"),
    ("tra_cancellation_note", "TRA cancellation note / approval"),
    ("credit_note", "Credit note"),
    ("replacement_invoice", "Corrected / replacement invoice"),
    ("other", "Other supporting document"),
]
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)

# Integrated EFD-to-Invoice utility, available from the portal selection screen.
from efd_portal import efd_bp
app.register_blueprint(efd_bp, url_prefix="/efd-invoice")

STATUSES = [
    "Initiated", "Under Tax Review", "Returned for Clarification",
    "Approved for TRA Processing", "Submitted to TRA", "TRA Approved",
    "TRA Rejected", "Closed"
]
TYPES = [("Cancellation", "Policy Cancellation"), ("Endorsement", "Policy Endorsement")]
TRA_STATUSES = ["Not Submitted", "Pending", "Approved", "Rejected", "Not Applicable"]

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    case_type = db.Column(db.String(30), nullable=False)
    policy_number = db.Column(db.String(80), nullable=False, index=True)
    customer_name = db.Column(db.String(160), nullable=False, index=True)
    customer_tin = db.Column(db.String(40))
    product = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    underwriter = db.Column(db.String(120))
    reason = db.Column(db.Text, nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    original_invoice_no = db.Column(db.String(100))
    original_invoice_amount = db.Column(db.Numeric(16,2), default=0)
    adjustment_amount = db.Column(db.Numeric(16,2), default=0)
    vat_amount = db.Column(db.Numeric(16,2), default=0)
    credit_note_no = db.Column(db.String(100))
    replacement_invoice_no = db.Column(db.String(100))
    adjustment_reference = db.Column(db.String(100))
    tra_status = db.Column(db.String(40), default="Not Submitted")
    tra_reference = db.Column(db.String(100))
    workflow_status = db.Column(db.String(50), default="Initiated", nullable=False)
    initiator_name = db.Column(db.String(120), nullable=False)
    tax_owner = db.Column(db.String(120))
    tax_notes = db.Column(db.Text)
    closure_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = db.Column(db.DateTime)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False, index=True)
    actor_role = db.Column(db.String(30), nullable=False)
    actor_name = db.Column(db.String(120))
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    case = db.relationship("Case", backref=db.backref("audit_logs", lazy=True, cascade="all, delete-orphan"))


class EmailNotificationLog(db.Model):
    """Audit trail for notification attempts; retained even if the case is later deleted."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, nullable=False, index=True)
    case_reference = db.Column(db.String(30), nullable=False, index=True)
    event_key = db.Column(db.String(40), nullable=False, default="new_request")
    recipient = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime)
    __table_args__ = (UniqueConstraint("case_id", "event_key", name="uq_email_notification_case_event"),)


class InAppNotification(db.Model):
    """In-portal alert created when a new cancellation/endorsement case is submitted."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id", ondelete="CASCADE"), nullable=False, index=True)
    case_reference = db.Column(db.String(30), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    case = db.relationship("Case", backref=db.backref("in_app_notifications", lazy=True, cascade="all, delete-orphan"))


class InAppNotificationRead(db.Model):
    """Per Tax Compliance actor read receipt; unread state is individual to the logged-in reviewer."""
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("in_app_notification.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_name = db.Column(db.String(120), nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notification = db.relationship("InAppNotification", backref=db.backref("read_receipts", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (UniqueConstraint("notification_id", "actor_name", name="uq_inapp_notification_actor_read"),)


class InitiatorNotification(db.Model):
    """Private in-app update for the Initiator who owns a case."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email = db.Column(db.String(254), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    event_key = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = db.Column(db.DateTime)
    case = db.relationship("Case", backref=db.backref("initiator_notifications", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (UniqueConstraint("case_id", "recipient_email", "event_key", name="uq_initiator_notification_event"),)


class ReconciliationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tax_type = db.Column(db.String(10), nullable=False, index=True)  # VAT or WHT
    period = db.Column(db.String(20), nullable=False, index=True)
    source = db.Column(db.String(80), nullable=False)
    reference = db.Column(db.String(120), index=True)
    counterparty = db.Column(db.String(180), index=True)
    category = db.Column(db.String(120))
    book_amount = db.Column(db.Numeric(16,2), nullable=False, default=0)
    tra_amount = db.Column(db.Numeric(16,2), nullable=False, default=0)
    notes = db.Column(db.Text)
    uploaded_by = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def variance(self):
        return Decimal(str(self.book_amount or 0)) - Decimal(str(self.tra_amount or 0))

class RegisterUpload(db.Model):
    """Monthly Premium Register upload history; stored separately to preserve existing V1.1 tables."""
    id = db.Column(db.Integer, primary_key=True)
    upload_batch = db.Column(db.String(80), unique=True, nullable=False, index=True)
    period = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    file_name = db.Column(db.String(255), nullable=False)
    source_rows = db.Column(db.Integer, default=0, nullable=False)
    negative_count = db.Column(db.Integer, default=0, nullable=False)
    matched_count = db.Column(db.Integer, default=0, nullable=False)
    different_count = db.Column(db.Integer, default=0, nullable=False)
    pure_count = db.Column(db.Integer, default=0, nullable=False)
    uploaded_by = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CancellationTrack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    upload_batch = db.Column(db.String(80), index=True)
    transaction_date = db.Column(db.Date)
    document_no = db.Column(db.String(120), index=True)
    policy_number = db.Column(db.String(80), nullable=False, index=True)
    endorsement_no = db.Column(db.String(120))
    insured_name = db.Column(db.String(180))
    product = db.Column(db.String(120))
    branch_name = db.Column(db.String(120))
    transaction_type = db.Column(db.String(100))
    negative_amount = db.Column(db.Numeric(16,2), nullable=False, default=0)
    matched_positive_amount = db.Column(db.Numeric(16,2), nullable=False, default=0)
    matched_document_no = db.Column(db.String(120))
    classification = db.Column(db.String(80), nullable=False)
    cancellation_reason = db.Column(db.Text)
    tra_status = db.Column(db.String(40), nullable=False, default="Not Submitted")
    tra_reference = db.Column(db.String(120))
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), index=True)
    imported_by = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    case = db.relationship("Case", foreign_keys=[case_id])

class CaseAttachment(db.Model):
    """Case-level document stored in the database to avoid ephemeral-host filesystem loss."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=False, default="application/octet-stream")
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    uploaded_by = db.Column(db.String(120), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    case = db.relationship("Case", backref=db.backref("attachments", lazy=True, cascade="all, delete-orphan"))


class TaxDeadline(db.Model):
    """A filing or payment obligation tracked by Tax Compliance."""
    id = db.Column(db.Integer, primary_key=True)
    obligation = db.Column(db.String(140), nullable=False, index=True)
    tax_type = db.Column(db.String(40), nullable=False, index=True)
    activity = db.Column(db.String(20), nullable=False, default="Filing")  # Filing / Payment
    period = db.Column(db.String(30), nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    assigned_to = db.Column(db.String(120))
    status = db.Column(db.String(40), nullable=False, default="Upcoming", index=True)
    completed_date = db.Column(db.Date)
    payment_amount = db.Column(db.Numeric(16,2))
    control_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TaxDeadlineAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deadline_id = db.Column(db.Integer, db.ForeignKey("tax_deadline.id", ondelete="CASCADE"), nullable=False, index=True)
    actor = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    deadline = db.relationship("TaxDeadline", backref=db.backref("audit_entries", lazy=True, cascade="all, delete-orphan"))


class TaxDeadlineAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deadline_id = db.Column(db.Integer, db.ForeignKey("tax_deadline.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=False, default="application/octet-stream")
    file_size = db.Column(db.Integer, nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    uploaded_by = db.Column(db.String(120), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    deadline = db.relationship("TaxDeadline", backref=db.backref("attachments", lazy=True, cascade="all, delete-orphan"))


class PortalEmailLog(db.Model):
    __tablename__ = "portal_email_logs"
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    recipient = db.Column(db.String(1000), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    error_message = db.Column(db.String(2000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = db.Column(db.DateTime)


class InvestmentWHTBatch(db.Model):
    __tablename__ = "investment_wht_batches"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    source_rows = db.Column(db.Integer, default=0, nullable=False)
    imported_rows = db.Column(db.Integer, default=0, nullable=False)
    skipped_rows = db.Column(db.Integer, default=0, nullable=False)
    uploaded_by = db.Column(db.String(120), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class InvestmentWHT(db.Model):
    __tablename__ = "investment_wht"
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(180), nullable=False, index=True)
    bank_tin = db.Column(db.String(40), nullable=False, index=True)
    amount_invested = db.Column(db.Numeric(18, 2), nullable=False)
    nature = db.Column(db.String(80), nullable=False, default="Fixed Deposit")
    start_date = db.Column(db.Date, nullable=False)
    maturity_date = db.Column(db.Date, nullable=False, index=True)
    annual_rate = db.Column(db.Numeric(9, 5), nullable=False)
    calculated_interest = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    confirmed_interest = db.Column(db.Numeric(18, 2))
    expected_wht = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    actual_wht = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    wht_rate = db.Column(db.Numeric(5, 2), nullable=False, default=10)
    certificate_reference = db.Column(db.String(150))
    certificate_date = db.Column(db.Date)
    certificate_filename = db.Column(db.String(255))
    certificate_content_type = db.Column(db.String(120))
    certificate_data = db.Column(db.LargeBinary)
    notes = db.Column(db.Text)
    batch_id = db.Column(db.Integer, db.ForeignKey("investment_wht_batches.id"), index=True)
    duplicate_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_by = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def days_invested(self):
        return max(0, (self.maturity_date - self.start_date).days)

    @property
    def interest_for_wht(self):
        return self.confirmed_interest if self.confirmed_interest is not None else self.calculated_interest

    @property
    def outstanding_wht(self):
        # A WHT receivable only becomes outstanding when the investment has matured.
        if self.maturity_date > _investment_local_today():
            return Decimal("0.00")
        return max(Decimal("0.00"), Decimal(self.expected_wht or 0) - Decimal(self.actual_wht or 0))

    @property
    def wht_filing_deadline(self):
        next_month = date(self.maturity_date.year + (1 if self.maturity_date.month == 12 else 0),
                          1 if self.maturity_date.month == 12 else self.maturity_date.month + 1, 1)
        return date(next_month.year, next_month.month, 7)

    @property
    def status(self):
        today = _investment_local_today()
        if self.maturity_date > today:
            return "Upcoming maturity"
        if self.actual_wht and self.outstanding_wht > 0:
            return "Partially reconciled"
        if self.outstanding_wht > 0:
            return "Matured – WHT outstanding"
        if not self.certificate_data:
            return "WHT certificate pending"
        return "WHT fully reconciled"


class InvestmentWHTEmailLog(db.Model):
    __tablename__ = "investment_wht_email_logs"
    id = db.Column(db.Integer, primary_key=True)
    investment_id = db.Column(db.Integer, db.ForeignKey("investment_wht.id"), nullable=False, index=True)
    event_key = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    recipient = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.String(2000))
    __table_args__ = (UniqueConstraint("investment_id", "event_key", "event_date", name="uq_investment_wht_email_event"),)


class VatLedgerUpload(db.Model):
    """Immutable source workbook upload for the VAT control account."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_sha256 = db.Column(db.String(64), nullable=False, unique=True, index=True)
    file_data = db.Column(db.LargeBinary, nullable=False)
    output_rows = db.Column(db.Integer, nullable=False, default=0)
    input_rows = db.Column(db.Integer, nullable=False, default=0)
    period_from = db.Column(db.String(7))
    period_to = db.Column(db.String(7))
    uploaded_by = db.Column(db.String(120), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class VatLedgerEntry(db.Model):
    """A transaction parsed from ERP account 330101 or 330107."""
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("vat_ledger_upload.id", ondelete="CASCADE"), nullable=False, index=True)
    ledger_account = db.Column(db.String(6), nullable=False, index=True)
    tax_period = db.Column(db.String(7), nullable=False, index=True)
    gl_date = db.Column(db.Date)
    transaction_number = db.Column(db.String(100))
    transaction_date = db.Column(db.Date)
    creation_date = db.Column(db.Date)
    posting_date = db.Column(db.Date)
    document_number = db.Column(db.String(150))
    batch_name = db.Column(db.String(255))
    counterparty = db.Column(db.String(255))
    transaction_source = db.Column(db.String(80))
    transaction_type = db.Column(db.String(100))
    natural_account_description = db.Column(db.String(180))
    transaction_description = db.Column(db.Text)
    entered_amount = db.Column(db.Numeric(20, 4))
    entered_currency = db.Column(db.String(8))
    accounted_amount = db.Column(db.Numeric(20, 4), nullable=False)
    accounted_currency = db.Column(db.String(8))
    initiator = db.Column(db.String(180))
    classification = db.Column(db.String(40), nullable=False, default="UNCLASSIFIED", index=True)
    review_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.String(120))
    reviewed_at = db.Column(db.DateTime)
    upload = db.relationship("VatLedgerUpload", backref=db.backref("entries", lazy=True, cascade="all, delete-orphan"))


class VatLedgerPeriodBalance(db.Model):
    """ERP opening/closing balance reported for an account and monthly period."""
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("vat_ledger_upload.id", ondelete="CASCADE"), nullable=False, index=True)
    ledger_account = db.Column(db.String(6), nullable=False, index=True)
    tax_period = db.Column(db.String(7), nullable=False, index=True)
    opening_balance = db.Column(db.Numeric(20, 4))
    closing_balance = db.Column(db.Numeric(20, 4))
    upload = db.relationship("VatLedgerUpload", backref=db.backref("period_balances", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (UniqueConstraint("upload_id", "ledger_account", "tax_period", name="uq_vat_ledger_period_balance"),)


VAT_MANUAL_CATEGORIES = {
    "INCREASING_ADJUSTMENT": ("Increasing adjustment", 1),
    "DECREASING_ADJUSTMENT": ("Decreasing adjustment", -1),
    "IMPORTED_SERVICE_OUTPUT_VAT": ("Imported services – output VAT", 1),
    "IMPORTED_SERVICE_INPUT_VAT": ("Imported services – input VAT credit", -1),
    "IMPORT_VAT_CREDIT": ("Import VAT credit", -1),
    "VAT_PAYMENT": ("VAT payment to TRA", -1),
    "VAT_REFUND_RECEIVED": ("VAT refund received", 1),
    "OTHER_INCREASE": ("Other increase in VAT liability", 1),
    "OTHER_DECREASE": ("Other decrease in VAT liability", -1),
}


class VatManualMovement(db.Model):
    """Manual VAT account movements not captured in the two ERP ledger extracts."""
    id = db.Column(db.Integer, primary_key=True)
    tax_period = db.Column(db.String(7), nullable=False, index=True)
    movement_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(40), nullable=False)
    amount = db.Column(db.Numeric(20, 4), nullable=False)
    supply_value = db.Column(db.Numeric(20, 4))
    counterparty = db.Column(db.String(255))
    document_number = db.Column(db.String(180))
    reference = db.Column(db.String(180))
    notes = db.Column(db.Text)
    filename = db.Column(db.String(255))
    content_type = db.Column(db.String(120))
    file_data = db.Column(db.LargeBinary)
    created_by = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def liability_effect(self):
        return Decimal(str(self.amount or 0)) * Decimal(str(VAT_MANUAL_CATEGORIES.get(self.category, ("", 0))[1]))


class VatReturnRecord(db.Model):
    """Key figures and filing evidence for a submitted TRA VAT return."""
    id = db.Column(db.Integer, primary_key=True)
    tax_period = db.Column(db.String(7), nullable=False, unique=True, index=True)
    submission_date = db.Column(db.Date)
    return_reference = db.Column(db.String(150))
    output_tax = db.Column(db.Numeric(20, 4), default=0, nullable=False)
    input_tax = db.Column(db.Numeric(20, 4), default=0, nullable=False)
    increasing_adjustments = db.Column(db.Numeric(20, 4), default=0, nullable=False)
    decreasing_adjustments = db.Column(db.Numeric(20, 4), default=0, nullable=False)
    declared_net_tax = db.Column(db.Numeric(20, 4), default=0, nullable=False)
    notes = db.Column(db.Text)
    filename = db.Column(db.String(255))
    content_type = db.Column(db.String(120))
    file_data = db.Column(db.LargeBinary)
    updated_by = db.Column(db.String(120), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VatAuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class CaseForm(FlaskForm):
    case_type = SelectField("Request type", choices=TYPES, validators=[DataRequired()])
    policy_number = StringField("Policy number", validators=[DataRequired(), Length(max=80)])
    customer_name = StringField("Customer / insured name", validators=[DataRequired(), Length(max=160)])
    customer_tin = StringField("Customer TIN", validators=[Optional(), Length(max=40)])
    product = StringField("Product / class", validators=[Optional(), Length(max=100)])
    branch = StringField("Branch", validators=[Optional(), Length(max=100)])
    underwriter = StringField("Underwriter", validators=[Optional(), Length(max=120)])
    initiator_name = StringField("Initiator name", validators=[DataRequired(), Length(max=120)])
    reason = TextAreaField("Reason for cancellation / endorsement", validators=[DataRequired(), Length(max=4000)])
    effective_date = DateField("Effective date", validators=[DataRequired()], format="%Y-%m-%d")
    original_invoice_no = StringField("Original invoice number", validators=[Optional(), Length(max=100)])
    original_invoice_amount = DecimalField("Original invoice amount (TZS)", validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    adjustment_amount = DecimalField("Adjustment amount (TZS)", validators=[Optional()], places=2, default=0)
    vat_amount = DecimalField("VAT adjustment (TZS)", validators=[Optional()], places=2, default=0)
    submit = SubmitField("Submit request")

class TaxForm(FlaskForm):
    workflow_status = SelectField("Workflow status", choices=[(s,s) for s in STATUSES], validators=[DataRequired()])
    tra_status = SelectField("TRA status", choices=[(s,s) for s in TRA_STATUSES], validators=[DataRequired()])
    tax_owner = StringField("Tax owner", validators=[Optional(), Length(max=120)])
    tra_reference = StringField("TRA reference / acknowledgement", validators=[Optional(), Length(max=100)])
    credit_note_no = StringField("Credit note number", validators=[Optional(), Length(max=100)])
    replacement_invoice_no = StringField("Replacement invoice number", validators=[Optional(), Length(max=100)])
    adjustment_reference = StringField("Adjustment reference", validators=[Optional(), Length(max=100)])
    tax_notes = TextAreaField("Tax review notes", validators=[Optional(), Length(max=4000)])
    closure_notes = TextAreaField("Closure notes", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save tax update")

def log_action(case, action, details=""):
    db.session.add(AuditLog(case_id=case.id, actor_role=session.get("role", "Unknown"),
                            actor_name=session.get("actor_name", ""), action=action, details=details))

def _smtp_port():
    try:
        return int(os.environ.get("SMTP_PORT", "587"))
    except (TypeError, ValueError):
        return 587


def _smtp_settings():
    """Single environment-driven SMTP configuration for every CETTP notification."""
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.mail.yahoo.com").strip(),
        "port": _smtp_port(),
        "username": os.environ.get("SMTP_USERNAME", "temporarytin2026@yahoo.com").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "sender": os.environ.get("SMTP_FROM", "temporarytin2026@yahoo.com").strip(),
    }


def _deliver_portal_email(recipients, subject, body):
    """Deliver through the shared Yahoo SMTP service and persist every attempt."""
    cfg = _smtp_settings()
    event_type = "test" if subject.startswith("Britam CETTP – Email configuration test") else "notification"
    log = PortalEmailLog(event_type=event_type, recipient=", ".join(recipients)[:1000] or "NOT_CONFIGURED",
                         subject=subject[:255], status="pending")
    db.session.add(log)
    db.session.commit()
    try:
        if not recipients or not cfg["username"] or not cfg["password"] or not cfg["sender"]:
            raise RuntimeError("Email is not configured. Set CETTP_TAX_COMPLIANCE_EMAIL and SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM in the Render environment.")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = cfg["sender"]
        message["To"] = recipients[0]
        if len(recipients) > 1: message["Cc"] = ", ".join(recipients[1:])
        message.set_content(body)
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(cfg["username"], cfg["password"])
            server.send_message(message)
        log.status = "sent"; log.sent_at = datetime.utcnow(); log.error_message = None
        db.session.commit()
    except Exception as exc:
        log.status = "not_configured" if isinstance(exc, RuntimeError) else "failed"
        log.error_message = f"{type(exc).__name__}: {str(exc)[:1800]}"
        db.session.commit()
        raise


def _notification_recipients():
    """Read shared mailbox recipient(s) from environment; allow semicolon/comma separated addresses."""
    raw = os.environ.get("CETTP_TAX_COMPLIANCE_EMAIL", "").strip()
    return [address.strip() for address in raw.replace(";", ",").split(",") if address.strip()]


def send_new_request_notification(case):
    """Log and send one notification per initiated case. Email failure never rolls back a submitted case."""
    recipients = _notification_recipients()
    recipient_label = ", ".join(recipients) if recipients else ""

    # A unique case/event record prevents duplicate sends if this function is invoked again.
    existing = EmailNotificationLog.query.filter_by(case_id=case.id, event_key="new_request").first()
    if existing:
        logger.info("New-request notification already logged for %s (status=%s)", case.reference, existing.status)
        return existing.status == "sent"

    if not recipients:
        log = EmailNotificationLog(case_id=case.id, case_reference=case.reference,
            event_key="new_request", recipient="NOT_CONFIGURED", status="not_configured",
            attempts=0, error_message="Set CETTP_TAX_COMPLIANCE_EMAIL to one or more approved notification recipients.")
        db.session.add(log)
        db.session.commit()
        logger.warning("Email notification not configured for case %s", case.reference)
        return False

    log = EmailNotificationLog(case_id=case.id, case_reference=case.reference,
        event_key="new_request", recipient=recipient_label, status="pending", attempts=0)
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Another worker may have inserted the unique case/event row concurrently.
        existing = EmailNotificationLog.query.filter_by(case_id=case.id, event_key="new_request").first()
        if existing:
            logger.info("Concurrent duplicate notification suppressed for %s", case.reference)
            return existing.status == "sent"
        logger.exception("Unable to create notification log for %s", case.reference)
        return False

    subject = f"CETTP – New {case.case_type} Request – {case.reference}"
    amount = f"TZS {case.adjustment_amount:,.2f}" if case.adjustment_amount is not None else "Not provided"
    effective_date = case.effective_date.strftime("%d %b %Y") if case.effective_date else "Not provided"
    body = f"""A new cancellation/endorsement request has been submitted in Britam CETTP and requires Tax Compliance review.

Case reference: {case.reference}
Request type: {case.case_type}
Policy number: {case.policy_number}
Customer / insured: {case.customer_name}
Adjustment amount: {amount}
Effective date: {effective_date}
Initiator: {case.initiator_name}
Submitted (UTC): {case.created_at.strftime('%Y-%m-%d %H:%M UTC') if case.created_at else datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Workflow status: {case.workflow_status}

Reason:
{case.reason or 'Not provided'}

Open the request in CETTP after signing in: {os.environ.get('CETTP_BASE_URL', request.url_root.rstrip('/')).rstrip('/')}{url_for('case_detail', case_id=case.id)}

This is an automated notification. Please do not reply to this message.
"""
    log.attempts = 1
    try:
        _deliver_portal_email(recipients, subject, body)
        log.status = "sent"
        log.sent_at = datetime.utcnow()
        log.error_message = None
        db.session.commit()
        logger.info("New-request email sent for %s to %s", case.reference, recipient_label)
        return True
    except Exception as exc:
        db.session.rollback()
        # Re-fetch log after rollback and persist a sanitized, bounded error detail.
        failed_log = EmailNotificationLog.query.filter_by(case_id=case.id, event_key="new_request").first()
        if failed_log:
            failed_log.status = "failed"
            failed_log.attempts = 1
            failed_log.error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
            db.session.commit()
        logger.exception("New-request email failed for case %s", case.reference)
        return False


def make_reference():
    year = datetime.utcnow().year
    latest = Case.query.filter(Case.reference.like(f"CETTP-{year}-%")).order_by(Case.id.desc()).first()
    seq = int(latest.reference.rsplit("-", 1)[1]) + 1 if latest else 1
    return f"CETTP-{year}-{seq:05d}"

def _normalise_policy(value):
    """Compare policy identifiers consistently despite spaces/case/punctuation."""
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())

def _case_action_signature(case_type, policy_number, effective_date, invoice_no, amount):
    try:
        amount_value = abs(Decimal(str(amount or 0))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        amount_value = Decimal("0.00")
    return (_normalise_policy(policy_number), str(case_type or "").strip().lower(),
            effective_date.isoformat() if effective_date else "", str(invoice_no or "").strip().upper(), amount_value)

def _find_duplicate_action(case_type, policy_number, effective_date, invoice_no, amount, exclude_case_id=None, exclude_tracker_id=None):
    """Find exact duplicate actions across initiator cases and Premium Register imports.

    Same-policy records of a different date/document/amount are surfaced as related
    actions, but are not blocked because one policy can legitimately have many endorsements.
    """
    target = _case_action_signature(case_type, policy_number, effective_date, invoice_no, amount)
    related = []
    for case in Case.query.all():
        if exclude_case_id and case.id == exclude_case_id:
            continue
        if _normalise_policy(case.policy_number) != target[0] or case.case_type.lower() != target[1]:
            continue
        related.append((case.reference, case.effective_date, case.original_invoice_no, case.adjustment_amount, case.workflow_status, case.tra_status))
        if _case_action_signature(case.case_type, case.policy_number, case.effective_date, case.original_invoice_no, case.adjustment_amount) == target:
            return ("case", case, related)
    # Tracker rows that have not yet been imported to CETTP also count as existing actions.
    tracker_rows = CancellationTrack.query.all()
    for row in tracker_rows:
        if exclude_tracker_id and row.id == exclude_tracker_id:
            continue
        inferred_type = "Endorsement" if (row.classification or "").startswith("Different amount") else "Cancellation"
        if _normalise_policy(row.policy_number) != target[0] or inferred_type.lower() != target[1]:
            continue
        related.append((f"Premium Register row #{row.id}", row.transaction_date, row.document_no, row.negative_amount, "Tracked", row.tra_status))
        if _case_action_signature(inferred_type, row.policy_number, row.transaction_date, row.document_no, row.negative_amount) == target:
            return ("tracker", row, related)
    return (None, None, related)

def _tax_actor_name():
    return (session.get("actor_name") or "Tax Compliance").strip()[:120]


def _notification_is_read(notification_id, actor_name=None):
    actor_name = actor_name or _tax_actor_name()
    return InAppNotificationRead.query.filter_by(notification_id=notification_id, actor_name=actor_name).first() is not None


@app.route("/notifications")
def notifications():
    if session.get("role") != "tax":
        return redirect(url_for("home"))
    actor = _tax_actor_name()
    rows = InAppNotification.query.order_by(InAppNotification.created_at.desc()).limit(250).all()
    read_ids = {r.notification_id for r in InAppNotificationRead.query.filter_by(actor_name=actor).all()}
    return render_template("notifications.html", notifications=rows, read_ids=read_ids, actor=actor, unread_count=sum(1 for row in rows if row.id not in read_ids))


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    if session.get("role") != "tax":
        return redirect(url_for("home"))
    notification = InAppNotification.query.get_or_404(notification_id)
    actor = _tax_actor_name()
    existing = InAppNotificationRead.query.filter_by(notification_id=notification.id, actor_name=actor).first()
    if not existing:
        db.session.add(InAppNotificationRead(notification_id=notification.id, actor_name=actor))
        db.session.commit()
    return redirect(url_for("case_detail", case_id=notification.case_id))


@app.route("/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    if session.get("role") != "tax":
        return redirect(url_for("home"))
    actor = _tax_actor_name()
    read_ids = {r.notification_id for r in InAppNotificationRead.query.filter_by(actor_name=actor).all()}
    unread = InAppNotification.query.filter(~InAppNotification.id.in_(read_ids)).all() if read_ids else InAppNotification.query.all()
    now = datetime.utcnow()
    for item in unread:
        db.session.add(InAppNotificationRead(notification_id=item.id, actor_name=actor, read_at=now))
    db.session.commit()
    flash(f"Marked {len(unread)} notification(s) as read.", "success")
    return redirect(url_for("notifications"))


def _initiator_email():
    return (session.get("initiator_email") or session.get("actor_name") or "").strip().lower()


def _initiator_case_query():
    email = _initiator_email()
    if not email:
        return Case.query.filter(Case.id == -1)
    return Case.query.filter(func.lower(Case.initiator_name) == email)


def _initiator_case_access(case):
    if session.get("role") == "tax":
        return True
    if session.get("role") == "initiator" and (case.initiator_name or "").strip().lower() == _initiator_email():
        return True
    abort(403)


def _notify_initiator(case, event_key, title, message):
    recipient = (case.initiator_name or "").strip().lower()
    if not recipient or "@" not in recipient:
        return
    try:
        existing = InitiatorNotification.query.filter_by(case_id=case.id, recipient_email=recipient, event_key=event_key).first()
        if not existing:
            db.session.add(InitiatorNotification(case_id=case.id, recipient_email=recipient,
                title=title[:180], message=message, event_key=event_key[:80]))
    except Exception:
        logger.exception("Could not create initiator notification for %s", case.reference)


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/enter/tax", methods=["GET", "POST"])
def enter_tax_role():
    if request.method == "POST":
        code = request.form.get("security_code", "")
        if code == os.environ.get("TAX_ACCESS_CODE", "4823"):
            session["role"] = "tax"
            session["actor_name"] = request.form.get("actor_name", "").strip() or "Tax Compliance"
            target = request.args.get("next", "")
            if target.startswith("/") and not target.startswith("//"):
                return redirect(target)
            return redirect(url_for("dashboard"))
        flash("Access Denied", "danger")
    return render_template("tax_access.html")


@app.route("/enter/initiator", methods=["GET", "POST"])
@csrf.exempt
def enter_initiator_role():
    # Pilot mode: email is the username only; no OTP, password or verification code.
    # CSRF is exempted only for this email-only entry endpoint.
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        import re
        if not email or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            flash("Enter a valid email address to continue.", "danger")
            return render_template("initiator_access.html")
        session.clear()
        session["role"] = "initiator"
        session["actor_name"] = email
        session["initiator_email"] = email
        return redirect(url_for("initiator_dashboard"))
    return render_template("initiator_access.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if session.get("role") != "tax":
        return redirect(url_for("home"))
    total = Case.query.count()
    open_cases = Case.query.filter(Case.workflow_status != "Closed").count()
    awaiting_tra = Case.query.filter(Case.tra_status.in_(["Not Submitted", "Pending"])).count()
    closed = Case.query.filter_by(workflow_status="Closed").count()
    recent = Case.query.order_by(Case.created_at.desc()).limit(8).all()
    # Default overdue threshold is configurable in Render using CETTP_OVERDUE_DAYS.
    try:
        overdue_days = max(1, int(os.environ.get("CETTP_OVERDUE_DAYS", "5")))
    except (TypeError, ValueError):
        overdue_days = 5
    overdue_cutoff = datetime.utcnow() - timedelta(days=overdue_days)
    overdue_query = Case.query.filter(Case.workflow_status != "Closed", Case.created_at <= overdue_cutoff)
    overdue_count = overdue_query.count()
    overdue_cases = overdue_query.order_by(Case.created_at.asc()).limit(10).all()
    by_status = db.session.query(Case.workflow_status, func.count(Case.id)).group_by(Case.workflow_status).all()
    by_type = db.session.query(Case.case_type, func.count(Case.id)).group_by(Case.case_type).all()
    return render_template("dashboard.html", total=total, open_cases=open_cases, awaiting_tra=awaiting_tra,
                           closed=closed, recent=recent, by_status=by_status, by_type=by_type,
                           overdue_days=overdue_days, overdue_count=overdue_count, overdue_cases=overdue_cases, now_utc=datetime.utcnow())

@app.route("/initiator")
def initiator_dashboard():
    if session.get("role") != "initiator":
        return redirect(url_for("home"))
    base = _initiator_case_query()
    all_cases = base.order_by(Case.created_at.desc()).all()
    overdue_days = max(1, int(os.environ.get("CETTP_OVERDUE_DAYS", "5")))
    cutoff = datetime.utcnow() - timedelta(days=overdue_days)
    counts = {
        "all": len(all_cases),
        "drafts": sum(1 for c in all_cases if c.workflow_status == "Draft"),
        "awaiting": sum(1 for c in all_cases if c.workflow_status in ("Initiated", "Under Tax Review", "Approved for TRA Processing", "Submitted to TRA")),
        "returned": sum(1 for c in all_cases if c.workflow_status == "Returned for Clarification"),
        "completed": sum(1 for c in all_cases if c.workflow_status in ("Closed", "TRA Approved")),
        "overdue": sum(1 for c in all_cases if c.workflow_status not in ("Closed", "TRA Approved", "TRA Rejected", "Draft") and c.created_at <= cutoff),
    }
    unread = InitiatorNotification.query.filter_by(recipient_email=_initiator_email(), read_at=None).count()
    recent = all_cases[:8]
    return render_template("initiator_dashboard.html", counts=counts, recent=recent, overdue_days=overdue_days, unread=unread)


@app.route("/initiator/notifications")
def initiator_notifications():
    if session.get("role") != "initiator":
        return redirect(url_for("home"))
    rows = InitiatorNotification.query.filter_by(recipient_email=_initiator_email()).order_by(InitiatorNotification.created_at.desc()).limit(200).all()
    return render_template("initiator_notifications.html", notifications=rows)


@app.route("/initiator/notifications/<int:notification_id>/read", methods=["POST"])
def initiator_notification_read(notification_id):
    if session.get("role") != "initiator":
        return redirect(url_for("home"))
    item = InitiatorNotification.query.filter_by(id=notification_id, recipient_email=_initiator_email()).first_or_404()
    item.read_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("case_detail", case_id=item.case_id))


@app.route("/cases")
def cases():
    if session.get("role") not in ("tax", "initiator"):
        return redirect(url_for("home"))
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    case_type = request.args.get("type", "")
    submitted_from = request.args.get("from", "").strip()
    submitted_to = request.args.get("to", "").strip()
    overdue_only = request.args.get("overdue", "") == "1"
    query = _initiator_case_query() if session.get("role") == "initiator" else Case.query
    if q:
        query = query.filter(or_(Case.reference.ilike(f"%{q}%"), Case.policy_number.ilike(f"%{q}%"),
                                 Case.customer_name.ilike(f"%{q}%"), Case.tra_reference.ilike(f"%{q}%")))
    if status:
        query = query.filter_by(workflow_status=status)
    if case_type:
        query = query.filter_by(case_type=case_type)
    if submitted_from:
        try: query = query.filter(Case.created_at >= datetime.strptime(submitted_from, "%Y-%m-%d"))
        except ValueError: flash("Invalid start date filter.", "warning")
    if submitted_to:
        try: query = query.filter(Case.created_at < datetime.strptime(submitted_to, "%Y-%m-%d") + timedelta(days=1))
        except ValueError: flash("Invalid end date filter.", "warning")
    if overdue_only:
        try: overdue_days = max(1, int(os.environ.get("CETTP_OVERDUE_DAYS", "5")))
        except (TypeError, ValueError): overdue_days = 5
        query = query.filter(Case.workflow_status.notin_(["Closed", "TRA Approved", "TRA Rejected", "Draft"]), Case.created_at <= datetime.utcnow() - timedelta(days=overdue_days))
    records = query.order_by(Case.created_at.desc()).all()
    return render_template("cases.html", records=records, statuses=STATUSES, q=q, status=status, case_type=case_type, submitted_from=submitted_from, submitted_to=submitted_to, overdue_only=overdue_only)

@app.route("/cases/<int:case_id>/delete", methods=["POST"])
def delete_case(case_id):
    # Destructive actions are restricted to Tax Compliance and require a CSRF-protected POST.
    if not _tax_required(): return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    reference = case.reference
    # Remove linked tracker rows as well, so the deleted action cannot remain as stale tracking.
    CancellationTrack.query.filter_by(case_id=case.id).delete(synchronize_session=False)
    # Audit logs are cascade-deleted with the case.
    db.session.delete(case)
    db.session.commit()
    flash(f"Case {reference} and its linked tracking record(s) were deleted.", "success")
    return redirect(url_for("cases"))

@app.route("/cases/export.xlsx")
def cases_export():
    if session.get("role") not in ("tax", "initiator"):
        return redirect(url_for("home"))
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    q = request.args.get("q", "").strip(); status = request.args.get("status", ""); case_type = request.args.get("type", "")
    query = _initiator_case_query() if session.get("role") == "initiator" else Case.query
    if q:
        query = query.filter(or_(Case.reference.ilike(f"%{q}%"), Case.policy_number.ilike(f"%{q}%"), Case.customer_name.ilike(f"%{q}%"), Case.tra_reference.ilike(f"%{q}%")))
    if status: query = query.filter_by(workflow_status=status)
    if case_type: query = query.filter_by(case_type=case_type)
    records = query.order_by(Case.created_at.desc()).all()
    wb = Workbook(); ws = wb.active; ws.title = "CETTP Case Register"
    ws.append(["Britam CETTP — Case Register"]); ws.append([])
    headers = ["Case Reference", "Type", "Policy Number", "Customer / Insured", "Customer TIN", "Product", "Branch", "Underwriter", "Reason", "Effective Date", "Original Invoice No.", "Original Invoice Amount (TZS)", "Adjustment Amount (TZS)", "VAT Amount (TZS)", "Credit Note No.", "Replacement Invoice No.", "Adjustment Reference", "TRA Status", "TRA Reference", "Workflow Status", "Initiator", "Tax Owner", "Tax Notes", "Closure Notes", "Created At", "Updated At"]
    ws.append(headers)
    for c in records:
        ws.append([c.reference,c.case_type,c.policy_number,c.customer_name,c.customer_tin,c.product,c.branch,c.underwriter,c.reason,c.effective_date,c.original_invoice_no,float(c.original_invoice_amount or 0),float(c.adjustment_amount or 0),float(c.vat_amount or 0),c.credit_note_no,c.replacement_invoice_no,c.adjustment_reference,c.tra_status,c.tra_reference,c.workflow_status,c.initiator_name,c.tax_owner,c.tax_notes,c.closure_notes,c.created_at,c.updated_at])
    for cell in ws[3]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="123B63"); cell.alignment=Alignment(wrap_text=True,vertical="center")
    ws.freeze_panes="A4"; ws.auto_filter.ref=f"A3:{get_column_letter(ws.max_column)}{ws.max_row}"
    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width=max(12,min(36,max(len(str(c.value or "")) for c in col)+2))
    for row in ws.iter_rows(min_row=4):
        for cell in row:
            if cell.column in (10,25,26) and cell.value: cell.number_format="yyyy-mm-dd hh:mm" if cell.column in (25,26) else "yyyy-mm-dd"
            if cell.column in (12,13,14) and cell.value is not None: cell.number_format='#,##0.00;[Red](#,##0.00)'
    out=io.BytesIO(); wb.save(out); out.seek(0)
    return send_file(out,mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",as_attachment=True,download_name="Britam_CETTP_Case_Register.xlsx")

def _save_case_attachment(case, uploaded_file, category):
    """Validate and save an uploaded file; raises ValueError for user-correctable errors."""
    if not uploaded_file or not uploaded_file.filename:
        return None
    original_name = uploaded_file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    safe_name = secure_filename(original_name)
    if not safe_name or "." not in safe_name:
        raise ValueError("Each attachment must have a valid file extension.")
    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ValueError(f"File type .{extension} is not allowed. Allowed types: PDF, JPG/PNG, Excel, Word and CSV.")
    content = uploaded_file.read(MAX_ATTACHMENT_BYTES + 1)
    if not content:
        raise ValueError(f"{safe_name} is empty.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError(f"{safe_name} exceeds the 12 MB per-file limit.")
    if category not in dict(ATTACHMENT_CATEGORIES):
        raise ValueError("Select a valid document category.")
    item = CaseAttachment(case_id=case.id, category=category,
        original_filename=original_name[:255], stored_filename=safe_name[:255],
        content_type=(uploaded_file.mimetype or "application/octet-stream")[:120],
        file_size=len(content), file_data=content,
        uploaded_by=(session.get("actor_name") or "Unknown user")[:120])
    db.session.add(item)
    db.session.flush()
    log_action(case, "Supporting document uploaded", f"{dict(ATTACHMENT_CATEGORIES)[category]}: {safe_name} ({len(content)} bytes)")
    return item


@app.errorhandler(413)
def attachment_too_large(_error):
    flash("The upload was too large. Keep the total request below 40 MB and each attachment at or below 12 MB.", "danger")
    return redirect(request.referrer or url_for("cases"))


@app.route("/cases/<int:case_id>/attachments/upload", methods=["POST"])
def upload_case_attachments(case_id):
    if session.get("role") not in ("initiator", "tax"):
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    _initiator_case_access(case)
    category = request.form.get("category", "")
    files = request.files.getlist("attachments")
    files = [f for f in files if f and f.filename]
    if not files:
        flash("Choose at least one file to upload.", "warning")
        return redirect(url_for("case_detail", case_id=case.id))
    try:
        for uploaded_file in files:
            _save_case_attachment(case, uploaded_file, category)
        db.session.commit()
        flash(f"Successfully uploaded {len(files)} document(s) to {case.reference}.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    except Exception:
        db.session.rollback()
        logger.exception("Attachment upload failed for case %s", case.reference)
        flash("The documents could not be saved. No upload was committed; please try again or contact the administrator.", "danger")
    return redirect(url_for("case_detail", case_id=case.id))


@app.route("/cases/<int:case_id>/attachments/<int:attachment_id>/download")
def download_case_attachment(case_id, attachment_id):
    if session.get("role") not in ("initiator", "tax"):
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    _initiator_case_access(case)
    attachment = CaseAttachment.query.filter_by(id=attachment_id, case_id=case.id, active=True).first_or_404()
    return send_file(BytesIO(attachment.file_data), mimetype=attachment.content_type,
        as_attachment=True, download_name=attachment.stored_filename, max_age=0)


@app.route("/cases/<int:case_id>/attachments/<int:attachment_id>/delete", methods=["POST"])
def delete_case_attachment(case_id, attachment_id):
    if not _tax_required():
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    attachment = CaseAttachment.query.filter_by(id=attachment_id, case_id=case.id, active=True).first_or_404()
    # Soft-delete so document metadata and the action remain auditable; binary is retained for audit recovery.
    attachment.active = False
    log_action(case, "Supporting document removed from case view", f"{attachment.original_filename} ({dict(ATTACHMENT_CATEGORIES).get(attachment.category, attachment.category)})")
    db.session.commit()
    flash("Document removed from the active case attachment list. Its audit record is retained.", "success")
    return redirect(url_for("case_detail", case_id=case.id))


@app.route("/cases/new", methods=["GET", "POST"])
def new_case():
    if session.get("role") not in ("initiator", "tax"):
        return redirect(url_for("home"))
    form = CaseForm()
    # Initiators do not submit the Initiator name field. Remove only the
    # DataRequired validator for this role; Tax Compliance must still provide it.
    # WTForms re-processes submitted fields during validate_on_submit(), so merely
    # assigning .data before validation is not sufficient for a missing field.
    if session.get("role") == "initiator":
        # Email-only Initiator sessions supply the name server-side. Keep the
        # field optional during WTForms validation because the UI intentionally
        # does not submit an editable initiator_name control.
        form.initiator_name.validators = [Optional(), Length(max=120)]
    if form.validate_on_submit():
        # The Initiator must attach the cancelled invoice/EFD before a request can be submitted.
        cancelled_invoice_files = [f for f in request.files.getlist("files_cancelled_invoice_efd") if f and f.filename]
        if not cancelled_invoice_files:
            flash("The cancelled invoice / EFD is mandatory. Attach it before submitting the cancellation or endorsement request.", "danger")
            return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES)
        duplicate_source, duplicate_record, related_actions = _find_duplicate_action(
            form.case_type.data, form.policy_number.data.strip(), form.effective_date.data,
            form.original_invoice_no.data.strip() or None, form.adjustment_amount.data or 0)
        if duplicate_source:
            if duplicate_source == "case":
                flash(f"DUPLICATE ALERT: This {form.case_type.data.lower()} for policy {form.policy_number.data.strip()} appears to have already been initiated as {duplicate_record.reference} (workflow: {duplicate_record.workflow_status}; TRA: {duplicate_record.tra_status}). Open the existing case instead of creating another.", "danger")
            else:
                flash(f"DUPLICATE ALERT: This action for policy {form.policy_number.data.strip()} is already recorded in the Premium Register tracker (row #{duplicate_record.id}, TRA status: {duplicate_record.tra_status}). Review the existing tracking record instead of creating a duplicate.", "danger")
            return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES)
        if related_actions:
            refs = ", ".join(str(x[0]) for x in related_actions[:4])
            flash(f"POLICY ALERT: Existing {form.case_type.data.lower()} tracking for this policy was found ({refs}). Confirm this is a separate action before submitting; different dates, documents or amounts can represent legitimate separate endorsements.", "warning")
        case = Case(reference=make_reference(), case_type=form.case_type.data,
                    policy_number=form.policy_number.data.strip(), customer_name=form.customer_name.data.strip(),
                    customer_tin=form.customer_tin.data.strip() or None, product=form.product.data.strip() or None,
                    branch=form.branch.data.strip() or None, underwriter=form.underwriter.data.strip() or None,
                    reason=form.reason.data.strip(), effective_date=form.effective_date.data,
                    original_invoice_no=form.original_invoice_no.data.strip() or None,
                    original_invoice_amount=form.original_invoice_amount.data or 0,
                    adjustment_amount=form.adjustment_amount.data or 0, vat_amount=form.vat_amount.data or 0,
                    initiator_name=((session.get("initiator_email") or session.get("actor_name") or "").strip().lower()
                                    if session.get("role") == "initiator" else (form.initiator_name.data or "").strip()))
        try:
            db.session.add(case)
            db.session.flush()
            log_action(case, "Case initiated", f"{case.case_type} submitted for policy {case.policy_number}")
            for category, _label in ATTACHMENT_CATEGORIES:
                for uploaded_file in request.files.getlist(f"files_{category}"):
                    if uploaded_file and uploaded_file.filename:
                        _save_case_attachment(case, uploaded_file, category)
            # Save the case, attachments, audit log and Tax Compliance alert in
            # one transaction so a successful case cannot be left without its alert.
            db.session.add(InAppNotification(
                case_id=case.id,
                case_reference=case.reference,
                title=f"New {case.case_type} request",
                message=f"{case.initiator_name} submitted a {case.case_type.lower()} for policy {case.policy_number} ({case.customer_name})."
            ))
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES)
        except Exception:
            db.session.rollback()
            logger.exception("Initiator case submission failed; transaction rolled back")
            flash("Submission failed and nothing was saved. Please contact the administrator with the time of submission so the server error can be checked.", "danger")
            return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES)
        email_sent = send_new_request_notification(case)
        if email_sent:
            flash(f"Request submitted successfully. Reference: {case.reference}. Tax Compliance email notification sent.", "success")
        else:
            flash(f"Request submitted successfully. Reference: {case.reference}. An in-app notification is available to Tax Compliance. Email delivery is not configured and has been logged.", "success")
        return redirect(url_for("case_detail", case_id=case.id))
    if request.method == "POST":
        # Make validation failures visible instead of silently redisplaying the form.
        for field_name, errors in form.errors.items():
            logger.warning("Case submission validation failed for %s: %s", field_name, "; ".join(errors))
        if form.errors:
            flash("The request was not submitted. Please review the highlighted fields and try again. " +
                  " ".join(f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()), "danger")
    return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES)

@app.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
def edit_case(case_id):
    if session.get("role") not in ("tax", "initiator"):
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    _initiator_case_access(case)
    role = session.get("role")
    if role == "initiator" and case.workflow_status != "Returned for Clarification":
        flash("You can edit and resubmit a request only after Tax Compliance returns it for clarification.", "warning")
        return redirect(url_for("case_detail", case_id=case.id))
    form = CaseForm(obj=case)
    if role == "initiator":
        form.initiator_name.validators = [Optional(), Length(max=120)]
    if form.validate_on_submit():
        old_values = {name: getattr(case, name) for name in (
            "case_type", "policy_number", "customer_name", "customer_tin", "product", "branch", "underwriter",
            "reason", "effective_date", "original_invoice_no", "original_invoice_amount", "adjustment_amount", "vat_amount")}
        try:
            for name in old_values:
                value = getattr(form, name).data
                if isinstance(value, str):
                    value = value.strip() or None
                setattr(case, name, value)
            if role == "tax":
                case.initiator_name = (form.initiator_name.data or case.initiator_name).strip()
            else:
                case.initiator_name = _initiator_email()
                # A successful initiator resubmission returns the case to the Tax Compliance queue.
                case.workflow_status = "Under Tax Review"
            for category, _label in ATTACHMENT_CATEGORIES:
                for uploaded_file in request.files.getlist(f"files_{category}"):
                    if uploaded_file and uploaded_file.filename:
                        _save_case_attachment(case, uploaded_file, category)
            changed = [name for name, old in old_values.items() if old != getattr(case, name)]
            actor = _initiator_email() if role == "initiator" else (session.get("actor_name") or "Tax Compliance")
            role_label = "Initiator" if role == "initiator" else "Tax Compliance"
            log_action(case, f"{role_label} amended case", "Changed fields: " + (", ".join(changed) if changed else "No core fields changed; documents may have been added"))
            if role == "initiator":
                db.session.add(InAppNotification(case_id=case.id, case_reference=case.reference,
                    title="Resubmitted request", message=f"{case.reference} was amended and resubmitted by {case.initiator_name} for Tax Compliance review."))
            else:
                _notify_initiator(case, f"tax-amendment:{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
                    "Tax Compliance amended your request", f"Tax Compliance updated details on case {case.reference}. Open the case to review the changes.")
            db.session.commit()
            flash("Case details updated successfully." if role == "tax" else "Your changes have been saved and the request resubmitted to Tax Compliance.", "success")
            return redirect(url_for("case_detail", case_id=case.id))
        except Exception:
            db.session.rollback()
            logger.exception("Case edit failed for case %s", case.reference)
            flash("The changes could not be saved. Please check the server logs and try again.", "danger")
    elif request.method == "POST" and form.errors:
        flash("Please correct the highlighted fields: " + " ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items()), "danger")
    return render_template("case_form.html", form=form, attachment_categories=ATTACHMENT_CATEGORIES,
                           is_edit=True, case=case)

@app.route("/cases/<int:case_id>")
def case_detail(case_id):
    if session.get("role") not in ("tax", "initiator"):
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    _initiator_case_access(case)
    return render_template("case_detail.html", case=case, attachment_categories=ATTACHMENT_CATEGORIES, attachment_category_labels=dict(ATTACHMENT_CATEGORIES))

@app.route("/cases/<int:case_id>/tax-update", methods=["GET", "POST"])
def tax_update(case_id):
    if session.get("role") != "tax":
        flash("Tax Compliance access is required.", "danger")
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    form = TaxForm(obj=case)
    if form.validate_on_submit():
        old_status = case.workflow_status
        for field in ("workflow_status", "tra_status", "tax_owner", "tra_reference", "credit_note_no",
                      "replacement_invoice_no", "adjustment_reference", "tax_notes", "closure_notes"):
            value = getattr(form, field).data
            setattr(case, field, value.strip() if isinstance(value, str) and value.strip() else None if isinstance(value, str) else value)
        if case.workflow_status == "Closed":
            case.closed_at = datetime.utcnow()
            if not case.closure_notes:
                case.closure_notes = "Closed by Tax Compliance."
        else:
            case.closed_at = None
        log_action(case, "Tax record updated", f"Workflow status: {old_status} → {case.workflow_status}; TRA status: {case.tra_status}")
        if old_status != case.workflow_status:
            _notify_initiator(case, f"status:{case.workflow_status}", "Request status updated", f"Your case {case.reference} status changed from {old_status} to {case.workflow_status}.")
        if form.tax_notes.data and form.tax_notes.data.strip():
            _notify_initiator(case, f"review-note:{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}", "Tax Compliance added a comment", f"A reviewer added an update to {case.reference}. Please open the case to review the latest comments.")
        if case.workflow_status == "Returned for Clarification":
            _notify_initiator(case, f"returned:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", "Action required: request returned", f"Case {case.reference} has been returned for clarification. Review the case notes and provide the required information.")
        if case.workflow_status in ("TRA Approved", "TRA Rejected", "Closed"):
            _notify_initiator(case, f"outcome:{case.workflow_status}", f"Request {case.workflow_status}", f"Your case {case.reference} is now marked {case.workflow_status}.")
        db.session.commit()
        flash("Tax tracking record updated.", "success")
        return redirect(url_for("case_detail", case_id=case.id))
    return render_template("tax_update.html", form=form, case=case)

@app.route("/cases/<int:case_id>/history")
def case_history(case_id):
    if session.get("role") != "tax":
        return redirect(url_for("home"))
    case = Case.query.get_or_404(case_id)
    return render_template("history.html", case=case)


RECON_COLUMNS = ["period", "source", "reference", "counterparty", "category", "book_amount", "tra_amount", "notes"]

def _tax_required():
    if session.get("role") != "tax":
        flash("Tax Compliance access is required.", "danger")
        return False
    return True

def _amount(value):
    raw = str(value or "0").replace(",", "").strip()
    try:
        return Decimal(raw or "0")
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid amount: {value}")

@app.route("/reconciliation")
def reconciliation_home():
    if not _tax_required():
        return redirect(url_for("home"))
    kind = request.args.get("type", "VAT").upper()
    if kind not in ("VAT", "WHT"):
        kind = "VAT"
    period = request.args.get("period", "").strip()
    query = ReconciliationItem.query.filter_by(tax_type=kind)
    if period:
        query = query.filter_by(period=period)
    items = query.order_by(ReconciliationItem.created_at.desc()).limit(1000).all()
    total_book = sum((Decimal(str(x.book_amount or 0)) for x in items), Decimal("0"))
    total_tra = sum((Decimal(str(x.tra_amount or 0)) for x in items), Decimal("0"))
    total_variance = total_book-total_tra
    return render_template("reconciliation.html", items=items, kind=kind, period=period,
                           total_book=total_book, total_tra=total_tra, total_variance=total_variance)

@app.route("/reconciliation/upload", methods=["POST"])
def reconciliation_upload():
    if not _tax_required():
        return redirect(url_for("home"))
    kind = request.form.get("tax_type", "VAT").upper()
    if kind not in ("VAT", "WHT"):
        flash("Select VAT or WHT reconciliation.", "danger")
        return redirect(url_for("reconciliation_home"))
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a CSV or Excel file to upload.", "warning")
        return redirect(url_for("reconciliation_home", type=kind))
    name = secure_filename(file.filename).lower()
    try:
        if name.endswith(".csv"):
            content = file.stream.read().decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(content)))
        elif name.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook
            wb = load_workbook(file, read_only=True, data_only=True)
            ws = wb.active
            vals = ws.iter_rows(values_only=True)
            headers = [str(v or "").strip().lower() for v in next(vals, [])]
            rows = [dict(zip(headers, row)) for row in vals]
        else:
            raise ValueError("File must be .csv or .xlsx")
        cleaned = []
        for index, row in enumerate(rows, start=2):
            row = {str(k or "").strip().lower(): v for k, v in row.items()}
            if not any(v not in (None, "") for v in row.values()):
                continue
            missing = [c for c in ("period", "source", "book_amount", "tra_amount") if c not in row]
            if missing:
                raise ValueError("Missing required column(s): " + ", ".join(missing) + ". Use the provided template.")
            period = str(row.get("period") or "").strip()
            source = str(row.get("source") or "").strip()
            if not period or not source:
                raise ValueError(f"Row {index}: period and source are required.")
            cleaned.append(ReconciliationItem(tax_type=kind, period=period, source=source[:80],
                reference=str(row.get("reference") or "").strip()[:120] or None,
                counterparty=str(row.get("counterparty") or "").strip()[:180] or None,
                category=str(row.get("category") or "").strip()[:120] or None,
                book_amount=_amount(row.get("book_amount")), tra_amount=_amount(row.get("tra_amount")),
                notes=str(row.get("notes") or "").strip() or None, uploaded_by=session.get("actor_name", "Tax Compliance")))
        if not cleaned:
            raise ValueError("The file contains no data rows.")
        db.session.add_all(cleaned)
        db.session.commit()
        flash(f"Imported {len(cleaned)} {kind} reconciliation row(s). Variances are calculated automatically.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Upload failed: {exc}", "danger")
    return redirect(url_for("reconciliation_home", type=kind))

@app.route("/reconciliation/template/<kind>")
def reconciliation_template(kind):
    if not _tax_required():
        return redirect(url_for("home"))
    kind = kind.upper()
    if kind not in ("VAT", "WHT"):
        return redirect(url_for("reconciliation_home"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(RECON_COLUMNS)
    if kind == "VAT":
        writer.writerow(["2026-09", "Premiums-General", "INV-0001", "Example Customer", "Premiums", "100000", "100000", "Replace sample row with your data"])
    else:
        writer.writerow(["2026-09", "Agents Commission", "AG-0001", "Example Agent", "Commission WHT", "15000", "15000", "Replace sample row with your data"])
    data = io.BytesIO(output.getvalue().encode("utf-8-sig")); data.seek(0)
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name=f"{kind.lower()}_reconciliation_template.csv")

@app.route("/reconciliation/<int:item_id>/delete", methods=["POST"])
def reconciliation_delete(item_id):
    if not _tax_required():
        return redirect(url_for("home"))
    item = ReconciliationItem.query.get_or_404(item_id)
    kind = item.tax_type
    db.session.delete(item); db.session.commit()
    flash("Reconciliation row deleted.", "success")
    return redirect(url_for("reconciliation_home", type=kind))

# Premium Register cancellation / endorsement tracking
CANCEL_TRA_STATUSES = ["Not Submitted", "Pending", "Approved", "Rejected", "Not Applicable"]

def _normal_header(value):
    return " ".join(str(value or "").replace("\\n", " ").strip().upper().split())

def _parse_register_date(value):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    raw = str(value or "").strip()
    if not raw: return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%y"):
        try: return datetime.strptime(raw[:10], fmt).date()
        except ValueError: pass
    try:
        from openpyxl.utils.datetime import from_ISO8601
        return from_ISO8601(raw).date()
    except Exception: return None

def _parse_register_amount(value):
    if value is None or str(value).strip() == "": return Decimal("0")
    if isinstance(value, (int, float, Decimal)): return Decimal(str(value)).quantize(Decimal("0.01"))
    raw = str(value).strip().replace(",", "").replace("TZS", "").replace(" ", "")
    if raw.startswith("(") and raw.endswith(")"): raw = "-" + raw[1:-1]
    try: return Decimal(raw).quantize(Decimal("0.01"))
    except InvalidOperation: return Decimal("0")

def _register_rows(file):
    name = secure_filename(file.filename or "").lower()
    if name.endswith(".csv"):
        text_data = file.stream.read().decode("utf-8-sig", errors="replace")
        matrix = list(csv.reader(io.StringIO(text_data)))
    elif name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            wb = load_workbook(file, read_only=True, data_only=True)
        except Exception as exc:
            raise ValueError("The Premium Register could not be opened as a standard Excel workbook. Please open it in Excel and Save As an unprotected .xlsx file, or upload a CSV export.") from exc
        ws = wb.active
        matrix = list(ws.iter_rows(values_only=True))
    else:
        raise ValueError("Upload the Premium Register as .xlsx or .csv.")
    header_index = None; headers = None
    for i, row in enumerate(matrix[:80]):
        normalized = [_normal_header(v) for v in row]
        if any("POLICY NO" in h for h in normalized) and any("GROSS PREMIUM" in h for h in normalized):
            header_index = i; headers = normalized; break
    if header_index is None:
        raise ValueError("Could not find the Premium Register header row. Required headings include POLICY NO and GROSS PREMIUM.")
    result=[]
    for row in matrix[header_index+1:]:
        values = list(row) + [None] * max(0, len(headers)-len(row))
        item = {headers[j]: values[j] for j in range(min(len(headers),len(values))) if headers[j]}
        policy = str(item.get("POLICY NO") or "").strip()
        if not policy or policy.upper() in ("NONE", "TOTAL", "GRAND TOTAL"):
            continue
        # Ignore repeated header lines and report totals.
        if policy.upper() == "POLICY NO": continue
        amount_value = item.get("GROSS PREMIUM")
        amount = _parse_register_amount(amount_value)
        if amount == 0:
            # Some exports place the signed transaction value in AMT or NETT PREMIUM.
            for alt in ("AMT", "NETT PREMIUM"):
                candidate = _parse_register_amount(item.get(alt))
                if candidate != 0: amount = candidate; break
        result.append({
            "transaction_date": _parse_register_date(item.get("TRANSACTION DATE")),
            "document_no": str(item.get("NO") or "").strip() or None,
            "policy_number": policy[:80],
            "endorsement_no": str(item.get("ENDORSEMENT NO") or "").strip() or None,
            "insured_name": str(item.get("NAME OF INSURED") or "").strip() or None,
            "product": str(item.get("PRODUCT") or "").strip() or None,
            "branch_name": str(item.get("BRANCH NAME") or "").strip() or None,
            "transaction_type": str(item.get("TRANSACTION TYPE") or "").strip() or None,
            "amount": amount,
        })
    if not result: raise ValueError("No Premium Register transactions were found under the detected headings.")
    return result

@app.route("/cancellation-tracker", methods=["GET"])
def cancellation_tracker():
    if not _tax_required(): return redirect(url_for("home"))
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    classification = request.args.get("classification", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    period = request.args.get("period", "").strip()
    query = CancellationTrack.query
    if q: query = query.filter(or_(CancellationTrack.policy_number.ilike(f"%{q}%"), CancellationTrack.insured_name.ilike(f"%{q}%"), CancellationTrack.document_no.ilike(f"%{q}%")))
    if status: query = query.filter_by(tra_status=status)
    if classification: query = query.filter_by(classification=classification)
    if period:
        batches = [u.upload_batch for u in RegisterUpload.query.filter_by(period=period).all()]
        if batches: query = query.filter(CancellationTrack.upload_batch.in_(batches))
        else: query = query.filter(CancellationTrack.id == -1)
    total_filtered = query.count()
    rows = query.order_by(CancellationTrack.created_at.desc(), CancellationTrack.id.desc()).offset((page-1)*10).limit(10).all()
    uploads = RegisterUpload.query.order_by(RegisterUpload.period.desc(), RegisterUpload.created_at.desc()).limit(120).all()
    periods = sorted({u.period for u in RegisterUpload.query.all()}, reverse=True)
    counts = {label: CancellationTrack.query.filter_by(classification=label).count() for label in
              ["Matched amount", "Different amount - review as endorsement", "Pure cancellation"]}
    return render_template("cancellation_tracker.html", rows=rows, q=q, status=status, period=period,
                           classification=classification, page=page, pages=max(1,(total_filtered+9)//10),
                           total_filtered=total_filtered, classification_counts=counts,
                           periods=periods, uploads=uploads, current_period=date.today().strftime("%Y-%m"), tra_statuses=CANCEL_TRA_STATUSES,
                           total=total_filtered, unreasoned=CancellationTrack.query.filter(CancellationTrack.cancellation_reason.is_(None)).count(),
                           unsubmitted=CancellationTrack.query.filter_by(tra_status="Not Submitted").count())

@app.route("/cancellation-tracker/upload", methods=["POST"])
def cancellation_tracker_upload():
    if not _tax_required(): return redirect(url_for("home"))
    file = request.files.get("file")
    period = request.form.get("period", "").strip()
    if not period or len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:7].isdigit() or not (1 <= int(period[5:7]) <= 12):
        flash("Select a valid reconciliation month before uploading the Premium Register.", "warning"); return redirect(url_for("cancellation_tracker"))
    if not file or not file.filename:
        flash("Choose the AIMS Premium Register to upload.", "warning"); return redirect(url_for("cancellation_tracker", period=period))
    try:
        source_rows = _register_rows(file)
        positives = {}
        for row in source_rows:
            if row["amount"] > 0: positives.setdefault(row["policy_number"], []).append(row)
        used_positive = set()
        negatives = [r for r in source_rows if r["amount"] < 0]
        batch = datetime.utcnow().strftime("REG-%Y%m%d-%H%M%S-%f")
        imported = []
        duplicate_skipped = 0
        same_policy_alerts = set()
        seen_in_upload = set()
        for neg in negatives:
            candidates = positives.get(neg["policy_number"], [])
            available = [(idx, pos) for idx, pos in enumerate(candidates) if (neg["policy_number"], idx) not in used_positive]
            exact = next(((idx,pos) for idx,pos in available if pos["amount"] == abs(neg["amount"])), None)
            chosen = exact or (min(available, key=lambda pair: abs(pair[1]["amount"]-abs(neg["amount"]))) if available else None)
            if chosen:
                idx, pos = chosen; used_positive.add((neg["policy_number"], idx))
                classification = "Matched amount" if pos["amount"] == abs(neg["amount"]) else "Different amount - review as endorsement"
            else:
                pos = None; classification = "Pure cancellation"
            inferred_type = "Endorsement" if classification.startswith("Different amount") else "Cancellation"
            signature = _case_action_signature(inferred_type, neg["policy_number"], neg["transaction_date"], neg["document_no"], neg["amount"])
            if signature in seen_in_upload:
                duplicate_skipped += 1
                continue
            seen_in_upload.add(signature)
            dup_source, dup_record, related = _find_duplicate_action(inferred_type, neg["policy_number"], neg["transaction_date"], neg["document_no"], neg["amount"])
            if dup_source:
                duplicate_skipped += 1
                continue
            if related:
                same_policy_alerts.add((neg["policy_number"], inferred_type))
            track = CancellationTrack(upload_batch=batch, transaction_date=neg["transaction_date"], document_no=neg["document_no"],
                policy_number=neg["policy_number"], endorsement_no=neg["endorsement_no"], insured_name=neg["insured_name"],
                product=neg["product"], branch_name=neg["branch_name"], transaction_type=neg["transaction_type"],
                negative_amount=neg["amount"], matched_positive_amount=pos["amount"] if pos else 0,
                matched_document_no=pos["document_no"] if pos else None, classification=classification,
                cancellation_reason=None, tra_status="Not Submitted", imported_by=session.get("actor_name", "Tax Compliance"))
            db.session.add(track); imported.append(track)
        if not imported and not duplicate_skipped:
            raise ValueError("No negative premium transactions were found. No cancellation records were created.")
        matched=sum(1 for x in imported if x.classification=="Matched amount")
        different=sum(1 for x in imported if x.classification=="Different amount - review as endorsement")
        pure=sum(1 for x in imported if x.classification=="Pure cancellation")
        upload = RegisterUpload(upload_batch=batch, period=period, file_name=secure_filename(file.filename)[:255] or "Premium Register",
            source_rows=len(source_rows), negative_count=len(imported), matched_count=matched, different_count=different,
            pure_count=pure, uploaded_by=session.get("actor_name", "Tax Compliance"))
        db.session.add(upload); db.session.commit()
        summary = f"{period} register saved: {len(source_rows)} transactions; {len(imported)} new negative-premium tracking record(s). Exact matches: {matched}; different positive amounts: {different}; pure cancellations: {pure}. Monthly upload retained in history."
        if duplicate_skipped:
            summary += f" DUPLICATE ALERT: {duplicate_skipped} record(s) were skipped because the same policy/action/date/document/amount is already tracked in CETTP or an earlier register upload."
        if same_policy_alerts:
            sample = ", ".join(f"{policy} ({kind})" for policy, kind in sorted(same_policy_alerts)[:8])
            summary += f" POLICY REVIEW ALERT: related actions already exist for {len(same_policy_alerts)} policy/action combination(s): {sample}. Different documents, dates or amounts were retained for review."
        flash(summary, "warning" if duplicate_skipped or same_policy_alerts else "success")
    except Exception as exc:
        db.session.rollback(); flash(f"Premium Register upload failed: {exc}", "danger")
    return redirect(url_for("cancellation_tracker", period=period))

@app.route("/cancellation-tracker/<int:item_id>/delete", methods=["POST"])
def cancellation_tracker_delete(item_id):
    if not _tax_required(): return redirect(url_for("home"))
    row = CancellationTrack.query.get_or_404(item_id)
    period = next((u.period for u in RegisterUpload.query.filter_by(upload_batch=row.upload_batch).all()), "")
    db.session.delete(row)
    db.session.commit()
    flash(f"Tracking record #{item_id} deleted.", "success")
    return redirect(url_for("cancellation_tracker", period=period))

@app.route("/cancellation-tracker/batch/<int:upload_id>/delete", methods=["POST"])
def cancellation_tracker_delete_batch(upload_id):
    """Delete one Premium Register upload and its tracker rows atomically.

    Deliberately retain Case records: a tracker row may point to a case that is
    also referenced by another batch, and cases are part of the formal CETTP
    workflow/audit history. Removing a batch must never delete an Initiator case
    or a case shared by another upload.
    """
    if not _tax_required():
        return redirect(url_for("home"))

    upload = RegisterUpload.query.get_or_404(upload_id)
    batch = upload.upload_batch
    period = upload.period
    filename = upload.file_name

    try:
        # Use a database-side DELETE scoped to the unique upload_batch value.
        # This works consistently on PostgreSQL and SQLite and avoids ORM
        # relationship state / stale loaded-object issues during bulk deletion.
        result = db.session.execute(
            delete(CancellationTrack).where(CancellationTrack.upload_batch == batch),
            execution_options={"synchronize_session": False},
        )
        deleted_tracker_rows = result.rowcount if result.rowcount is not None else 0
        # Execute the child-row deletion before removing the upload record. The
        # database enforces cancellation_track.case_id -> case.id; Cases remain.
        db.session.flush()

        # Do not delete linked Case rows here. They may be shared with another
        # register batch and carry audit logs, attachments and notifications.
        db.session.delete(upload)
        db.session.commit()

        logger.info(
            "Premium Register batch deleted: upload_id=%s batch=%s period=%s "
            "tracker_rows=%s actor=%s; linked CETTP cases retained",
            upload_id, batch, period, deleted_tracker_rows,
            session.get("actor_name", "Tax Compliance"),
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "Premium Register batch deletion failed: upload_id=%s batch=%s period=%s",
            upload_id, batch, period,
        )
        # Keep the message generic; the full exception is available in Render logs.
        error_code = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        flash(
            f"Batch deletion was not completed. No changes were saved. "
            f"Reference: {error_code}. Please provide this reference to the system administrator.",
            "danger",
        )
        return redirect(url_for("cancellation_tracker", period=period))

    flash(
        f"Deleted upload batch '{filename}' for {period}, including "
        f"{deleted_tracker_rows} tracking record(s). Existing CETTP cases and their "
        f"audit history were retained.",
        "success",
    )
    return redirect(url_for("cancellation_tracker", period=period))

@app.route("/cancellation-tracker/<int:item_id>/update", methods=["POST"])
def cancellation_tracker_update(item_id):
    if not _tax_required(): return redirect(url_for("home"))
    row = CancellationTrack.query.get_or_404(item_id)
    reason = request.form.get("cancellation_reason", "").strip()
    status = request.form.get("tra_status", "Not Submitted").strip()
    classification = request.form.get("classification", row.classification).strip()
    allowed_classifications = {"Matched amount", "Different amount - review as endorsement", "Pure cancellation"}
    tra_ref = request.form.get("tra_reference", "").strip()
    if status not in CANCEL_TRA_STATUSES:
        flash("Invalid TRA status selected.", "danger")
    elif classification not in allowed_classifications:
        flash("Invalid classification selected.", "danger")
    else:
        row.classification = classification
        row.cancellation_reason = reason[:4000] or None
        row.tra_status = status; row.tra_reference = tra_ref[:120] or None
        if row.case_id:
            case = db.session.get(Case, row.case_id)
            if case:
                case.reason = row.cancellation_reason; case.tra_status = status; case.tra_reference = row.tra_reference
                case.tax_notes = (case.tax_notes or "") + f"\\nPremium Register tracker updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}."
                log_action(case, "Register cancellation tracking updated", f"Reason updated; TRA status: {status}")
        db.session.commit(); flash("Cancellation tracking record updated.", "success")
    return redirect(url_for("cancellation_tracker"))

@app.route("/cancellation-tracker/import-to-cettp", methods=["POST"])
def cancellation_tracker_import_to_cettp():
    if not _tax_required(): return redirect(url_for("home"))
    selected = request.form.getlist("item_ids")
    selected_classification = request.form.get("import_classification", "").strip()
    query = CancellationTrack.query.filter(CancellationTrack.case_id.is_(None))
    if selected_classification in {"Matched amount", "Different amount - review as endorsement", "Pure cancellation"}:
        query = query.filter_by(classification=selected_classification)
    if selected:
        try: ids=[int(x) for x in selected]
        except ValueError: ids=[]
        query=query.filter(CancellationTrack.id.in_(ids))
    rows=query.order_by(CancellationTrack.id.asc()).all()
    if not rows:
        flash("No unimported records were selected. Select records or use Auto-fill all unimported records.", "warning")
        return redirect(url_for("cancellation_tracker"))
    created=0
    duplicate_skipped=0
    for row in rows:
        case_type = "Endorsement" if row.classification.startswith("Different amount") else "Cancellation"
        effective = row.transaction_date or date.today()
        dup_source, dup_record, related = _find_duplicate_action(case_type, row.policy_number, effective, row.document_no, row.negative_amount, exclude_tracker_id=row.id)
        if dup_source:
            # Link the register row to the already existing CETTP case where possible,
            # so the same action is not imported as a second case.
            if dup_source == "case": row.case_id = dup_record.id
            duplicate_skipped += 1
            continue
        case = Case(reference=make_reference(), case_type=case_type, policy_number=row.policy_number,
            customer_name=row.insured_name or "Insured name not provided", customer_tin=None, product=row.product,
            branch=row.branch_name, underwriter=None,
            reason=row.cancellation_reason or "REASON REQUIRED — Tax Compliance to complete before TRA submission.",
            effective_date=effective, original_invoice_no=row.matched_document_no or row.document_no,
            original_invoice_amount=abs(row.matched_positive_amount) if row.matched_positive_amount else 0,
            adjustment_amount=row.negative_amount, vat_amount=0, initiator_name="Premium Register Import",
            tra_status=row.tra_status, tra_reference=row.tra_reference,
            workflow_status="Initiated")
        db.session.add(case); db.session.flush(); row.case_id=case.id
        log_action(case, "Imported from Premium Register", f"Classification: {row.classification}; negative premium {row.negative_amount}; positive match {row.matched_positive_amount}")
        created+=1
    db.session.commit()
    message = f"Imported {created} cancellation/endorsement record(s) into the CETTP case workflow. Records without reasons remain flagged for completion."
    if duplicate_skipped:
        message += f" DUPLICATE ALERT: {duplicate_skipped} already tracked action(s) were not imported again; existing CETTP cases were linked where available."
    flash(message, "warning" if duplicate_skipped else "success")
    return redirect(url_for("cancellation_tracker"))

@app.route("/cancellation-tracker/export.xlsx")
def cancellation_tracker_export():
    if not _tax_required(): return redirect(url_for("home"))
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    period = request.args.get("period", "").strip()
    query = CancellationTrack.query
    if period:
        batches = [u.upload_batch for u in RegisterUpload.query.filter_by(period=period).all()]
        query = query.filter(CancellationTrack.upload_batch.in_(batches)) if batches else query.filter(CancellationTrack.id == -1)
    rows=query.order_by(CancellationTrack.policy_number.asc(), CancellationTrack.transaction_date.asc()).all()
    period_by_batch = {u.upload_batch: u.period for u in RegisterUpload.query.all()}
    wb=Workbook(); ws=wb.active; ws.title="Cancellation Tracker"
    ws.append(["Reporting month", period or "All months"])
    ws.append([])
    headers=["Reporting Month","Tracker ID","Transaction Date","Document No.","Policy No.","Endorsement No.","Insured Name","Product","Branch","Transaction Type","Negative Premium (TZS)","Matched Positive Premium (TZS)","Matched Positive Document No.","Classification","Cancellation / Endorsement Reason","TRA Status","TRA Reference","CETTP Case Reference","Imported By","Created At"]
    ws.append(headers)
    for r in rows:
        ws.append([period_by_batch.get(r.upload_batch, "Legacy / Unknown"), r.id, r.transaction_date, r.document_no, r.policy_number, r.endorsement_no, r.insured_name, r.product, r.branch_name, r.transaction_type, float(r.negative_amount or 0), float(r.matched_positive_amount or 0), r.matched_document_no, r.classification, r.cancellation_reason, r.tra_status, r.tra_reference, r.case.reference if r.case else None, r.imported_by, r.created_at])
    for cell in ws[3]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="123B63"); cell.alignment=Alignment(wrap_text=True,vertical="center")
    ws.freeze_panes="A4"; ws.auto_filter.ref=f"A3:{get_column_letter(ws.max_column)}{ws.max_row}"
    for col in ws.columns:
        width=max(12,min(34,max(len(str(c.value or "")) for c in col)+2)); ws.column_dimensions[get_column_letter(col[0].column)].width=width
    for row in ws.iter_rows(min_row=4):
        for cell in row:
            if cell.column in (3,20) and cell.value: cell.number_format="yyyy-mm-dd hh:mm" if cell.column==20 else "yyyy-mm-dd"
            if cell.column in (11,12) and cell.value is not None: cell.number_format='#,##0.00;[Red](#,##0.00)'
    out=io.BytesIO(); wb.save(out); out.seek(0)
    return send_file(out,mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",as_attachment=True,download_name=(f"Britam_Cancellation_Endorsement_Tracker_{period}.xlsx" if period else "Britam_Cancellation_Endorsement_Tracker_All_Months.xlsx"))

@app.route("/cancellation-tracker/template.csv")
def cancellation_tracker_template():
    if not _tax_required(): return redirect(url_for("home"))
    headers=["TRANSACTION DATE","NO","CLASS","PRODUCT","PERIOD","POLICY NO","ENDORSEMENT NO","TOTAL","TRANSACTION TYPE","OLD POLICY RENEWAL","OLD POLICY NO","BUSINESS TYPE","CLASSIFICATION","NAME OF INSURED","BRANCH","BRANCH NAME","INTERMEDIARY CODE","INTERMEDIARY NAME","CHANNEL","EFFECTIVE DATE","PERIOD FROM","EXPIRING","CURRENCY","CURRENCY RATE","SUM INSURED","EFFECTIVE SUM INSURED","GROSS PREMIUM","AMT","NETT PREMIUM","COMM AMT","PREMIUM STATUS"]
    out=io.StringIO(); csv.writer(out).writerow(headers); data=io.BytesIO(out.getvalue().encode("utf-8-sig")); data.seek(0)
    return send_file(data,mimetype="text/csv",as_attachment=True,download_name="AIMS_Premium_Register_import_template.csv")


# ---------------------------------------------------------------------------
# Tax Compliance Calendar & Monitoring
# ---------------------------------------------------------------------------
TAX_DEADLINE_STATUSES = ["Upcoming", "In Progress", "Pending Review", "Filed - Payment Pending", "Completed", "Not Applicable"]
TAX_DEADLINE_TYPES = ["TRA VAT", "ZRA VAT", "VAT", "PAYE", "SDL", "WHT", "Corporate Income Tax", "Tax Audit", "Tax Objection", "Tax Appeal", "Demand Notice", "TRA Verification", "Transfer Pricing", "Insurance Regulatory", "Other"]
TAX_DEADLINE_ACTIVITIES = ["Filing", "Payment", "Notification received", "Information request", "Response to information request", "Response to audit findings", "Exit meeting", "Objection filing", "Appeal filing", "Demand notice response", "Hearing", "Follow-up", "Other milestone"]
RECURRING_DEADLINE_OWNER = "SYSTEM - RECURRING SCHEDULE"
TAX_DEADLINE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "doc", "docx", "csv"}

def _month_label(year, month):
    return date(year, month, 1).strftime("%B %Y")


def _ensure_recurring_tax_deadlines():
    """Create the configured monthly/annual schedule once; officers update each generated record."""
    today = date.today()
    start_year = today.year
    end_year = today.year + 1
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            due_month = date(year, month, 1)
            prior_month = 12 if month == 1 else month - 1
            prior_year = year - 1 if month == 1 else year
            period = _month_label(prior_year, prior_month)
            monthly = [("WHT", 7), ("PAYE", 7), ("SDL", 7), ("TRA VAT", 20), ("ZRA VAT", 20)]
            for tax_type, day in monthly:
                due = date(year, month, day)
                obligation = f"{tax_type} Return"
                # Upgrade V2.5 generic recurring VAT records to TRA VAT; ZRA VAT is generated separately.
                if tax_type == "TRA VAT":
                    legacy_vat = TaxDeadline.query.filter_by(obligation="VAT Return", tax_type="VAT", activity="Filing", period=period, due_date=due, created_by=RECURRING_DEADLINE_OWNER).first()
                    if legacy_vat:
                        legacy_vat.obligation = "TRA VAT Return"
                        legacy_vat.tax_type = "TRA VAT"
                exists = TaxDeadline.query.filter_by(obligation=obligation, tax_type=tax_type,
                    activity="Filing", period=period, due_date=due,
                    created_by=RECURRING_DEADLINE_OWNER).first()
                if not exists:
                    db.session.add(TaxDeadline(obligation=obligation, tax_type=tax_type,
                        activity="Filing", period=period, due_date=due,
                        status="Upcoming", created_by=RECURRING_DEADLINE_OWNER,
                        notes="System-generated recurring deadline. Update status and attach filing/payment evidence."))
        # Annual corporate income tax return and provisional return.
        annual_items = [
            ("Corporate Income Tax - Annual Return", "Corporate Income Tax", "Filing", date(year, 6, 30), f"Year {year - 1}"),
            ("Corporate Income Tax - Provisional Return", "Corporate Income Tax", "Filing", date(year, 3, 31), f"Year {year}"),
        ]
        for quarter, due in [("Q1", date(year, 3, 31)), ("Q2", date(year, 6, 30)), ("Q3", date(year, 9, 30)), ("Q4", date(year, 12, 31))]:
            annual_items.append((f"Corporate Income Tax - Instalment ({quarter})", "Corporate Income Tax", "Payment", due, f"{year} {quarter}"))
        for obligation, tax_type, activity, due, period in annual_items:
            exists = TaxDeadline.query.filter_by(obligation=obligation, tax_type=tax_type,
                activity=activity, period=period, due_date=due,
                created_by=RECURRING_DEADLINE_OWNER).first()
            if not exists:
                db.session.add(TaxDeadline(obligation=obligation, tax_type=tax_type,
                    activity=activity, period=period, due_date=due, status="Upcoming",
                    created_by=RECURRING_DEADLINE_OWNER,
                    notes="System-generated recurring deadline. Confirm statutory applicability and update status/evidence."))
    db.session.commit()


def _tax_calendar_required():
    if session.get("role") != "tax":
        return False
    return True

def _deadline_audit(item, action, details=""):
    db.session.add(TaxDeadlineAudit(deadline_id=item.id, actor=(session.get("actor_name") or "Tax Compliance")[:120], action=action, details=details[:4000]))

def _deadline_status(item, today=None):
    today = today or date.today()
    if item.status not in ("Completed", "Not Applicable") and item.due_date < today:
        return "Overdue"
    return item.status

@app.route("/tax-calendar")
def tax_calendar():
    if not _tax_calendar_required(): return redirect(url_for("home"))
    _ensure_recurring_tax_deadlines()
    today = date.today()
    # Show one selected month at a time; default to the current month.
    try:
        selected_year = int(request.args.get("year", today.year))
        selected_month = int(request.args.get("month", today.month))
        if selected_month < 1 or selected_month > 12: raise ValueError
        month_start = date(selected_year, selected_month, 1)
    except (TypeError, ValueError):
        selected_year, selected_month = today.year, today.month
        month_start = date(selected_year, selected_month, 1)
    next_month = date(selected_year + (1 if selected_month == 12 else 0), 1 if selected_month == 12 else selected_month + 1, 1)
    prev_month = date(selected_year - (1 if selected_month == 1 else 0), 12 if selected_month == 1 else selected_month - 1, 1)
    q = TaxDeadline.query.filter(TaxDeadline.due_date >= month_start, TaxDeadline.due_date < next_month)
    selected_status = request.args.get("status", "").strip()
    selected_type = request.args.get("tax_type", "").strip()
    if selected_type: q = q.filter_by(tax_type=selected_type)
    if selected_status == "Overdue":
        q = q.filter(TaxDeadline.due_date < today, TaxDeadline.status.notin_(["Completed", "Not Applicable"]))
    elif selected_status: q = q.filter_by(status=selected_status)
    rows = q.order_by(TaxDeadline.due_date.asc(), TaxDeadline.obligation.asc()).all()
    month_rows = TaxDeadline.query.filter(TaxDeadline.due_date >= month_start, TaxDeadline.due_date < next_month).all()
    counts = {
        "upcoming": sum(1 for x in month_rows if x.due_date >= today and x.due_date <= today + timedelta(days=7) and x.status not in ("Completed", "Not Applicable")),
        "today": sum(1 for x in month_rows if x.due_date == today and x.status not in ("Completed", "Not Applicable")),
        "overdue": sum(1 for x in month_rows if x.due_date < today and x.status not in ("Completed", "Not Applicable")),
        "pending": sum(1 for x in month_rows if x.status == "Filed - Payment Pending"),
        "completed": sum(1 for x in month_rows if x.status == "Completed"),
    }
    return render_template("tax_calendar.html", deadlines=rows, counts=counts, today=today,
        statuses=TAX_DEADLINE_STATUSES, tax_types=TAX_DEADLINE_TYPES,
        selected_status=selected_status, selected_type=selected_type, deadline_status=_deadline_status,
        selected_year=selected_year, selected_month=selected_month, month_label=month_start.strftime("%B %Y"),
        prev_year=prev_month.year, prev_month=prev_month.month, next_year=next_month.year, next_month=next_month.month)

@app.route("/tax-calendar/new", methods=["GET", "POST"])
def tax_deadline_new():
    if not _tax_calendar_required(): return redirect(url_for("home"))
    if request.method == "POST":
        try:
            due = date.fromisoformat(request.form.get("due_date", ""))
        except ValueError:
            flash("Please enter a valid due date.", "danger")
            return render_template("tax_deadline_form.html", item=None, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)
        obligation = request.form.get("obligation", "").strip()
        period = request.form.get("period", "").strip()
        tax_type = request.form.get("tax_type", "Other").strip()
        activity = request.form.get("activity", "Filing").strip()
        status = request.form.get("status", "Upcoming").strip()
        if not obligation or not period or tax_type not in TAX_DEADLINE_TYPES or activity not in TAX_DEADLINE_ACTIVITIES or status not in TAX_DEADLINE_STATUSES:
            flash("Complete all required fields using the available options.", "danger")
            return render_template("tax_deadline_form.html", item=None, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)
        item = TaxDeadline(obligation=obligation[:140], tax_type=tax_type, activity=activity, period=period[:30], due_date=due,
            assigned_to=request.form.get("assigned_to", "").strip()[:120] or None, status=status,
            completed_date=(date.fromisoformat(request.form["completed_date"]) if request.form.get("completed_date") else None),
            payment_amount=(Decimal(request.form["payment_amount"]) if request.form.get("payment_amount") else None),
            control_number=request.form.get("control_number", "").strip()[:100] or None,
            notes=request.form.get("notes", "").strip(), created_by=(session.get("actor_name") or "Tax Compliance")[:120])
        db.session.add(item); db.session.flush(); _deadline_audit(item, "Created", f"Obligation created with due date {due.isoformat()}.")
        db.session.commit(); flash("Tax obligation added to the compliance calendar.", "success")
        return redirect(url_for("tax_calendar"))
    return render_template("tax_deadline_form.html", item=None, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)

@app.route("/tax-calendar/<int:deadline_id>/edit", methods=["GET", "POST"])
def tax_deadline_edit(deadline_id):
    if not _tax_calendar_required(): return redirect(url_for("home"))
    item = TaxDeadline.query.get_or_404(deadline_id)
    if request.method == "POST":
        try: due = date.fromisoformat(request.form.get("due_date", ""))
        except ValueError:
            flash("Please enter a valid due date.", "danger")
            return render_template("tax_deadline_form.html", item=item, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)
        old_due, old_status = item.due_date, item.status
        old_assignee = item.assigned_to
        if item.created_by != RECURRING_DEADLINE_OWNER:
            item.obligation=request.form.get("obligation", "").strip()[:140]
            item.tax_type=request.form.get("tax_type", "Other").strip()
            item.activity=request.form.get("activity", "Other milestone").strip()
            item.period=request.form.get("period", "").strip()[:30]
            item.due_date=due
        else:
            # Recurring statutory dates are schedule-controlled; officers update progress and evidence only.
            due = item.due_date
        item.assigned_to=request.form.get("assigned_to", "").strip()[:120] or None
        item.status=request.form.get("status", "Upcoming").strip()
        item.completed_date=date.fromisoformat(request.form["completed_date"]) if request.form.get("completed_date") else None
        item.payment_amount=Decimal(request.form["payment_amount"]) if request.form.get("payment_amount") else None
        item.control_number=request.form.get("control_number", "").strip()[:100] or None
        item.notes=request.form.get("notes", "").strip()
        if not item.obligation or not item.period or item.tax_type not in TAX_DEADLINE_TYPES or item.activity not in TAX_DEADLINE_ACTIVITIES or item.status not in TAX_DEADLINE_STATUSES:
            flash("Please check the required fields.", "danger")
            return render_template("tax_deadline_form.html", item=item, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)
        changes=[]
        if old_due != due: changes.append(f"Due date: {old_due} → {due}")
        if old_status != item.status: changes.append(f"Status: {old_status} → {item.status}")
        if old_assignee != item.assigned_to: changes.append(f"Assigned to: {old_assignee or 'Unassigned'} → {item.assigned_to or 'Unassigned'}")
        _deadline_audit(item, "Updated", "; ".join(changes) or "Obligation details updated.")
        db.session.commit(); flash("Obligation updated successfully.", "success")
        return redirect(url_for("tax_calendar_detail", deadline_id=item.id))
    return render_template("tax_deadline_form.html", item=item, tax_types=TAX_DEADLINE_TYPES, statuses=TAX_DEADLINE_STATUSES, activities=TAX_DEADLINE_ACTIVITIES)

@app.route("/tax-calendar/<int:deadline_id>/delete", methods=["POST"])
def tax_deadline_delete(deadline_id):
    if not _tax_calendar_required():
        return redirect(url_for("home"))
    item = TaxDeadline.query.get_or_404(deadline_id)
    if item.created_by == RECURRING_DEADLINE_OWNER:
        flash("System-generated recurring deadlines cannot be deleted from the calendar.", "warning")
        return redirect(url_for("tax_calendar"))
    obligation = item.obligation
    db.session.delete(item)
    db.session.commit()
    flash(f'Manual deadline "{obligation}" deleted successfully.', "success")
    return redirect(url_for("tax_calendar"))

@app.route("/tax-calendar/<int:deadline_id>")
def tax_calendar_detail(deadline_id):
    if not _tax_calendar_required(): return redirect(url_for("home"))
    item=TaxDeadline.query.get_or_404(deadline_id)
    return render_template("tax_deadline_detail.html", item=item, deadline_status=_deadline_status)

@app.route("/tax-calendar/<int:deadline_id>/attachments", methods=["POST"])
def tax_deadline_attachment(deadline_id):
    if not _tax_calendar_required(): return redirect(url_for("home"))
    item=TaxDeadline.query.get_or_404(deadline_id)
    f=request.files.get("document")
    if not f or not f.filename:
        flash("Choose a document to upload.", "warning"); return redirect(url_for("tax_calendar_detail", deadline_id=item.id))
    filename=secure_filename(f.filename)
    ext=filename.rsplit(".",1)[-1].lower() if "." in filename else ""
    data=f.read()
    if ext not in TAX_DEADLINE_EXTENSIONS or len(data)>MAX_ATTACHMENT_BYTES:
        flash("Unsupported file type or file exceeds the 12 MB limit.", "danger"); return redirect(url_for("tax_calendar_detail", deadline_id=item.id))
    db.session.add(TaxDeadlineAttachment(deadline_id=item.id, filename=filename[:255], content_type=f.mimetype or "application/octet-stream", file_size=len(data), file_data=data, uploaded_by=(session.get("actor_name") or "Tax Compliance")[:120]))
    _deadline_audit(item, "Evidence uploaded", filename)
    db.session.commit(); flash("Supporting document uploaded.", "success")
    return redirect(url_for("tax_calendar_detail", deadline_id=item.id))

@app.route("/tax-calendar/attachments/<int:attachment_id>/download")
def tax_deadline_attachment_download(attachment_id):
    if not _tax_calendar_required(): return redirect(url_for("home"))
    a=TaxDeadlineAttachment.query.get_or_404(attachment_id)
    return send_file(BytesIO(a.file_data), as_attachment=True, download_name=a.filename, mimetype=a.content_type)

@app.route("/tax-calendar/export.csv")
def tax_calendar_export():
    if not _tax_calendar_required(): return redirect(url_for("home"))
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(["Obligation", "Tax Type", "Activity", "Period", "Due Date", "Assigned To", "Status", "Completed Date", "Payment Amount (TZS)", "Control Number", "Notes"])
    for x in TaxDeadline.query.order_by(TaxDeadline.due_date.asc()).all():
        writer.writerow([x.obligation,x.tax_type,x.activity,x.period,x.due_date,x.assigned_to or "",_deadline_status(x),x.completed_date or "",x.payment_amount or "",x.control_number or "",x.notes or ""])
    return send_file(BytesIO(output.getvalue().encode("utf-8-sig")), mimetype="text/csv", as_attachment=True, download_name=f"tax_compliance_calendar_{date.today().isoformat()}.csv")


# ---------------------------------------------------------------------------
# Investment WHT Credits – Tax Compliance Workspace
INVESTMENT_WHT_RATE = Decimal("10.00")

def _investment_local_today():
    return datetime.now(ZoneInfo("Africa/Dar_es_Salaam")).date()

INVESTMENT_WHT_TEMPLATE_HEADERS = [
    "Bank Name", "TIN Number", "Amount Invested", "Nature of Investment", "From",
    "Matured Date", "Rate", "Expected WHT (10%)", "Actual WHT remitted to TRA",
    "Confirmed Expected Interest (Optional)", "WHT Certificate Reference (Optional)",
    "WHT Certificate Date (Optional)", "Notes (Optional)",
]


def _investment_wht_calculation(principal, annual_rate, start_date, maturity_date, confirmed_interest=None):
    principal = Decimal(str(principal))
    annual_rate = Decimal(str(annual_rate))
    days = (maturity_date - start_date).days
    if days <= 0:
        raise ValueError("Matured Date must be later than the From date.")
    calculated_interest = (principal * annual_rate / Decimal("100") * Decimal(days) / Decimal("365")).quantize(Decimal("0.01"))
    taxable_interest = Decimal(str(confirmed_interest)) if confirmed_interest not in (None, "") else calculated_interest
    if taxable_interest < 0:
        raise ValueError("Confirmed expected interest cannot be negative.")
    expected_wht = (taxable_interest * INVESTMENT_WHT_RATE / Decimal("100")).quantize(Decimal("0.01"))
    return days, calculated_interest, expected_wht


def _investment_duplicate_key(bank_tin, principal, nature, start_date, maturity_date):
    raw = "|".join([str(bank_tin).strip(), str(Decimal(str(principal)).quantize(Decimal("0.01"))),
                    str(nature).strip().lower(), start_date.isoformat(), maturity_date.isoformat()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _investment_wht_send_email(item, event_key, event_date, subject, body):
    recipients_raw = os.environ.get("CETTP_INVESTMENT_WHT_EMAIL", os.environ.get("CETTP_TAX_COMPLIANCE_EMAIL", ""))
    recipients = [x.strip() for x in recipients_raw.replace(";", ",").split(",") if x.strip()]
    recipient_label = ", ".join(recipients) if recipients else "NOT_CONFIGURED"
    existing = InvestmentWHTEmailLog.query.filter_by(investment_id=item.id, event_key=event_key, event_date=event_date).first()
    if existing and existing.status == "sent":
        return True
    if existing is None:
        existing = InvestmentWHTEmailLog(investment_id=item.id, event_key=event_key, event_date=event_date,
            recipient=recipient_label, status="pending")
        db.session.add(existing)
        db.session.flush()
    if not recipients:
        existing.status = "not_configured"
        existing.error_message = "Set CETTP_INVESTMENT_WHT_EMAIL or CETTP_TAX_COMPLIANCE_EMAIL."
        db.session.commit()
        return False
    try:
        _deliver_portal_email(recipients, subject, body)
        existing.status = "sent"; existing.sent_at = datetime.utcnow(); existing.error_message = None
        db.session.commit()
        return True
    except Exception as exc:
        existing.status = "failed"; existing.error_message = str(exc)[:1900]
        db.session.commit()
        logger.exception("Investment WHT email failed for investment %s", item.id)
        return False


@app.route("/tax-email/test", methods=["POST"])
def tax_email_test():
    if not _tax_required(): return redirect(url_for("home"))
    recipients = _notification_recipients()
    try:
        cfg = _smtp_settings()
        _deliver_portal_email(recipients, "Britam CETTP – Email configuration test",
            "This is a test notification from Britam CETTP. Central email delivery is configured successfully.")
        logger.info("CETTP SMTP test email sent to %s via %s", ", ".join(recipients), cfg["host"])
        flash("Test email sent successfully to the configured notification recipients.", "success")
    except Exception as exc:
        logger.exception("CETTP SMTP test failed")
        flash(f"Email test failed: {type(exc).__name__}: {str(exc)[:300]}", "danger")
    return redirect(request.referrer or url_for("tax_investment_wht"))


@app.route("/tax-investment-wht")
def tax_investment_wht():
    if not _tax_required(): return redirect(url_for("home"))
    rows = InvestmentWHT.query.order_by(InvestmentWHT.maturity_date.asc(), InvestmentWHT.bank_name.asc()).all()
    batches = InvestmentWHTBatch.query.order_by(InvestmentWHTBatch.uploaded_at.desc()).all()
    email_logs = PortalEmailLog.query.order_by(PortalEmailLog.created_at.desc()).limit(50).all()
    today = _investment_local_today()
    upcoming = [x for x in rows if today <= x.maturity_date <= today + timedelta(days=30)]
    matured_outstanding = [x for x in rows if x.maturity_date < today and x.outstanding_wht > 0]
    total_expected = sum((Decimal(x.expected_wht or 0) for x in rows), Decimal("0.00"))
    total_actual = sum((Decimal(x.actual_wht or 0) for x in rows), Decimal("0.00"))
    total_outstanding = sum((x.outstanding_wht for x in rows), Decimal("0.00"))
    return render_template("tax_investment_wht.html", investments=rows, upcoming_count=len(upcoming),
        matured_outstanding_count=len(matured_outstanding), total_expected=total_expected,
        total_actual=total_actual, total_outstanding=total_outstanding, today=today, batches=batches, email_logs=email_logs)


@app.route("/tax-investment-wht/template.xlsx")
def tax_investment_wht_template():
    if not _tax_required(): return redirect(url_for("home"))
    wb = Workbook(); ws = wb.active; ws.title = "Investment WHT Upload"
    ws.append(INVESTMENT_WHT_TEMPLATE_HEADERS)
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="123B63"); c.alignment = Alignment(wrap_text=True)
    ws.freeze_panes = "A2"; ws.auto_filter.ref = f"A1:N{ws.max_row}"
    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(34, max(16, max(len(str(c.value or "")) for c in col) + 2))
    for row in ws.iter_rows(min_row=2):
        for idx in (5, 6, 12): row[idx-1].number_format = "yyyy-mm-dd"
        for idx in (3, 8, 9, 10): row[idx-1].number_format = '#,##0.00;[Red](#,##0.00)'
    out = BytesIO(); wb.save(out); out.seek(0)
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="Britam_Investment_WHT_Batch_Template.xlsx")


@app.route("/tax-investment-wht/upload", methods=["POST"])
def tax_investment_wht_upload():
    if not _tax_required(): return redirect(url_for("home"))
    file = request.files.get("investment_file")
    if not file or not file.filename or not file.filename.lower().endswith(".xlsx"):
        flash("Upload an Excel .xlsx investment register.", "danger"); return redirect(url_for("tax_investment_wht"))
    try:
        wb = load_workbook(file, data_only=True, read_only=True)
        ws = wb.active
        headers = [str(c.value or "").strip() for c in ws[1]]
        required = INVESTMENT_WHT_TEMPLATE_HEADERS[:9]
        if any(h not in headers for h in required):
            raise ValueError("The workbook is missing required columns. Download and use the CETTP template.")
        positions = {h: headers.index(h) for h in headers if h}
        def val(values, name, default=None):
            idx = positions.get(name)
            return values[idx] if idx is not None and idx < len(values) else default
        batch = InvestmentWHTBatch(filename=secure_filename(file.filename)[:255] or "investment_upload.xlsx",
            uploaded_by=(session.get("actor_name") or "Tax Compliance")[:120])
        db.session.add(batch); db.session.flush()
        imported = skipped = source_rows = 0
        for row_num, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not values or not any(v not in (None, "") for v in values): continue
            source_rows += 1
            # Ignore the illustrative template row unless replaced with actual investment details.
            bank = str(val(values, "Bank Name", "") or "").strip()
            tin = str(val(values, "TIN Number", "") or "").strip()
            if not bank or not tin: raise ValueError(f"Row {row_num}: Bank Name and TIN Number are required.")
            principal = _amount(val(values, "Amount Invested"))
            rate = _amount(val(values, "Rate"))
            nature = str(val(values, "Nature of Investment", "Fixed Deposit") or "Fixed Deposit").strip()
            start_raw, maturity_raw = val(values, "From"), val(values, "Matured Date")
            def to_date(v):
                if isinstance(v, datetime): return v.date()
                if isinstance(v, date): return v
                return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
            start_date, maturity_date = to_date(start_raw), to_date(maturity_raw)
            if principal <= 0: raise ValueError(f"Row {row_num}: Amount Invested must be greater than zero.")
            if rate < 0 or rate > 100: raise ValueError(f"Row {row_num}: Rate must be between 0 and 100.")
            confirmed = val(values, "Confirmed Expected Interest (Optional)")
            if confirmed in (None, ""): confirmed = None
            elif Decimal(str(confirmed)) < 0: raise ValueError(f"Row {row_num}: Confirmed interest cannot be negative.")
            _, calculated, expected = _investment_wht_calculation(principal, rate, start_date, maturity_date, confirmed)
            duplicate_key = _investment_duplicate_key(tin, principal, nature, start_date, maturity_date)
            if InvestmentWHT.query.filter_by(duplicate_key=duplicate_key).first(): skipped += 1; continue
            actual = _amount(val(values, "Actual WHT remitted to TRA", 0) or 0)
            if actual < 0: raise ValueError(f"Row {row_num}: Actual WHT cannot be negative.")
            item = InvestmentWHT(bank_name=bank[:180], bank_tin=tin[:40], amount_invested=principal,
                nature=nature[:80], start_date=start_date, maturity_date=maturity_date, annual_rate=rate,
                calculated_interest=calculated, confirmed_interest=confirmed, expected_wht=expected,
                actual_wht=actual, wht_rate=INVESTMENT_WHT_RATE,
                certificate_reference=(str(val(values, "WHT Certificate Reference (Optional)", "") or "").strip() or None),
                certificate_date=(to_date(val(values, "WHT Certificate Date (Optional)")) if val(values, "WHT Certificate Date (Optional)") else None),
                notes=(str(val(values, "Notes (Optional)", "") or "").strip() or None),
                batch_id=batch.id, duplicate_key=duplicate_key, created_by=(session.get("actor_name") or "Tax Compliance")[:120])
            db.session.add(item); imported += 1
        batch.source_rows = source_rows; batch.imported_rows = imported; batch.skipped_rows = skipped
        db.session.commit()
        flash(f"Investment upload completed: {imported} imported, {skipped} exact duplicate(s) skipped from {source_rows} data row(s).", "success")
    except Exception as exc:
        db.session.rollback(); logger.exception("Investment WHT batch upload failed")
        flash(f"Investment upload failed. No records from this batch were saved: {exc}", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/add", methods=["POST"])
def tax_investment_wht_add():
    if not _tax_required(): return redirect(url_for("home"))
    try:
        bank = request.form.get("bank_name", "").strip(); tin = request.form.get("bank_tin", "").strip()
        principal = _amount(request.form.get("amount_invested")); rate = _amount(request.form.get("annual_rate"))
        nature = request.form.get("nature", "Fixed Deposit").strip()
        start_date = datetime.strptime(request.form.get("start_date", ""), "%Y-%m-%d").date()
        maturity_date = datetime.strptime(request.form.get("maturity_date", ""), "%Y-%m-%d").date()
        confirmed_raw = request.form.get("confirmed_interest", "").strip()
        confirmed = _amount(confirmed_raw) if confirmed_raw else None
        if not bank or not tin: raise ValueError("Bank Name and TIN Number are required.")
        if principal <= 0 or rate < 0 or rate > 100: raise ValueError("Enter a positive principal and a valid annual rate between 0 and 100.")
        _, calculated, expected = _investment_wht_calculation(principal, rate, start_date, maturity_date, confirmed)
        key = _investment_duplicate_key(tin, principal, nature, start_date, maturity_date)
        if InvestmentWHT.query.filter_by(duplicate_key=key).first(): raise ValueError("This investment appears to be an exact duplicate already registered.")
        item = InvestmentWHT(bank_name=bank[:180], bank_tin=tin[:40], amount_invested=principal, nature=nature[:80],
            start_date=start_date, maturity_date=maturity_date, annual_rate=rate, calculated_interest=calculated,
            confirmed_interest=confirmed, expected_wht=expected, actual_wht=Decimal("0"), wht_rate=INVESTMENT_WHT_RATE,
            duplicate_key=key, created_by=(session.get("actor_name") or "Tax Compliance")[:120])
        db.session.add(item); db.session.commit(); flash("Investment registered and expected WHT calculated.", "success")
    except Exception as exc:
        db.session.rollback(); flash(f"Investment was not saved: {exc}", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/<int:investment_id>/edit", methods=["POST"])
def tax_investment_wht_edit(investment_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = InvestmentWHT.query.get_or_404(investment_id)
    try:
        bank = request.form.get("bank_name", "").strip()
        tin = request.form.get("bank_tin", "").strip()
        principal = _amount(request.form.get("amount_invested"))
        rate = _amount(request.form.get("annual_rate"))
        nature = request.form.get("nature", "Fixed Deposit").strip()
        start_date = datetime.strptime(request.form.get("start_date", ""), "%Y-%m-%d").date()
        maturity_date = datetime.strptime(request.form.get("maturity_date", ""), "%Y-%m-%d").date()
        confirmed_raw = request.form.get("confirmed_interest", "").strip()
        confirmed = _amount(confirmed_raw) if confirmed_raw else None
        if not bank or not tin: raise ValueError("Bank Name and TIN Number are required.")
        if principal <= 0 or rate < 0 or rate > 100: raise ValueError("Enter a positive principal and a valid annual rate.")
        _, calculated, expected = _investment_wht_calculation(principal, rate, start_date, maturity_date, confirmed)
        key = _investment_duplicate_key(tin, principal, nature, start_date, maturity_date)
        duplicate = InvestmentWHT.query.filter(InvestmentWHT.duplicate_key == key, InvestmentWHT.id != item.id).first()
        if duplicate: raise ValueError("Another investment already has the same duplicate key.")
        item.bank_name=bank[:180]; item.bank_tin=tin[:40]; item.amount_invested=principal
        item.nature=nature[:80]; item.start_date=start_date; item.maturity_date=maturity_date
        item.annual_rate=rate; item.confirmed_interest=confirmed
        item.calculated_interest=calculated; item.expected_wht=expected; item.duplicate_key=key
        db.session.commit()
        flash("Investment registration updated successfully.", "success")
    except Exception as exc:
        db.session.rollback(); flash(f"Investment update was not saved: {exc}", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/<int:investment_id>/delete", methods=["POST"])
def tax_investment_wht_delete(investment_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = InvestmentWHT.query.get_or_404(investment_id)
    try:
        # Explicitly remove reminder logs first; preserve the batch and all other investments.
        InvestmentWHTEmailLog.query.filter_by(investment_id=item.id).delete(synchronize_session=False)
        db.session.delete(item); db.session.commit()
        flash("Investment and its associated reminder email logs were deleted. Other registrations were retained.", "success")
    except Exception:
        db.session.rollback(); logger.exception("Investment deletion failed: %s", investment_id)
        flash("Investment deletion failed; no changes were saved.", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/batch/<int:batch_id>/delete", methods=["POST"])
def tax_investment_wht_delete_batch(batch_id):
    if not _tax_required(): return redirect(url_for("home"))
    batch = InvestmentWHTBatch.query.get_or_404(batch_id)
    batch_filename = batch.filename
    try:
        ids = [x[0] for x in db.session.query(InvestmentWHT.id).filter_by(batch_id=batch.id).all()]
        if ids:
            InvestmentWHTEmailLog.query.filter(InvestmentWHTEmailLog.investment_id.in_(ids)).delete(synchronize_session=False)
            InvestmentWHT.query.filter(InvestmentWHT.id.in_(ids)).delete(synchronize_session=False)
        db.session.delete(batch); db.session.commit()
        flash(f"Imported batch '{batch_filename}' and {len(ids)} associated investment(s) were deleted. Manual registrations and other batches were preserved.", "success")
    except Exception:
        db.session.rollback(); logger.exception("Investment batch deletion failed: %s", batch_id)
        flash("Batch deletion failed; no changes were saved.", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/<int:investment_id>/reconcile", methods=["POST"])
def tax_investment_wht_reconcile(investment_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = InvestmentWHT.query.get_or_404(investment_id)
    try:
        actual = _amount(request.form.get("actual_wht"))
        if actual < 0: raise ValueError("Actual WHT cannot be negative.")
        item.actual_wht = actual
        item.certificate_reference = request.form.get("certificate_reference", "").strip()[:150] or None
        cert_date = request.form.get("certificate_date", "").strip()
        item.certificate_date = datetime.strptime(cert_date, "%Y-%m-%d").date() if cert_date else None
        item.notes = request.form.get("notes", "").strip() or item.notes
        uploaded = request.files.get("certificate_file")
        if uploaded and uploaded.filename:
            name = secure_filename(uploaded.filename)
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext not in {"pdf", "png", "jpg", "jpeg"}: raise ValueError("WHT certificate must be PDF, JPG or PNG.")
            content = uploaded.read(5 * 1024 * 1024 + 1)
            if len(content) > 5 * 1024 * 1024: raise ValueError("WHT certificate exceeds 5 MB.")
            item.certificate_filename = name[:255]; item.certificate_content_type = uploaded.mimetype or "application/octet-stream"; item.certificate_data = content
        db.session.commit(); flash("Actual WHT and certificate details updated. Outstanding WHT has been recalculated.", "success")
    except Exception as exc:
        db.session.rollback(); flash(f"Reconciliation was not saved: {exc}", "danger")
    return redirect(url_for("tax_investment_wht"))


@app.route("/tax-investment-wht/<int:investment_id>/certificate")
def tax_investment_wht_certificate(investment_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = InvestmentWHT.query.get_or_404(investment_id)
    if not item.certificate_data: abort(404)
    return send_file(BytesIO(item.certificate_data), mimetype=item.certificate_content_type or "application/octet-stream",
        as_attachment=True, download_name=item.certificate_filename or "WHT_Certificate", max_age=0)


@app.route("/tax-investment-wht/export.xlsx")
def tax_investment_wht_export():
    if not _tax_required(): return redirect(url_for("home"))
    wb = Workbook(); ws = wb.active; ws.title = "Investment WHT Register"
    headers = INVESTMENT_WHT_TEMPLATE_HEADERS + ["Calculated Interest", "Days Invested", "Outstanding WHT", "Status", "Certificate Status"]
    ws.append(headers)
    for x in InvestmentWHT.query.order_by(InvestmentWHT.maturity_date.asc()).all():
        ws.append([x.bank_name, x.bank_tin, float(x.amount_invested), x.nature, x.start_date, x.maturity_date,
            float(x.annual_rate), float(x.expected_wht), float(x.actual_wht),
            float(x.confirmed_interest) if x.confirmed_interest is not None else None,
            x.certificate_reference, x.certificate_date, x.notes, float(x.calculated_interest), x.days_invested,
            float(x.outstanding_wht), x.status, "Received" if x.certificate_data else "Pending"])
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="123B63"); c.alignment = Alignment(wrap_text=True)
    ws.freeze_panes = "A2"; ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
    for col in ws.columns: ws.column_dimensions[get_column_letter(col[0].column)].width = min(32, max(14, max(len(str(c.value or "")) for c in col) + 2))
    for row in ws.iter_rows(min_row=2):
        for idx in (5, 6, 12): row[idx-1].number_format = "yyyy-mm-dd"
        for idx in (3, 8, 9, 10, 14, 16):
            if idx <= len(row): row[idx-1].number_format = '#,##0.00;[Red](#,##0.00)'
    out = BytesIO(); wb.save(out); out.seek(0)
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="Britam_Investment_WHT_Register.xlsx")


@app.route("/tax-investment-wht/reminders/run", methods=["POST"])
def tax_investment_wht_run_reminders():
    """Scheduled external cron endpoint. Requires INVESTMENT_WHT_CRON_TOKEN."""
    token = os.environ.get("INVESTMENT_WHT_CRON_TOKEN", "")
    supplied = request.headers.get("X-CETTP-CRON-TOKEN", "")
    if not token or not supplied or not hmac.compare_digest(token, supplied):
        abort(403)
    today = _investment_local_today(); sent = failed = skipped = 0
    for item in InvestmentWHT.query.all():
        maturity = item.maturity_date
        if maturity - timedelta(days=5) == today:
            event = "maturity_5_days_before"; subject = f"CETTP: Fixed deposit maturity in 5 days – {item.bank_name}"
            body = f"Investment maturity reminder\nBank: {item.bank_name}\nTIN: {item.bank_tin}\nPrincipal: TZS {item.amount_invested:,.2f}\nMaturity: {maturity:%d %b %Y}\nExpected interest: TZS {item.interest_for_wht:,.2f}\nExpected WHT (10%): TZS {item.expected_wht:,.2f}\nPlease confirm the bank's maturity arrangements and expected WHT deduction."
            ok = _investment_wht_send_email(item, event, today, subject, body); sent += int(ok); failed += int(not ok)
        if maturity == today:
            event = "maturity_due_date"; subject = f"CETTP: Fixed deposit matures today – {item.bank_name}"
            body = f"Investment maturity is today.\nBank: {item.bank_name}\nTIN: {item.bank_tin}\nPrincipal: TZS {item.amount_invested:,.2f}\nExpected interest: TZS {item.interest_for_wht:,.2f}\nExpected WHT (10%): TZS {item.expected_wht:,.2f}\nPlease verify the bank's WHT deduction and update the investment reconciliation in CETTP."
            ok = _investment_wht_send_email(item, event, today, subject, body); sent += int(ok); failed += int(not ok)
        next_month = date(maturity.year + (1 if maturity.month == 12 else 0), 1 if maturity.month == 12 else maturity.month + 1, 1)
        wht_due = date(next_month.year, next_month.month, 7)
        if today == wht_due + timedelta(days=1) and (item.outstanding_wht > 0 or not item.certificate_data):
            event = "certificate_followup_after_wht_deadline"; subject = f"CETTP: Verify TRA WHT certificate – {item.bank_name}"
            body = f"The WHT filing deadline (7th of the month following maturity) has passed. Please follow up with {item.bank_name} and verify the TRA WHT certificate.\nMaturity date: {maturity:%d %b %Y}\nExpected WHT: TZS {item.expected_wht:,.2f}\nActual WHT recorded: TZS {item.actual_wht:,.2f}\nOutstanding WHT receivable: TZS {item.outstanding_wht:,.2f}\nUpdate the actual deduction and upload the TRA certificate in CETTP."
            ok = _investment_wht_send_email(item, event, today, subject, body); sent += int(ok); failed += int(not ok)
    return jsonify({"date": today.isoformat(), "sent": sent, "failed_or_not_configured": failed, "message": "Reminder run completed; sent events are de-duplicated."})


# VAT Control Account – Tax Compliance Workspace
# ---------------------------------------------------------------------------
VAT_LEDGER_CLASSIFICATIONS = {
    "OUTPUT_VAT": "Output VAT",
    "INPUT_VAT": "Input VAT credit",
    "VAT_PAYMENT": "VAT payment",
    "INCREASING_ADJUSTMENT": "Increasing adjustment",
    "DECREASING_ADJUSTMENT": "Decreasing adjustment",
    "IMPORTED_SERVICE_OUTPUT_VAT": "Imported services – output VAT",
    "IMPORTED_SERVICE_INPUT_VAT": "Imported services – input VAT credit",
    "IMPORT_VAT_CREDIT": "Import VAT credit",
    "UNCLASSIFIED": "Unclassified – review required",
    "EXCLUDE_NON_VAT": "Exclude from VAT account (reconcile separately)",
}


def _vat_actor_name():
    return (session.get("actor_name") or "Tax Compliance").strip()[:120]


def _vat_text(value, max_length=255):
    if value is None:
        return None
    text = str(value).replace("\xa0", " ").strip()
    return text[:max_length] or None


def _vat_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    return None


def _vat_decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        raw = value.replace(",", "").strip()
        if raw in ("*****", "-", "—"):
            return None
        if raw.startswith("(") and raw.endswith(")"):
            raw = "-" + raw[1:-1]
        value = raw
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _vat_default_classification(account, description, batch_name, transaction_type=None):
    # The supplier ledger can contain ordinary supplier-payment wording. Keep
    # payment detection limited to VAT-related movements in 330101.
    text = " ".join(str(x or "") for x in (description, batch_name)).lower()
    if "imported service" in text or "imported services" in text or "reverse charge" in text:
        return "IMPORTED_SERVICE_INPUT_VAT" if account == "330107" or "input" in text else "IMPORTED_SERVICE_OUTPUT_VAT"
    if "import vat" in text or "customs vat" in text:
        return "IMPORT_VAT_CREDIT"
    if any(word in text for word in ("input", "recovery", "recoverable", "claim")):
        if "reversal" in text or "reverse" in text:
            return "INCREASING_ADJUSTMENT"
        return "INPUT_VAT"
    if account == "330101" and any(word in text for word in ("payment", "paid", "settlement", "instalment", "installment")) and any(word in text for word in ("vat", "mainland", "znz", "zra", "tra")):
        return "VAT_PAYMENT"
    if any(word in text for word in ("increasing adjustment", "under-declar", "underdeclar", "short declared")):
        return "INCREASING_ADJUSTMENT"
    if any(word in text for word in ("decreasing adjustment", "credit note", "over-declar", "overdeclared", "output reversal")):
        return "DECREASING_ADJUSTMENT"
    if account == "330101" and "adjustment" in text:
        return "UNCLASSIFIED"
    # 330101 is the ERP output VAT account and 330107 is the VAT recovery account.
    # Ambiguous manual journal descriptions are left for Tax Compliance review.
    if account == "330101" and "vat" in text and not any(x in text for x in ("output", "premium", "salvage", "facultative")):
        return "UNCLASSIFIED"
    return "OUTPUT_VAT" if account == "330101" else "INPUT_VAT"


def _parse_vat_ledger_workbook(content):
    workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
    required = {"330101", "330107"}
    available = {str(name).strip() for name in workbook.sheetnames}
    if not required.issubset(available):
        raise ValueError("The ERP workbook must contain both worksheets named 330101 and 330107.")
    all_entries, all_balances = [], []
    counts = {"330101": 0, "330107": 0}
    for account in ("330101", "330107"):
        sheet = workbook[account]
        current_period = None
        pending_opening = False
        for row in sheet.iter_rows(values_only=True):
            first = str(row[0] or "").replace("\xa0", " ").strip().lower() if row else ""
            if first.startswith("period") and len(row) > 1:
                period_date = _vat_date(row[1])
                if period_date:
                    current_period = period_date.strftime("%Y-%m")
                    pending_opening = False
                continue
            if first.startswith("opening"):
                pending_opening = True
                continue
            if pending_opening:
                opening = _vat_decimal(row[43] if len(row) > 43 else None)
                if opening is not None and current_period:
                    all_balances.append({"account": account, "period": current_period, "opening": opening, "closing": None})
                    pending_opening = False
                    continue
            if first.startswith("closing") and current_period:
                closing = _vat_decimal(row[43] if len(row) > 43 else None)
                for balance in reversed(all_balances):
                    if balance["account"] == account and balance["period"] == current_period:
                        balance["closing"] = closing
                        break
                continue
            if first == "gl date":
                continue
            gl_date = _vat_date(row[0] if row else None)
            amount = _vat_decimal(row[43] if len(row) > 43 else None)
            if not current_period or not gl_date or amount is None:
                continue
            # ERP report fields are at fixed columns in the supplied Detailed Account Analysis export.
            get = lambda idx: row[idx] if len(row) > idx else None
            txn_type = _vat_text(get(32))
            desc = _vat_text(get(35), 4000)
            batch = _vat_text(get(22))
            all_entries.append({
                "account": account, "period": current_period, "gl_date": gl_date,
                "transaction_number": _vat_text(get(5)), "transaction_date": _vat_date(get(7)),
                "creation_date": _vat_date(get(10)), "posting_date": _vat_date(get(12)),
                "document_number": _vat_text(get(14)), "batch_name": batch,
                "counterparty": _vat_text(get(26)), "transaction_source": _vat_text(get(29)),
                "transaction_type": txn_type, "natural_account_description": _vat_text(get(2)),
                "transaction_description": desc, "entered_amount": _vat_decimal(get(37)),
                "entered_currency": _vat_text(get(40)), "accounted_amount": amount,
                "accounted_currency": _vat_text(get(46)), "initiator": _vat_text(get(49)),
                "classification": _vat_default_classification(account, desc, batch),
            })
            counts[account] += 1
    workbook.close()
    if not all_entries:
        raise ValueError("No ledger transactions were found. Check that this is the standard ERP Detailed Account Analysis export.")
    if not all_balances:
        raise ValueError("No monthly opening balances were found. Check the ERP workbook's monthly report sections.")
    periods_by_account = {account: {b["period"] for b in all_balances if b["account"] == account} for account in ("330101", "330107")}
    if not periods_by_account["330101"] or not periods_by_account["330107"]:
        raise ValueError("Both ledger worksheets must contain monthly opening balances.")
    if periods_by_account["330101"] != periods_by_account["330107"]:
        raise ValueError("The 330101 and 330107 worksheets must cover the same monthly reporting periods.")
    return all_entries, all_balances, counts


def _vat_liability_effect(amount):
    # ERP signs: a credit balance in output VAT (330101) is negative; a debit
    # balance in recoverable VAT (330107) is positive. The liability movement
    # for either ledger is therefore the negative of its signed accounted amount.
    return -Decimal(str(amount or 0))


def _vat_manual_effect(item):
    multiplier = VAT_MANUAL_CATEGORIES.get(item.category, ("", 0))[1]
    return Decimal(str(item.amount or 0)) * Decimal(str(multiplier))


def _vat_period_summary(upload, periods=None):
    entries = VatLedgerEntry.query.filter_by(upload_id=upload.id).all()
    balances = VatLedgerPeriodBalance.query.filter_by(upload_id=upload.id).all()
    manual = VatManualMovement.query.all()
    returns = {r.tax_period: r for r in VatReturnRecord.query.all()}
    balance_map = {(b.ledger_account, b.tax_period): b for b in balances}
    entry_map = {}
    for entry in entries:
        entry_map.setdefault(entry.tax_period, []).append(entry)
    manual_map = {}
    for item in manual:
        manual_map.setdefault(item.tax_period, []).append(item)
    all_periods = sorted(set([x[1] for x in balance_map] + list(entry_map) + list(manual_map)))
    if periods:
        all_periods = [p for p in all_periods if p in periods]
    output = []
    for period in all_periods:
        b_out = balance_map.get(("330101", period))
        b_in = balance_map.get(("330107", period))
        opening_raw = (Decimal(str(b_out.opening_balance or 0)) if b_out else Decimal("0")) + (Decimal(str(b_in.opening_balance or 0)) if b_in else Decimal("0"))
        opening = -opening_raw if b_out and b_in and b_out.opening_balance is not None and b_in.opening_balance is not None else None
        rows = entry_map.get(period, [])
        by_class = {}
        unclassified_count = 0
        excluded_count = 0
        for entry in rows:
            effect = _vat_liability_effect(entry.accounted_amount)
            by_class[entry.classification] = by_class.get(entry.classification, Decimal("0")) + effect
            if entry.classification == "UNCLASSIFIED": unclassified_count += 1
            if entry.classification == "EXCLUDE_NON_VAT": excluded_count += 1
        ledger_effect = sum((v for k, v in by_class.items() if k != "EXCLUDE_NON_VAT"), Decimal("0"))
        manual_rows = manual_map.get(period, [])
        manual_effect = sum((_vat_manual_effect(x) for x in manual_rows), Decimal("0"))
        manual_tax_effect = sum((_vat_manual_effect(x) for x in manual_rows if x.category != "VAT_PAYMENT"), Decimal("0"))
        closing = (opening + ledger_effect + manual_effect) if opening is not None else None
        source_closing = None
        if b_out and b_in and b_out.closing_balance is not None and b_in.closing_balance is not None:
            source_closing = -(Decimal(str(b_out.closing_balance)) + Decimal(str(b_in.closing_balance)))
        expected_from_gl = (source_closing + manual_effect) if source_closing is not None else None
        variance = (closing - expected_from_gl) if closing is not None and expected_from_gl is not None else None
        period_net_tax = sum((v for k, v in by_class.items() if k != "VAT_PAYMENT" and k != "EXCLUDE_NON_VAT"), Decimal("0")) + manual_tax_effect
        ret = returns.get(period)
        return_variance = (period_net_tax - Decimal(str(ret.declared_net_tax or 0))) if ret else None
        output.append({"period": period, "opening": opening, "output_vat": by_class.get("OUTPUT_VAT", Decimal("0")),
            "input_vat": by_class.get("INPUT_VAT", Decimal("0")), "payments": by_class.get("VAT_PAYMENT", Decimal("0")),
            "increasing": by_class.get("INCREASING_ADJUSTMENT", Decimal("0")),
            "decreasing": by_class.get("DECREASING_ADJUSTMENT", Decimal("0")),
            "imported_output": by_class.get("IMPORTED_SERVICE_OUTPUT_VAT", Decimal("0")),
            "imported_input": by_class.get("IMPORTED_SERVICE_INPUT_VAT", Decimal("0")),
            "import_vat": by_class.get("IMPORT_VAT_CREDIT", Decimal("0")),
            "unclassified": by_class.get("UNCLASSIFIED", Decimal("0")),
            "excluded": by_class.get("EXCLUDE_NON_VAT", Decimal("0")),
            "ledger_effect": ledger_effect, "manual_effect": manual_effect, "manual_tax_effect": manual_tax_effect, "closing": closing,
            "source_closing": source_closing, "variance": variance, "period_net_tax": period_net_tax,
            "return_record": ret, "return_variance": return_variance,
            "unclassified_count": unclassified_count, "excluded_count": excluded_count,
            "manual_count": len(manual_rows), "entry_count": len(rows)})
    return output


@app.route("/tax-vat-control", methods=["GET"])
def tax_vat_control():
    if not _tax_required(): return redirect(url_for("home"))
    uploads = VatLedgerUpload.query.order_by(VatLedgerUpload.uploaded_at.desc()).limit(20).all()
    selected_id = request.args.get("upload_id", type=int)
    upload = VatLedgerUpload.query.get(selected_id) if selected_id else (uploads[0] if uploads else None)
    summaries = _vat_period_summary(upload) if upload else []
    selected_period = request.args.get("period", "").strip()
    if not selected_period and summaries:
        selected_period = summaries[-1]["period"]
    selected_summary = next((x for x in summaries if x["period"] == selected_period), None)
    entries_query = VatLedgerEntry.query.filter_by(upload_id=upload.id) if upload else VatLedgerEntry.query.filter(VatLedgerEntry.id == -1)
    if selected_period: entries_query = entries_query.filter_by(tax_period=selected_period)
    classification_filter = request.args.get("classification", "").strip()
    if classification_filter in VAT_LEDGER_CLASSIFICATIONS:
        entries_query = entries_query.filter_by(classification=classification_filter)
    entries = entries_query.order_by(VatLedgerEntry.gl_date.desc(), VatLedgerEntry.id.desc()).limit(300).all()
    movements = VatManualMovement.query.filter_by(tax_period=selected_period).order_by(VatManualMovement.movement_date.desc()).all() if selected_period else []
    return_records = VatReturnRecord.query.order_by(VatReturnRecord.tax_period.desc()).limit(24).all()
    selected_return = VatReturnRecord.query.filter_by(tax_period=selected_period).first() if selected_period else None
    return_summary_map = {x["period"]: x for x in summaries}
    return render_template("tax_vat_control.html", uploads=uploads, upload=upload, summaries=summaries, return_summary_map=return_summary_map, selected_return=selected_return,
        selected_period=selected_period, selected_summary=selected_summary, entries=entries,
        classifications=VAT_LEDGER_CLASSIFICATIONS, classification_filter=classification_filter,
        movements=movements, manual_categories=VAT_MANUAL_CATEGORIES, return_records=return_records)


@app.route("/tax-vat-control/upload", methods=["POST"])
def tax_vat_control_upload():
    if not _tax_required(): return redirect(url_for("home"))
    f = request.files.get("ledger_file")
    if not f or not f.filename:
        flash("Select the ERP Excel workbook containing both 330101 and 330107 worksheets.", "warning")
        return redirect(url_for("tax_vat_control"))
    filename = secure_filename(f.filename) or "ERP_VAT_Ledgers.xlsx"
    if not filename.lower().endswith(".xlsx"):
        flash("Upload the ERP ledger workbook in .xlsx format.", "danger")
        return redirect(url_for("tax_vat_control"))
    content = f.read()
    if not content or len(content) > 30 * 1024 * 1024:
        flash("The workbook is empty or exceeds the 30 MB upload limit.", "danger")
        return redirect(url_for("tax_vat_control"))
    digest = hashlib.sha256(content).hexdigest()
    if VatLedgerUpload.query.filter_by(file_sha256=digest).first():
        flash("This exact ERP workbook has already been uploaded. The existing batch has been retained; no duplicate rows were imported.", "warning")
        return redirect(url_for("tax_vat_control"))
    try:
        parsed, balances, counts = _parse_vat_ledger_workbook(content)
        periods = sorted(set([x["period"] for x in parsed] + [x["period"] for x in balances]))
        upload = VatLedgerUpload(filename=filename, file_sha256=digest, file_data=content,
            output_rows=counts["330101"], input_rows=counts["330107"],
            period_from=periods[0], period_to=periods[-1], uploaded_by=_tax_actor_name())
        db.session.add(upload); db.session.flush()
        db.session.add(VatAuditLog(actor=_vat_actor_name(), action="ERP ledgers uploaded", record_type="upload", record_id=upload.id, details=f"{counts['330101']} rows in 330101; {counts['330107']} rows in 330107; {len(periods)} periods."))
        for item in parsed:
            db.session.add(VatLedgerEntry(upload_id=upload.id, ledger_account=item["account"], tax_period=item["period"],
                gl_date=item["gl_date"], transaction_number=item["transaction_number"], transaction_date=item["transaction_date"],
                creation_date=item["creation_date"], posting_date=item["posting_date"], document_number=item["document_number"],
                batch_name=item["batch_name"], counterparty=item["counterparty"], transaction_source=item["transaction_source"],
                transaction_type=item["transaction_type"], natural_account_description=item["natural_account_description"],
                transaction_description=item["transaction_description"], entered_amount=item["entered_amount"],
                entered_currency=item["entered_currency"], accounted_amount=item["accounted_amount"],
                accounted_currency=item["accounted_currency"], initiator=item["initiator"], classification=item["classification"]))
        for item in balances:
            db.session.add(VatLedgerPeriodBalance(upload_id=upload.id, ledger_account=item["account"], tax_period=item["period"],
                opening_balance=item["opening"], closing_balance=item["closing"]))
        db.session.commit()
        flash(f"ERP ledgers imported successfully: {counts['330101']:,} output-ledger rows and {counts['330107']:,} recoverable-ledger rows across {len(periods)} periods. Review unclassified transactions before relying on the final account.", "success")
        return redirect(url_for("tax_vat_control", upload_id=upload.id, period=periods[-1]))
    except Exception as exc:
        db.session.rollback()
        logger.exception("VAT ledger workbook import failed")
        flash(f"VAT ledger import failed: {str(exc)[:350]}", "danger")
        return redirect(url_for("tax_vat_control"))


@app.route("/tax-vat-control/entry/<int:entry_id>/classify", methods=["POST"])
def tax_vat_control_classify(entry_id):
    if not _tax_required(): return redirect(url_for("home"))
    entry = VatLedgerEntry.query.get_or_404(entry_id)
    classification = request.form.get("classification", "")
    if classification not in VAT_LEDGER_CLASSIFICATIONS:
        flash("Select a valid VAT transaction classification.", "danger")
    else:
        entry.classification = classification
        entry.review_notes = request.form.get("review_notes", "").strip()[:2000] or None
        entry.reviewed_by = _tax_actor_name()
        entry.reviewed_at = datetime.utcnow()
        db.session.add(VatAuditLog(actor=_vat_actor_name(), action="Ledger transaction reclassified", record_type="ledger_entry", record_id=entry.id, details=f"Classification set to {classification}. {entry.review_notes or ''}"))
        db.session.commit()
        flash("VAT ledger transaction classification updated.", "success")
    return redirect(url_for("tax_vat_control", upload_id=entry.upload_id, period=entry.tax_period, classification=request.args.get("classification", "")))


@app.route("/tax-vat-control/movement", methods=["POST"])
def tax_vat_control_add_movement():
    if not _tax_required(): return redirect(url_for("home"))
    try:
        movement_date = date.fromisoformat(request.form.get("movement_date", ""))
        category = request.form.get("category", "")
        amount = _amount(request.form.get("amount", "0"))
        if category not in VAT_MANUAL_CATEGORIES or amount <= 0:
            raise ValueError("Choose a valid movement category and enter an amount greater than zero.")
        f = request.files.get("supporting_file")
        file_data = f.read() if f and f.filename else None
        if file_data and len(file_data) > 12 * 1024 * 1024:
            raise ValueError("Supporting documents must not exceed 12 MB.")
        if file_data and secure_filename(f.filename).rsplit(".", 1)[-1].lower() not in {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "doc", "docx", "csv"}:
            raise ValueError("Unsupported supporting-document type. Upload PDF, image, Excel, Word or CSV files.")
        supply_value_raw = request.form.get("supply_value", "").strip()
        supply_value = _amount(supply_value_raw) if supply_value_raw else None
        if supply_value is not None and supply_value < 0:
            raise ValueError("Supply value must be zero or positive.")
        item = VatManualMovement(tax_period=movement_date.strftime("%Y-%m"), movement_date=movement_date,
            category=category, amount=amount, supply_value=supply_value,
            counterparty=request.form.get("counterparty", "").strip()[:255] or None,
            document_number=request.form.get("document_number", "").strip()[:180] or None,
            reference=request.form.get("reference", "").strip()[:180] or None,
            notes=request.form.get("notes", "").strip()[:4000] or None,
            filename=secure_filename(f.filename) if file_data else None, content_type=(f.mimetype or "application/octet-stream") if file_data else None,
            file_data=file_data, created_by=_tax_actor_name())
        db.session.add(item); db.session.flush()
        db.session.add(VatAuditLog(actor=_vat_actor_name(), action="Manual VAT movement added", record_type="manual_movement", record_id=item.id, details=f"{category} TZS {amount} for {item.tax_period}; reference {item.reference or 'not provided'}."))
        db.session.commit()
        flash("VAT control movement recorded. It will be included in the selected period's final account.", "success")
        return redirect(url_for("tax_vat_control", period=item.tax_period))
    except Exception as exc:
        db.session.rollback(); flash(f"Could not record VAT movement: {str(exc)[:250]}", "danger")
        return redirect(url_for("tax_vat_control"))


@app.route("/tax-vat-control/movement/<int:movement_id>/delete", methods=["POST"])
def tax_vat_control_delete_movement(movement_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = VatManualMovement.query.get_or_404(movement_id)
    period = item.tax_period
    db.session.add(VatAuditLog(actor=_vat_actor_name(), action="Manual VAT movement deleted", record_type="manual_movement", record_id=item.id, details=f"Deleted {item.category} TZS {item.amount} for {period}; reference {item.reference or 'not provided'}."))
    db.session.delete(item); db.session.commit()
    flash("Manual VAT movement deleted.", "success")
    return redirect(url_for("tax_vat_control", period=period))


@app.route("/tax-vat-control/return", methods=["POST"])
def tax_vat_control_save_return():
    if not _tax_required(): return redirect(url_for("home"))
    try:
        period = request.form.get("tax_period", "").strip()
        try:
            datetime.strptime(period, "%Y-%m")
        except ValueError:
            raise ValueError("Select a valid tax period in YYYY-MM format.")
        submission_date = date.fromisoformat(request.form["submission_date"]) if request.form.get("submission_date") else None
        def val(name):
            result = _amount(request.form.get(name, "0"))
            if result < 0: raise ValueError("VAT return amounts must be zero or positive.")
            return result
        output_tax, input_tax = val("output_tax"), val("input_tax")
        increasing, decreasing = val("increasing_adjustments"), val("decreasing_adjustments")
        declared = _amount(request.form.get("declared_net_tax")) if request.form.get("declared_net_tax", "").strip() else output_tax - input_tax + increasing - decreasing
        f = request.files.get("return_file")
        file_data = f.read() if f and f.filename else None
        if file_data and len(file_data) > 12 * 1024 * 1024: raise ValueError("Return evidence must not exceed 12 MB.")
        if file_data and secure_filename(f.filename).rsplit(".", 1)[-1].lower() not in {"pdf", "png", "jpg", "jpeg", "xlsx", "xls", "doc", "docx", "csv"}:
            raise ValueError("Unsupported return-evidence type. Upload PDF, image, Excel, Word or CSV files.")
        item = VatReturnRecord.query.filter_by(tax_period=period).first()
        if not item:
            item = VatReturnRecord(tax_period=period, updated_by=_tax_actor_name()); db.session.add(item)
        item.submission_date=submission_date; item.return_reference=request.form.get("return_reference", "").strip()[:150] or None
        item.output_tax=output_tax; item.input_tax=input_tax; item.increasing_adjustments=increasing
        item.decreasing_adjustments=decreasing; item.declared_net_tax=declared
        item.notes=request.form.get("return_notes", "").strip()[:4000] or None; item.updated_by=_tax_actor_name()
        if file_data:
            item.filename=secure_filename(f.filename); item.content_type=f.mimetype or "application/octet-stream"; item.file_data=file_data
        db.session.flush()
        db.session.add(VatAuditLog(actor=_vat_actor_name(), action="TRA VAT return saved", record_type="vat_return", record_id=item.id, details=f"Return figures saved for {period}; declared net VAT TZS {declared}."))
        db.session.commit()
        flash("TRA VAT return figures saved for reconciliation.", "success")
        return redirect(url_for("tax_vat_control", period=period))
    except Exception as exc:
        db.session.rollback(); flash(f"Could not save VAT return: {str(exc)[:250]}", "danger")
        return redirect(url_for("tax_vat_control"))


@app.route("/tax-vat-control/upload/<int:upload_id>/source")
def tax_vat_control_source_workbook(upload_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = VatLedgerUpload.query.get_or_404(upload_id)
    return send_file(BytesIO(item.file_data), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=item.filename or "ERP_VAT_Ledgers.xlsx")


@app.route("/tax-vat-control/movement/<int:movement_id>/attachment")
def tax_vat_control_movement_attachment(movement_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = VatManualMovement.query.get_or_404(movement_id)
    if not item.file_data: abort(404)
    return send_file(BytesIO(item.file_data), mimetype=item.content_type or "application/octet-stream", as_attachment=True, download_name=item.filename or "VAT_supporting_document")


@app.route("/tax-vat-control/return/<int:return_id>/attachment")
def tax_vat_control_return_attachment(return_id):
    if not _tax_required(): return redirect(url_for("home"))
    item = VatReturnRecord.query.get_or_404(return_id)
    if not item.file_data: abort(404)
    return send_file(BytesIO(item.file_data), mimetype=item.content_type or "application/octet-stream", as_attachment=True, download_name=item.filename or "TRA_VAT_return_evidence")


@app.route("/tax-vat-control/export.xlsx")
def tax_vat_control_export():
    if not _tax_required(): return redirect(url_for("home"))
    upload_id = request.args.get("upload_id", type=int)
    upload = VatLedgerUpload.query.get_or_404(upload_id) if upload_id else VatLedgerUpload.query.order_by(VatLedgerUpload.uploaded_at.desc()).first_or_404()
    summaries = _vat_period_summary(upload)
    entries = VatLedgerEntry.query.filter_by(upload_id=upload.id).order_by(VatLedgerEntry.tax_period, VatLedgerEntry.gl_date, VatLedgerEntry.id).all()
    movements = VatManualMovement.query.order_by(VatManualMovement.tax_period, VatManualMovement.movement_date).all()
    returns = VatReturnRecord.query.order_by(VatReturnRecord.tax_period).all()
    wb = Workbook(); ws = wb.active; ws.title = "VAT Control Account"
    ws.append(["BRITAM – VAT CONTROL ACCOUNT"]); ws.append(["ERP source workbook", upload.filename]); ws.append(["Uploaded by", upload.uploaded_by]); ws.append(["Uploaded at", upload.uploaded_at.strftime("%Y-%m-%d %H:%M")]); ws.append([])
    headers=["Tax period","Opening VAT payable/(credit)","Output VAT movement","Input VAT movement (liability effect)","VAT payments (liability effect)","Increasing adjustments","Decreasing adjustments","Imported services output VAT","Imported services input VAT","Import VAT credit","Unclassified movement","Excluded movement","Manual movements","Closing VAT payable/(credit)","ERP closing VAT payable/(credit)","Reconciliation variance","VAT return declared net tax","Return variance","Review rows"]
    ws.append(headers)
    for x in summaries:
        ws.append([x["period"],float(x["opening"]) if x["opening"] is not None else None,float(x["output_vat"]),float(x["input_vat"]),float(x["payments"]),float(x["increasing"]),float(x["decreasing"]),float(x["imported_output"]),float(x["imported_input"]),float(x["import_vat"]),float(x["unclassified"]),float(x["excluded"]),float(x["manual_effect"]),float(x["closing"]) if x["closing"] is not None else None,float(x["source_closing"]) if x["source_closing"] is not None else None,float(x["variance"]) if x["variance"] is not None else None,float(x["return_record"].declared_net_tax) if x["return_record"] else None,float(x["return_variance"]) if x["return_variance"] is not None else None,x["unclassified_count"]])
    ws.freeze_panes="A7"; ws.auto_filter.ref=ws.dimensions
    tx=wb.create_sheet("ERP Transactions")
    tx.append(["Tax period","Ledger account","GL date","Transaction number","Transaction date","Posting date","Document number","Batch name","Supplier/customer","Source","Transaction","Description","Entered amount","Entered currency","Accounted amount (TZS)","Classification","Reviewed by","Review notes"])
    for e in entries:
        tx.append([e.tax_period,e.ledger_account,e.gl_date.isoformat() if e.gl_date else None,e.transaction_number,e.transaction_date.isoformat() if e.transaction_date else None,e.posting_date.isoformat() if e.posting_date else None,e.document_number,e.batch_name,e.counterparty,e.transaction_source,e.transaction_type,e.transaction_description,float(e.entered_amount) if e.entered_amount is not None else None,e.entered_currency,float(e.accounted_amount),VAT_LEDGER_CLASSIFICATIONS.get(e.classification,e.classification),e.reviewed_by,e.review_notes])
    mv=wb.create_sheet("Manual Movements")
    mv.append(["Tax period","Date","Category","Supplier / counterparty","Source document number","Supply value (TZS)","VAT amount (TZS)","Liability effect (TZS)","Payment/control reference","Notes","Recorded by"])
    for m in movements:
        mv.append([m.tax_period,m.movement_date.isoformat(),VAT_MANUAL_CATEGORIES.get(m.category,(m.category,0))[0],m.counterparty,m.document_number,float(m.supply_value) if m.supply_value is not None else None,float(m.amount),float(_vat_manual_effect(m)),m.reference,m.notes,m.created_by])
    rt=wb.create_sheet("TRA VAT Returns")
    rt.append(["Tax period","Submission date","Return reference","Output tax","Input tax","Increasing adjustments","Decreasing adjustments","Declared net tax","Notes"])
    for r in returns:
        rt.append([r.tax_period,r.submission_date.isoformat() if r.submission_date else None,r.return_reference,float(r.output_tax),float(r.input_tax),float(r.increasing_adjustments),float(r.decreasing_adjustments),float(r.declared_net_tax),r.notes])
    audit=wb.create_sheet("VAT Audit Trail")
    audit.append(["Date/time (UTC)","Actor","Action","Record type","Record ID","Details"])
    for a in VatAuditLog.query.order_by(VatAuditLog.created_at).all():
        audit.append([a.created_at.strftime("%Y-%m-%d %H:%M:%S"),a.actor,a.action,a.record_type,a.record_id,a.details])
    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2" if sheet.title != "VAT Control Account" else "A7"
        header_row = 6 if sheet.title == "VAT Control Account" else 1
        for cell in sheet[header_row]:
            cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="123B66"); cell.alignment=Alignment(wrap_text=True,vertical="center")
        if sheet.max_row > 1:
            for cell in sheet[1]: cell.alignment=Alignment(wrap_text=True,vertical="center")
        for col in sheet.columns:
            letter=get_column_letter(col[0].column)
            width=min(max(max(len(str(c.value or "")) for c in col[:250])+2,12),42)
            sheet.column_dimensions[letter].width=width
        if sheet.max_row > 1:
            if sheet.title == "VAT Control Account":
                sheet.auto_filter.ref = f"A6:{get_column_letter(sheet.max_column)}{sheet.max_row}"
            else:
                sheet.auto_filter.ref = sheet.dimensions
    # Financial figures are exported with two decimal places.
    for row in ws.iter_rows(min_row=7, min_col=2, max_col=18):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.00;[Red](#,##0.00)'
    data=BytesIO(); wb.save(data); data.seek(0)
    return send_file(data,mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",as_attachment=True,download_name=f"CETTP_VAT_Control_Account_{upload.period_from}_{upload.period_to}.xlsx")


@app.route("/health")
def health():
    return jsonify(status="ok", application="CETTP Tax Compliance & Cancellation Tracking Portal", version="3.0.0-vat-control")

@app.context_processor
def inject_globals():
    unread_notification_count = 0
    if session.get("role") == "tax":
        try:
            actor = _tax_actor_name()
            read_ids = db.session.query(InAppNotificationRead.notification_id).filter_by(actor_name=actor)
            unread_notification_count = InAppNotification.query.filter(~InAppNotification.id.in_(read_ids)).count()
        except Exception:
            # Keep the portal usable during first-time database initialization.
            unread_notification_count = 0
    initiator_unread_count = 0
    if session.get("role") == "initiator":
        try:
            initiator_unread_count = InitiatorNotification.query.filter_by(recipient_email=_initiator_email(), read_at=None).count()
        except Exception:
            initiator_unread_count = 0
    return {"current_role": session.get("role"), "current_actor": session.get("actor_name"),
            "unread_notification_count": unread_notification_count, "initiator_unread_count": initiator_unread_count}

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
