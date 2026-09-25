import pytest
from config import Config

def test_config_validation():
    # Verifica che la configurazione sia valida
    Config.validate()
    assert Config.TELEGRAM_BOT_TOKEN != ""
    assert Config.GEMINI_API_KEY != ""
    assert Config.NOTION_TOKEN != ""
    assert Config.NOTION_PARENT_PAGE_ID != ""
    assert 12345678 in Config.ALLOWED_USER_IDS

def test_user_whitelist():
    assert Config.is_user_allowed(12345678) is True
    assert Config.is_user_allowed(99999999) is False
