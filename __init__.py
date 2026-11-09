"""Fixed Asset Governance models, registered on CETTP's existing SQLAlchemy instance.
All tables are namespaced fa_* to coexist safely with the CETTP schema.
"""
from datetime import datetime
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.types import JSON


def register_models(db):
    class AssetCategory(db.Model):
        __tablename__ = 'fa_category'
        id = db.Column(db.Integer, primary_key=True)
        code = db.Column(db.String(30), unique=True, nullable=False, index=True)
        name = db.Column(db.String(120), nullable=False, unique=True)
        major_category = db.Column(db.String(120), nullable=False)
        useful_life_months = db.Column(db.Integer)
        depreciation_method = db.Column(db.String(30), default='STRAIGHT_LINE', nullable=False)
        depreciation_rate = db.Column(db.Numeric(9, 6))
        gl_cost_account = db.Column(db.String(40))
        gl_accum_dep_account = db.Column(db.String(40))
        gl_expense_account = db.Column(db.String(40))
        is_intangible = db.Column(db.Boolean, default=False, nullable=False)
        active = db.Column(db.Boolean, default=True, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class AssetDepartment(db.Model):
        __tablename__ = 'fa_department'
        id = db.Column(db.Integer, primary_key=True)
        code = db.Column(db.String(30), unique=True, nullable=False)
        name = db.Column(db.String(120), unique=True, nullable=False)
        active = db.Column(db.Boolean, default=True, nullable=False)

    class AssetLocation(db.Model):
        __tablename__ = 'fa_location'
        id = db.Column(db.Integer, primary_key=True)
        code = db.Column(db.String(30), unique=True, nullable=False)
        name = db.Column(db.String(150), unique=True, nullable=False)
        branch = db.Column(db.String(120))
        active = db.Column(db.Boolean, default=True, nullable=False)

    class AssetVendor(db.Model):
        __tablename__ = 'fa_vendor'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(180), unique=True, nullable=False)
        tin = db.Column(db.String(40))
        active = db.Column(db.Boolean, default=True, nullable=False)

    class Asset(db.Model):
        __tablename__ = 'fa_asset'
        id = db.Column(db.Integer, primary_key=True)
        asset_number = db.Column(db.String(60), unique=True, nullable=False, index=True)
        description = db.Column(db.String(255), nullable=False, index=True)
        major_category = db.Column(db.String(120), nullable=False, index=True)
        minor_category = db.Column(db.String(120), nullable=False, index=True)
        department = db.Column(db.String(120), index=True)
        location = db.Column(db.String(150), index=True)
        custodian = db.Column(db.String(150))
        tag_number = db.Column(db.String(80), unique=True, index=True)
        serial_number = db.Column(db.String(120), index=True)
        supplier = db.Column(db.String(180))
        invoice_number = db.Column(db.String(100))
        purchase_order_number = db.Column(db.String(100))
        purchase_date = db.Column(db.Date)
        placed_in_service = db.Column(db.Date, nullable=False, index=True)
        cost = db.Column(db.Numeric(20, 2), nullable=False)
        residual_value = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        useful_life_months = db.Column(db.Integer, nullable=False, default=0)
        depreciation_method = db.Column(db.String(30), nullable=False, default='STRAIGHT_LINE')
        depreciation_rate = db.Column(db.Numeric(9, 6))
        total_units_of_production = db.Column(db.Numeric(20, 2))
        opening_accum_dep = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        ytd_depreciation = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        accumulated_dep = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        nbv = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        status = db.Column(db.String(30), nullable=False, default='ACTIVE', index=True)
        is_intangible = db.Column(db.Boolean, nullable=False, default=False)
        disposed_at = db.Column(db.Date)
        disposed_proceeds = db.Column(db.Numeric(20, 2))
        disposal_gain_loss = db.Column(db.Numeric(20, 2))
        source_batch_id = db.Column(db.Integer, db.ForeignKey('fa_import_batch.id'))
        created_by = db.Column(db.String(160))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
        archived_at = db.Column(db.DateTime)
        __table_args__ = (Index('ix_fa_asset_category_status', 'major_category', 'minor_category', 'status'),
                          Index('ix_fa_asset_dept_location', 'department', 'location'))

    class AssetImportBatch(db.Model):
        __tablename__ = 'fa_import_batch'
        id = db.Column(db.Integer, primary_key=True)
        batch_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
        import_type = db.Column(db.String(30), nullable=False, default='FAR')
        file_name = db.Column(db.String(255), nullable=False)
        status = db.Column(db.String(30), nullable=False, default='STAGED')
        column_mapping = db.Column(JSON)
        total_rows = db.Column(db.Integer, default=0, nullable=False)
        successful_rows = db.Column(db.Integer, default=0, nullable=False)
        failed_rows = db.Column(db.Integer, default=0, nullable=False)
        uploaded_by = db.Column(db.String(160))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class AssetImportRow(db.Model):
        __tablename__ = 'fa_import_row'
        id = db.Column(db.Integer, primary_key=True)
        batch_id = db.Column(db.Integer, db.ForeignKey('fa_import_batch.id', ondelete='CASCADE'), nullable=False, index=True)
        row_number = db.Column(db.Integer, nullable=False)
        raw_data = db.Column(JSON, nullable=False)
        mapped_data = db.Column(JSON)
        errors = db.Column(JSON)
        warnings = db.Column(JSON)
        imported_asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'))
        __table_args__ = (UniqueConstraint('batch_id', 'row_number', name='uq_fa_import_batch_row'),)

    class AssetAdditionRequest(db.Model):
        __tablename__ = 'fa_addition_request'
        id = db.Column(db.Integer, primary_key=True)
        requested_by = db.Column(db.String(160), nullable=False)
        asset_payload = db.Column(JSON, nullable=False)
        status = db.Column(db.String(30), nullable=False, default='SUBMITTED')
        reviewed_by = db.Column(db.String(160)); reviewed_at = db.Column(db.DateTime)
        review_comments = db.Column(db.Text)
        posted_asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class AssetApproval(db.Model):
        __tablename__ = 'fa_approval'
        id = db.Column(db.Integer, primary_key=True)
        request_type = db.Column(db.String(40), nullable=False)
        request_id = db.Column(db.Integer, nullable=False, index=True)
        approver = db.Column(db.String(160), nullable=False)
        status = db.Column(db.String(20), nullable=False, default='PENDING')
        comments = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        decided_at = db.Column(db.DateTime)

    class AssetTransfer(db.Model):
        __tablename__ = 'fa_transfer'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        from_location = db.Column(db.String(150)); to_location = db.Column(db.String(150))
        from_department = db.Column(db.String(120)); to_department = db.Column(db.String(120))
        from_custodian = db.Column(db.String(150)); to_custodian = db.Column(db.String(150))
        transfer_date = db.Column(db.Date, nullable=False)
        reason = db.Column(db.Text, nullable=False)
        status = db.Column(db.String(20), default='POSTED', nullable=False)
        requested_by = db.Column(db.String(160)); approved_by = db.Column(db.String(160))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class AssetDisposal(db.Model):
        __tablename__ = 'fa_disposal'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        disposal_type = db.Column(db.String(30), nullable=False)
        disposal_date = db.Column(db.Date, nullable=False)
        proceeds = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        nbv_at_disposal = db.Column(db.Numeric(20, 2), nullable=False)
        gain_loss = db.Column(db.Numeric(20, 2), nullable=False)
        buyer = db.Column(db.String(180)); reason = db.Column(db.Text, nullable=False)
        approval_reference = db.Column(db.String(100))
        status = db.Column(db.String(20), default='POSTED', nullable=False)
        requested_by = db.Column(db.String(160)); approved_by = db.Column(db.String(160))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class DepreciationUsage(db.Model):
        __tablename__ = 'fa_depreciation_usage'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        units_produced = db.Column(db.Numeric(20,2), nullable=False)
        entered_by = db.Column(db.String(160), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        __table_args__ = (UniqueConstraint('asset_id','period',name='uq_fa_usage_asset_period'),)

    class DepreciationRun(db.Model):
        __tablename__ = 'fa_depreciation_run'
        id = db.Column(db.Integer, primary_key=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        status = db.Column(db.String(20), nullable=False, default='POSTED')
        total_amount = db.Column(db.Numeric(20, 2), nullable=False, default=0)
        asset_count = db.Column(db.Integer, nullable=False, default=0)
        created_by = db.Column(db.String(160))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        __table_args__ = (UniqueConstraint('period', name='uq_fa_depreciation_period'),)

    class DepreciationLine(db.Model):
        __tablename__ = 'fa_depreciation_line'
        id = db.Column(db.Integer, primary_key=True)
        run_id = db.Column(db.Integer, db.ForeignKey('fa_depreciation_run.id'), nullable=False, index=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        opening_nbv = db.Column(db.Numeric(20, 2), nullable=False)
        charge = db.Column(db.Numeric(20, 2), nullable=False)
        closing_nbv = db.Column(db.Numeric(20, 2), nullable=False)
        __table_args__ = (UniqueConstraint('run_id', 'asset_id', name='uq_fa_dep_run_asset'),)

    class CwipProject(db.Model):
        __tablename__ = 'fa_cwip_project'
        id = db.Column(db.Integer, primary_key=True)
        project_code = db.Column(db.String(50), unique=True, nullable=False)
        name = db.Column(db.String(180), nullable=False)
        description = db.Column(db.Text)
        department = db.Column(db.String(120))
        start_date = db.Column(db.Date, nullable=False)
        expected_completion = db.Column(db.Date)
        status = db.Column(db.String(30), default='IN_PROGRESS', nullable=False)
        total_cost = db.Column(db.Numeric(20, 2), default=0, nullable=False)
        capitalized_asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'))
        created_by = db.Column(db.String(160)); created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class CwipExpenditure(db.Model):
        __tablename__ = 'fa_cwip_expenditure'
        id = db.Column(db.Integer, primary_key=True)
        project_id = db.Column(db.Integer, db.ForeignKey('fa_cwip_project.id'), nullable=False, index=True)
        expenditure_date = db.Column(db.Date, nullable=False)
        amount = db.Column(db.Numeric(20, 2), nullable=False)
        description = db.Column(db.String(255), nullable=False)
        reference = db.Column(db.String(100))
        created_by = db.Column(db.String(160)); created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class TrialBalanceImport(db.Model):
        __tablename__ = 'fa_tb_import'
        id = db.Column(db.Integer, primary_key=True)
        batch_reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        file_name = db.Column(db.String(255), nullable=False)
        row_count = db.Column(db.Integer, default=0, nullable=False)
        uploaded_by = db.Column(db.String(160)); created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class TrialBalanceLine(db.Model):
        __tablename__ = 'fa_tb_line'
        id = db.Column(db.Integer, primary_key=True)
        import_id = db.Column(db.Integer, db.ForeignKey('fa_tb_import.id'), nullable=False, index=True)
        account_number = db.Column(db.String(60), nullable=False, index=True)
        account_name = db.Column(db.String(180), nullable=False)
        balance = db.Column(db.Numeric(20, 2), nullable=False)
        __table_args__ = (Index('ix_fa_tb_import_account', 'import_id', 'account_number'),)

    class GLMapping(db.Model):
        __tablename__ = 'fa_gl_mapping'
        id = db.Column(db.Integer, primary_key=True)
        major_category = db.Column(db.String(120), nullable=False, index=True)
        minor_category = db.Column(db.String(120))
        balance_type = db.Column(db.String(20), nullable=False)  # COST / ACCUM_DEP
        account_number = db.Column(db.String(60), nullable=False, index=True)
        account_name = db.Column(db.String(180))
        active = db.Column(db.Boolean, default=True, nullable=False)
        __table_args__ = (UniqueConstraint('major_category','minor_category','balance_type','account_number', name='uq_fa_gl_map'),)

    class AssetPeriodSnapshot(db.Model):
        __tablename__ = 'fa_asset_period_snapshot'
        id = db.Column(db.Integer, primary_key=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        asset_number = db.Column(db.String(60), nullable=False)
        major_category = db.Column(db.String(120), nullable=False)
        cost = db.Column(db.Numeric(20,2), nullable=False)
        accumulated_dep = db.Column(db.Numeric(20,2), nullable=False)
        nbv = db.Column(db.Numeric(20,2), nullable=False)
        status = db.Column(db.String(30), nullable=False)
        captured_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        __table_args__ = (UniqueConstraint('period','asset_id',name='uq_fa_snapshot_period_asset'),)

    class Reconciliation(db.Model):
        __tablename__ = 'fa_reconciliation'
        id = db.Column(db.Integer, primary_key=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        run_reference = db.Column(db.String(50), nullable=False, index=True)
        major_category = db.Column(db.String(120), nullable=False)
        balance_type = db.Column(db.String(20), nullable=False)
        far_balance = db.Column(db.Numeric(20, 2), nullable=False)
        tb_balance = db.Column(db.Numeric(20, 2), nullable=False)
        variance = db.Column(db.Numeric(20, 2), nullable=False)
        status = db.Column(db.String(20), default='OPEN', nullable=False)
        created_by = db.Column(db.String(160)); created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class ReconciliationInvestigation(db.Model):
        __tablename__ = 'fa_reconciliation_investigation'
        id = db.Column(db.Integer, primary_key=True)
        reconciliation_id = db.Column(db.Integer, db.ForeignKey('fa_reconciliation.id'), nullable=False, index=True)
        cause = db.Column(db.String(100), nullable=False)
        description = db.Column(db.Text, nullable=False)
        resolution = db.Column(db.Text)
        resolved_by = db.Column(db.String(160)); resolved_at = db.Column(db.DateTime)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class VerificationRecord(db.Model):
        __tablename__ = 'fa_verification_record'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        outcome = db.Column(db.String(20), nullable=False)
        verified_by = db.Column(db.String(160), nullable=False)
        verified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        notes = db.Column(db.Text); latitude = db.Column(db.Numeric(10,7)); longitude = db.Column(db.Numeric(10,7))

    class InsurancePolicy(db.Model):
        __tablename__ = 'fa_insurance_policy'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        policy_number = db.Column(db.String(100), nullable=False)
        insurer = db.Column(db.String(180), nullable=False)
        insured_amount = db.Column(db.Numeric(20,2), nullable=False)
        coverage_amount = db.Column(db.Numeric(20,2), nullable=False)
        renewal_date = db.Column(db.Date); expiry_date = db.Column(db.Date)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class InsuranceClaim(db.Model):
        __tablename__ = 'fa_insurance_claim'
        id = db.Column(db.Integer, primary_key=True)
        policy_id = db.Column(db.Integer, db.ForeignKey('fa_insurance_policy.id'), nullable=False, index=True)
        claim_reference = db.Column(db.String(100), nullable=False)
        claim_date = db.Column(db.Date, nullable=False)
        claim_amount = db.Column(db.Numeric(20,2), nullable=False)
        status = db.Column(db.String(30), nullable=False, default='OPEN')
        notes = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class AssetDocument(db.Model):
        __tablename__ = 'fa_document'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), index=True)
        file_name = db.Column(db.String(255), nullable=False)
        mime_type = db.Column(db.String(120), nullable=False)
        category = db.Column(db.String(60), nullable=False)
        file_data = db.Column(db.LargeBinary, nullable=False)
        file_size = db.Column(db.Integer, nullable=False)
        uploaded_by = db.Column(db.String(160)); created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class TaxSchedule(db.Model):
        __tablename__ = 'fa_tax_schedule'
        id = db.Column(db.Integer, primary_key=True)
        asset_id = db.Column(db.Integer, db.ForeignKey('fa_asset.id'), nullable=False, index=True)
        period = db.Column(db.String(7), nullable=False, index=True)
        tax_wdv = db.Column(db.Numeric(20,2), nullable=False)
        accounting_nbv = db.Column(db.Numeric(20,2), nullable=False)
        temporary_difference = db.Column(db.Numeric(20,2), nullable=False)
        tax_rate = db.Column(db.Numeric(9,6), nullable=False)
        deferred_tax = db.Column(db.Numeric(20,2), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        __table_args__ = (UniqueConstraint('asset_id','period', name='uq_fa_tax_asset_period'),)

    class PeriodLock(db.Model):
        __tablename__ = 'fa_period_lock'
        id = db.Column(db.Integer, primary_key=True)
        period = db.Column(db.String(7), unique=True, nullable=False)
        status = db.Column(db.String(20), default='OPEN', nullable=False)
        locked_by = db.Column(db.String(160)); locked_at = db.Column(db.DateTime)
        reopened_by = db.Column(db.String(160)); reopened_at = db.Column(db.DateTime); reopen_reason = db.Column(db.Text)

    class AssetAuditLog(db.Model):
        __tablename__ = 'fa_audit_log'
        id = db.Column(db.Integer, primary_key=True)
        actor = db.Column(db.String(160), nullable=False)
        action = db.Column(db.String(80), nullable=False)
        module = db.Column(db.String(80), nullable=False)
        record_type = db.Column(db.String(80)); record_id = db.Column(db.String(80))
        old_value = db.Column(JSON); new_value = db.Column(JSON)
        ip_address = db.Column(db.String(64)); user_agent = db.Column(db.String(255))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    return {name: cls for name, cls in locals().copy().items() if isinstance(cls, type) and hasattr(cls, '__tablename__')}
