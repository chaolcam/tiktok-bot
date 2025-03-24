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
    await update.message.reply_text(
        "🎉 Merhaba! Sosyal medya linklerini gönderin:\n"
        "- TikTok\n- Reddit\n- Twitter/X\n- YouTube/Shorts\n\n"
        "⚠️ Not: Bazı linkler çalışmayabilir, alternatif link deneyin"
    )

async def download_tiktok(url: str) -> list:
    try:
        headers = {
            "X-RapidAPI-Key": TIKTOK_API_KEY,
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        response = requests.get(
            f"https://tiktok-video-no-watermark2.p.rapidapi.com/?url={url}",
            headers=headers,
            timeout=20
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
        # Yeni ve eski Reddit URL formatlarını işle
        if '/s/' in url:  # Yeni Reddit formatı
            post_id = url.split('/s/')[-1].split('/')[0]
            url = f"https://old.reddit.com/comments/{post_id}"
        else:  # Eski format
            url = url.replace("www.reddit.com", "old.reddit.com")
        
        logger.info(f"Processing Reddit URL: {url}")
        
        submission = await reddit.submission(url=url.split('?')[0])
        await submission.load()
        
        # Video içeriği
        if getattr(submission, 'is_video', False):
            video_url = submission.media['reddit_video']['fallback_url']
            return [{"type": "video", "url": video_url.split('?')[0]}]
            
        # Direkt medya linki (resim veya video)
        if submission.url.endswith(('jpg', 'jpeg', 'png', 'gif', 'mp4')):
            return [{
                "type": "video" if submission.url.endswith('mp4') else "photo",
                "url": submission.url
            }]
            
        return []
    except Exception as e:
        logger.error(f"Reddit Error (URL: {url}): {str(e)}")
        return []

async def download_twitter(url: str) -> list:
    try:
        # URL'yi standart forma dönüştür (x.com -> twitter.com)
        url = url.replace("x.com", "twitter.com").split('?')[0]
        
        # 1. Yöntem: Twitter API
        headers = {
            "X-RapidAPI-Key": TWITTER_API_KEY,
            "X-RapidAPI-Host": "twitter241.p.rapidapi.com"
        }
        response = requests.get(
            f"https://twitter241.p.rapidapi.com/api/v1/get_tweet?url={url}",
            headers=headers,
            timeout=20
        )
        
        logger.info(f"Twitter API Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('media'):
                media_url = data['media'][0]['url']
                if media_url.startswith('http'):
                    return [{"type": "video", "url": media_url}]
        
        # 2. Yöntem: TwitFix
        tweet_id = re.search(r'/status/(\d+)', url)
        if tweet_id:
            response = requests.get(
                f"https://twitfix.onrender.com/tweet.php?id={tweet_id.group(1)}",
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('download_url'):
                    return [{"type": "video", "url": data['download_url']}]
        
        return []
    except Exception as e:
        logger.error(f"Twitter Error (URL: {url}): {str(e)}")
        return []

async def download_youtube(url: str) -> list:
    try:
        # Video ID çıkarma (normal video ve shorts desteği)
        video_id = re.search(r'(?:v=|youtu\.be/|shorts/)([\w-]{11})', url)
        if not video_id:
            logger.error(f"Geçersiz YouTube URL: {url}")
            return []
            
        video_id = video_id.group(1)
        
        # yt-dlp ile indirme
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 20,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['js']
                }
            }
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://youtu.be/{video_id}",
                download=False
            )
            if info and 'url' in info:
                return [{"type": "video", "url": info['url']}]
        
        return []
    except Exception as e:
        logger.error(f"YouTube Error (URL: {url}): {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"Processing URL: {url}")
    
    try:
        if 'tiktok.com' in url.lower():
            media = await download_tiktok(url)
            platform = "TikTok"
        elif 'reddit.com' in url.lower():
            media = await download_reddit(url)
            platform = "Reddit"
        elif 'twitter.com' in url.lower() or 'x.com' in url.lower():
            media = await download_twitter(url)
            platform = "Twitter/X"
        elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            media = await download_youtube(url)
            platform = "YouTube"
        else:
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı")
            return
        
        if not media:
            logger.warning(f"Medya bulunamadı: {url}")
            await update.message.reply_text(
                f"⚠️ {platform} içeriği indirilemedi.\n\n"
                "🔎 Çözüm için:\n"
                "- Linkin doğruluğunu kontrol edin\n"
                "- Farklı bir link deneyin\n"
                "- Video/gönderi herkese açık mı kontrol edin"
            )
            return
            
        for item in media:
            try:
                if item["type"] == "video":
                    await update.message.reply_video(
                        video=item["url"],
                        caption=f"🎥 {platform} videosu",
                        supports_streaming=True,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
                else:
                    await update.message.reply_photo(
                        photo=item["url"],
                        caption=f"📷 {platform} resmi",
                        read_timeout=60,
                        write_timeout=60
                    )
            except Exception as e:
                logger.error(f"Gönderim Hatası: {str(e)} - URL: {item.get('url')}")
                await update.message.reply_text(
                    f"⚠️ Medya gönderilemedi: {str(e)}\n\n"
                    "📌 Bu bir sunucu hatası olabilir, "
                    "birkaç dakika sonra tekrar deneyin"
                )
    except Exception as e:
        logger.error(f"Genel Hata: {str(e)}")
        await update.message.reply_text(
            "⚠️ Bir hata oluştu, lütfen daha sonra tekrar deneyin\n\n"
            "🔧 Hata detayı:\n"
            f"{str(e)[:200]}..."
        )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sistem durumunu test etme komutu"""
    services = {
        "Reddit": bool(REDDIT_CLIENT_ID),
        "Twitter": bool(TWITTER_API_KEY),
        "YouTube": bool(YOUTUBE_API_KEY),
        "TikTok": bool(TIKTOK_API_KEY)
    }
    status = "\n".join([f"{k}: {'✅' if v else '❌'}" for k, v in services.items()])
    await update.message.reply_text(f"🛠️ Sistem Durumu:\n{status}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    
    # Mesaj handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    try:
        app.run_polling()
    finally:
        import asyncio
        asyncio.run(cleanup())
