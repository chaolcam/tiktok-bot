import os
import requests
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# TikTok video ve resim indirme fonksiyonu
def download_tiktok_media(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        video_url = data.get('data', {}).get('play')
        image_urls = data.get('data', {}).get('images', [])  # Resimler (birden fazla olabilir)
        return video_url, image_urls
    return None, None

# Resimleri gruplar halinde gönderme fonksiyonu
async def send_images_in_groups(update: Update, image_urls):
    # Resimleri 10'lu gruplara ayır
    for i in range(0, len(image_urls), 10):
        group = image_urls[i:i + 10]  # 10 resimlik bir grup oluştur
        media_group = [InputMediaPhoto(media=url) for url in group]  # Medya grubu oluştur
        await update.message.reply_media_group(media_group)  # Grubu gönder

# /start komutu
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Merhaba! Bana bir TikTok linki gönderin, ben de size videoyu veya resmi indireyim.')

# Mesaj işleme
async def handle_message(update: Update, context: CallbackContext):
    try:
        url = update.message.text
        if "tiktok.com" in url:
            # Video ve resimleri indir
            video_url, image_urls = download_tiktok_media(url)
            
            # Video varsa gönder
            if video_url:
                await update.message.reply_video(video_url)
            
            # Resimler varsa gruplar halinde gönder
            if image_urls:
                await send_images_in_groups(update, image_urls)
            
            # Hiçbir medya bulunamazsa
            if not video_url and not image_urls:
                await update.message.reply_text('Üzgünüm, medya indirilemedi.')
        else:
            await update.message.reply_text('Lütfen geçerli bir TikTok linki gönderin.')
    except Exception as e:
        print(f"Hata: {e}")
        await update.message.reply_text('Bir hata oluştu, lütfen daha sonra tekrar deneyin.')

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
