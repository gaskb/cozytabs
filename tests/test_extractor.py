import os
import pytest
from extractor import extract_url_from_text


class FakeResponse:
    def __init__(
        self,
        *,
        status_code=200,
        json_data=None,
        content=b"",
        content_type="video/mp4",
        content_length=None,
        chunks=None,
    ):
        self.status_code = status_code
        self._json_data = json_data
        self._chunks = chunks if chunks is not None else [content]
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(content) if content_length is None else content_length),
        }

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size):
        assert chunk_size > 0
        for chunk in self._chunks:
            if isinstance(chunk, BaseException):
                raise chunk
            yield chunk

    def close(self):
        pass

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
    import requests
    from extractor import download_tiktok_direct

    def mock_get(url, *args, **kwargs):
        if "tikwm.com/api" in url:
            return FakeResponse(json_data={
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
            })
        return FakeResponse(content=b"fake mp4 video bytes" * 100)

    monkeypatch.setattr(requests, "get", mock_get)
    result = download_tiktok_direct("https://vm.tiktok.com/ZN8rhxqVP/", output_dir=str(tmp_path))
    assert result["id"] == "77777"
    assert result["title"] == "Riff TikWM"
    assert result["media_type"] == "video"
    assert os.path.exists(result["file_path"])

def test_download_tiktok_direct_photo_mock(monkeypatch, tmp_path):
    import requests
    from extractor import download_tiktok_direct

    def mock_get(url, *args, **kwargs):
        if "tikwm.com/api" in url:
            return FakeResponse(json_data={
                "code": 0,
                "data": {
                    "id": "88888",
                    "title": "Infografica TikWM",
                    "author": {"nickname": "GuitarTeacher"},
                    "duration": 0,
                    "cover": "https://example.com/cover.jpg",
                    "images": [f"https://example.com/img{index}.jpg" for index in range(7)]
                }
            })
        return FakeResponse(
            content=b"fake jpeg bytes" * 100,
            content_type="image/jpeg",
        )

    monkeypatch.setattr(requests, "get", mock_get)
    result = download_tiktok_direct("https://vm.tiktok.com/ZN8rY8VRW/", output_dir=str(tmp_path))
    assert result["id"] == "88888"
    assert result["media_type"] == "photo"
    assert len(result["image_paths"]) == 7


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "payload non valido"),
        ({"code": 0, "data": []}, "dati media validi"),
        ({"code": 0, "data": {"images": "not-a-list"}}, "lista immagini non valida"),
        ({"code": 0, "data": {"images": ["not-a-url"]}}, "URL immagini non validi"),
        ({"code": 0, "data": {}}, "Nessun flusso video"),
    ],
)
def test_download_tiktok_direct_rejects_invalid_payload(monkeypatch, tmp_path, payload, message):
    import requests
    from extractor import download_tiktok_direct

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(json_data=payload))

    with pytest.raises(ValueError, match=message):
        download_tiktok_direct("https://vm.tiktok.com/invalid/", output_dir=str(tmp_path))


def test_download_tiktok_direct_encodes_source_url(monkeypatch, tmp_path):
    import requests
    from extractor import download_tiktok_direct

    calls = []

    def mock_get(url, *args, **kwargs):
        calls.append((url, kwargs))
        if "tikwm.com/api" in url:
            return FakeResponse(json_data={
                "code": 0,
                "data": {"id": "99999", "play": "https://example.com/video.mp4"},
            })
        return FakeResponse(content=b"video" * 300)

    monkeypatch.setattr(requests, "get", mock_get)
    source_url = "https://vm.tiktok.com/ZM8abcde/?foo=1&bar=2"

    download_tiktok_direct(source_url, output_dir=str(tmp_path))

    assert calls[0][0] == "https://www.tikwm.com/api/"
    assert calls[0][1]["params"] == {"url": source_url}


def test_safe_download_stream_rejects_oversized_response(monkeypatch, tmp_path):
    import requests
    from extractor import MAX_DOWNLOAD_BYTES, _safe_download_stream

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(content_length=MAX_DOWNLOAD_BYTES + 1),
    )
    destination = tmp_path / "large.mp4"

    with pytest.raises(ValueError, match="dimensione massima"):
        _safe_download_stream("https://example.com/large.mp4", str(destination), {}, ("video/",))

    assert not destination.exists()
    assert not (tmp_path / "large.mp4.part").exists()


def test_safe_download_stream_removes_partial_file_on_failure(monkeypatch, tmp_path):
    import requests
    from extractor import _safe_download_stream

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            content_type="image/jpeg",
            chunks=[b"image" * 300, requests.exceptions.ChunkedEncodingError("truncated")],
        ),
    )
    destination = tmp_path / "image.jpg"

    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        _safe_download_stream("https://example.com/image.jpg", str(destination), {}, ("image/",))

    assert not destination.exists()
    assert not (tmp_path / "image.jpg.part").exists()


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (FakeResponse(status_code=500), "status 500"),
        (FakeResponse(content_type="text/html", content=b"error" * 300), "Tipo di contenuto"),
    ],
)
def test_safe_download_stream_rejects_invalid_response(monkeypatch, tmp_path, response, message):
    import requests
    from extractor import _safe_download_stream

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(ValueError, match=message):
        _safe_download_stream("https://example.com/media", str(tmp_path / "media.mp4"), {}, ("video/",))


def test_safe_download_stream_propagates_timeout(monkeypatch, tmp_path):
    import requests
    from extractor import _safe_download_stream

    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("read timeout")

    monkeypatch.setattr(requests, "get", raise_timeout)

    with pytest.raises(requests.Timeout):
        _safe_download_stream("https://example.com/media", str(tmp_path / "media.mp4"), {}, ("video/",))

