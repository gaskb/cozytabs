import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "1.3.3"
API_VERSION = "1.3.3"
UI_VERSION = "1.3.3"

class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "").strip()
    NOTION_PARENT_PAGE_ID: str = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "00000000-0000-0000-0000-000000000000").strip()
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/cozytabs").strip()
    COOKIES_FILE: str = os.getenv("COOKIES_FILE", "").strip()
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip()

    # Parsed allowed users
    _raw_users = os.getenv("ALLOWED_USER_IDS", "").strip()
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip()) for uid in _raw_users.split(",") if uid.strip().isdigit()
    ]

    @classmethod
    def reload(cls):
        """Ricarica i parametri di configurazione dall'ambiente (utile per test o reload dinamici)."""
        cls.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        cls.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        cls.NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
        cls.NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
        cls.NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "00000000-0000-0000-0000-000000000000").strip()
        cls.DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/cozytabs").strip()
        cls.COOKIES_FILE = os.getenv("COOKIES_FILE", "").strip()
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip()
        raw_users = os.getenv("ALLOWED_USER_IDS", "").strip()
        cls.ALLOWED_USER_IDS = [
            int(uid.strip()) for uid in raw_users.split(",") if uid.strip().isdigit()
        ]

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.NOTION_TOKEN:
            missing.append("NOTION_TOKEN")
        if not cls.NOTION_PARENT_PAGE_ID:
            missing.append("NOTION_PARENT_PAGE_ID")
        if not cls.ALLOWED_USER_IDS:
            missing.append("ALLOWED_USER_IDS")

        if missing:
            raise ValueError(f"Variabili di configurazione mancanti: {', '.join(missing)}")

    @classmethod
    def is_user_allowed(cls, user_id: int) -> bool:
        return user_id in cls.ALLOWED_USER_IDS
