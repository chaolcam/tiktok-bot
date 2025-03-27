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

# Configurations
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))
BASE_WAIT = 12  # Temel bekleme süresi (saniye)
REDDIT_WAIT = 18  # Reddit için ek bekleme süresi

# Bot mapping
BOT_MAPPING = {
    'tiktok': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
    'reddit': ['@reddit_download_bot'],
    'twitter': ['@twitterimage_bot', '@embedybot'],
    'youtube': ['@embedybot']
}

HELP_MESSAGE = """
🤖 **Kişisel İndirme Botu** 📥

🔹 **Komutlar:**
`.tiktok <url>` - TikTok indir
`.reddit <url>` - Reddit indir (Otomatik en iyi kalite)
`.twitter <url>` - Twitter indir
`.youtube <url>` - YouTube indir
`.help` - Yardım mesajı

⏳ **Reddit işlemleri 15-20 saniye sürebilir**
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def handle_reddit_interaction(chat_id, original_msg_id):
    """Reddit botuyla etkileşimi yönetir"""
    try:
        last_msg_id = original_msg_id
        final_response = None
        
        async for message in client.iter_messages(chat_id, min_id=original_msg_id, wait_time=REDDIT_WAIT):
            if message.id > last_msg_id:
                last_msg_id = message.id
                
                # 1. Media/File seçimi
                if hasattr(message, 'buttons') and "Download album as media or file?" in message.text:
                    for row in message.buttons:
                        for button in row:
                            if "media" in button.text.lower():
                                await button.click()
                                await asyncio.sleep(3)
                                break
                
                # 2. Kalite seçimi
                elif hasattr(message, 'buttons') and "select the quality" in message.text:
                    for row in message.buttons:
                        for button in row:
                            if "720p" in button.text:
                                await button.click()
                                await asyncio.sleep(3)
                                break
                            elif "480p" in button.text:
                                await button.click()
                                await asyncio.sleep(3)
                                break
                
                # 3. Sonuç mesajı
                elif message.media or (hasattr(message, 'text') and 'http' in message.text:
                    final_response = message
                    break
        
        return final_response
        
    except Exception as e:
        logger.error(f"Reddit işleme hatası: {str(e)}")
        return None

async def get_bot_response(bot_username, url, platform):
    """Bot ile iletişim kurar ve yanıt alır"""
    try:
        bot_entity = await client.get_entity(bot_username)
        await client.send_message(bot_entity, url)
        
        wait_time = REDDIT_WAIT if platform == 'reddit' else BASE_WAIT
        responses = []
        
        async for message in client.iter_messages(bot_entity, limit=5, wait_time=wait_time):
            if message.text and 'http' in message.text or message.media:
                responses.append(message)
        
        if platform == 'reddit' and responses:
            return await handle_reddit_interaction(bot_entity.id, responses[-1].id)
        
        return responses[-1] if responses else None
        
    except Exception as e:
        logger.error(f"Bot iletişim hatası ({bot_username}): {str(e)}")
        return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_command(event):
    try:
        if event.sender_id != AUTHORIZED_USER:
            return
            
        command = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        processing_msg = await event.edit(f"⏳ **{command.upper()}** işleniyor...\n{url}")
        
        response = None
        for bot_username in BOT_MAPPING.get(command, []):
            response = await get_bot_response(bot_username, url, command)
            if response:
                break
        
        if response:
            await event.delete()
            await client.send_message(event.chat_id, f"✅ **{command.upper()}** indirme tamamlandı!")
            await client.forward_messages(event.chat_id, response)
        else:
            await event.edit(f"❌ **{command.upper()}** indirilemedi!")
            
    except Exception as e:
        logger.error(f"Komut işleme hatası: {str(e)}")
        await event.edit(f"❌ Hata oluştu!\n{str(e)}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    if event.sender_id == AUTHORIZED_USER:
        await event.edit(HELP_MESSAGE)

async def main():
    await client.start()
    me = await client.get_me()
    logger.info(f"Bot başlatıldı: @{me.username}")
    await client.send_message('me', '🤖 Bot aktif!')
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Başlatma hatası: {str(e)}")
