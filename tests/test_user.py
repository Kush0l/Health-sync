import unittest
from unittest.mock import patch, MagicMock
from app.user import User
import bcrypt


class TestUser(unittest.TestCase):
    def setUp(self):
        # Patch GeminiService only for tests to avoid API key errors
        patcher = patch('app.user.GeminiService')
        self.mock_gemini_class = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_db = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_db.get_collection.return_value = self.mock_collection
        self.user = User(self.mock_db)

    @patch('builtins.input', side_effect=["Test User", "test@example.com", "patient"])
    @patch('getpass.getpass', return_value="secure123")
    def test_register_success(self, mock_getpass, mock_input):
        self.mock_collection.find_one.return_value = None
        self.mock_collection.insert_one.return_value.inserted_id = "mocked_user_id"

        result = self.user.register()
        self.assertEqual(result, "mocked_user_id")

    @patch('builtins.input', side_effect=["Test User", "invalidemail", "doctor"])
    @patch('getpass.getpass', return_value="secure123")
    def test_register_invalid_email(self, mock_getpass, mock_input):
        result = self.user.register()
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=["Test User", "test@example.com", "doctor"])
    @patch('getpass.getpass', return_value="123")
    def test_register_short_password(self, mock_getpass, mock_input):
        self.mock_collection.find_one.return_value = None
        result = self.user.register()
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=["Test User", "test@example.com", "invalidrole"])
    @patch('getpass.getpass', return_value="secure123")
    def test_register_invalid_role(self, mock_getpass, mock_input):
        self.mock_collection.find_one.return_value = None
        result = self.user.register()
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=["test@example.com"])
    @patch('getpass.getpass', return_value="secure123")
    def test_login_success(self, mock_getpass, mock_input):
        hashed_pw = bcrypt.hashpw("secure123".encode(), bcrypt.gensalt())
        self.mock_collection.find_one.return_value = {
            "name": "Test User",
            "email": "test@example.com",
            "password": hashed_pw,
            "role": "doctor"
        }

        user = self.user.login()
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Test User")

    @patch('builtins.input', side_effect=["test@example.com"])
    @patch('getpass.getpass', return_value="wrongpass")
    def test_login_invalid_password(self, mock_getpass, mock_input):
        hashed_pw = bcrypt.hashpw("secure123".encode(), bcrypt.gensalt())
        self.mock_collection.find_one.return_value = {
            "name": "Test User",
            "email": "test@example.com",
            "password": hashed_pw,
            "role": "doctor"
        }

        user = self.user.login()
        self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
