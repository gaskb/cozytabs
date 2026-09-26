import os
import re
import logging
import urllib.request
from typing import Dict, Any, Optional, List
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
    Scarica il video o le immagini (per i post in Photo Mode) tramite yt-dlp.
    Supporta cookie da file (cookies.txt) o da browser.
    Restituisce un dizionario con metadati, media_type ('video' o 'photo'), file_path ed eventuali image_paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Normalizzazione URL TikTok: i post fotografici hanno /photo/ nel path che yt-dlp
    # non riconosce direttamente, mentre /video/ permette l'estrazione completa dei metadati.
    normalized_url = url.replace("/photo/", "/video/")

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
            logger.info("Estrazione metadati per: %s", normalized_url)
            info = ydl.extract_info(normalized_url, download=True)
            if not info:
                raise ValueError("Impossibile estrarre informazioni dal media")

            video_id = str(info.get("id", "media"))
            title = info.get("title") or "Riff o Lezione di Chitarra"
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Sconosciuto"
            duration = info.get("duration", 0)

            # Verifica se è presente uno stream video effettivo
            has_video_stream = any(f.get("vcodec") != "none" for f in info.get("formats", []))
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_file = f"{base}.mp4"

            if has_video_stream and os.path.exists(mp4_file):
                return {
                    "id": video_id,
                    "title": title,
                    "uploader": uploader,
                    "url": info.get("webpage_url") or url,
                    "duration": duration,
                    "media_type": "video",
                    "file_path": mp4_file,
                    "image_paths": [],
                }
            elif has_video_stream and os.path.exists(filename):
                return {
                    "id": video_id,
                    "title": title,
                    "uploader": uploader,
                    "url": info.get("webpage_url") or url,
                    "duration": duration,
                    "media_type": "video",
                    "file_path": filename,
                    "image_paths": [],
                }
            else:
                # Post fotografico (Photo Mode / Infografica)
                logger.info("Rilevato post in Photo Mode / Infografica senza flusso video. Download immagini...")
                thumbnails = info.get("thumbnails", [])
                image_paths: List[str] = []

                # Cerca originCover o cover tra i thumbnail
                thumb_urls = []
                for t in thumbnails:
                    u = t.get("url")
                    if u and u not in thumb_urls:
                        # Preferisci originCover o cover
                        if t.get("id") in ("originCover", "cover"):
                            thumb_urls.insert(0, u)
                        else:
                            thumb_urls.append(u)

                # Scarica la/le immagini migliori
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                for idx, t_url in enumerate(thumb_urls[:3]):
                    dest_img = os.path.join(output_dir, f"photo_{video_id}_{idx}.jpg")
                    try:
                        req = urllib.request.Request(t_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=15) as resp, open(dest_img, "wb") as out_f:
                            out_f.write(resp.read())
                        if os.path.exists(dest_img) and os.path.getsize(dest_img) > 1000:
                            image_paths.append(dest_img)
                            logger.info("Scaricata immagine %d: %s (%d bytes)", idx, dest_img, os.path.getsize(dest_img))
                    except Exception as img_err:
                        logger.warning("Errore download thumbnail %s: %s", t_url, img_err)

                if not image_paths:
                    raise ValueError("Nessuna immagine valida trovata per il post fotografico.")

                return {
                    "id": video_id,
                    "title": title,
                    "uploader": uploader,
                    "url": info.get("webpage_url") or url,
                    "duration": 0,
                    "media_type": "photo",
                    "file_path": image_paths[0],
                    "image_paths": image_paths,
                }

    except Exception as e:
        logger.error("Errore durante il download con yt-dlp: %s", e)
        raise RuntimeError(f"Errore download media: {e}") from e

