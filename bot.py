import os
import logging
import requests
from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')  # RapidAPI'den alınan API anahtarı

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 Merhaba! TikTok/Twitter linklerini gönder.')

async def download_tiktok(url: str) -> str:
    """TikTok videosunu API ile indirir"""
    try:
        headers = {
            "X-RapidAPI-Key": TIKTOK_API_KEY,
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(
            "https://tiktok-video-no-watermark2.p.rapidapi.com/",
            headers=headers,
            params=params
        )
        data = response.json()
        return data["data"]["play"]  # İndirilebilir video URL'si
    except Exception as e:
        logger.error(f"TikTok API Hatası: {str(e)}")
        raise

async def download_twitter(url: str) -> str:
    """Twitter videosunu API ile indirir"""
    try:
        response = requests.get(f"https://twitsave.com/info?url={url}")
        data = response.json()
        return data["video"][0]["url"]  # İndirilebilir video URL'si
    except Exception as e:
        logger.error(f"Twitter API Hatası: {str(e)}")
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            video_url = await download_tiktok(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("✅ TikTok video indirildi")

        elif 'twitter.com' in url:
            video_url = await download_twitter(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("✅ Twitter video indirildi")

        if media_group:
            await update.message.reply_media_group(media=media_group)
        else:
            await update.message.reply_text("❌ Desteklenmeyen link formatı")

    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
