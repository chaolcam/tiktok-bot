import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp as youtube_dl
from bs4 import BeautifulSoup
import asyncpraw as praw
import re

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reddit API bağlantısı (AsyncPRAW)
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="TelegramBot/1.0"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıya başlangıç mesajı gönderir."""
    help_text = """
🎉 Merhaba! Sosyal medya linklerini gönderin:
- TikTok (video/resim)
- Reddit (video/resim)
- Twitter (video/resim)
- YouTube (video/shorts)
"""
    await update.message.reply_text(help_text)

def is_tiktok(url):
    return "tiktok.com" in url.lower()

def is_reddit(url):
    return "reddit.com" in url.lower()

def is_twitter(url):
    return "twitter.com" in url.lower() or "x.com" in url.lower()

def is_youtube(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

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
            params=params,
            timeout=15
        )
        data = response.json()
        
        media_urls = []
        if "data" in data:
            if "play" in data["data"]:
                media_urls.append({"type": "video", "url": data["data"]["play"]})
            if "images" in data["data"]:
                for image in data["data"]["images"]:
                    media_urls.append({"type": "photo", "url": image})
        return media_urls
    except Exception as e:
        logger.error(f"TikTok Hatası: {str(e)}")
        return []

async def download_reddit(url: str) -> list:
    """Reddit gönderilerini indirir."""
    try:
        # URL düzeltme
        url = re.sub(r'/s/(\w+)$', r'/comments/\1', url)
        
        if not any(p in url for p in ['/comments/', '/r/']):
            return []
            
        submission = await reddit.submission(url=url.split('?')[0])
        await submission.load()
        
        media_urls = []
        
        # Video
        if getattr(submission, 'is_video', False):
            try:
                video_url = submission.media['reddit_video']['fallback_url'].split('?')[0]
                media_urls.append({"type": "video", "url": video_url})
            except:
                pass
        
        # Galeri
        elif hasattr(submission, 'gallery_data'):
            try:
                for item in submission.gallery_data['items']:
                    media_id = item['media_id']
                    media_url = submission.media_metadata[media_id]['s']['u']
                    media_url = media_url.replace('preview.redd.it', 'i.redd.it')
                    media_urls.append({"type": "photo", "url": media_url})
            except:
                pass
        
        # Tek resim
        elif submission.url.endswith(('jpg', 'jpeg', 'png', 'gif')):
            media_urls.append({"type": "photo", "url": submission.url})
            
        return media_urls
    except Exception as e:
        logger.error(f"Reddit Hatası: {str(e)}")
        return []

async def download_twitter(url: str) -> list:
    """Twitter gönderilerini indirir."""
    try:
        # API alternatifleri
        apis = [
            f"https://twitfix.onrender.com/{url.split('/')[-1]}",
            f"https://twitsave.com/info?url={url}",
            f"https://vxtwitter.com/{url.split('twitter.com/')[-1]}"
        ]
        
        for api_url in apis:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('media'):
                        return [{"type": "video", "url": data['media'][0]['url']}]
                    elif data.get('url'):
                        return [{"type": "video", "url": data['url']}]
            except:
                continue
        
        # Son çare: Mobil sayfa
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Pixel 3)'}
        mobile_url = url.replace("twitter.com", "mobile.twitter.com").replace("x.com", "mobile.twitter.com")
        response = requests.get(mobile_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Video
        if video := soup.find('video'):
            if video_url := video.get('src'):
                return [{"type": "video", "url": f"https:{video_url}" if not video_url.startswith('http') else video_url}]
        
        # Resimler
        return [{"type": "photo", "url": f"https:{img['src']}"} for img in soup.select('img[alt="Image"]') if 'profile_images' not in img['src']]
        
    except Exception as e:
        logger.error(f"Twitter Hatası: {str(e)}")
        return []

async def download_youtube(url: str) -> list:
    """YouTube videolarını indirir."""
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': True,
        'geo_bypass': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    }
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            return [{"type": "video", "url": info['url'], "title": info.get('title', '')}]
    except Exception as e:
        logger.error(f"YouTube Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı mesajlarını işler."""
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
        return await update.message.reply_text("⚠️ Desteklenmeyen link formatı.")
    
    if not media:
        return await update.message.reply_text(f"⚠️ {platform} içeriği indirilemedi. Linki kontrol edin.")
    
    for item in media:
        try:
            if item["type"] == "video":
                await update.message.reply_video(video=item["url"], caption=f"🎥 {platform}")
            else:
                await update.message.reply_photo(photo=item["url"], caption=f"📷 {platform}")
        except Exception as e:
            logger.error(f"Gönderim Hatası: {str(e)}")
            await update.message.reply_text(f"⚠️ Medya gönderilemedi: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
