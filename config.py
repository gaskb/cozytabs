import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "1.0.0"
API_VERSION = "1.0.0"

class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "").strip()
    NOTION_PARENT_PAGE_ID: str = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/cozytabs").strip()
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip()

    # Parsed allowed users
    _raw_users = os.getenv("ALLOWED_USER_IDS", "").strip()
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip()) for uid in _raw_users.split(",") if uid.strip().isdigit()
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
