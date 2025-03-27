import os
import asyncio
import logging
import re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerUser

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurations
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))
BASE_WAIT_TIME = int(os.environ.get('BASE_WAIT_TIME', 10))  # Varsayılan 10 saniye
REDDIT_EXTRA_WAIT = int(os.environ.get('REDDIT_EXTRA_WAIT', 5))  # Reddit için ek 5 saniye

# Validate configuration
if not all([API_ID, API_HASH, STRING_SESSION, AUTHORIZED_USER]):
    logger.error("Lütfen gerekli ortam değişkenlerini ayarlayın!")
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
🤖 **Gelişmiş Sosyal Medya İndirme Botu** 📥

🔹 **Komutlar:**
`.tiktok <url>` - TikTok videosu indir
`.reddit <url>` - Reddit içeriği indir (Otomatik en yüksek kalite)
`.twitter <url>` - Twitter içeriği indir
`.youtube <url>` - YouTube videosu indir
`.help` - Bu yardım mesajını göster

🔹 **Reddit Özellikleri:**
- Otomatik "Media" seçeneği seçilir
- Kalite butonlarını otomatik basar (720p > 480p > 360p)
- Uzun bekleme süreleri ile güvenilir indirme
"""

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection_retries=5,
    auto_reconnect=True
)

async def handle_reddit_buttons(event, initial_response):
    """Reddit botundaki tüm buton işlemlerini yönetir"""
    try:
        current_msg = initial_response
        last_msg_id = current_msg.id
        
        # 1. Adım: Media/File seçimi
        if "Download album as media or file?" in current_msg.text:
            for row in current_msg.buttons:
                for button in row:
                    if "media" in button.text.lower():
                        logger.info("'Media' butonuna basılıyor...")
                        current_msg = await button.click()
                        await asyncio.sleep(3)  # Buton sonrası bekleme
                        last_msg_id = current_msg.id
                        break
        
        # 2. Adım: Kalite seçimi
        async for new_msg in client.iter_messages(current_msg.chat_id, min_id=last_msg_id, wait_time=10):
            if new_msg.id > last_msg_id and new_msg.buttons and "select the quality" in new_msg.text:
                logger.info("Kalite butonları tespit edildi")
                for row in new_msg.buttons:
                    for button in row:
                        if "720p" in button.text:
                            logger.info("720p seçiliyor...")
                            current_msg = await button.click()
                            return current_msg
                        elif "480p" in button.text:
                            logger.info("480p seçiliyor...")
                            current_msg = await button.click()
                            return current_msg
                        elif "360p" in button.text:
                            logger.info("360p seçiliyor...")
                            current_msg = await button.click()
                            return current_msg
        
        return current_msg
        
    except Exception as e:
        logger.error(f"Buton işleme hatası: {str(e)}")
        return initial_response

async def send_to_bot_and_get_response(platform, url, event):
    bots = BOT_MAPPING.get(platform, [])
    if not bots:
        logger.error(f"{platform} için bot bulunamadı")
        return None
        
    for bot_username in bots:
        try:
            logger.info(f"{bot_username} botuna istek gönderiliyor...")
            bot_entity = await client.get_entity(bot_username)
            
            # Mesajı gönder
            sent_message = await client.send_message(bot_entity, url)
            
            # Platforma özel bekleme süresi
            wait_time = BASE_WAIT_TIME
            if platform == 'reddit':
                wait_time += REDDIT_EXTRA_WAIT
            
            # Yanıtı bekle
            response = None
            start_time = asyncio.get_event_loop().time()
            
            async for message in client.iter_messages(bot_entity, limit=10, wait_time=wait_time):
                if message.id > sent_message.id:
                    response = message
                    logger.info(f"Yanıt alındı ({(asyncio.get_event_loop().time()-start_time):.1f}s): {message.text[:50]}...")
                    
                    # Reddit için özel işlemler
                    if platform == 'reddit':
                        response = await handle_reddit_buttons(event, response)
                        await asyncio.sleep(3)  # Ek bekleme süresi
                    
                    break
            
            return response
                
        except Exception as e:
            logger.error(f"Hata: {str(e)}")
            continue
            
    logger.error(f"Hiçbir bot yanıt vermedi")
    return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_download_command(event):
    try:
        if event.sender_id != AUTHORIZED_USER:
            return
            
        command = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        processing_msg = await event.edit(f"⏳ **{command.capitalize()}** işleniyor...\n`{url}`")
        
        # Daha uzun bekleme süresi
        await asyncio.sleep(2)
        
        response = await send_to_bot_and_get_response(command, url, event)
        
        if response and (response.text or response.media):
            await event.edit(f"✅ **{command.capitalize()}** başarıyla indirildi!")
            await asyncio.sleep(1)
            await client.forward_messages(event.chat_id, response)
        else:
            await event.edit(f"❌ **{command.capitalize()}** indirilemedi! (Zaman aşımı)")
            
    except Exception as e:
        logger.error(f"Hata: {str(e)}", exc_info=True)
        await event.edit(f"❌ Hata!\n`{str(e)}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help_command(event):
    if event.sender_id == AUTHORIZED_USER:
        await event.edit(HELP_MESSAGE)

async def main():
    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"Bot başlatıldı: @{me.username}")
        await client.send_message('me', f'🤖 Bot başarıyla başlatıldı!\n\nBekleme Süreleri:\n- Temel: {BASE_WAIT_TIME}s\n- Reddit: +{REDDIT_EXTRA_WAIT}s')
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Başlatma hatası: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot kapatılıyor...")
    except Exception as e:
        logger.error(f"Kritik hata: {str(e)}")
        exit(1)
