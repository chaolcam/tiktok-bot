import os
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import DocumentAttributeFilename

# ██████  ██████  ████████ 
#██    ██ ██   ██    ██    
#██    ██ ██████     ██    
#██    ██ ██         ██    
# ██████  ██         ██    

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='▸ %(asctime)s ▸ %(levelname)s ▸ %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ██████  ██████  ████████ 
#██    ██ ██   ██    ██    
#██    ██ ██████     ██    
#██    ██ ██         ██    
# ██████  ██         ██    

# Config
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))

# ██████  ██████  ████████ 
#██    ██ ██   ██    ██    
#██    ██ ██████     ██    
#██    ██ ██         ██    
# ██████  ██         ██    

# Bot ayarları
BOT_SETTINGS = {
    'tiktok': {
        'bots': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'wait': 15,
        'retry_wait': 8,
        'retry_text': "Yanlış TikTok Linki",
        'album_wait': 3
    },
    'reddit': {
        'bots': ['@reddit_download_bot'],
        'wait': 35
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

# ██████  ██████  ████████ 
#██    ██ ██   ██    ██    
#██    ██ ██████     ██    
#██    ██ ██         ██    
# ██████  ██         ██    

HELP_MESSAGE = """
✨ <b>Social Media Downloader Bot</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.reddit</code> <i>url</i> - Reddit içeriği indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.youtube</code> <i>url</i> - YouTube videosu indir
<code>.help</code> - Bu mesajı göster

⏳ <i>TikTok albümleri 10-15s, Reddit 35s sürebilir</i>
"""

# ██████  ██████  ████████ 
#██    ██ ██   ██    ██    
#██    ██ ██████     ██    
#██    ██ ██         ██    
# ██████  ██         ██    

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def send_typing(chat, seconds):
    """Yazıyor efekti"""
    end_time = datetime.now().timestamp() + seconds
    while datetime.now().timestamp() < end_time:
        await client.send_read_acknowledge(chat)
        await asyncio.sleep(2)

async def format_time(seconds):
    """Saniyeyi okunabilir zamana çevirir"""
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"

async def get_all_album_messages(bot_entity, first_msg_id, wait_time):
    """Tüm albüm mesajlarını toplar"""
    messages = []
    logger.info(f"▸ Albüm indirme başladı (max {wait_time}s)")
    
    async with client.action(bot_entity, 'photo') as action:
        end_time = datetime.now().timestamp() + wait_time
        
        while datetime.now().timestamp() < end_time:
            try:
                async for msg in client.iter_messages(bot_entity, min_id=first_msg_id):
                    if msg.id > first_msg_id and (msg.media or 'tiktok' in getattr(msg, 'text', '').lower()):
                        if msg not in messages:
                            messages.append(msg)
                            logger.info(f"▸ Albüm parçası eklendi: {len(messages)}. resim")
                await asyncio.sleep(BOT_SETTINGS['tiktok']['album_wait'])
            except Exception as e:
                logger.error(f"▸ Albüm hatası: {str(e)}")
                break
    
    logger.info(f"▸ Albüm tamamlandı: {len(messages)} resim")
    return messages

async def handle_tiktok(bot_entity, url):
    """TikTok için özel işlem"""
    try:
        logger.info(f"▸ TikTok işlemi başladı [@{bot_entity.username}]")
        sent_msg = await client.send_message(bot_entity, url)
        wait_time = BOT_SETTINGS['tiktok']['retry_wait'] if bot_entity.username == BOT_SETTINGS['tiktok']['bots'][1] else BOT_SETTINGS['tiktok']['wait']
        
        first_response = await wait_for_response(bot_entity, sent_msg.id, wait_time)
        
        if not first_response:
            logger.warning("▸ TikTok yanıt alınamadı")
            return None
            
        if BOT_SETTINGS['tiktok']['retry_text'] in getattr(first_response, 'text', ''):
            logger.warning("▸ Geçersiz TikTok linki")
            return None
        
        if hasattr(first_response, 'grouped_id') or (first_response.text and "album" in first_response.text.lower()):
            logger.info("▸ TikTok albümü tespit edildi")
            return await get_all_album_messages(bot_entity, sent_msg.id, wait_time)
        
        return [first_response]
    except Exception as e:
        logger.error(f"▸ TikTok hatası: {str(e)}")
        return None

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Botun yanıtını bekler"""
    logger.info(f"▸ Yanıt bekleniyor (max {wait_time}s) [@{bot_entity.username}]")
    last_msg_id = after_msg_id
    end_time = datetime.now().timestamp() + wait_time
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
                if msg.id > last_msg_id:
                    if msg.media or (hasattr(msg, 'text') and ('http' in msg.text or any(x in msg.text.lower() for x in ['tiktok', 'reddit', 'twitter', 'youtube'])):
                        logger.info("▸ Yanıt alındı")
                        return msg
                    last_msg_id = msg.id
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Bekleme hatası: {str(e)}")
            await asyncio.sleep(1)
    
    logger.warning("▸ Yanıt zaman aşımı")
    return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_command(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    try:
        cmd = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        settings = BOT_SETTINGS.get(cmd, {})
        
        await event.delete()
        logger.info(f"▸ Yeni komut: {cmd.upper()} {url}")
        
        # İşlem başladı mesajı
        start_time = datetime.now()
        status_msg = await event.respond(
            f"🔄 <b>{cmd.upper()}</b> işleniyor...\n"
            f"⏳ Tahmini süre: <code>{format_time(settings.get('wait', 20))}</code>",
            parse_mode='html'
        )
        
        # Yazıyor efekti
        typing_task = asyncio.create_task(send_typing(event.chat_id, settings.get('wait', 20)))
        
        result = None
        for bot_username in settings.get('bots', []):
            try:
                bot_entity = await client.get_entity(bot_username)
                logger.info(f"▸ Hedef bot: @{bot_entity.username}")
                
                if cmd == 'tiktok':
                    result = await handle_tiktok(bot_entity, url)
                elif cmd == 'reddit':
                    result = await handle_reddit_interaction(bot_entity, url)
                else:
                    sent_msg = await client.send_message(bot_entity, url)
                    result = [await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))]
                
                if result and any(result):
                    break
            except Exception as e:
                logger.error(f"▸ Bot hatası @{bot_username}: {str(e)}")
                continue
        
        # Sonuçları işle
        typing_task.cancel()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        await status_msg.delete()
        if result and any(result):
            success_msg = await event.respond(
                f"✅ <b>{cmd.upper()}</b> başarıyla indirildi\n"
                f"📦 <code>{len(result)}</code> içerik • ⏱️ <code>{elapsed:.1f}s</code>",
                parse_mode='html'
            )
            
            for item in result:
                if item:
                    await client.send_message(
                        event.chat_id,
                        file=item.media if item.media else item.text,
                        parse_mode='html'
                    )
                    await asyncio.sleep(1)  # Flood önleme
        else:
            await event.respond(
                f"❌ <b>{cmd.upper()}</b> indirilemedi\n"
                f"⏱️ <code>{elapsed:.1f}s</code>",
                parse_mode='html'
            )
            
    except Exception as e:
        logger.error(f"▸ Komut hatası: {str(e)}")
        await event.respond(
            f"⚠️ <b>Sistem Hatası</b>\n<code>{str(e)}</code>",
            parse_mode='html'
        )

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(HELP_MESSAGE, parse_mode='html')

async def main():
    await client.start()
    me = await client.get_me()
    
    # ASCII Art Banner
    BANNER = """
░█▀▀░█▀▀░█▀█░█▀▄░▀█▀░█▀▀░█░█
░█▀▀░█▀▀░█░█░█▀▄░░█░░▀▀█░█▀█
░▀▀▀░▀▀▀░▀░▀░▀░▀░▀▀▀░▀▀▀░▀░▀
    """
    
    logger.info(f"\n{BANNER}")
    logger.info(f"▸ UserBot başlatıldı ▸ @{me.username}")
    logger.info(f"▸ Versiyon ▸ 2.1.0")
    
    # Başlangıç bildirimi
    await client.send_message(
        'me',
        f"🚀 <b>UserBot Aktif</b>\n"
        f"👤 <code>@{me.username}</code>\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>",
        parse_mode='html'
    )
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
