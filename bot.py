import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ortam Değişkenleri
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Platformlara özel botlar
BOTS = {
    'reddit': '@reddit_download_bot',
    'twitter': '@embedybot',
    'youtube': '@embedybot',
    'tiktok': None  # Kendi işlevimizle çalışacak
}

# Loglama Ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Merhaba! Link gönderin, ilgili botlarla indirelim:\n\n"
        "• TikTok: Direkt indirilir\n"
        "• Reddit: @reddit_download_bot\n"
        "• Twitter/YT: @embedybot\n\n"
        "⚠️ Not: Bazen yanıt gecikebilir"
    )

async def download_tiktok(url: str) -> list:
    """TikTok için kendi indirme fonksiyonumuz"""
    try:
        headers = {
            "X-RapidAPI-Key": os.getenv('TIKTOK_API_KEY'),
            "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
        }
        response = requests.get(
            f"https://tiktok-video-no-watermark2.p.rapidapi.com/?url={url}",
            headers=headers,
            timeout=15
        )
        data = response.json()
        if data.get('data', {}).get('play'):
            return [{"type": "video", "url": data['data']['play']}]
        return []
    except Exception as e:
        logger.error(f"TikTok Error: {str(e)}")
        return []

async def forward_to_target_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, target_bot: str):
    """Mesajı hedef bota ilet ve yanıtı al"""
    try:
        # Kullanıcıya bilgi mesajı
        processing_msg = await update.message.reply_text(f"⏳ {target_bot} işliyor...")
        
        # Mesajı forward et
        forwarded = await update.message.forward(target_bot)
        
        # Yanıtı bekleyelim (max 25 saniye)
        response = await context.bot.wait_for(
            update=lambda u: u.message.from_user.username == target_bot.replace('@', ''),
            timeout=25
        )
        
        await processing_msg.delete()
        return response
    except Exception as e:
        logger.error(f"Forward Error: {str(e)}")
        await update.message.reply_text(f"⚠️ {target_bot} yanıt vermedi. Lütfen manuel deneyin.")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    url = update.message.text.strip().lower()
    
    try:
        # Platform belirleme
        if 'tiktok.com' in url:
            # TikTok için kendi fonksiyonumuz
            media = await download_tiktok(update.message.text.strip())
            if media:
                await update.message.reply_video(video=media[0]['url'])
            else:
                await update.message.reply_text("❌ TikTok içeriği indirilemedi")
            return
                
        elif 'reddit.com' in url:
            target_bot = BOTS['reddit']
        elif 'twitter.com' in url or 'x.com' in url:
            target_bot = BOTS['twitter']
        elif 'youtube.com' in url or 'youtu.be' in url:
            target_bot = BOTS['youtube']
        else:
            await update.message.reply_text("⚠️ Desteklenmeyen link formatı")
            return
        
        # Hedef bota yönlendir
        response = await forward_to_target_bot(update, context, target_bot)
        
        if response:
            # Gelen medyayı kullanıcıya ilet
            if response.message.video:
                await response.message.video.send_copy(chat_id=update.effective_chat.id)
            elif response.message.photo:
                await response.message.photo[-1].send_copy(chat_id=update.effective_chat.id)
            elif response.message.document:
                await response.message.document.send_copy(chat_id=update.effective_chat.id)
            else:
                await update.message.reply_text("❌ Desteklenmeyen medya formatı")
    except Exception as e:
        logger.error(f"Genel Hata: {str(e)}")
        await update.message.reply_text("⚠️ İşlem sırasında bir hata oluştu")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start))
    
    # Mesaj handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()
