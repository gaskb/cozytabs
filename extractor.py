import os
import re
import logging
from typing import Dict, Any, Optional
import yt_dlp

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r"(https?://(?:www\.|vm\.|vt\.)?(?:tiktok\.com|instagram\.com|youtube\.com|youtu\.be)/[^\s]+)"
)

def extract_url_from_text(text: str) -> Optional[str]:
    """Cerca e restituisce il primo link supportato (TikTok, Instagram, YouTube) presente nel testo."""
    match = URL_REGEX.search(text)
    if match:
        return match.group(1)
    return None

def download_video(url: str, output_dir: str = "/tmp/cozytabs") -> Dict[str, Any]:
    """
    Scarica il video tramite yt-dlp in formato MP4 e restituisce metadati e path del file.
    Supporta cookie da file (cookies.txt) o da browser.
    """
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 50 * 1024 * 1024,
    }

    # Controllo cookie
    cookies_path = os.getenv("COOKIES_FILE", "")
    if not cookies_path or not os.path.exists(cookies_path):
        candidate = os.path.join(os.path.dirname(__file__), "cookies.txt")
        if os.path.exists(candidate):
            cookies_path = candidate

    if cookies_path and os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path
        logger.info("Utilizzo file cookie: %s", cookies_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Estrazione metadati per: %s", url)
            info = ydl.extract_info(url, download=True)
            if not info:
                raise ValueError("Impossibile estrarre informazioni dal video")

            video_id = info.get("id", "video")
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            actual_file = f"{base}.mp4"
            if not os.path.exists(actual_file):
                actual_file = filename

            return {
                "id": video_id,
                "title": info.get("title") or "Riff di Chitarra",
                "uploader": info.get("uploader") or info.get("channel") or info.get("creator") or "Sconosciuto",
                "url": info.get("webpage_url") or url,
                "duration": info.get("duration", 0),
                "file_path": actual_file,
            }
    except Exception as e:
        logger.error("Errore durante il download con yt-dlp: %s", e)
        raise RuntimeError(f"Errore download video: {e}") from e
