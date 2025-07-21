import unittest
from unittest.mock import patch, MagicMock

class TestEmailService(unittest.TestCase):

    @patch("app.email_service.smtplib.SMTP")  # patch where it's used
    @patch("app.email_service.Config")        # patch config to avoid using real .env
    def test_send_email_success(self, mock_config_class, mock_smtp):
        # Mock config values
        mock_config = MagicMock()
        mock_config.EMAIL_FROM = "noreply@test.com"
        mock_config.EMAIL_HOST = "smtp.test.com"
        mock_config.EMAIL_PORT = 587
        mock_config.EMAIL_USERNAME = "user@test.com"
        mock_config.EMAIL_PASSWORD = "password"
        mock_config_class.return_value = mock_config

        # Mock SMTP object
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Import after patching
        from app.email_service import EmailService

        service = EmailService()
        result = service.send_email("to@example.com", "Test Subject", "<p>Hello</p>")

        # ✅ Assertions
        self.assertTrue(result)
        mock_smtp.assert_called_with("smtp.test.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_with("user@test.com", "password")
        mock_smtp_instance.send_message.assert_called_once()

    @patch("app.email_service.EmailService.send_email")
    def test_send_medication_reminder(self, mock_send_email):
        # Setup
        mock_send_email.return_value = True

        from app.email_service import EmailService

        service = EmailService()
        result = service.send_medication_reminder(
            patient_email="user@example.com",
            medicine_name="Paracetamol",
            dosage="500mg",
            time_of_day="morning"
        )

        self.assertTrue(result)

        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        self.assertIn("Paracetamol", args[1])  # subject
        self.assertIn("500mg", args[2])        # body
        self.assertIn("Morning", args[2])      # capitalized time

if __name__ == "__main__":
    unittest.main()
