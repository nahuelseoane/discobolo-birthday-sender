import os
from dotenv import load_dotenv
load_dotenv()

# Paths (written by the GitHub Action)
CREDENTIALS_PATH = os.getenv("CREDENTIALS_PATH")
TOKEN_PATH = os.getenv("TOKEN_PATH")

# Gmail SMTP
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

# Google Contacts group
GMAIL_GROUP_ID = os.getenv("GMAIL_GROUP_ID", "DIFUSION SOCIOS 2025")
GMAIL_FALLBACK_ID = os.getenv("GMAIL_FALLBACK_ID")
