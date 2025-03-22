import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Kendi botunuzun token'ı
TIKTOK_TARGET_BOT = "@best_tiktok_downloader_bot"  # TikTok hedef botu
X_TARGET_BOT = "@twitterimage_bot"  # X (Twitter) hedef botu
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')  # TikTok API anahtarı

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıya başlangıç mesajı gönderir."""
    await update.message.reply_text('🎉 Merhaba! TikTok veya X (Twitter) linklerini gönder.')

async def download_tiktok(url: str) -> list:
    """TikTok videolarını ve resimlerini API ile indirir."""
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
            if "play" in data["data"]:  # Video URL'si
                media_urls.append({"type": "video", "url": data["data"]["play"]})
            if "images" in data["data"]:  # Resimler varsa
                for image in data["data"]["images"]:
                    media_urls.append({"type": "photo", "url": image})
        return media_urls
    except Exception as e:
        logger.error(f"TikTok API Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan gelen mesajı işler ve TikTok veya X medyasını gönderir."""
    url = update.message.text
    
    try:
        if 'tiktok.com' in url:  # TikTok linki
            # Önce TikTok API'si ile video veya resim indirmeyi dene
            media_urls = await download_tiktok(url)
            
            if media_urls:  # Video veya resim bulundu
                # Medya öğelerini tek tek gönder
                for media in media_urls:
                    try:
                        if media["type"] == "video":
                            await update.message.reply_video(video=media["url"])
                        elif media["type"] == "photo":
                            await update.message.reply_photo(photo=media["url"])
                        logger.info(f"✅ TikTok medya gönderildi: {media['url']}")
                    except Exception as e:
                        logger.error(f"⛔ Medya gönderim hatası: {str(e)}")
                        await update.message.reply_text(f"⚠️ Medya gönderilirken hata oluştu: {str(e)}")
            else:  # Video veya resim bulunamadı, TikTok hedef bota yönlendir
                await update.message.reply_text(
                    f"⏳ TikTok hikayesi veya desteklenmeyen link. "
                    f"Lütfen bu linki şu bota gönderin: {TIKTOK_TARGET_BOT}"
                )

        elif 'x.com' in url or 'twitter.com' in url:  # X (Twitter) linki
            await update.message.reply_text(
                f"⏳ X (Twitter) linki. "
                f"Lütfen bu linki şu bota gönderin: {X_TARGET_BOT}\n\n"
                f"⚠️ Not: Bu bot medyayı dosya olarak gönderebilir. "
                f"Eğer medyayı doğrudan resim veya video olarak indirmek istiyorsanız, "
                f"başka bir bot veya uygulama kullanmanız gerekecektir."
            )

        else:
            await update.message.reply_text("❌ Geçersiz link. Sadece TikTok veya X (Twitter) linkleri desteklenmektedir.")
    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
