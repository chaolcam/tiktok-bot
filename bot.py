import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))

# Bot eşleştirmeleri
BOT_MAPPING = {
    'tiktok': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
    'reddit': ['@reddit_download_bot'],
    'twitter': ['@twitterimage_bot', '@embedybot'],
    'youtube': ['@embedybot']
}

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def process_reddit_interaction(bot_entity, url):
    """Reddit botuyla etkileşim"""
    try:
        # Linki gönder
        sent_msg = await client.send_message(bot_entity, url)
        
        # Yanıtı bekle (20 saniye)
        async for msg in client.iter_messages(bot_entity, limit=3, wait_time=20):
            if msg.id > sent_msg.id:
                # Media/file seçimi
                if hasattr(msg, 'buttons') and "Download album as media or file?" in msg.text:
                    for row in msg.buttons:
                        for btn in row:
                            if "media" in btn.text.lower():
                                await btn.click()
                                break
                
                # Kalite seçimi
                elif hasattr(msg, 'buttons') and "Please select the quality." in msg.text:
                    for row in msg.buttons:
                        for btn in row:
                            if "720p" in btn.text:
                                await btn.click()
                                break
                            elif "480p" in btn.text:
                                await btn.click()
                                break
                
                # Sonuç mesajı
                elif msg.media or (hasattr(msg, 'text') and 'http' in msg.text):
                    return msg
        
        return None
        
    except Exception as e:
        logger.error(f"Reddit hatası: {str(e)}")
        return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_command(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    try:
        cmd = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        # Komut mesajını sil
        await event.delete()
        
        # İşlem başladı mesajı
        status_msg = await event.respond(f"⏳ {cmd.capitalize()} işleniyor...")
        
        # Hedef botlara sırayla deneme
        result = None
        for bot_username in BOT_MAPPING.get(cmd, []):
            try:
                bot_entity = await client.get_entity(bot_username)
                
                if cmd == 'reddit':
                    result = await process_reddit_interaction(bot_entity, url)
                else:
                    await client.send_message(bot_entity, url)
                    async for msg in client.iter_messages(bot_entity, limit=2, wait_time=15):
                        if msg.media or (hasattr(msg, 'text') and 'http' in msg.text):
                            result = msg
                            break
                
                if result:
                    break
                    
            except Exception as e:
                logger.error(f"{bot_username} hatası: {str(e)}")
                continue
        
        # Sonuçları işle
        if result:
            await status_msg.delete()
            await client.send_message(event.chat_id, f"✅ {cmd.capitalize()} indirme tamam!")
            await client.forward_messages(event.chat_id, result)
        else:
            await status_msg.edit("❌ İndirme başarısız oldu")
            
    except Exception as e:
        logger.error(f"Komut hatası: {str(e)}")
        await event.respond(f"❌ Hata: {str(e)}")

async def main():
    await client.start()
    logger.info("UserBot başlatıldı!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
