import pytest
from unittest.mock import patch, MagicMock
from config import Config
from analyzer import GuitarLesson, Chord
from notion_sync import publish_to_notion, split_text_chunks

def test_split_text_chunks_short():
    text = "Short line"
    chunks = split_text_chunks(text, max_length=50)
    assert chunks == ["Short line"]

def test_split_text_chunks_long():
    lines = ["Line " + str(i) for i in range(100)]
    long_text = "\n".join(lines)
    chunks = split_text_chunks(long_text, max_length=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 100
    assert "\n".join(chunks) == long_text

def test_notion_publish_database_mode(monkeypatch):
    monkeypatch.setattr(Config, "NOTION_DATABASE_ID", "mock-database-id-123")
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "id": "mock-page-id",
        "url": "https://notion.so/test-page"
    }

    lesson = GuitarLesson(
        title="Progressione Test",
        tuning="Standard",
        capo="Capotasto al 2° tasto",
        key="C",
        progression="C -> G",
        chords=[Chord(name="C", fingering="x32010", description="Do")],
        tablature="e|---|\nB|---|",
        right_hand_technique="Plettro",
        execution_tips=["Rilassa il polso"],
        summary="Test riassunto"
    )

    with patch("requests.post", mock_post):
        url = publish_to_notion(
            lesson,
            "https://tiktok.com/@test/123",
            "TestCreator",
            cover_url="https://example.com/cover.jpg",
            media_type="video"
        )
        assert url == "https://notion.so/test-page"
        assert mock_post.called
        called_json = mock_post.call_args[1]["json"]
        assert called_json["parent"]["database_id"] == Config.NOTION_DATABASE_ID
        assert called_json["properties"]["Titolo"]["title"][0]["text"]["content"] == "Progressione Test"
        assert called_json["properties"]["Autore"]["rich_text"][0]["text"]["content"] == "TestCreator"
        assert called_json["properties"]["Tonalità"]["select"]["name"] == "C"
        assert called_json["properties"]["Formato"]["select"]["name"] == "Video Lezione"
        assert called_json["properties"]["Link Originale"]["url"] == "https://tiktok.com/@test/123"
        assert called_json["cover"]["external"]["url"] == "https://example.com/cover.jpg"

def test_notion_publish_page_fallback(monkeypatch):
    monkeypatch.setattr(Config, "NOTION_DATABASE_ID", "")
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "id": "mock-page-id",
        "url": "https://notion.so/test-page"
    }

    lesson = GuitarLesson(
        title="Progressione Fallback",
        tuning="Standard",
        capo="Nessuno",
        key="Am",
        progression="Am -> F",
        chords=[Chord(name="Am", fingering="x02210", description="La minore")],
        tablature="",
        right_hand_technique="Arpeggio",
        execution_tips=[],
        summary="Test fallback"
    )

    with patch("requests.post", mock_post):
        url = publish_to_notion(lesson, "https://tiktok.com/@test/456", "FallbackCreator")
        assert url == "https://notion.so/test-page"
        assert mock_post.called
        called_json = mock_post.call_args[1]["json"]
        assert "page_id" in called_json["parent"]
        assert called_json["properties"]["title"]["title"][0]["text"]["content"] == "Progressione Fallback"

def test_notion_publish_uploads_all_photo_images_in_order(tmp_path):
    image_paths = []
    for index in range(2):
        image_path = tmp_path / f"photo_{index}.jpg"
        image_path.write_bytes(b"jpeg-data" * 200)
        image_paths.append(str(image_path))

    upload_one = MagicMock(status_code=200)
    upload_one.json.return_value = {"id": "upload-one"}
    send_one = MagicMock(status_code=200)
    upload_two = MagicMock(status_code=200)
    upload_two.json.return_value = {"id": "upload-two"}
    send_two = MagicMock(status_code=200)
    page_response = MagicMock(status_code=200)
    page_response.json.return_value = {"id": "page-id", "url": "https://notion.so/photo-page"}
    mock_post = MagicMock(side_effect=[upload_one, send_one, upload_two, send_two, page_response])

    lesson = GuitarLesson(title="Carosello Test")
    with patch("requests.post", mock_post):
        page_url = publish_to_notion(
            lesson,
            "https://tiktok.com/@test/photo/123",
            "PhotoCreator",
            media_type="photo",
            image_paths=image_paths,
        )

    assert page_url == "https://notion.so/photo-page"
    page_body = mock_post.call_args_list[-1].kwargs["json"]
    image_blocks = [block for block in page_body["children"] if block["type"] == "image"]
    assert [block["image"]["file_upload"]["id"] for block in image_blocks] == ["upload-one", "upload-two"]
    assert mock_post.call_args_list[1].kwargs["headers"].get("Content-Type") is None
    assert mock_post.call_args_list[3].kwargs["headers"].get("Content-Type") is None

def test_notion_publish_ignores_missing_photo_files(tmp_path):
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "page-id", "url": "https://notion.so/test-page"}

    with patch("requests.post", mock_post):
        publish_to_notion(
            GuitarLesson(title="Immagine Assente"),
            "https://tiktok.com/@test/photo/456",
            "PhotoCreator",
            media_type="photo",
            image_paths=[str(tmp_path / "missing.jpg")],
        )

    page_body = mock_post.call_args.kwargs["json"]
    assert not any(block["type"] == "image" for block in page_body["children"])

def test_notion_publish_http_error(monkeypatch):
    mock_post = MagicMock()
    mock_post.return_value.status_code = 403
    mock_post.return_value.text = "Forbidden - Invalid Notion Token"

    lesson = GuitarLesson(title="Test Errore")
    with patch("requests.post", mock_post):
        with pytest.raises(RuntimeError, match="Errore Notion API \\(403\\)"):
            publish_to_notion(lesson, "https://example.com/riff", "Creator")

def test_notion_publish_timeout(monkeypatch):
    import requests
    mock_post = MagicMock(side_effect=requests.exceptions.Timeout("Connection timed out"))

    lesson = GuitarLesson(title="Test Timeout")
    with patch("requests.post", mock_post):
        with pytest.raises(requests.exceptions.Timeout):
            publish_to_notion(lesson, "https://example.com/riff", "Creator")

def test_notion_publish_handles_partial_image_upload_failure(tmp_path):
    image_paths = []
    for index in range(2):
        image_path = tmp_path / f"photo_{index}.jpg"
        image_path.write_bytes(b"jpeg-data" * 200)
        image_paths.append(str(image_path))

    # First image fails creation (HTTP 500), second succeeds, page creation succeeds
    upload_fail = MagicMock(status_code=500, text="Internal Server Error")
    upload_two = MagicMock(status_code=200)
    upload_two.json.return_value = {"id": "upload-two"}
    send_two = MagicMock(status_code=200)
    page_response = MagicMock(status_code=200)
    page_response.json.return_value = {"id": "page-id", "url": "https://notion.so/partial-photo-page"}
    mock_post = MagicMock(side_effect=[upload_fail, upload_two, send_two, page_response])

    lesson = GuitarLesson(title="Carosello Con Fallimento Singolo")
    with patch("requests.post", mock_post):
        page_url = publish_to_notion(
            lesson,
            "https://tiktok.com/@test/photo/123",
            "PhotoCreator",
            media_type="photo",
            image_paths=image_paths,
        )

    assert page_url == "https://notion.so/partial-photo-page"
    page_body = mock_post.call_args_list[-1].kwargs["json"]
    image_blocks = [block for block in page_body["children"] if block["type"] == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["image"]["file_upload"]["id"] == "upload-two"

