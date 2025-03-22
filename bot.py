import os
import logging
import requests
from telegram import Update, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from playwright.sync_api import sync_playwright

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, _):
    await update.message.reply_text('Merhaba! TikTok ve Twitter linklerini gönderin.')

def download_tiktok(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto("https://snaptik.app/")
            page.fill("input#url", url)
            page.click("button[type='submit']")
            page.wait_for_selector(".download-link", timeout=30000)
            download_url = page.query_selector(".download-link >> a").get_attribute("href")
            return download_url
        finally:
            browser.close()

async def handle_message(update: Update, _):
    url = update.message.text
    media_group = []
    
    try:
        if 'tiktok.com' in url:
            video_url = download_tiktok(url)
            media_group.append(InputMediaVideo(requests.get(video_url).content)
        
        if media_group:
            await update.message.reply_media_group(media=media_group)
    except Exception as e:
        await update.message.reply_text(f"Hata: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()
