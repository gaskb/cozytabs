import os
import re
import logging
import requests
from typing import Dict, Any, Optional, List
import yt_dlp

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MIN_MEDIA_BYTES = 1000
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 30
DOWNLOAD_CHUNK_SIZE = 64 * 1024

URL_REGEX = re.compile(
    r"(https?://(?:www\.|vm\.|vt\.)?(?:tiktok\.com|instagram\.com|youtube\.com|youtu\.be)/[^\s]+)"
)

def _safe_download_stream(
    url: str,
    destination: str,
    headers: Dict[str, str],
    allowed_content_types: tuple[str, ...],
) -> int:
    """Scarica un media con limiti di dimensione e scrittura atomica."""
    response = None
    temporary_path = f"{destination}.part"

    try:
        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        )
        if response.status_code != 200:
            raise ValueError(f"Download media fallito con status {response.status_code}")

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if not content_type or not any(content_type.startswith(prefix) for prefix in allowed_content_types):
            raise ValueError(f"Tipo di contenuto non supportato: {content_type or 'assente'}")

        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError as error:
                raise ValueError("Content-Length non valido") from error
            if declared_size > MAX_DOWNLOAD_BYTES:
                raise ValueError("Il media supera la dimensione massima consentita")

        downloaded_bytes = 0
        with open(temporary_path, "wb") as media_file:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if not chunk:
                    continue
                downloaded_bytes += len(chunk)
                if downloaded_bytes > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Il media supera la dimensione massima consentita")
                media_file.write(chunk)

        if downloaded_bytes < MIN_MEDIA_BYTES:
            raise ValueError("Il media scaricato e' troppo piccolo o incompleto")

        os.replace(temporary_path, destination)
        return downloaded_bytes
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise
    finally:
        if response is not None:
            response.close()

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
        "max_filesize": MAX_DOWNLOAD_BYTES,
    }

    # Controllo cookie
    from config import Config
    cookies_path = Config.COOKIES_FILE
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

            thumbnail_url = info.get("thumbnail") or (thumb_urls[0] if 'thumb_urls' in locals() and thumb_urls else "")

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
                    "thumbnail_url": thumbnail_url,
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
                    "thumbnail_url": thumbnail_url,
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
                for idx, t_url in enumerate(thumb_urls):
                    dest_img = os.path.join(output_dir, f"photo_{video_id}_{idx}.jpg")
                    try:
                        downloaded_bytes = _safe_download_stream(
                            t_url, dest_img, headers, ("image/",)
                        )
                        image_paths.append(dest_img)
                        logger.info("Scaricata immagine %d: %s (%d bytes)", idx, dest_img, downloaded_bytes)
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
                    "thumbnail_url": thumb_urls[0] if thumb_urls else (info.get("thumbnail") or ""),
                }

    except Exception as e:
        logger.warning("Download primario yt-dlp non riuscito: %s", e)
        is_tiktok = any(d in url.lower() for d in ["tiktok.com", "vm.tiktok", "vt.tiktok"])
        if is_tiktok:
            logger.info("Rilevato link TikTok (%s). Avvio fallback tramite API diretta...", url)
            try:
                return download_tiktok_direct(url, output_dir)
            except Exception as fb_err:
                logger.error("Anche il fallback diretto TikTok ha fallito: %s", fb_err)
                raise RuntimeError(f"Errore download media TikTok: {fb_err}") from fb_err

        logger.error("Errore irreversibile durante il download con yt-dlp: %s", e)
        raise RuntimeError(f"Errore download media: {e}") from e

def download_tiktok_direct(url: str, output_dir: str = "/tmp/cozytabs") -> Dict[str, Any]:
    """
    Scarica video o caroselli fotografici da TikTok tramite endpoint diretto TikWM.
    Bypassa le restrizioni di login obbligatorio e i redirect dei link brevi (vm.tiktok.com).
    """
    os.makedirs(output_dir, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    logger.info("Chiamata endpoint TikWM per URL: %s", url)
    resp = requests.get(
        "https://www.tikwm.com/api/",
        params={"url": url},
        headers=headers,
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )
    if resp.status_code != 200:
        raise ValueError(f"Endpoint TikWM non raggiungibile (HTTP {resp.status_code})")

    try:
        res_json = resp.json()
    except ValueError as error:
        raise ValueError("TikWM ha restituito una risposta JSON non valida") from error

    if not isinstance(res_json, dict):
        raise ValueError("TikWM ha restituito un payload non valido")
    if res_json.get("code") != 0:
        err_msg = res_json.get("msg") or "Dati non disponibili o video privato"
        raise ValueError(f"TikWM: {err_msg}")

    data = res_json.get("data")
    if not isinstance(data, dict):
        raise ValueError("TikWM non ha restituito dati media validi")

    video_id = str(data.get("id") or "tiktok_media")
    title = data.get("title") or "Riff o Lezione di Chitarra"
    author_info = data.get("author") or {}
    if not isinstance(author_info, dict):
        author_info = {}
    uploader = author_info.get("nickname") or author_info.get("unique_id") or "TikTok Creator"
    duration = data.get("duration", 0)
    thumbnail_url = data.get("cover") or data.get("origin_cover") or ""

    images = data.get("images") or []
    if not isinstance(images, list):
        raise ValueError("TikWM ha restituito una lista immagini non valida")
    if images and not all(isinstance(image_url, str) and image_url.startswith(("http://", "https://")) for image_url in images):
        raise ValueError("TikWM ha restituito URL immagini non validi")

    if images:
        # Carosello fotografico / Photo Mode
        logger.info("TikWM: rilevato carosello fotografico con %d immagini", len(images))
        image_paths: List[str] = []
        for idx, img_url in enumerate(images):
            dest_img = os.path.join(output_dir, f"photo_{video_id}_{idx}.jpg")
            try:
                downloaded_bytes = _safe_download_stream(
                    img_url, dest_img, headers, ("image/",)
                )
                image_paths.append(dest_img)
                logger.info("Scaricata immagine carosello %d: %s (%d bytes)", idx, dest_img, downloaded_bytes)
            except Exception as img_err:
                logger.warning("Errore scaricamento immagine %d (%s): %s", idx, img_url, img_err)

        if not image_paths:
            raise ValueError("Impossibile scaricare le immagini del carosello TikTok")

        return {
            "id": video_id,
            "title": title,
            "uploader": uploader,
            "url": url,
            "duration": 0,
            "media_type": "photo",
            "file_path": image_paths[0],
            "image_paths": image_paths,
            "thumbnail_url": thumbnail_url or images[0],
        }
    else:
        # Video MP4 normale
        play_url = data.get("play") or data.get("wmplay")
        if not isinstance(play_url, str) or not play_url.startswith(("http://", "https://")):
            raise ValueError("Nessun flusso video trovato nei dati restituiti da TikTok")

        mp4_file = os.path.join(output_dir, f"{video_id}.mp4")
        logger.info("TikWM: scaricamento video da CDN verso %s...", mp4_file)
        downloaded_bytes = _safe_download_stream(
            play_url, mp4_file, headers, ("video/", "application/octet-stream")
        )

        logger.info("Download video TikTok completato: %s (%d bytes)", mp4_file, downloaded_bytes)
        return {
            "id": video_id,
            "title": title,
            "uploader": uploader,
            "url": url,
            "duration": duration,
            "media_type": "video",
            "file_path": mp4_file,
            "image_paths": [],
            "thumbnail_url": thumbnail_url,
        }

