import os
import yt_dlp
import requests
import tempfile
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Bot çalışıyor! TikTok veya Twitter bağlantısını gönderin.")

def download_media(url):
    options = {
        'outtmpl': f'{tempfile.gettempdir()}/%(title)s.%(ext)s',
        'format': 'best'
    }
    
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return filename
    except Exception as e:
        return None, str(e)

def send_media(update: Update, context: CallbackContext):
    url = update.message.text
    chat_id = update.message.chat_id
    
    update.message.reply_text("Medya indiriliyor, lütfen bekleyin...")
    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
    
    media_file, error = download_media(url)
    if media_file:
        with open(media_file, 'rb') as file:
            update.message.reply_document(file)
        os.remove(media_file)
    else:
        update.message.reply_text(f'Medya indirilemedi: {error}')

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, send_media))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
