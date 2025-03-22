import os
import logging
import requests
from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutunu işler"""
    await update.message.reply_text('🎉 Merhaba! TikTok ve Twitter linklerini bana gönder.')

async def download_tiktok(url: str) -> str:
    """TikTok videosunu indirir"""
    async with async_playwright() as p:
        # Heroku uyumlu tarayıcı ayarları
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        try:
            # Snaptik.app üzerinden indirme
            await page.goto("https://snaptik.app/", timeout=120000)
            await page.fill("input#url", url)
            await page.click("button[type='submit']")
            
            # İndirme linkini bekleyip al
            await page.wait_for_selector(".download-link", timeout=60000)
            download_element = await page.query_selector(".download-link >> a")
            video_url = await download_element.get_attribute("href")
            return video_url
        except Exception as e:
            logger.error(f"TikTok indirme hatası: {str(e)}")
            raise
        finally:
            await browser.close()

async def download_twitter(url: str) -> list:
    """Twitter medyasını indirir (Basitleştirilmiş)"""
    try:
        # Twitsave API alternatifi
        response = requests.get(f"https://twitsave.com/info?url={url}")
        data = response.json()
        return [data["video"][0]["url"]]  # Gerçek API yapısına göre düzenleyin
    except Exception as e:
        logger.error(f"Twitter indirme hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gelen mesajları işler"""
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            # TikTok işlemleri
            video_url = await download_tiktok(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("✅ TikTok video indirildi")

        elif 'twitter.com' in url:
            # Twitter işlemleri
            media_urls = await download_twitter(url)
            for media_url in media_urls:
                if media_url.endswith('.mp4'):
                    media_group.append(InputMediaVideo(requests.get(media_url).content))
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content))
            logger.info("✅ Twitter medya indirildi")

        if media_group:
            await update.message.reply_media_group(media=media_group)
        else:
            await update.message.reply_text("❌ Desteklenmeyen link formatı")

    except Exception as e:
        logger.error(f"⛔ Kritik hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Üzgünüm, şu hata oluştu:\n{str(e)}")

if __name__ == '__main__':
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    
    # Handler'ları ekle
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Polling başlat
    app.run_polling()
