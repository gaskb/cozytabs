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
