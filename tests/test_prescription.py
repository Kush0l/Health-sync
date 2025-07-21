import unittest
from unittest.mock import MagicMock, patch
from app.prescription import Prescription
from datetime import datetime


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
