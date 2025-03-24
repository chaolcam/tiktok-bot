import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp as youtube_dl
from bs4 import BeautifulSoup

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')  # Twitter241 API key
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # YouTube API key

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 Merhaba! TikTok/Reddit/Twitter/YouTube linklerini gönderin")

def is_tiktok(url):
    return "tiktok.com" in url.lower()

def is_reddit(url):
    return "reddit.com" in url.lower()

def is_twitter(url):
    return "twitter.com" in url.lower() or "x.com" in url.lower()

def is_youtube(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

async def download_tiktok(url: str) -> list:
    """TikTok indirme (mevcut kodunuz aynı kaldı)"""
    try:
        headers = {
            "X-RapidAPI-Key": TIKTOK_API_KEY,
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        params = {"url": url}
        response = requests.get(
            "https://tiktok-video-no-watermark2.p.rapidapi.com/",
            headers=headers,
            params=params,
            timeout=15
        )
        data = response.json()
        if "data" in data:
            if "play" in data["data"]:
                return [{"type": "video", "url": data["data"]["play"]}]
        return []
    except Exception as e:
        logger.error(f"TikTok Hatası: {str(e)}")
        return []

async def download_twitter(url: str) -> list:
    """Twitter241 API entegrasyonu"""
    try:
        headers = {
            "X-RapidAPI-Key": TWITTER_API_KEY,
            "X-RapidAPI-Host": "twitter241.p.rapidapi.com"
        }
        params = {"url": url}
        
        response = requests.get(
            "https://twitter241.p.rapidapi.com/api/v1/get_tweet",
            headers=headers,
            params=params,
            timeout=15
        )
        data = response.json()
        
        # API yanıt formatına göre işlem
        if data.get('media'):
            return [{"type": "video", "url": data['media'][0]['url']}]
        
        # Alternatif yöntem
        return await _twitter_fallback(url)
        
    except Exception as e:
        logger.error(f"Twitter API Hatası: {str(e)}")
        return await _twitter_fallback(url)

async def _twitter_fallback(url: str) -> list:
    """Twitter için yedek yöntem"""
    try:
        # 1. TwitFix
        tweet_id = url.split('/')[-1].split('?')[0]
        response = requests.get(f"https://twitfix.onrender.com/{tweet_id}", timeout=10)
        if response.status_code == 200:
            return [{"type": "video", "url": response.json().get('url')}]
        
        # 2. Mobil sayfa
        headers = {'User-Agent': 'Mozilla/5.0'}
        mobile_url = url.replace("twitter.com", "mobile.twitter.com")
        response = requests.get(mobile_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        if video := soup.find('video'):
            return [{"type": "video", "url": f"https:{video['src']}"}]
            
        return []
    except Exception as e:
        logger.error(f"Twitter Yedek Hatası: {str(e)}")
        return []

async def download_youtube(url: str) -> list:
    """YouTube Data API v3 entegrasyonu"""
    try:
        # YouTube API ile
        video_id = url.split('v=')[-1].split('&')[0]
        response = requests.get(
            f"https://www.googleapis.com/youtube/v3/videos?part=player&id={video_id}&key={YOUTUBE_API_KEY}",
            timeout=15
        )
        if response.status_code == 200:
            return [{"type": "video", "url": f"https://youtu.be/{video_id}"}]
        
        # yt-dlp fallback
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'ignoreerrors': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'url' in info:
                return [{"type": "video", "url": info['url']}]
        
        return []
    except Exception as e:
        logger.error(f"YouTube Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if is_tiktok(url):
        media = await download_tiktok(url)
        platform = "TikTok"
    elif is_reddit(url):
        media = await download_reddit(url)
        platform = "Reddit"
    elif is_twitter(url):
        media = await download_twitter(url)
        platform = "Twitter"
    elif is_youtube(url):
        media = await download_youtube(url)
        platform = "YouTube"
    else:
        return await update.message.reply_text("⚠️ Desteklenmeyen link formatı")
    
    if not media:
        return await update.message.reply_text(f"⚠️ {platform} içeriği indirilemedi")
    
    try:
        if media[0]["type"] == "video":
            await update.message.reply_video(video=media[0]["url"])
        else:
            await update.message.reply_photo(photo=media[0]["url"])
    except Exception as e:
        logger.error(f"Gönderim Hatası: {str(e)}")
        await update.message.reply_text(f"⚠️ İçerik gönderilemedi: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
