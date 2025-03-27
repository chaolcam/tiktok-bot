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

async def wait_for_bot_response(bot_entity, sent_msg_id, wait_time=20):
    """Hedef botun yanıtını bekler"""
    try:
        async for msg in client.iter_messages(bot_entity, min_id=sent_msg_id, wait_time=wait_time):
            if msg.id > sent_msg_id and (msg.media or 'http' in getattr(msg, 'text', '')):
                return msg
        return None
    except Exception as e:
        logger.error(f"Yanıt bekleme hatası: {str(e)}")
        return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_command(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    try:
        # Komut mesajını sil
        await event.delete()
        
        cmd = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        # İşlem başladı mesajı
        status_msg = await event.respond(f"⌛️ {cmd.capitalize()} işleniyor...")
        
        # Hedef botlara sırayla deneme
        result = None
        for bot_username in BOT_MAPPING.get(cmd, []):
            try:
                bot_entity = await client.get_entity(bot_username)
                
                # Linki hedef bota gönder
                sent_msg = await client.send_message(bot_entity, url)
                
                # Reddit için özel işlem
                if cmd == 'reddit':
                    # İlk yanıtı bekle
                    first_response = await wait_for_bot_response(bot_entity, sent_msg.id)
                    if first_response and hasattr(first_response, 'buttons'):
                        # Buton varsa tıkla
                        for row in first_response.buttons:
                            for btn in row:
                                if "media" in btn.text.lower() or "720p" in btn.text or "480p" in btn.text:
                                    await btn.click()
                                    break
                    
                    # Son yanıtı bekle
                    result = await wait_for_bot_response(bot_entity, sent_msg.id)
                else:
                    # Diğer botlar için normal bekleme
                    result = await wait_for_bot_response(bot_entity, sent_msg.id)
                
                if result:
                    break
                    
            except Exception as e:
                logger.error(f"{bot_username} hatası: {str(e)}")
                continue
        
        # Sonuçları işle
        await status_msg.delete()
        if result:
            await client.send_message(event.chat_id, f"✅ {cmd.capitalize()} indirme başarılı!")
            await client.forward_messages(event.chat_id, result)
        else:
            await client.send_message(event.chat_id, "❌ İndirme başarısız oldu")
            
    except Exception as e:
        logger.error(f"Komut hatası: {str(e)}")
        await client.send_message(event.chat_id, f"❌ Hata: {str(e)}")

async def main():
    await client.start()
    logger.info("UserBot başlatıldı!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
