import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Kendi botunuzun token'ı
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')  # Twitter API anahtarı (örneğin, RapidAPI'den alınan)

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıya başlangıç mesajı gönderir."""
    await update.message.reply_text('🎉 Merhaba! Twitter linklerini gönder.')

async def download_twitter(url: str) -> list:
    """Twitter medyalarını API ile indirir."""
    try:
        headers = {
            "X-RapidAPI-Key": TWITTER_API_KEY,
            "X-RapidAPI-Host": "twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(
            "https://twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com/video",
            headers=headers,
            params=params
        )
        data = response.json()
        
        # API yanıtını logla
        logger.info(f"Twitter API Yanıtı: {data}")
        
        # Medya URL'lerini çek
        media_urls = []
        if "media" in data:
            for media in data["media"]:
                if media["type"] == "video":
                    media_urls.append({"type": "video", "url": media["url"]})
                elif media["type"] == "image":
                    media_urls.append({"type": "photo", "url": media["url"]})
        return media_urls
    except Exception as e:
        logger.error(f"Twitter API Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan gelen mesajı işler ve Twitter medyasını gönderir."""
    url = update.message.text
    
    try:
        if 'twitter.com' in url or 'x.com' in url:  # Twitter linki
            # Twitter API'si ile medya indirmeyi dene
            media_urls = await download_twitter(url)
            
            if media_urls:  # Medya bulundu
                # Medya öğelerini tek tek gönder
                for media in media_urls:
                    try:
                        if media["type"] == "video":
                            await update.message.reply_video(video=media["url"])
                        elif media["type"] == "photo":
                            await update.message.reply_photo(photo=media["url"])
                        logger.info(f"✅ Twitter medya gönderildi: {media['url']}")
                    except Exception as e:
                        logger.error(f"⛔ Medya gönderim hatası: {str(e)}")
                        await update.message.reply_text(f"⚠️ Medya gönderilirken hata oluştu: {str(e)}")
            else:  # Medya bulunamadı
                await update.message.reply_text("❌ Twitter medyası bulunamadı.")
        else:
            await update.message.reply_text("❌ Geçersiz link. Sadece Twitter linkleri desteklenmektedir.")
    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
