import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# TikTok video indirme fonksiyonu
def download_tiktok_video(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        video_url = data.get('data', {}).get('play')
        return video_url
    return None

# /start komutu
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Merhaba! Bana bir TikTok linki gönderin, ben de size filigransız bir şekilde indireyim.')

# Mesaj işleme
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    if "tiktok.com" in url:
        video_url = download_tiktok_video(url)
        if video_url:
            await update.message.reply_video(video_url)
        else:
            await update.message.reply_text('Üzgünüm, video indirilemedi.')
    else:
        await update.message.reply_text('Lütfen geçerli bir TikTok linki gönderin.')

# Botu başlatma
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Lütfen TELEGRAM_BOT_TOKEN çevre değişkenini ayarlayın.")
        return

    # ApplicationBuilder ile botu başlatma
    application = ApplicationBuilder().token(token).build()

    # Handlers ekleme
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Botu çalıştırma
    application.run_polling()

if __name__ == '__main__':
    main()
