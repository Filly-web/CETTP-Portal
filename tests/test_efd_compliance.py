"""EFD compliance parser and permanent-delete regression tests.

Run with: python -m unittest discover -s tests
"""
import os
import unittest
import tempfile
from pathlib import Path
from io import BytesIO

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret")

from openpyxl import Workbook
import efd_portal
from app import (
    app, db, _parse_efd_upload, EFDInvoiceRequest, EFDRequestAudit,
    PortalEmailLog, DigitalTaxInvoice, EFDReconBatch, EFDReconRow
)


class EFDComplianceTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def test_streaming_aims_parser_skips_empty_rows_and_uses_header(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Report generated", ""])
        ws.append(["PolicyNo", "PolicyStatus", "TXNType", "TaxEfdCode", "GrossPremium"])
        ws.append(["POL-1", "Active", "New Business", " ab 123 ", 118000])
        ws.append([None, None, None, None, None])
        bio = BytesIO()
        wb.save(bio)
        records = _parse_efd_upload(bio.getvalue(), "aims.xlsx", "AIMS")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["row_number"], 3)
        self.assertEqual(records[0]["verification_code"], "AB123")
        self.assertEqual(records[0]["policy_number"], "POL-1")

    def test_tra_parser_uses_rctvnum_not_z_number(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Z#", "RCTVNUM", "Receipt Date", "Receipt Time", "Receipt Type"])
        ws.append(["Z001", "TRA-9988", "2026-10-15", "10:30:00", "Fiscal Receipt"])
        bio = BytesIO()
        wb.save(bio)
        records = _parse_efd_upload(bio.getvalue(), "tra.xlsx", "TRA")
        self.assertEqual(records[0]["verification_code"], "TRA-9988")
        raw = __import__("json").loads(records[0]["raw_data"])
        self.assertEqual(raw["z_number"], "Z001")
        self.assertEqual(raw["receipt_time"], "10:30:00")

    def test_corrupt_workbook_returns_actionable_validation_error(self):
        with self.assertRaises(ValueError):
            _parse_efd_upload(b"not-an-excel-file", "broken.xlsx", "AIMS")

    def _create_request(self):
        with app.app_context():
            item = EFDInvoiceRequest(
                reference="EFD-DELETE-001", requester_email="initiator@example.com",
                requester_name="Initiator", supplier_name="Test Supplier",
                purpose="Testing deletion", original_filename="original.docx",
                original_file_data=b"original", processed_filename="processed.docx",
                processed_file_data=b"processed", status="Completed"
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(DigitalTaxInvoice(request_id=item.id, invoice_data="{}", vat_rate="18"))
            db.session.add(EFDRequestAudit(
                request_id=item.id, reference=item.reference, actor="Tax",
                action="Processed"
            ))
            db.session.add(PortalEmailLog(
                module="efd_invoice_requests", event_key="processed",
                reference_id=item.id, recipient="x@example.com", subject="Done",
                status="sent"
            ))
            db.session.commit()
            return item.id

    def test_tax_can_delete_processed_invoice_and_related_records(self):
        request_id = self._create_request()
        with self.client.session_transaction() as sess:
            sess["role"] = "tax"
        response = self.client.post(f"/efd-requests/{request_id}/delete")
        self.assertIn(response.status_code, (302, 303))
        with app.app_context():
            self.assertIsNone(db.session.get(EFDInvoiceRequest, request_id))
            self.assertEqual(EFDRequestAudit.query.filter_by(request_id=request_id).count(), 0)
            self.assertEqual(PortalEmailLog.query.filter_by(reference_id=request_id).count(), 0)
            self.assertEqual(DigitalTaxInvoice.query.filter_by(request_id=request_id).count(), 0)


    def test_two_thousand_row_tra_upload_is_saved_atomically(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["RCTVNUM", "Policy Number", "Receipt Date", "Receipt Type", "Customer Name", "Amount"])
        for i in range(2000):
            ws.append([f"TRA-{i:06d}", f"POL-{i:06d}", "2026-11-15", "Fiscal Receipt", f"Customer {i}", 1000 + i])
        bio = BytesIO()
        wb.save(bio)
        with self.client.session_transaction() as sess:
            sess["role"] = "tax"
            sess["actor_name"] = "Tax Compliance Test"
        response = self.client.post("/efd-compliance/upload", data={
            "period": "2026-11", "source": "TRA",
            "file": (BytesIO(bio.getvalue()), "tra_november.xlsx"),
        }, content_type="multipart/form-data")
        self.assertIn(response.status_code, (302, 303))
        with app.app_context():
            batch = EFDReconBatch.query.filter_by(period="2026-11", source="TRA", is_current=True).first()
            self.assertIsNotNone(batch)
            self.assertEqual(batch.row_count, 2000)
            self.assertEqual(EFDReconRow.query.filter_by(batch_id=batch.id).count(), 2000)

    def test_tax_can_delete_current_tra_batch_and_restore_previous(self):
        with app.app_context():
            previous = EFDReconBatch(period="2026-11", source="TRA", filename="previous.xlsx",
                file_sha256="a" * 64, row_count=1, imported_by="Tax", is_current=False)
            current = EFDReconBatch(period="2026-11", source="TRA", filename="current.xlsx",
                file_sha256="b" * 64, row_count=1, imported_by="Tax", is_current=True)
            db.session.add_all([previous, current])
            db.session.flush()
            current_id = current.id
            db.session.add(EFDReconRow(batch_id=current.id, row_number=2, verification_code="TRA-1"))
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess["role"] = "tax"
        response = self.client.post(f"/efd-compliance/batch/{current_id}/delete")
        self.assertIn(response.status_code, (302, 303))
        with app.app_context():
            self.assertIsNone(db.session.get(EFDReconBatch, current_id))
            restored = EFDReconBatch.query.filter_by(period="2026-11", source="TRA", is_current=True).first()
            self.assertIsNotNone(restored)
            self.assertEqual(restored.filename, "previous.xlsx")

    def test_tax_user_sees_delete_action_but_not_replace_control(self):
        with app.app_context():
            batch = EFDReconBatch(period="2026-11", source="TRA", filename="tra.xlsx",
                file_sha256="c" * 64, row_count=1, imported_by="Tax", is_current=True)
            db.session.add(batch)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess["role"] = "tax"
        response = self.client.get("/efd-compliance?period=2026-11")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Delete", response.data)
        self.assertNotIn(b"Replace existing batch", response.data)


    def test_tax_can_delete_standalone_efd_portal_history_record(self):
        original_database = efd_portal.DATABASE
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                efd_portal.DATABASE = Path(temp_dir) / "portal_history.db"
                efd_portal.init_db()
                with efd_portal.get_db() as conn:
                    cursor = conn.execute("""
                        INSERT INTO processing_history
                        (created_at, process_date, filename, verification_code, receipt_time)
                        VALUES (?, ?, ?, ?, ?)
                    """, ("2026-11-28 10:00:00", "2026-11-28", "sample.docx", "TRA-1", "10:00:00"))
                    record_id = cursor.lastrowid
                with self.client.session_transaction() as sess:
                    sess["role"] = "tax"
                response = self.client.post(f"/efd-invoice/history/{record_id}/delete")
                self.assertIn(response.status_code, (302, 303))
                with efd_portal.get_db() as conn:
                    remaining = conn.execute(
                        "SELECT COUNT(*) AS n FROM processing_history WHERE id = ?", (record_id,)
                    ).fetchone()["n"]
                    self.assertEqual(remaining, 0)
        finally:
            efd_portal.DATABASE = original_database

    def test_initiator_cannot_delete_processed_invoice(self):
        request_id = self._create_request()
        with self.client.session_transaction() as sess:
            sess["role"] = "initiator"
        response = self.client.post(f"/efd-requests/{request_id}/delete")
        self.assertEqual(response.status_code, 403)
        with app.app_context():
            self.assertIsNotNone(db.session.get(EFDInvoiceRequest, request_id))


if __name__ == "__main__":
    unittest.main()
