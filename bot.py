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

# İndirme Servisleri
SERVICES = {
    'twitter': 'https://ssstwitter.com/tr',
    'reddit': 'https://rapidsave.com/'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Merhaba! Şu platformlardan link gönderin:\n"
        "- TikTok\n"
        "- Reddit\n"
        "- Twitter/X\n\n"
        "⚠️ Not: Bazı linkler çalışmayabilir"
    )

async def download_tiktok(url: str) -> str:
    """TikTok indirme (orjinal kod aynı kaldı)"""
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

async def download_via_website(url: str, service: str) -> str:
    """Web arayüzü üzerinden indirme"""
    try:
        # SSSTwitter için özel işlem
        if service == 'twitter':
            # Twitter linkini düzelt
            clean_url = url.replace("x.com", "twitter.com").split('?')[0]
            payload = {
                'id': clean_url,
                'locale': 'tr'
            }
            response = requests.post(
                f"{SERVICES[service]}/api/index",
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=20
            )
            data = response.json()
            return data.get('url', '')

        # RapidSave için işlem
        elif service == 'reddit':
            session = requests.Session()
            response = session.get(SERVICES[service], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': '_token'})['value']
            
            payload = {
                '_token': csrf_token,
                'url': url
            }
            response = session.post(
                f"{SERVICES[service]}/info",
                data=payload,
                timeout=20
            )
            data = response.json()
            return data.get('data', {}).get('url', '')

    except Exception as e:
        logger.error(f"{service.upper()} Error: {str(e)}")
        return ''

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"Processing URL: {url}")

    try:
        if 'tiktok.com' in url.lower():
            # TikTok için orjinal fonksiyon
            video_url = await download_tiktok(url)
            if video_url:
                await update.message.reply_video(video=video_url)
            else:
                await update.message.reply_text("❌ TikTok içeriği indirilemedi")

        elif 'reddit.com' in url.lower():
            # RapidSave kullanımı
            processing_msg = await update.message.reply_text("⏳ Reddit içeriği indiriliyor...")
            video_url = await download_via_website(url, 'reddit')
            await processing_msg.delete()
            
            if video_url:
                if video_url.endswith(('.jpg', '.png', '.jpeg')):
                    await update.message.reply_photo(photo=video_url)
                else:
                    await update.message.reply_video(video=video_url)
            else:
                await update.message.reply_text("❌ Reddit içeriği indirilemedi")

        elif 'twitter.com' in url.lower() or 'x.com' in url.lower():
            # SSSTwitter kullanımı
            processing_msg = await update.message.reply_text("⏳ Twitter içeriği indiriliyor...")
            video_url = await download_via_website(url, 'twitter')
            await processing_msg.delete()
            
            if video_url:
                await update.message.reply_video(video=video_url)
            else:
                await update.message.reply_text("❌ Twitter içeriği indirilemedi")

        else:
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı")

    except Exception as e:
        logger.error(f"Genel Hata: {str(e)}")
        await update.message.reply_text("⚠️ İşlem sırasında bir hata oluştu")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
