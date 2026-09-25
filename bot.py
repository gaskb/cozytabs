import os
import shutil
import logging
import asyncio
from telegram import Update
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risponde al comando /start verificando l'ID utente."""
    user = update.effective_user
    if not user or not Config.is_user_allowed(user.id):
        logger.warning("Accesso negato per user_id=%s (@%s)", user.id if user else "None", user.username if user else "None")
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Spiacente, questo bot è riservato ad utenti autorizzati.")
        return

    msg = (
        f"🎸 **CozyTabs Bot v{APP_VERSION}**\n\n"
        "Ciao Gas! Inviami o condividi qui qualsiasi link di **TikTok**, **Instagram Reels** o **YouTube Shorts** che parla di chitarra, arpeggi o accordi.\n\n"
        "Dietro le quinte:\n"
        "1. Scarico il video in background.\n"
        "2. Gemini analizza i fotogrammi e trascrive accordi, diteggiature e tablatura.\n"
        "3. Creo automaticamente la scheda su Notion sotto **🎸 CozyTabs** per la tua postazione studio!"
    )
    if update.effective_message:
        await update.effective_message.reply_markdown(msg)

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
        "🎸 Ricevuto! Scarico il media ed elaboro gli accordi con Gemini... un attimo di pazienza."
    )

    work_dir = os.path.join(Config.DOWNLOAD_DIR, f"task_{message.message_id}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        # 1. Download video o immagini (Photo Mode)
        logger.info("Avvio download per URL: %s", url)
        video_info = await asyncio.to_thread(download_video, url, work_dir)
        video_path = video_info["file_path"]

        # 2. Analisi multimodale Gemini
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
        logger.info("Pubblicazione scheda su Notion...")
        notion_url = await asyncio.to_thread(
            publish_to_notion,
            lesson,
            url,
            video_info.get("uploader", "")
        )

        # 4. Risposta finale
        preview_block = ""
        if lesson.tablature and lesson.tablature.strip():
            preview_block = f"**Tablatura:**\n```\n{lesson.tablature.strip()}\n```\n\n"
        elif lesson.progression:
            preview_block = f"🎶 **Progressione:** `{lesson.progression}`\n\n"
        elif lesson.chords:
            chords_str = ", ".join([f"{c.name} ({c.fingering})" for c in lesson.chords[:5]])
            preview_block = f"🎼 **Accordi:** {chords_str}\n\n"

        response_text = (
            f"✅ **Scheda pronta su Notion!**\n\n"
            f"🎸 **{lesson.title}**\n"
            f"👤 Autore: {video_info.get('uploader')}\n"
            f"🎵 Tonalità: `{lesson.key or 'N/D'}` | ⚙️ Accordatura: `{lesson.tuning}`\n"
            f"Capotasto: `{lesson.capo}`\n\n"
            f"{preview_block}"
            f"👉 [Apri la scheda su Notion]({notion_url})"
        )
        await status_msg.edit_text(response_text, parse_mode="Markdown", disable_web_page_preview=True)
        logger.info("Elaborazione completata con successo per URL: %s", url)

    except Exception as e:
        logger.error("Errore durante l'elaborazione: %s", e, exc_info=True)
        error_msg = (
            f"❌ **Si è verificato un errore durante l'elaborazione del video:**\n\n"
            f"`{str(e)}`\n\n"
            "Verifica che il video sia pubblico e accessibile e riprova."
        )
        await status_msg.edit_text(error_msg, parse_mode="Markdown")

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

    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
