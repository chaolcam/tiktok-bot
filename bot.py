import os
import logging
import requests
from telegram import Update, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Merhaba! TikTok/Twitter linklerini gönderin')

async def download_tiktok(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        try:
            await page.goto("https://snaptik.app/", timeout=60000)
            await page.fill("input#url", url)
            await page.click("button[type='submit']")
            await page.wait_for_selector(".download-link", timeout=60000)
            download_element = await page.query_selector(".download-link >> a")
            video_url = await download_element.get_attribute("href")
            return video_url
        finally:
            await browser.close()

async def download_twitter(url: str) -> list:
    # Twdown API alternatifi
    try:
        response = requests.get(f"https://twdown.net/download.php?url={url}")
        # HTML parsing ile medya URL'leri çekilecek
        # Bu kısım özelleştirilmeli
        return ["twitter_video_url_1", "twitter_photo_url_2"]
    except Exception as e:
        logger.error(f"Twitter hatası: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            video_url = await download_tiktok(url)
            media_content = requests.get(video_url).content
            media_group.append(InputMediaVideo(media_content))
            logger.info("TikTok video indirildi")

        elif 'twitter.com' in url:
            media_urls = await download_twitter(url)
            for media_url in media_urls:
                if media_url.endswith('.mp4'):
                    media_group.append(InputMediaVideo(requests.get(media_url).content)
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content)
            logger.info("Twitter medya indirildi")

        if media_group:
            await update.message.reply_media_group(media=media_group)
        else:
            await update.message.reply_text("Desteklenmeyen link formatı")

    except Exception as e:
        logger.error(f"Hata: {str(e)}")
        await update.message.reply_text(f"Üzgünüm, bir hata oluştu: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
