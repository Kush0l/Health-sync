import unittest
from unittest.mock import MagicMock, patch
from app.prescription import Prescription
from datetime import datetime
from bson import ObjectId



class TestPrescription(unittest.TestCase):

    @patch('app.prescription.EmailService')
    @patch('app.prescription.BackgroundScheduler')
    def setUp(self, mock_scheduler_cls, mock_email_service_cls):
        # Mock database and its collections
        self.mock_db = MagicMock()
        self.mock_pres_collection = MagicMock()
        self.mock_med_record_collection = MagicMock()
        self.mock_db.get_collection.side_effect = lambda name: {
            "prescriptions": self.mock_pres_collection,
            "medication_records": self.mock_med_record_collection
        }[name]

        # Mock scheduler and email service
        self.mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = self.mock_scheduler
        self.mock_email_service = MagicMock()
        mock_email_service_cls.return_value = self.mock_email_service

        self.prescription = Prescription(self.mock_db)

    def test_reset_daily_status(self):
        self.prescription.reset_daily_status()
        self.mock_pres_collection.update_many.assert_called_once_with(
            {}, {"$set": {"medicines.$[].taken_today": False}}
        )

    def test_get_cron_schedule_valid(self):
        self.assertEqual(self.prescription._get_cron_schedule(
            "morning"), {"hour": 9, "minute": 0})

    def test_get_cron_schedule_invalid(self):
        self.assertIsNone(self.prescription._get_cron_schedule("dawn"))

    def test_send_reminder_email_calls_email_service(self):
        self.prescription._send_reminder_email(
            "test@example.com", "Paracetamol", "500mg", "morning"
        )
        self.mock_email_service.send_medication_reminder.assert_called_once()

    def test_mark_medicine_taken_updates_db(self):
        valid_id = "64d2fbb1547fbc38b94c76aa"  # 24-char hex

        mock_prescription = {
            "_id": valid_id,
            "patient_id": "pat1",
            "doctor_id": "doc1",
            "medicines": [{"name": "Med1", "dosage": "500mg", "taken_today": False, "total_taken": 0}]
        }
        self.mock_pres_collection.find_one.return_value = mock_prescription
        self.mock_pres_collection.update_one.return_value.modified_count = 1

        result = self.prescription.mark_medicine_taken(valid_id, 0)
        self.assertTrue(result)
        self.mock_med_record_collection.insert_one.assert_called_once()

    def test_mark_medicine_taken_already_taken(self):
        mock_prescription = {
            "_id": "abc123",
            "patient_id": "pat1",
            "doctor_id": "doc1",
            "medicines": [{
                "name": "Med1", "dosage": "500mg",
                "taken_today": True,
                "last_taken": datetime.now(),
                "total_taken": 1
            }]
        }
        self.mock_pres_collection.find_one.return_value = mock_prescription

        result = self.prescription.mark_medicine_taken("abc123", 0)
        self.assertFalse(result)  # Already marked as taken

    def test_delete_prescription_success(self):
        """
        Test successful deletion of a prescription and removal of its scheduled jobs.
        """
        prescription_id = "64d2fbb1547fbc38b94c76aa"

        # Mock the collection delete response
        self.mock_pres_collection.delete_one.return_value.deleted_count = 1

        # Mock scheduler jobs
        mock_job1 = MagicMock()
        mock_job1.id = f"reminder_{prescription_id}_Med1_morning"

        mock_job2 = MagicMock()
        mock_job2.id = f"reminder_{prescription_id}_Med1_evening"

        self.mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]

        result = self.prescription.delete_prescription(prescription_id)
        self.assertTrue(result)

        # Ensure delete_one was called
        self.mock_pres_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(prescription_id)})

        # Ensure both jobs were removed
        mock_job1.remove.assert_called_once()
        mock_job2.remove.assert_called_once()

    def test_delete_prescription_not_found(self):
        """
        Test deleting a prescription that does not exist (delete_one returns 0).
        Should return False and not attempt job removal.
        """
        prescription_id = "64d2fbb1547fbc38b94c76aa"
        self.mock_pres_collection.delete_one.return_value.deleted_count = 0

        result = self.prescription.delete_prescription(prescription_id)
        self.assertFalse(result)

        # Confirm deletion was attempted
        self.mock_pres_collection.delete_one.assert_called_once()

    def test_remove_scheduled_jobs_only_matching(self):
        """
        Test _remove_scheduled_jobs only removes jobs that match the prescription_id prefix.
        """
        prescription_id = "64d2fbb1547fbc38b94c76aa"

        # Jobs with mixed IDs
        matching_job = MagicMock()
        matching_job.id = f"reminder_{prescription_id}_Med1_night"

        non_matching_job = MagicMock()
        non_matching_job.id = f"reminder_otherid_Med2_morning"

        self.mock_scheduler.get_jobs.return_value = [matching_job, non_matching_job]

        self.prescription._remove_scheduled_jobs(prescription_id)

        # Only the matching job should be removed
        matching_job.remove.assert_called_once()
        non_matching_job.remove.assert_not_called()
