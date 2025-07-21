import unittest
from unittest.mock import patch


class TestConfig(unittest.TestCase):

    @patch.dict('os.environ', {
        'EMAIL_HOST': 'smtp.test.com',
        'EMAIL_PORT': '465',
        'EMAIL_USERNAME': 'testuser',
        'EMAIL_PASSWORD': 'testpass',
        'EMAIL_FROM': 'noreply@test.com',
        'EMAIL_USE_TLS': 'False',
    })
    def test_config_values_from_env(self):
        from app.config import Config

        cfg = Config()

        self.assertEqual(cfg.EMAIL_HOST, 'smtp.test.com')
        self.assertEqual(cfg.EMAIL_PORT, 465)  # Now an int
        self.assertEqual(cfg.EMAIL_USERNAME, 'testuser')
        self.assertEqual(cfg.EMAIL_PASSWORD, 'testpass')
        self.assertEqual(cfg.EMAIL_FROM, 'noreply@test.com')
        self.assertFalse(cfg.EMAIL_USE_TLS)  # Now a boolean


if __name__ == '__main__':
    unittest.main()
