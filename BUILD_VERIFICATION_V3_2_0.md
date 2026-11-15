"""Regression test for Premium Register batch deletion.

Run with: python -m unittest discover -s tests
The test uses an isolated in-memory SQLite database and does not touch Render.
"""
import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-only-secret"

from app import app, db, Case, RegisterUpload, CancellationTrack


class BatchDeleteRegressionTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["role"] = "tax"
            sess["actor_name"] = "Batch Delete Test"
        with app.app_context():
            db.drop_all()
            db.create_all()
            shared_case = Case(
                reference="TEST-CASE-001", case_type="Cancellation",
                policy_number="POL-001", customer_name="Test Customer",
                reason="Test reason", effective_date=__import__("datetime").date(2026, 1, 1),
                initiator_name="Premium Register Import", workflow_status="Initiated",
            )
            db.session.add(shared_case)
            db.session.flush()
            self.case_id = shared_case.id
            first = RegisterUpload(upload_batch="BATCH-ONE", period="2026-01", file_name="one.xlsx")
            second = RegisterUpload(upload_batch="BATCH-TWO", period="2026-01", file_name="two.xlsx")
            db.session.add_all([first, second])
            db.session.flush()
            self.upload_id = first.id
            db.session.add_all([
                CancellationTrack(upload_batch="BATCH-ONE", policy_number="POL-001", classification="Pure cancellation", case_id=shared_case.id),
                CancellationTrack(upload_batch="BATCH-TWO", policy_number="POL-001", classification="Pure cancellation", case_id=shared_case.id),
            ])
            db.session.commit()

    def test_delete_batch_removes_only_its_rows_and_preserves_shared_case(self):
        response = self.client.post(f"/cancellation-tracker/batch/{self.upload_id}/delete", follow_redirects=False)
        self.assertIn(response.status_code, (302, 303))
        with app.app_context():
            self.assertIsNone(RegisterUpload.query.filter_by(upload_batch="BATCH-ONE").first())
            self.assertEqual(CancellationTrack.query.filter_by(upload_batch="BATCH-ONE").count(), 0)
            self.assertEqual(CancellationTrack.query.filter_by(upload_batch="BATCH-TWO").count(), 1)
            self.assertIsNotNone(db.session.get(Case, self.case_id))


if __name__ == "__main__":
    unittest.main()
