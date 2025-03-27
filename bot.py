import os
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='▸ %(asctime)s ▸ %(levelname)s ▸ %(message)s',
    datefmt='%H:%M:%S'
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
        'wait': 15,
        'retry_wait': 8,
        'retry_text': "Yanlış TikTok Linki",
        'album_wait': 2  # Albüm tarama aralığı
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

HELP_MESSAGE = """
✨ <b>Social Media Downloader Bot</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.reddit</code> <i>url</i> - Reddit içeriği indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.youtube</code> <i>url</i> - YouTube videosu indir
<code>.help</code> - Bu mesajı göster

⏳ <i>Albümler için ~10s, videolar için ~5s</i>
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def get_unique_album_messages(bot_entity, first_msg_id, wait_time):
    """Yinelenenleri kaldırarak albüm mesajlarını toplar"""
    messages = []
    message_ids = set()
    logger.info(f"▸ Albüm taraması başladı (max {wait_time}s)")
    
    end_time = datetime.now().timestamp() + wait_time
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=first_msg_id):
                if msg.id > first_msg_id and msg.id not in message_ids:
                    if msg.media or 'tiktok' in getattr(msg, 'text', '').lower():
                        messages.append(msg)
                        message_ids.add(msg.id)
                        logger.info(f"▸ Albüm parçası eklendi: {len(messages)}. içerik")
            
            # Albüm tamamlandı mı kontrol et
            if len(messages) > 0 and not await has_more_album_parts(bot_entity, messages[-1].id):
                break
                
            await asyncio.sleep(BOT_SETTINGS['tiktok']['album_wait'])
        except Exception as e:
            logger.error(f"▸ Albüm tarama hatası: {str(e)}")
            break
    
    logger.info(f"▸ Albüm taraması tamamlandı: {len(messages)} içerik")
    return messages

async def has_more_album_parts(bot_entity, last_msg_id):
    """Daha fazla albüm parçası var mı kontrol eder"""
    try:
        async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
            if msg.id > last_msg_id:
                return True
        return False
    except:
        return False

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
            return await get_unique_album_messages(bot_entity, sent_msg.id, wait_time)
        
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
                    if msg.media or (hasattr(msg, 'text') and ('http' in msg.text or any(x in msg.text.lower() for x in ['tiktok', 'reddit', 'twitter', 'youtube']))):
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
        
        # Tahmini süre hesapla
        estimated_time = settings.get('wait', 20)
        if cmd == 'tiktok' and 'album' in url.lower():
            estimated_time = 12  # Albümler için ortalama süre
        
        # İşlem başladı mesajı
        start_time = datetime.now()
        status_msg = await event.respond(
            f"🔄 <b>{cmd.upper()}</b> işleniyor...\n"
            f"⏳ Tahmini süre: <code>{estimated_time}s</code>",
            parse_mode='html'
        )
        
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
        elapsed = (datetime.now() - start_time).total_seconds()
        
        await status_msg.delete()
        if result and any(result):
            # Gerçek içerik sayısını filtrele (yinelenenleri kaldır)
            unique_results = []
            seen_ids = set()
            for item in result:
                if item and item.id not in seen_ids:
                    unique_results.append(item)
                    seen_ids.add(item.id)
            
            await event.respond(
                f"✅ <b>{cmd.upper()}</b> başarıyla indirildi\n"
                f"📦 <code>{len(unique_results)}</code> içerik • ⏱️ <code>{elapsed:.1f}s</code>",
                parse_mode='html'
            )
            
            for item in unique_results:
                if item:
                    await client.send_message(
                        event.chat_id,
                        file=item.media if item.media else item.text,
                        parse_mode='html'
                    )
                    await asyncio.sleep(0.5)  # Flood önleme
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
