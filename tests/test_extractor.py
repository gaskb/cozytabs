import os
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

def test_download_video_failure(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from extractor import download_video
    import yt_dlp

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.side_effect = Exception("Video non disponibile o privato")
    mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__enter__.return_value = mock_ydl_instance

    monkeypatch.setattr(yt_dlp, "YoutubeDL", mock_ydl_class)

    with pytest.raises(RuntimeError, match="Errore download media"):
        download_video("https://instagram.com/reel/nonexistent/", output_dir=str(tmp_path))

def test_download_tiktok_direct_video_mock(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    import requests
    from extractor import download_tiktok_direct

    def mock_get(url, *args, **kwargs):
        res = MagicMock()
        res.status_code = 200
        if "tikwm.com/api" in url:
            res.json.return_value = {
                "code": 0,
                "data": {
                    "id": "77777",
                    "title": "Riff TikWM",
                    "author": {"nickname": "GuitarGod"},
                    "duration": 30,
                    "cover": "https://example.com/cover.jpg",
                    "play": "https://example.com/video.mp4",
                    "images": None
                }
            }
        else:
            res.content = b"fake mp4 video bytes" * 100
        return res

    monkeypatch.setattr(requests, "get", mock_get)
    result = download_tiktok_direct("https://vm.tiktok.com/ZN8rhxqVP/", output_dir=str(tmp_path))
    assert result["id"] == "77777"
    assert result["title"] == "Riff TikWM"
    assert result["media_type"] == "video"
    assert os.path.exists(result["file_path"])

def test_download_tiktok_direct_photo_mock(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    import requests
    from extractor import download_tiktok_direct

    def mock_get(url, *args, **kwargs):
        res = MagicMock()
        res.status_code = 200
        if "tikwm.com/api" in url:
            res.json.return_value = {
                "code": 0,
                "data": {
                    "id": "88888",
                    "title": "Infografica TikWM",
                    "author": {"nickname": "GuitarTeacher"},
                    "duration": 0,
                    "cover": "https://example.com/cover.jpg",
                    "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
                }
            }
        else:
            res.content = b"fake jpeg bytes" * 100
        return res

    monkeypatch.setattr(requests, "get", mock_get)
    result = download_tiktok_direct("https://vm.tiktok.com/ZN8rY8VRW/", output_dir=str(tmp_path))
    assert result["id"] == "88888"
    assert result["media_type"] == "photo"
    assert len(result["image_paths"]) == 2

