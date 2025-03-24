import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import youtube_dl
import praw
from bs4 import BeautifulSoup

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

# Reddit API bağlantısı
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
- Twitter (video/resim) - API kullanılmadan
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
            params=params
        )
        data = response.json()
        
        logger.info(f"TikTok API Yanıtı: {data}")
        
        media_urls = []
        if "data" in data:
            if "play" in data["data"]:
                media_urls.append({"type": "video", "url": data["data"]["play"]})
            if "images" in data["data"]:
                for image in data["data"]["images"]:
                    media_urls.append({"type": "photo", "url": image})
        return media_urls
    except Exception as e:
        logger.error(f"TikTok API Hatası: {str(e)}")
        return []

async def download_reddit(url: str) -> list:
    """Reddit gönderilerini indirir."""
    try:
        submission = reddit.submission(url=url)
        media_urls = []
        
        if submission.is_video:
            media_urls.append({
                "type": "video",
                "url": submission.media['reddit_video']['fallback_url'].split('?')[0]
            })
        elif hasattr(submission, 'gallery_data'):
            for item in submission.gallery_data['items']:
                media_id = item['media_id']
                media_url = submission.media_metadata[media_id]['s']['u']
                media_urls.append({"type": "photo", "url": media_url})
        elif submission.url.endswith(('jpg', 'jpeg', 'png', 'gif')):
            media_urls.append({"type": "photo", "url": submission.url})
            
        return media_urls
    except Exception as e:
        logger.error(f"Reddit indirme hatası: {str(e)}")
        return []

async def download_twitter(url: str) -> list:
    """Twitter gönderilerini tamamen API'siz indirir."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # URL'yi standardize et
        parsed_url = url.replace("x.com", "twitter.com").replace("//twitter", "//mobile.twitter")
        
        # Önce twdown.net alternatifini dene
        try:
            api_url = f"https://twdown.net/download.php?url={parsed_url}"
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                download_btn = soup.find('a', {'id': 'download'})
                if download_btn and download_btn.get('href'):
                    return [{"type": "video", "url": download_btn['href']}]
        except:
            pass
        
        # Mobil sayfayı parse et
        if not parsed_url.startswith(('http://', 'https://')):
            parsed_url = 'https://' + parsed_url
            
        response = requests.get(parsed_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        media_urls = []
        
        # Video kontrolü
        video_tag = soup.find('video')
        if video_tag:
            video_url = video_tag.get('src')
            if video_url:
                if not video_url.startswith('http'):
                    video_url = f"https:{video_url}"
                media_urls.append({"type": "video", "url": video_url})
        
        # Resim kontrolü
        images = soup.find_all('img', {'alt': 'Image'})
        for img in images:
            img_url = img.get('src')
            if img_url and 'profile_images' not in img_url:
                if not img_url.startswith('http'):
                    img_url = f"https:{img_url}"
                media_urls.append({"type": "photo", "url": img_url})
                
        return media_urls
    except Exception as e:
        logger.error(f"Twitter indirme hatası: {str(e)}")
        return []

async def download_youtube(url: str) -> list:
    """YouTube videolarını indirir."""
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
                
            media_urls = [{
                "type": "video",
                "url": info['url'],
                "title": info.get('title', 'YouTube Video')
            }]
            
            return media_urls
    except Exception as e:
        logger.error(f"YouTube indirme hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcıdan gelen mesajı işler ve medya gönderir."""
    url = update.message.text.strip()
    
    try:
        if is_tiktok(url):
            media_urls = await download_tiktok(url)
            platform = "TikTok"
        elif is_reddit(url):
            media_urls = await download_reddit(url)
            platform = "Reddit"
        elif is_twitter(url):
            media_urls = await download_twitter(url)
            platform = "Twitter"
        elif is_youtube(url):
            media_urls = await download_youtube(url)
            platform = "YouTube"
        else:
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı.")
            return
            
        if media_urls:
            for media in media_urls:
                try:
                    if media["type"] == "video":
                        await update.message.reply_video(
                            video=media["url"],
                            caption=f"🎥 {platform} videosu"
                        )
                    elif media["type"] == "photo":
                        await update.message.reply_photo(
                            photo=media["url"],
                            caption=f"📷 {platform} resmi"
                        )
                    logger.info(f"✅ {platform} medya gönderildi: {media['url']}")
                except Exception as e:
                    logger.error(f"⛔ Medya gönderim hatası: {str(e)}")
                    await update.message.reply_text(f"⚠️ Medya gönderilirken hata oluştu: {str(e)}")
        else:
            await update.message.reply_text(f"⚠️ {platform} içeriği indirilemedi. Linki kontrol edin.")
    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start))
    
    # Tüm mesajları işleyen handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()
