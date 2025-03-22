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
    await update.message.reply_text('🎉 Merhaba! TikTok ve X (Twitter) linklerini gönder.')

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

async def download_twitter(url: str) -> list:
    """Twitter/X videosunu API ile indirir"""
    try:
        # Linki Twitsave API'sine uygun hale getir
        if 'x.com' in url:
            url = url.replace('x.com', 'twitter.com')  # x.com -> twitter.com
        
        # Twitsave API kullanımı
        response = requests.post("https://twitsave.com/info", data={"url": url})
        data = response.json()
        
        # Medya URL'lerini çek
        media_urls = []
        if "media" in data:
            for media in data["media"]:
                if media["type"] == "video":
                    media_urls.append(media["url"])
                elif media["type"] == "photo":
                    media_urls.append(media["url"])
        return media_urls
    except Exception as e:
        logger.error(f"Twitter/X API Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            # TikTok işlemleri
            video_url = await download_tiktok(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("✅ TikTok video indirildi")

        elif 'twitter.com' in url or 'x.com' in url:
            # Twitter/X işlemleri
            media_urls = await download_twitter(url)
            for media_url in media_urls:
                if media_url.endswith('.mp4'):
                    media_group.append(InputMediaVideo(requests.get(media_url).content))
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content))
            logger.info("✅ Twitter/X medya indirildi")

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
