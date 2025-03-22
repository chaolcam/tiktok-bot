import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# TikTok video ve resim indirme fonksiyonu
def download_tiktok_media(url):
    # Video ve resimler için API
    api_url = f"https://api.tiklydown.eu.org/api/download?url={url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        video_url = data.get('video', {}).get('url')
        image_urls = data.get('images', [])  # Resimler (birden fazla olabilir)
        return video_url, image_urls
    return None, None

# /start komutu
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Merhaba! Bana bir TikTok linki gönderin, ben de size videoyu veya resmi indireyim.')

# Mesaj işleme
async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    if "tiktok.com" in url:
        # Video ve resimleri indir
        video_url, image_urls = download_tiktok_media(url)
        
        # Video varsa gönder
        if video_url:
            await update.message.reply_video(video_url)
        
        # Resimler varsa gönder (birden fazla resim olabilir)
        if image_urls:
            for image_url in image_urls:
                await update.message.reply_photo(image_url)
        
        # Hiçbir medya bulunamazsa
        if not video_url and not image_urls:
            await update.message.reply_text('Üzgünüm, medya indirilemedi.')
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
