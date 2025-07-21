import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from main import HealthTracker


class TestHealthTracker(unittest.TestCase):

    @patch('builtins.input', side_effect=["3"])
    def test_run_exit_immediately(self, mock_input):
        tracker = HealthTracker()
        with patch.object(tracker, 'user') as mock_user:
            tracker.run()
            mock_user.register.assert_not_called()
            mock_user.login.assert_not_called()

    @patch('builtins.input', side_effect=["2", "test@example.com", "testpass", "4", "3"])
    def test_login_and_patient_logout(self, mock_input):
        tracker = HealthTracker()
        mock_user = MagicMock()
        mock_user.login.return_value = {
            "_id": "abc123",
            "name": "Test Patient",
            "role": "patient"
        }
        tracker.user = mock_user
        with patch.object(tracker, 'patient_menu') as mock_patient_menu:
            tracker.run()
            mock_user.login.assert_called_once()
            mock_patient_menu.assert_called_once()

    @patch('builtins.input', side_effect=["2", "doc@example.com", "docpass", "4", "3"])
    def test_login_and_doctor_logout(self, mock_input):
        tracker = HealthTracker()
        mock_user = MagicMock()
        mock_user.login.return_value = {
            "_id": "doc123",
            "name": "Dr. John",
            "role": "doctor"
        }
        tracker.user = mock_user
        with patch.object(tracker, 'doctor_menu') as mock_doctor_menu:
            tracker.run()
            mock_user.login.assert_called_once()
            mock_doctor_menu.assert_called_once()

    def test_view_prescriptions_display(self):
        tracker = HealthTracker()
        sample_prescription = [{
            "created_at": datetime.now(),
            "notes": "Take with food.",
            "medicines": [
                {
                    "name": "Paracetamol",
                    "dosage": "500mg",
                    "frequency": "2 times/day",
                    "time": "morning",
                    "taken_today": False,
                    "total_taken": 3,
                    "last_taken": None
                }
            ]
        }]
        with patch("builtins.print") as mock_print:
            tracker.display_prescriptions(sample_prescription)
            mock_print.assert_any_call("\nDoctor's Notes: Take with food.")
