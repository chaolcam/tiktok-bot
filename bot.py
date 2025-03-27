import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerUser

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurations from environment variables
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))

# Validate configuration
if not API_ID or not API_HASH or not STRING_SESSION or not AUTHORIZED_USER:
    logger.error("Lütfen API_ID, API_HASH, STRING_SESSION ve AUTHORIZED_USER ortam değişkenlerini ayarlayın!")
    exit(1)

# Bot mapping
BOT_MAPPING = {
    'tiktok': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
    'reddit': ['@reddit_download_bot'],
    'twitter': ['@twitterimage_bot', '@embedybot'],
    'youtube': ['@embedybot']
}

# Help message
HELP_MESSAGE = """
🤖 **Kişisel Sosyal Medya İndirme UserBot** 📥

🔹 **Komutlar:"""
# ... (önceki HELP_MESSAGE içeriği aynı kalacak)

# Initialize client with connection retry
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH,
                       connection_retries=5, auto_reconnect=True)

async def ensure_connection():
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            if not client.is_connected():
                await client.connect()
            if not await client.is_user_authorized():
                logger.error("Oturum yetkilendirilmemiş!")
                exit(1)
            return True
        except Exception as e:
            retries += 1
            logger.error(f"Bağlantı hatası (Deneme {retries}/{max_retries}): {str(e)}")
            await asyncio.sleep(5)
    return False

async def send_to_bot_and_get_response(platform, url, event):
    # ... (önceki fonksiyon içeriği aynı kalacak)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_download_command(event):
    # ... (önceki fonksiyon içeriği aynı kalacak)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help_command(event):
    # ... (önceki fonksiyon içeriği aynı kalacak)

async def main():
    try:
        # Bağlantıyı sağlamayı garantile
        if not await ensure_connection():
            logger.error("Telegram'a bağlanılamadı!")
            return

        me = await client.get_me()
        logger.info(f"UserBot başlatıldı! ID: {me.id} - Kullanıcı adı: @{me.username}")
        
        # Oturum bilgilerini logla
        logger.info(f"String Session: {STRING_SESSION[:15]}...")
        logger.info(f"Yetkili kullanıcı: {AUTHORIZED_USER}")

        # Başlangıç mesajını gönder
        try:
            await client.send_message('me', '🤖 UserBot başarıyla başlatıldı!')
        except Exception as e:
            logger.warning(f"Başlangıç mesajı gönderilemedi: {str(e)}")

        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Ana işlevde hata: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("UserBot kapatılıyor...")
    except Exception as e:
        logger.error(f"Kritik hata: {str(e)}", exc_info=True)
        exit(1)
