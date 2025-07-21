import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
        self.EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
        self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
        self.EMAIL_FROM = os.getenv('EMAIL_FROM', 'medtrack@example.com')
        self.EMAIL_USE_TLS = os.getenv(
            'EMAIL_USE_TLS', 'True').lower() == 'true'
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

