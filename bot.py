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
        'wait': 25,
        'retry_text': "Yanlış TikTok Linki"
    },
    'reddit': {
        'bots': ['@reddit_download_bot'],
        'wait': 40
    },
    'twitter': {
        'bots': ['@twitterimage_bot', '@embedybot'],
        'wait': 25
    },
    'youtube': {
        'bots': ['@embedybot'],
        'wait': 25
    }
}

HELP_MESSAGE = """
📚 **Kullanım Kılavuzu**

🔹 **Komutlar:**
`.tiktok <url>` - TikTok videosu indir
`.reddit <url>` - Reddit içeriği indir
`.twitter <url>` - Twitter içeriği indir
`.youtube <url>` - YouTube videosu indir
`.help` - Bu yardım mesajını göster

⏳ **Reddit işlemleri 30-40 saniye sürebilir**
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def click_inline_button(msg, button_text):
    """Inline butona basar"""
    if not hasattr(msg, 'buttons'):
        return False
        
    for row in msg.buttons:
        for button in row:
            if button_text.lower() in button.text.lower():
                await button.click()
                return True
    return False

async def handle_reddit_interaction(bot_entity, url):
    """Reddit botuyla etkileşim"""
    try:
        # Linki gönder
        sent_msg = await client.send_message(bot_entity, url)
        
        # İlk yanıtı bekle (media/file seçimi)
        first_resp = await wait_for_response(bot_entity, sent_msg.id, 15)
        if not first_resp:
            return None
            
        # Media butonuna bas
        await click_inline_button(first_resp, "media")
        
        # Kalite seçimini bekle
        quality_resp = await wait_for_response(bot_entity, first_resp.id, 15)
        if not quality_resp:
            return None
            
        # En yüksek kaliteyi seç (720p > 480p)
        if not await click_inline_button(quality_resp, "720p"):
            await click_inline_button(quality_resp, "480p")
        
        # Sonucu al
        return await wait_for_response(bot_entity, quality_resp.id, 15)
    except Exception as e:
        logger.error(f"Reddit hatası: {str(e)}")
        return None

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Botun yanıtını bekler"""
    last_msg_id = after_msg_id
    end_time = asyncio.get_event_loop().time() + wait_time
    
    while asyncio.get_event_loop().time() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
                if msg.id > last_msg_id:
                    if msg.media or (hasattr(msg, 'text') and ('http' in msg.text or any(x in msg.text.lower() for x in ['tiktok', 'reddit', 'twitter', 'youtube'])):
                        return msg
                    last_msg_id = msg.id
                    await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Bekleme hatası: {str(e)}")
            await asyncio.sleep(2)
    
    return None

async def handle_tiktok(bot_entity, url):
    """TikTok için özel işlem"""
    try:
        sent_msg = await client.send_message(bot_entity, url)
        response = await wait_for_response(bot_entity, sent_msg.id, 15)
        
        # Eğer hatalı link mesajı gelirse None döndür
        if response and BOT_SETTINGS['tiktok']['retry_text'] in response.text:
            return None
        return response
    except Exception as e:
        logger.error(f"TikTok hatası: {str(e)}")
        return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_command(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    try:
        cmd = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        settings = BOT_SETTINGS.get(cmd, {})
        
        # Komut mesajını sil
        await event.delete()
        
        # İşlem başladı mesajı
        status_msg = await event.respond(f"⏳ {cmd.upper()} işleniyor...")
        
        result = None
        for bot_username in settings.get('bots', []):
            try:
                bot_entity = await client.get_entity(bot_username)
                
                if cmd == 'reddit':
                    result = await handle_reddit_interaction(bot_entity, url)
                elif cmd == 'tiktok':
                    result = await handle_tiktok(bot_entity, url)
                else:
                    sent_msg = await client.send_message(bot_entity, url)
                    result = await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))
                
                if result:
                    break
            except Exception as e:
                logger.error(f"{bot_username} hatası: {str(e)}")
                continue
        
        await status_msg.delete()
        if result:
            # İçerik indirildi mesajı
            await event.respond(f"✅ {cmd.upper()} içeriği indirildi:")
            # Medyayı gönder (orijinal gönderim şekliyle)
            await client.send_message(event.chat_id, file=result.media if result.media else result.text)
        else:
            await event.respond(f"❌ {cmd.upper()} içeriği indirilemedi")
            
    except Exception as e:
        logger.error(f"Komut hatası: {str(e)}")
        await event.respond(f"❌ Hata: {str(e)}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(HELP_MESSAGE)

async def main():
    await client.start()
    me = await client.get_me()
    logger.info(f"UserBot başlatıldı: @{me.username}")
    
    # Başlangıç bildirimi
    await client.send_message('me', '🤖 UserBot aktif ve komut bekliyor!\n\nYardım için `.help` yazın')
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
