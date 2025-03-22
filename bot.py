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
    await update.message.reply_text('🎉 Merhaba! TikTok linklerini gönder.')

async def download_tiktok(url: str) -> list:
    """TikTok videolarını ve resimlerini API ile indirir"""
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
        
        # API yanıtını logla
        logger.info(f"TikTok API Yanıtı: {data}")
        
        # Medya URL'lerini çek
        media_urls = []
        if "data" in data:
            media_urls.append(data["data"]["play"])  # Video URL'si
            if "images" in data["data"]:  # Resimler varsa
                for image in data["data"]["images"]:
                    media_urls.append(image)
        return media_urls
    except Exception as e:
        logger.error(f"TikTok API Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            # TikTok işlemleri
            media_urls = await download_tiktok(url)
            for media_url in media_urls:
                if media_url.endswith('.mp4'):
                    media_group.append(InputMediaVideo(requests.get(media_url).content))
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content))
            logger.info("✅ TikTok medya indirildi")

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
