import os
import logging
import requests
from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from tiktok_api import TikTokApi

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Merhaba! TikTok ve Twitter linklerini bana gönderin.')

def download_tiktok(url):
    api = TikTokApi()
    video = api.get_video_by_url(url)
    return video

def download_twitter(url):
    # Twitter indirme mantığı (API veya web scraping)
    # Örnek bir servis kullanımı (Değiştirmeniz gerekebilir)
    response = requests.get(f"https://twdown.net/download.php?url={url}")
    # HTML parsing ile medya URL'leri çekilir
    # Bu kısım Twitter'ın API politikasına göre özelleştirilmeli
    return media_urls

async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    media_group = []
    
    if 'tiktok.com' in url:
        video_bytes = download_tiktok(url)
        media_group.append(InputMediaVideo(video_bytes))
    elif 'twitter.com' in url:
        media_urls = download_twitter(url)
        for media_url in media_urls:
            if media_url.endswith('.mp4'):
                media_group.append(InputMediaVideo(media_url))
            else:
                media_group.append(InputMediaPhoto(media_url))
    
    if media_group:
        await update.message.reply_media_group(media=media_group)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
