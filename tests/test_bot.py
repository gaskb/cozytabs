import html
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.constants import ParseMode
from bot import PROCESSING_SEMAPHORE

def test_html_escaping_in_messages():
    raw_uploader = "guitar_master_99 <pro>"
    safe_uploader = html.escape(raw_uploader)
    assert safe_uploader == "guitar_master_99 &lt;pro&gt;"
    assert "_" in safe_uploader  # In HTML, underscore is safe without crashing!

def test_semaphore_limit():
    assert PROCESSING_SEMAPHORE._value <= 2
