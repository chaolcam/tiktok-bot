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

# Bot ayarları
BOT_SETTINGS = {
    'tiktok': {
        'bots': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'wait': 20  # 20 saniye bekle
    },
    'reddit': {
        'bots': ['@reddit_download_bot'],
        'wait': 30  # 30 saniye bekle (butonlar için)
    },
    'twitter': {
        'bots': ['@twitterimage_bot', '@embedybot'],
        'wait': 20
    },
    'youtube': {
        'bots': ['@embedybot'],
        'wait': 20
    }
}

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Botun yanıtını sabırla bekler"""
    last_msg_id = after_msg_id
    end_time = asyncio.get_event_loop().time() + wait_time
    
    while asyncio.get_event_loop().time() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
                if msg.id > last_msg_id:
                    if msg.media or (hasattr(msg, 'text') and ('http' in msg.text or 'tiktok' in msg.text.lower()):
                        return msg
                    last_msg_id = msg.id
                    # 2 saniye bekle ve tekrar kontrol et
                    await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Bekleme hatası: {str(e)}")
            await asyncio.sleep(2)
    
    return None

async def handle_reddit(bot_entity, url):
    """Reddit botu için özel işlemler"""
    try:
        # Linki gönder
        sent_msg = await client.send_message(bot_entity, url)
        
        # İlk yanıtı bekle (media/file seçimi)
        first_resp = await wait_for_response(bot_entity, sent_msg.id, 15)
        if not first_resp:
            return None
        
        # Media butonuna bas
        if hasattr(first_resp, 'buttons'):
            for row in first_resp.buttons:
                for btn in row:
                    if "media" in btn.text.lower():
                        await btn.click()
                        break
        
        # Kalite seçimini bekle
        quality_resp = await wait_for_response(bot_entity, first_resp.id, 15)
        if not quality_resp:
            return None
        
        # En yüksek kaliteyi seç
        if hasattr(quality_resp, 'buttons'):
            for row in quality_resp.buttons:
                for btn in row:
                    if "720p" in btn.text:
                        await btn.click()
                        break
                    elif "480p" in btn.text:
                        await btn.click()
                        break
        
        # Sonucu al
        return await wait_for_response(bot_entity, quality_resp.id, 15)
    except Exception as e:
        logger.error(f"Reddit hatası: {str(e)}")
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
        settings = BOT_SETTINGS.get(cmd, {})
        
        # İşlem başladı mesajı (20 saniye boyunca göster)
        status_msg = await event.respond(f"⏳ {cmd.upper()} işleniyor (Lütfen bekleyin, bu işlem {settings.get('wait', 20)} saniye sürebilir)...")
        
        result = None
        for bot_username in settings.get('bots', []):
            try:
                bot_entity = await client.get_entity(bot_username)
                
                if cmd == 'reddit':
                    result = await handle_reddit(bot_entity, url)
                else:
                    sent_msg = await client.send_message(bot_entity, url)
                    result = await wait_for_response(bot_entity, sent_msg.id, settings.get('wait', 20))
                
                if result:
                    break
            except Exception as e:
                logger.error(f"{bot_username} hatası: {str(e)}")
                continue
        
        # Sonuçları işle
        await status_msg.delete()
        if result:
            await client.forward_messages(event.chat_id, result)
        else:
            await client.send_message(event.chat_id, "❌ Hedef bot yanıt vermedi")
            
    except Exception as e:
        logger.error(f"Komut hatası: {str(e)}")
        await client.send_message(event.chat_id, f"❌ Sistem hatası: {str(e)}")

async def main():
    await client.start()
    logger.info("UserBot başlatıldı!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
