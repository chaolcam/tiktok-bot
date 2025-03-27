import os
import asyncio
import logging
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
WAIT_TIME = int(os.environ.get('WAIT_TIME', 5))  # Varsayılan bekleme süresi 5 saniye

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

🔹 **Özellikler:**
- Otomatik kalite seçimi (Reddit)
- Optimize edilmiş bekleme süreleri
- Sadece sizin kullanımınız
"""

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection_retries=5,
    auto_reconnect=True
)

async def press_buttons(event, response):
    """Reddit botundaki butonlara otomatik basar"""
    if not response.buttons:
        return response
        
    buttons = response.buttons
    best_quality = None
    
    # En yüksek kaliteyi bul
    for button_row in buttons:
        for button in button_row:
            text = button.text.lower()
            if '720p' in text:
                best_quality = button
                break
            elif '480p' in text and not best_quality:
                best_quality = button
            elif 'media' in text and not best_quality:
                best_quality = button
    
    if best_quality:
        logger.info(f"Buton bulundu: {best_quality.text}")
        await best_quality.click()
        await asyncio.sleep(3)  # Butona basıldıktan sonra bekle
        async for new_msg in client.iter_messages(response.chat_id, limit=1):
            if new_msg.id > response.id:
                return new_msg
    
    return response

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
            
            # Reddit için daha uzun bekle
            wait_time = WAIT_TIME + 3 if platform == 'reddit' else WAIT_TIME
            
            # Yanıtı bekle
            response = None
            async for message in client.iter_messages(bot_entity, limit=1, wait_time=wait_time):
                if message.id > sent_message.id:
                    response = message
                    break
            
            if response:
                logger.info(f"Yanıt alındı, işleniyor...")
                
                # Reddit botu için buton işleme
                if platform == 'reddit' and response.buttons:
                    response = await press_buttons(event, response)
                
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
        
        if response:
            await event.edit(f"✅ **{command.capitalize()}** başarıyla indirildi!")
            await asyncio.sleep(1)
            await client.forward_messages(event.chat_id, response)
        else:
            await event.edit(f"❌ **{command.capitalize()}** indirilemedi!")
            
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
        await client.send_message('me', '🤖 Bot başarıyla başlatıldı!')
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
