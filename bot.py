import os
import logging
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Kendi botunuzun token'ı
TARGET_BOT_USERNAME = "@best_tiktok_downloader_bot"  # Hedef botun kullanıcı adı

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıya başlangıç mesajı gönderir."""
    await update.message.reply_text('🎉 Merhaba! TikTok linklerini veya hikayelerini gönder.')

async def download_tiktok(url: str) -> list:
    """TikTok videolarını ve resimlerini API ile indirir."""
    try:
        headers = {
            "X-RapidAPI-Key": os.getenv('TIKTOK_API_KEY'),
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
                media_urls.append(data["data"]["play"])
            if "images" in data["data"]:  # Resimler varsa
                media_urls.extend(data["data"]["images"])  # Tüm resimleri ekle
        return media_urls
    except Exception as e:
        logger.error(f"TikTok API Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan gelen mesajı işler ve TikTok medyasını gönderir."""
    url = update.message.text
    
    try:
        if 'tiktok.com' in url:
            # Önce TikTok API'si ile video veya resim indirmeyi dene
            media_urls = await download_tiktok(url)
            
            if media_urls:  # Video veya resim bulundu
                # Medya öğelerini tek tek gönder
                for media_url in media_urls:
                    try:
                        if media_url.endswith('.mp4'):
                            await update.message.reply_video(video=media_url)
                        else:
                            await update.message.reply_photo(photo=media_url)
                        logger.info(f"✅ TikTok medya gönderildi: {media_url}")
                    except Exception as e:
                        logger.error(f"⛔ Medya gönderim hatası: {str(e)}")
                        await update.message.reply_text(f"⚠️ Medya gönderilirken hata oluştu: {str(e)}")
            else:  # Video veya resim bulunamadı, hedef bota yönlendir
                await update.message.reply_text("⏳ TikTok hikayesi veya desteklenmeyen link, hedef bota yönlendiriliyor...")
                
                # Hedef bota linki gönder
                target_bot = Bot(token=TOKEN)
                await target_bot.send_message(chat_id=TARGET_BOT_USERNAME, text=url)
                
                # Hedef botun yanıtını bekleyin (örneğin, 10 saniye)
                await update.message.reply_text("✅ Hedef bot medyayı işliyor...")
        else:
            await update.message.reply_text("❌ Geçersiz TikTok linki.")
    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
