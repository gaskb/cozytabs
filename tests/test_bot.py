import html
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from bot import PROCESSING_SEMAPHORE, start_command
from config import Config

def test_html_escaping_in_messages():
    raw_uploader = "guitar_master_99 <pro>"
    safe_uploader = html.escape(raw_uploader)
    assert safe_uploader == "guitar_master_99 &lt;pro&gt;"
    assert "_" in safe_uploader

def test_semaphore_limit():
    assert PROCESSING_SEMAPHORE._value <= 2

def test_inline_keyboard_creation():
    notion_url = "https://notion.so/test-page"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎸 Apri Scheda su Notion", url=notion_url)]
    ])
    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "🎸 Apri Scheda su Notion"
    assert keyboard.inline_keyboard[0][0].url == notion_url

@pytest.mark.asyncio
async def test_start_command_allowed(monkeypatch):
    monkeypatch.setattr(Config, "is_user_allowed", lambda uid: True)
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    await start_command(update, context)

    assert update.effective_message.reply_text.called
    args, kwargs = update.effective_message.reply_text.call_args
    assert "CozyTabs Bot" in args[0]
    assert kwargs.get("parse_mode") == ParseMode.HTML

@pytest.mark.asyncio
async def test_start_command_denied(monkeypatch):
    monkeypatch.setattr(Config, "is_user_allowed", lambda uid: False)
    update = MagicMock()
    update.effective_user.id = 99999
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    await start_command(update, context)

    assert update.effective_message.reply_text.called
    args, _ = update.effective_message.reply_text.call_args
    assert "riservato ad utenti autorizzati" in args[0]
