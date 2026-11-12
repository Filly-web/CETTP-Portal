import os
import unittest
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from openpyxl import Workbook

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-only-secret'
os.environ['INVESTMENT_WHT_CRON_TOKEN'] = 'test-cron-token'

from app import app, db, InvestmentWHT, InvestmentWHTBatch, InvestmentWHTEmailLog, _investment_wht_calculation, _investment_duplicate_key

class InvestmentWHTTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['role'] = 'tax'
            sess['actor_name'] = 'Investment WHT Test'
        with app.app_context():
            db.drop_all(); db.create_all()

    def test_interest_and_wht_calculation_uses_actual_days_and_override(self):
        days, interest, wht = _investment_wht_calculation(100000000, 10, date(2026, 1, 1), date(2026, 7, 1))
        self.assertEqual(days, 181)
        self.assertEqual(interest, Decimal('4958904.11'))
        self.assertEqual(wht, Decimal('495890.41'))
        _, calc, overridden_wht = _investment_wht_calculation(100000000, 10, date(2026, 1, 1), date(2026, 7, 1), 5000000)
        self.assertEqual(calc, interest)
        self.assertEqual(overridden_wht, Decimal('500000.00'))

    def test_workspace_page_and_template_are_accessible(self):
        self.assertEqual(self.client.get('/tax-investment-wht').status_code, 200)
        response = self.client.get('/tax-investment-wht/template.xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Britam_Investment_WHT_Batch_Template.xlsx', response.headers.get('Content-Disposition', ''))

    def test_individual_register_and_reconciliation(self):
        response = self.client.post('/tax-investment-wht/add', data={
            'bank_name':'Example Bank', 'bank_tin':'123456789', 'amount_invested':'100000000',
            'nature':'Fixed Deposit', 'start_date':'2026-01-01', 'maturity_date':'2026-07-01',
            'annual_rate':'10', 'confirmed_interest':'5000000'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            item = InvestmentWHT.query.one()
            self.assertEqual(Decimal(item.expected_wht), Decimal('500000.00'))
            item_id = item.id
        self.client.post(f'/tax-investment-wht/{item_id}/reconcile', data={
            'actual_wht':'400000', 'certificate_reference':'CERT-001', 'certificate_date':'2026-07-08'
        }, follow_redirects=True)
        with app.app_context():
            item = db.session.get(InvestmentWHT, item_id)
            self.assertEqual(item.outstanding_wht, Decimal('100000.00'))
            self.assertEqual(item.certificate_reference, 'CERT-001')

    def test_batch_upload_and_duplicate_prevention(self):
        wb = Workbook(); ws = wb.active
        ws.append(['Bank Name','TIN Number','Amount Invested','Nature of Investment','From','Matured Date','Rate','Expected WHT (10%)','Actual WHT remitted to TRA','Confirmed Expected Interest (Optional)'])
        ws.append(['Example Bank','123456789',100000000,'Fixed Deposit',date(2026,1,1),date(2026,7,1),10,495890.41,0,5000000])
        bio = BytesIO(); wb.save(bio); bio.seek(0)
        response = self.client.post('/tax-investment-wht/upload', data={'investment_file':(bio,'investments.xlsx')}, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertEqual(InvestmentWHT.query.count(), 1)
            self.assertEqual(InvestmentWHTBatch.query.one().imported_rows, 1)
            self.assertEqual(Decimal(InvestmentWHT.query.one().expected_wht), Decimal('500000.00'))


    def test_edit_and_delete_individual_investment_removes_only_its_email_logs(self):
        self.client.post('/tax-investment-wht/add', data={
            'bank_name':'Manual Bank', 'bank_tin':'111222333', 'amount_invested':'1000000',
            'nature':'Fixed Deposit', 'start_date':'2026-01-01', 'maturity_date':'2026-07-01',
            'annual_rate':'10'
        })
        with app.app_context():
            item = InvestmentWHT.query.one()
            item_id = item.id
            db.session.add(InvestmentWHTEmailLog(investment_id=item_id, event_key='test_event',
                event_date=date(2026, 7, 1), recipient='tax@example.com', status='sent'))
            db.session.commit()
        response = self.client.post(f'/tax-investment-wht/{item_id}/edit', data={
            'bank_name':'Updated Bank', 'bank_tin':'111222333', 'amount_invested':'2000000',
            'nature':'Call Deposit', 'start_date':'2026-01-01', 'maturity_date':'2026-08-01',
            'annual_rate':'9', 'confirmed_interest':'100000'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            item = db.session.get(InvestmentWHT, item_id)
            self.assertEqual(item.bank_name, 'Updated Bank')
            self.assertEqual(item.expected_wht, Decimal('10000.00'))
        self.client.post(f'/tax-investment-wht/{item_id}/delete', follow_redirects=True)
        with app.app_context():
            self.assertIsNone(db.session.get(InvestmentWHT, item_id))
            self.assertEqual(InvestmentWHTEmailLog.query.filter_by(investment_id=item_id).count(), 0)

    def test_batch_delete_preserves_manual_registration_and_other_batch(self):
        with app.app_context():
            batch_one = InvestmentWHTBatch(filename='one.xlsx', uploaded_by='Test', imported_rows=1)
            batch_two = InvestmentWHTBatch(filename='two.xlsx', uploaded_by='Test', imported_rows=1)
            db.session.add_all([batch_one, batch_two]); db.session.flush()
            def make_item(batch_id, tin):
                key = _investment_duplicate_key(tin, 100000, 'Fixed Deposit', date(2026,1,1), date(2026,7,1))
                return InvestmentWHT(bank_name='Bank', bank_tin=tin, amount_invested=100000,
                    nature='Fixed Deposit', start_date=date(2026,1,1), maturity_date=date(2026,7,1),
                    annual_rate=10, calculated_interest=1000, expected_wht=100, actual_wht=0,
                    wht_rate=10, duplicate_key=key, created_by='Test', batch_id=batch_id)
            first=make_item(batch_one.id,'111111111')
            second=make_item(batch_two.id,'222222222')
            manual=make_item(None,'333333333')
            db.session.add_all([first,second,manual]); db.session.commit()
            batch_id=batch_one.id
        self.client.post(f'/tax-investment-wht/batch/{batch_id}/delete', follow_redirects=True)
        with app.app_context():
            self.assertEqual(InvestmentWHT.query.count(), 2)
            self.assertIsNotNone(InvestmentWHT.query.filter_by(bank_tin='222222222').first())
            self.assertIsNotNone(InvestmentWHT.query.filter_by(bank_tin='333333333').first())
            self.assertIsNone(InvestmentWHTBatch.query.get(batch_id))

    def test_reminder_endpoint_requires_token_and_suppresses_duplicate_sent_events(self):
        self.assertEqual(self.client.post('/tax-investment-wht/reminders/run').status_code, 403)
        with app.app_context():
            maturity = date.today() + timedelta(days=5)
            key = _investment_duplicate_key('123456789', 100000, 'Fixed Deposit', date.today(), maturity)
            item = InvestmentWHT(bank_name='Example Bank', bank_tin='123456789', amount_invested=100000,
                nature='Fixed Deposit', start_date=date.today(), maturity_date=maturity, annual_rate=10,
                calculated_interest=1000, expected_wht=100, actual_wht=0, wht_rate=10,
                duplicate_key=key, created_by='Test')
            db.session.add(item); db.session.commit()
        response = self.client.post('/tax-investment-wht/reminders/run', headers={'X-CETTP-CRON-TOKEN':'test-cron-token'})
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            log = InvestmentWHTEmailLog.query.one()
            self.assertEqual(log.event_key, 'maturity_5_days_before')
            self.assertIn(log.status, ('not_configured', 'failed', 'sent'))

if __name__ == '__main__':
    unittest.main()
