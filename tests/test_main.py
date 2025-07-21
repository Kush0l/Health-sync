import unittest
from unittest.mock import patch, mock_open, MagicMock
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

    @patch('main.User')  # Patch the User class used in delete_prescription
    @patch('builtins.input', side_effect=[
        "patient@example.com",  # patient email
        "1",                    # prescription number
        "y"                     # confirm deletion
    ])
    def test_delete_prescription_success(self, mock_input, mock_user_class):
        tracker = HealthTracker()

        # Set up mock user manager
        mock_user_manager = MagicMock()
        mock_user_class.return_value = mock_user_manager  # User(db) will return this

        # Mock patient found
        mock_user_manager.collection.find_one.return_value = {
            "_id": "patient123",
            "email": "patient@example.com",
            "role": "patient"
        }

        # Mock prescriptions
        sample_prescription = [{
            "_id": "presc456",
            "created_at": MagicMock(strftime=lambda x: "2025-07-21"),
            "notes": "Test notes",
            "medicines": [{
                "name": "Medicine A",
                "dosage": "100mg",
                "frequency": "Once a day",
                "time": "morning",
                "taken_today": False,
                "total_taken": 2,
                "last_taken": None
            }]
        }]

        # Mock Prescription methods
        mock_prescription = MagicMock()
        mock_prescription.get_for_patient.return_value = sample_prescription
        mock_prescription.delete_prescription.return_value = True

        tracker.prescription = mock_prescription

        # Patch display to avoid print clutter
        with patch.object(tracker, 'display_prescriptions'):
            tracker.delete_prescription("doctor123")

        # Assert the mock was used
        mock_user_manager.collection.find_one.assert_called_once_with(
            {"email": "patient@example.com", "role": "patient"}
        )
        mock_prescription.get_for_patient.assert_called_once_with("patient123")
        mock_prescription.delete_prescription.assert_called_once_with("presc456")


    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_save_prescriptions_success(self, mock_print, mock_file):
        # Sample user and prescription
        user = {"name": "John Doe"}
        prescriptions = [{
            "created_at": datetime(2025, 7, 21),
            "notes": "Take with meals.",
            "medicines": [{
                "name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "Twice a day",
                "time": "morning"
            }]
        }]

        tracker = HealthTracker()
        tracker.save_prescriptions(prescriptions, user)

        # File should be opened with expected filename
        mock_file.assert_called_once_with("prescriptions/John Doe.txt", "w")

        # Check if print() was called with the table
        self.assertTrue(mock_print.called)
        mock_print.assert_any_call(
            "\nprinted the prescription in 'prescriptions/John Doe.txt'"
        )

    @patch.object(HealthTracker, 'save_prescriptions')
    def test_printPriscription_calls_save_prescriptions(self, mock_save_prescriptions):
        # Set up mock user and tracker
        user = {"_id": "user123", "name": "John Doe"}
        tracker = HealthTracker()

        # Mock prescription fetching
        sample_prescriptions = [{
            "created_at": datetime(2025, 7, 21),
            "notes": "Test Note",
            "medicines": [{
                "name": "Med A",
                "dosage": "10mg",
                "frequency": "Once",
                "time": "night"
            }]
        }]
        tracker.prescription.get_for_patient = MagicMock(
            return_value=sample_prescriptions)

        tracker.printPriscription(user)

        # Assert the method is called with expected data
        mock_save_prescriptions.assert_called_once_with(
            sample_prescriptions, user
        )


if __name__ == "__main__":
    unittest.main()

