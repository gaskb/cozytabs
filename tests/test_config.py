import pytest
from config import Config

def test_config_validation_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key_456")
    monkeypatch.setenv("NOTION_TOKEN", "mock_notion_token_789")
    monkeypatch.setenv("NOTION_PARENT_PAGE_ID", "mock_page_id_abc")
    monkeypatch.setenv("ALLOWED_USER_IDS", "111,222,333")

    Config.reload()
    Config.validate()

    assert Config.TELEGRAM_BOT_TOKEN == "mock_bot_token_123"
    assert Config.GEMINI_API_KEY == "mock_gemini_key_456"
    assert Config.ALLOWED_USER_IDS == [111, 222, 333]
    assert Config.is_user_allowed(111) is True
    assert Config.is_user_allowed(999) is False

def test_config_validation_missing_key(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")
    monkeypatch.setenv("NOTION_TOKEN", "mock_notion")
    monkeypatch.setenv("NOTION_PARENT_PAGE_ID", "mock_page")
    monkeypatch.setenv("ALLOWED_USER_IDS", "123")

    Config.reload()
    with pytest.raises(ValueError) as excinfo:
        Config.validate()
    assert "TELEGRAM_BOT_TOKEN" in str(excinfo.value)
