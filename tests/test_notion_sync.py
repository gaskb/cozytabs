import pytest
from unittest.mock import patch, MagicMock
from analyzer import GuitarLesson, Chord
from notion_sync import publish_to_notion

def test_notion_publish_mock(monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "id": "mock-page-id",
        "url": "https://notion.so/test-page"
    }

    lesson = GuitarLesson(
        title="Progressione Test",
        tuning="Standard",
        capo="Nessuno",
        key="C",
        progression="C -> G",
        chords=[Chord(name="C", fingering="x32010", description="Do")],
        tablature="e|---|\nB|---|",
        right_hand_technique="Plettro",
        execution_tips=["Rilassa il polso"],
        summary="Test riassunto"
    )

    with patch("requests.post", mock_post):
        url = publish_to_notion(lesson, "https://tiktok.com/@test/123", "TestCreator")
        assert url == "https://notion.so/test-page"
        assert mock_post.called
        called_json = mock_post.call_args[1]["json"]
        assert called_json["properties"]["title"]["title"][0]["text"]["content"] == "Progressione Test"
