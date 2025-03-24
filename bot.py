import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Güncel İndirme Servisleri (Sadece Twitter ve Reddit güncellendi)
SERVICES = {
    'twitter': 'https://twitsave.com',
    'reddit': 'https://redditsave.com'
}

# Kullanıcı agent bilgisi
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Merhaba! Şu platformlardan link gönderin:\n"
        "- TikTok\n"
        "- Reddit\n"
        "- Twitter/X\n\n"
        "⏳ İndirme işlemi biraz zaman alabilir..."
    )

async def download_tiktok(url: str) -> str:
    """TikTok video indirme fonksiyonu (Orjinal kod aynı kaldı)"""
    try:
        headers = {
            "X-RapidAPI-Key": os.getenv('TIKTOK_API_KEY'),
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        response = requests.get(
            f"https://tiktok-video-no-watermark2.p.rapidapi.com/?url={url}",
            headers=headers,
            timeout=15
        )
        data = response.json()
        return data.get('data', {}).get('play', '')
    except Exception as e:
        logger.error(f"TikTok Error: {str(e)}")
        return ''

async def download_twitter(url: str) -> str:
    """Twitter/X video indirme fonksiyonu (Yeni versiyon)"""
    try:
        # URL'yi standardize et
        clean_url = url.replace("x.com", "twitter.com").split('?')[0]
        
        # Twitsave API'si
        response = requests.post(
            f"{SERVICES['twitter']}/info",
            data={'url': clean_url},
            headers=HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('url', data.get('video_url', ''))
        return ''
    except Exception as e:
        logger.error(f"Twitter Error: {str(e)}", exc_info=True)
        return ''

async def download_reddit(url: str) -> str:
    """Reddit video/medya indirme fonksiyonu (Yeni versiyon)"""
    try:
        # RedditSave API'si
        response = requests.post(
            f"{SERVICES['reddit']}/info",
            data={'url': url},
            headers=HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('url', data.get('media_url', ''))
        return ''
    except Exception as e:
        logger.error(f"Reddit Error: {str(e)}", exc_info=True)
        return ''

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"Processing URL: {url}")

    try:
        # İşlem mesajını gönder
        processing_msg = await update.message.reply_text("⏳ İçerik indiriliyor, lütfen bekleyin...")
        
        if 'tiktok.com' in url.lower():
            video_url = await download_tiktok(url)
            await processing_msg.delete()
            
            if video_url:
                await update.message.reply_video(video=video_url)
            else:
                await update.message.reply_text("❌ TikTok içeriği indirilemedi. Linki kontrol edip tekrar deneyin.")

        elif 'reddit.com' in url.lower():
            media_url = await download_reddit(url)
            await processing_msg.delete()
            
            if media_url:
                if media_url.endswith(('.jpg', '.png', '.jpeg', '.gif')):
                    await update.message.reply_photo(photo=media_url)
                elif media_url.endswith(('.mp4', '.mov', '.webm')):
                    await update.message.reply_video(video=media_url)
                else:
                    await update.message.reply_text("ℹ️ İndirilen içerik desteklenmeyen bir formatta.")
            else:
                await update.message.reply_text("❌ Reddit içeriği indirilemedi. Linki kontrol edip tekrar deneyin.")

        elif 'twitter.com' in url.lower() or 'x.com' in url.lower():
            video_url = await download_twitter(url)
            await processing_msg.delete()
            
            if video_url:
                await update.message.reply_video(video=video_url)
            else:
                await update.message.reply_text("❌ Twitter/X içeriği indirilemedi. Linki kontrol edip tekrar deneyin.")

        else:
            await processing_msg.delete()
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı. Lütfen TikTok, Reddit veya Twitter/X linki gönderin.")

    except Exception as e:
        logger.error(f"Genel Hata: {str(e)}", exc_info=True)
        try:
            await processing_msg.delete()
        except:
            pass
        await update.message.reply_text("⚠️ İşlem sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot başlatılıyor...")
    app.run_polling()
