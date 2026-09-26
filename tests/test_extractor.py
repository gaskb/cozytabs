import pytest
from extractor import extract_url_from_text

def test_extract_url_tiktok():
    text = "Guarda questo riff https://www.tiktok.com/@janersarias/video/7673962323874172180 stupendo!"
    url = extract_url_from_text(text)
    assert url == "https://www.tiktok.com/@janersarias/video/7673962323874172180"

def test_extract_url_short_tiktok():
    text = "https://vm.tiktok.com/ZM8abcde/"
    url = extract_url_from_text(text)
    assert url == "https://vm.tiktok.com/ZM8abcde/"

def test_extract_url_reels():
    text = "Ecco https://www.instagram.com/reel/C34xyz987/ per chitarra"
    url = extract_url_from_text(text)
    assert url == "https://www.instagram.com/reel/C34xyz987/"

def test_extract_url_tiktok_photo():
    text = "Guarda questa infografica https://www.tiktok.com/@raphael.matos27/photo/7688776423246417173 utilissima"
    url = extract_url_from_text(text)
    assert url == "https://www.tiktok.com/@raphael.matos27/photo/7688776423246417173"

def test_extract_url_none():
    text = "Ciao come stai nessun link qui"
    url = extract_url_from_text(text)
    assert url is None

def test_download_video_mock(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from extractor import download_video
    import yt_dlp

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        "id": "12345",
        "title": "Mock Riff",
        "uploader": "Guitarist",
        "webpage_url": "https://tiktok.com/@g/video/12345",
        "duration": 15,
        "formats": [{"vcodec": "h264"}],
    }
    # Create fake downloaded file
    fake_mp4 = tmp_path / "12345.mp4"
    fake_mp4.write_text("dummy video")
    mock_ydl_instance.prepare_filename.return_value = str(fake_mp4)

    mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__enter__.return_value = mock_ydl_instance

    monkeypatch.setattr(yt_dlp, "YoutubeDL", mock_ydl_class)

    result = download_video("https://tiktok.com/@g/video/12345", output_dir=str(tmp_path))
    assert result["id"] == "12345"
    assert result["media_type"] == "video"
    assert result["file_path"] == str(fake_mp4)

