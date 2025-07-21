import unittest
from unittest.mock import patch, MagicMock


class TestDatabase(unittest.TestCase):

    # Patch the MongoClient used inside your class
    @patch("app.database.MongoClient")
    def test_get_collection_returns_correct_collection(self, mock_mongo_client):
        # Mock the client and db
        mock_client_instance = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Set up mock behavior
        # mock_client["medtrack"] -> mock_db
        mock_client_instance.__getitem__.return_value = mock_db
        # mock_db["patients"] -> mock_collection
        mock_db.__getitem__.return_value = mock_collection
        # MongoClient() -> mock_client_instance
        mock_mongo_client.return_value = mock_client_instance

        # Import after patch to avoid early execution
        from app.database import Database

        db = Database()
        result = db.get_collection("patients")

        # Check the right collection is accessed
        mock_client_instance.__getitem__.assert_called_with("medtrack")
        mock_db.__getitem__.assert_called_with("patients")
        self.assertEqual(result, mock_collection)


if __name__ == "__main__":
    unittest.main()
