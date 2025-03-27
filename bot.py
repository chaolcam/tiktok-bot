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

# Bot eşleştirmeleri ve bekleme süreleri
BOT_SETTINGS = {
    'tiktok': {
        'bots': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'wait_time': 15  # 15 saniye bekle
    },
    'reddit': {
        'bots': ['@reddit_download_bot'],
        'wait_time': 25  # 25 saniye bekle
    },
    'twitter': {
        'bots': ['@twitterimage_bot', '@embedybot'],
        'wait_time': 15
    },
    'youtube': {
        'bots': ['@embedybot'],
        'wait_time': 15
    }
}

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def get_bot_response(bot_entity, sent_msg_id, wait_time):
    """Hedef botun yanıtını bekler ve döndürür"""
    try:
        async for msg in client.iter_messages(
            bot_entity,
            min_id=sent_msg_id,
            wait_time=wait_time,
            limit=5
        ):
            if msg.id > sent_msg_id and (msg.media or 'http' in getattr(msg, 'text', '')):
                return msg
        return None
    except Exception as e:
        logger.error(f"Yanıt bekleme hatası: {str(e)}")
        return None

async def handle_reddit_buttons(bot_entity, sent_msg_id):
    """Reddit botundaki butonlara basar"""
    try:
        # İlk yanıtı bekle (media/file seçimi)
        first_response = await get_bot_response(bot_entity, sent_msg_id, 10)
        if not first_response or not hasattr(first_response, 'buttons'):
            return None

        # Media butonuna bas
        for row in first_response.buttons:
            for btn in row:
                if "media" in btn.text.lower():
                    await btn.click()
                    break

        # Kalite seçimini bekle (2. yanıt)
        quality_response = await get_bot_response(bot_entity, first_response.id, 10)
        if not quality_response or not hasattr(quality_response, 'buttons'):
            return None

        # En yüksek kaliteyi seç (720p > 480p)
        for row in quality_response.buttons:
            for btn in row:
                if "720p" in btn.text:
                    await btn.click()
                    break
                elif "480p" in btn.text:
                    await btn.click()
                    break

        # Son yanıtı al (3. yanıt)
        return await get_bot_response(bot_entity, quality_response.id, 10)
    except Exception as e:
        logger.error(f"Reddit buton hatası: {str(e)}")
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
        
        # İşlem başladı mesajı
        status_msg = await event.respond(f"⏳ {cmd.capitalize()} işleniyor (Bu biraz zaman alabilir)...")
        
        # Hedef botlara sırayla deneme
        result = None
        for bot_username in settings.get('bots', []):
            try:
                bot_entity = await client.get_entity(bot_username)
                
                # Linki hedef bota gönder
                sent_msg = await client.send_message(bot_entity, url)
                
                if cmd == 'reddit':
                    result = await handle_reddit_buttons(bot_entity, sent_msg.id)
                else:
                    result = await get_bot_response(
                        bot_entity, 
                        sent_msg.id, 
                        settings.get('wait_time', 15)
                    )
                
                if result:
                    break
                    
            except Exception as e:
                logger.error(f"{bot_username} hatası: {str(e)}")
                continue
        
        # Sonuçları işle
        await status_msg.delete()
        if result:
            await client.send_message(event.chat_id, f"✅ {cmd.capitalize()} başarıyla indirildi!")
            await client.forward_messages(event.chat_id, result)
        else:
            await client.send_message(
                event.chat_id,
                "⚠️ İndirme tamamlanamadı, ancak hedef bot işlemi tamamlamış olabilir. "
                "Lütfen hedef botun sohbetini kontrol edin."
            )
            
    except Exception as e:
        logger.error(f"Komut hatası: {str(e)}")
        await client.send_message(event.chat_id, f"❌ Sistem hatası: {str(e)}")

async def main():
    await client.start()
    logger.info("UserBot başlatıldı!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
