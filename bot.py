import os
import logging
import re
import requests
import asyncpraw
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp as youtube_dl
from bs4 import BeautifulSoup

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reddit API bağlantısı
reddit = asyncpraw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="TelegramBot/1.0"
)

async def cleanup():
    await reddit.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 Merhaba! Sosyal medya linklerini gönderin:\n- TikTok\n- Reddit\n- Twitter\n- YouTube")

async def download_tiktok(url: str) -> list:
    try:
        headers = {
            "X-RapidAPI-Key": TIKTOK_API_KEY,
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        response = requests.get(
            f"https://tiktok-video-no-watermark2.p.rapidapi.com/?url={url}",
            headers=headers,
            timeout=15
        )
        data = response.json()
        if data.get('data', {}).get('play'):
            return [{"type": "video", "url": data['data']['play']}]
        return []
    except Exception as e:
        logger.error(f"TikTok Error: {str(e)}")
        return []

async def download_reddit(url: str) -> list:
    try:
        # URL düzeltme
        url = re.sub(r'/s/(\w+)$', r'/comments/\1', url)
        if not re.search(r'/comments/|/r/', url):
            return []
            
        submission = await reddit.submission(url=url.split('?')[0])
        await submission.load()
        
        if getattr(submission, 'is_video', False):
            video_url = submission.media['reddit_video']['fallback_url']
            return [{"type": "video", "url": video_url.split('?')[0]}]
            
        elif hasattr(submission, 'gallery_data'):
            media_urls = []
            for item in submission.gallery_data['items']:
                media_url = submission.media_metadata[item['media_id']]['s']['u']
                media_url = media_url.replace('preview.redd.it', 'i.redd.it')
                media_urls.append({"type": "photo", "url": media_url})
            return media_urls
            
        elif submission.url.endswith(('jpg', 'jpeg', 'png', 'gif')):
            return [{"type": "photo", "url": submission.url}]
            
        return []
    except Exception as e:
        logger.error(f"Reddit Error: {str(e)}")
        return []

async def download_twitter(url: str) -> list:
    try:
        # 1. Yöntem: Twitter API
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
        if response.status_code == 200:
            data = response.json()
            if data.get('media'):
                return [{"type": "video", "url": data['media'][0]['url']}]
        
        # 2. Yöntem: TwitFix
        tweet_id = re.search(r'/status/(\d+)', url).group(1)
        response = requests.get(f"https://twitfix.onrender.com/{tweet_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('url'):
                return [{"type": "video", "url": data['url']}]
        
        # 3. Yöntem: Mobil sayfa
        headers = {'User-Agent': 'Mozilla/5.0'}
        mobile_url = url.replace("twitter.com", "mobile.twitter.com").replace("x.com", "mobile.twitter.com")
        response = requests.get(mobile_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        if video := soup.find('video'):
            video_url = video.get('src')
            if video_url:
                if not video_url.startswith('http'):
                    video_url = f"https:{video_url}"
                return [{"type": "video", "url": video_url}]
        
        return []
    except Exception as e:
        logger.error(f"Twitter Error: {str(e)}")
        return []

async def download_youtube(url: str) -> list:
    try:
        # YouTube API
        video_id = re.search(r'(?:v=|youtu\.be/)([\w-]+)', url).group(1)
        response = requests.get(
            f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=contentDetails",
            timeout=15
        )
        if response.status_code == 200:
            return [{"type": "video", "url": f"https://youtu.be/{video_id}"}]
        
        # yt-dlp fallback
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'geo_bypass': True,
            'socket_timeout': 15,
            'extract_flat': False
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'url' in info:
                return [{"type": "video", "url": info['url']}]
        
        return []
    except Exception as e:
        logger.error(f"YouTube Error: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    try:
        if 'tiktok.com' in url.lower():
            media = await download_tiktok(url)
            platform = "TikTok"
        elif 'reddit.com' in url.lower():
            media = await download_reddit(url)
            platform = "Reddit"
        elif 'twitter.com' in url.lower() or 'x.com' in url.lower():
            media = await download_twitter(url)
            platform = "Twitter"
        elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            media = await download_youtube(url)
            platform = "YouTube"
        else:
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı")
            return
        
        if not media:
            await update.message.reply_text(f"⚠️ {platform} içeriği indirilemedi")
            return
            
        for item in media:
            try:
                if item["type"] == "video":
                    await update.message.reply_video(
                        video=item["url"],
                        caption=f"🎥 {platform} videosu",
                        supports_streaming=True,
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30
                    )
                else:
                    await update.message.reply_photo(
                        photo=item["url"],
                        caption=f"📷 {platform} resmi",
                        read_timeout=30,
                        write_timeout=30
                    )
            except Exception as e:
                logger.error(f"Send Error: {str(e)}")
                await update.message.reply_text(f"⚠️ Gönderim hatası: {str(e)}")
    except Exception as e:
        logger.error(f"General Error: {str(e)}")
        await update.message.reply_text("⚠️ Bir hata oluştu, lütfen daha sonra tekrar deneyin")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    try:
        app.run_polling()
    finally:
        import asyncio
        asyncio.run(cleanup())
