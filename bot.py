import os
import logging
import requests
from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🎉 Merhaba! TikTok/Twitter linklerini gönder.')

async def download_tiktok(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        try:
            await page.goto("https://snaptik.app/", timeout=120000)
            await page.fill("input#url", url)
            await page.click("button[type='submit']")
            await page.wait_for_selector(".download-link", timeout=60000)
            download_element = await page.query_selector(".download-link >> a")
            return await download_element.get_attribute("href")
        except Exception as e:
            logger.error(f"TikTok Hatası: {str(e)}")
            raise
        finally:
            await browser.close()

async def download_twitter(url: str) -> list:
    try:
        # TEST İÇİN GEÇERLİ BİR MEDYA URL'Sİ (Örnek YouTube video)
        return ["https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"]
    except Exception as e:
        logger.error(f"Twitter Hatası: {str(e)}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            video_url = await download_tiktok(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("TikTok Başarılı")

        elif 'twitter.com' in url:
            media_urls = await download_twitter(url)
            for media_url in media_urls:
                if media_url.endswith('.mp4'):
                    media_group.append(InputMediaVideo(requests.get(media_url).content))  # Düzeltildi
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content))  # Düzeltildi
            logger.info("Twitter Başarılı")

        if media_group:
            await update.message.reply_media_group(media=media_group)
        else:
            await update.message.reply_text("❌ Desteklenmeyen Link")

    except Exception as e:
        logger.error(f"Kritik Hata: {str(e)}")
        await update.message.reply_text(f"⚠️ Hata: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
