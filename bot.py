import os
import html
import shutil
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import Config, APP_VERSION, API_VERSION
from extractor import extract_url_from_text, download_video
from analyzer import analyze_guitar_video
from notion_sync import publish_to_notion

# Configurazione logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger("cozytabs")

# Limite di concorrenza per evitare saturazione di memoria/CPU nell'homelab
PROCESSING_SEMAPHORE = asyncio.Semaphore(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risponde al comando /start verificando l'ID utente."""
    user = update.effective_user
    if not user or not Config.is_user_allowed(user.id):
        logger.warning("Accesso negato per user_id=%s (@%s)", user.id if user else "None", user.username if user else "None")
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Spiacente, questo bot è riservato ad utenti autorizzati.")
        return

    msg = (
        f"🎸 <b>CozyTabs Bot v{APP_VERSION}</b>\n\n"
        "Ciao Gas! Inviami o condividi qui qualsiasi link di <b>TikTok</b>, <b>Instagram Reels</b> o <b>YouTube Shorts</b> che parla di chitarra, arpeggi o accordi.\n\n"
        "Dietro le quinte:\n"
        "1. Scarico il video o le infografiche in background.\n"
        "2. Gemini analizza i fotogrammi e trascrive accordi, diteggiature e tablatura.\n"
        "3. Creo automaticamente la scheda su Notion sotto <b>🎸 CozyTabs</b> per la tua postazione studio!"
    )
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi di testo contenenti URL."""
    user = update.effective_user
    if not user or not Config.is_user_allowed(user.id):
        logger.warning("Messaggio ignorato da utente non autorizzato: %s", user.id if user else "None")
        return

    message = update.effective_message
    if not message or not message.text:
        return

    url = extract_url_from_text(message.text)
    if not url:
        await message.reply_text(
            "🎸 Invia un link TikTok, Instagram Reel o YouTube Shorts valido per iniziare la trascrizione."
        )
        return

    # Feedback immediato
    status_msg = await message.reply_text(
        "🎸 Ricevuto! In attesa di elaborazione..."
    )

    work_dir = os.path.join(Config.DOWNLOAD_DIR, f"task_{message.message_id}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        async with PROCESSING_SEMAPHORE:
            # 1. Download video o immagini (Photo Mode)
            await status_msg.edit_text("⏳ <b>[1/3]</b> Scarico il media da analizzare...", parse_mode=ParseMode.HTML)
            logger.info("Avvio download per URL: %s", url)
            video_info = await asyncio.to_thread(download_video, url, work_dir)
            video_path = video_info["file_path"]

            # 2. Analisi multimodale Gemini
            await status_msg.edit_text("🧠 <b>[2/3]</b> Analisi armonica e diteggiature con Gemini Vision...", parse_mode=ParseMode.HTML)
            logger.info("Avvio analisi Gemini per: %s", video_path)
            lesson = await asyncio.to_thread(
                analyze_guitar_video,
                video_path,
                Config.GEMINI_API_KEY,
                video_info.get("title", ""),
                video_info.get("uploader", ""),
                video_info.get("image_paths", [])
            )

            # 3. Creazione pagina Notion
            await status_msg.edit_text("📝 <b>[3/3]</b> Creo la scheda formattata su Notion...", parse_mode=ParseMode.HTML)
            logger.info("Pubblicazione scheda su Notion...")
            notion_url = await asyncio.to_thread(
                publish_to_notion,
                lesson,
                url,
                video_info.get("uploader", "")
            )

            # 4. Risposta finale formattata in HTML sicuro con Inline Keyboard
            safe_title = html.escape(lesson.title or "Senza Titolo")
            safe_uploader = html.escape(video_info.get("uploader") or "Sconosciuto")
            safe_key = html.escape(lesson.key or "N/D")
            safe_tuning = html.escape(lesson.tuning or "Standard")
            safe_capo = html.escape(lesson.capo or "Nessuno")

            preview_block = ""
            if lesson.tablature and lesson.tablature.strip():
                clean_tab = lesson.tablature.strip()
                if len(clean_tab) > 800:
                    clean_tab = clean_tab[:800] + "\n..."
                preview_block = f"<b>Tablatura:</b>\n<pre>{html.escape(clean_tab)}</pre>\n\n"
            elif lesson.progression:
                preview_block = f"🎶 <b>Progressione:</b> <code>{html.escape(lesson.progression)}</code>\n\n"
            elif lesson.chords:
                chords_str = ", ".join([f"{html.escape(c.name)} ({html.escape(c.fingering)})" for c in lesson.chords[:5]])
                preview_block = f"🎼 <b>Accordi:</b> {chords_str}\n\n"

            response_text = (
                f"✅ <b>Scheda pronta su Notion!</b>\n\n"
                f"🎸 <b>{safe_title}</b>\n"
                f"👤 Autore: {safe_uploader}\n"
                f"🎵 Tonalità: <code>{safe_key}</code> | ⚙️ Accordatura: <code>{safe_tuning}</code>\n"
                f"Capotasto: <code>{safe_capo}</code>\n\n"
                f"{preview_block}"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎸 Apri Scheda su Notion", url=notion_url)]
            ])

            await status_msg.edit_text(
                response_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            logger.info("Elaborazione completata con successo per URL: %s", url)

    except Exception as e:
        logger.error("Errore durante l'elaborazione di %s: %s", url, e, exc_info=True)
        # Mostra un messaggio di errore pulito e sicuro, privo di dump interni
        safe_err_text = html.escape(str(e)[:300])
        error_msg = (
            "❌ <b>Si è verificato un errore durante l'elaborazione del video:</b>\n\n"
            f"<code>{safe_err_text}</code>\n\n"
            "Verifica che il link sia pubblico e accessibile e riprova."
        )
        try:
            await status_msg.edit_text(error_msg, parse_mode=ParseMode.HTML)
        except Exception as edit_err:
            logger.warning("Impossibile modificare il messaggio di errore: %s", edit_err)

    finally:
        # Pulizia file temporanei scaricati
        if os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir)
            except Exception as clean_err:
                logger.warning("Errore pulizia directory temporanea %s: %s", work_dir, clean_err)

def main():
    Config.validate()
    logger.info("Avvio CozyTabs Bot v%s (API v%s)...", APP_VERSION, API_VERSION)
    logger.info("Utenti autorizzati: %s", Config.ALLOWED_USER_IDS)

    # Pulizia preventiva della directory temporanea
    if os.path.exists(Config.DOWNLOAD_DIR):
        logger.info("Pulizia preventiva della cartella di download: %s", Config.DOWNLOAD_DIR)
        for item in os.listdir(Config.DOWNLOAD_DIR):
            item_path = os.path.join(Config.DOWNLOAD_DIR, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                logger.warning("Impossibile rimuovere %s: %s", item_path, e)

    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

