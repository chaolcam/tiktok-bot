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
        # TEST İÇİN SABİT BİR URL (GERÇEK KULLANIMDA API ENTEGRE EDİN)
        return ["https://v16m-webapp.tiktokcdn-us.com/ed129ecb01ab00e202682e99f68a9288/62f03e3c/video/tos/useast5/tos-useast5-pve-0068-tx/14709862e3b644a1a229c5b68b7190c6/?a=1988&ch=0&cr=0&dr=0&lr=all&cd=0%7C0%7C1%7C0&cv=1&br=4020&bt=2010&cs=0&ds=3&ft=ebtHKH-qMyq8ZjFl1we2N9befl7Gb&mime_type=video_mp4&qs=0&rc=OTU4MzU0NzVnaDpnOGg8OEBpajM5Z2c6ZmYzZTMzZzczNEAuMC9jLWBgNmExNTIvY18tYSMxX28vcjRnMGRgLS1kMS9zcw%3D%3D&l=202208050810490102450402240A55B25B"]
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
                    media_group.append(InputMediaVideo(requests.get(media_url).content))
                else:
                    media_group.append(InputMediaPhoto(requests.get(media_url).content))
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
