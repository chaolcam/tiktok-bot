import os
import sys
import importlib
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaDocument

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

# Plugin klasörü
PLUGIN_DIR = "plugins"
os.makedirs(PLUGIN_DIR, exist_ok=True)

# Bot ayarları (TÜM SOSYAL MEDYALAR KORUNDU)
BOT_SETTINGS = {
    'tiktok': {
        'bots': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'wait': 15,
        'retry_wait': 8,
        'retry_text': "Yanlış TikTok Linki",
        'album_wait': 2
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

# Dinamik HELP mesajı
BASE_HELP = f"""
✨ <b>Social Media UserBot</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.reddit</code> <i>url</i> - Reddit içeriği indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.youtube</code> <i>url</i> - YouTube videosu indir

<b>🔌 Plugin Komutları:</b>
<code>.install</code> <i>(yanıt)</i> - .py plugin yükle
<code>.uninstall</code> <i>plugin_adi</i> - Plugin kaldır
<code>.plugins</code> - Yüklü pluginleri listele

📂 <b>Plugin Klasörü:</b> <code>{PLUGIN_DIR}</code>
⏳ <i>Albümler ~10s, videolar ~5s, Reddit ~35s</i>
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
client._help_message = BASE_HELP

# ORİJİNAL FONKSİYONLARINIZ (Tüm platformlar korundu)
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
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['tiktok', 'reddit', 'twitter', 'youtube']):
                        messages.append(msg)
                        message_ids.add(msg.id)
            
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

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Botun yanıtını bekler (TÜM PLATFORMLAR İÇİN)"""
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

# TÜM SOSYAL MEDYA KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_social_command(event):
    """Tüm sosyal medya komutlarını işler"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    try:
        cmd = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        settings = BOT_SETTINGS.get(cmd, {})
        
        await event.delete()
        logger.info(f"▸ {cmd.upper()} komutu: {url}")
        
        estimated_time = settings.get('wait', 20)
        if cmd == 'tiktok' and 'album' in url.lower():
            estimated_time = 12
        
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
                
                if cmd == 'tiktok':
                    sent_msg = await client.send_message(bot_entity, url)
                    first_response = await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))
                    
                    if not first_response:
                        continue
                        
                    if settings.get('retry_text', '') in getattr(first_response, 'text', ''):
                        continue
                    
                    if hasattr(first_response, 'grouped_id') or (first_response.text and "album" in first_response.text.lower()):
                        result = await get_unique_album_messages(bot_entity, sent_msg.id, settings.get('wait'))
                    else:
                        result = [first_response]
                else:
                    sent_msg = await client.send_message(bot_entity, url)
                    result = [await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))]
                
                if result and any(result):
                    break
            except Exception as e:
                logger.error(f"▸ {cmd.upper()} hatası @{bot_username}: {str(e)}")
                continue
        
        elapsed = (datetime.now() - start_time).total_seconds()
        await status_msg.delete()
        
        if result and any(result):
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
                    await asyncio.sleep(0.5)
        else:
            await event.respond(
                f"❌ <b>{cmd.upper()}</b> indirilemedi\n"
                f"⏱️ <code>{elapsed:.1f}s</code>",
                parse_mode='html'
            )
            
    except Exception as e:
        logger.error(f"▸ {cmd.upper()} komut hatası: {str(e)}")
        await event.respond(
            f"⚠️ <b>{cmd.upper()} Hatası</b>\n<code>{str(e)}</code>",
            parse_mode='html'
        )

# PLUGIN SİSTEMİ (Önceki gibi korundu)
async def load_plugins():
    """Plugin yükleme fonksiyonu"""
    loaded = 0
    for filename in os.listdir(PLUGIN_DIR):
        if filename.endswith('.py'):
            try:
                plugin_path = os.path.join(PLUGIN_DIR, filename)
                spec = importlib.util.spec_from_file_location(filename[:-3], plugin_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[filename[:-3]] = module
                spec.loader.exec_module(module)
                
                if hasattr(module, 'register_plugin'):
                    module.register_plugin(client)
                    loaded += 1
                    logger.info(f"▸ Plugin yüklendi: {filename}")
            except Exception as e:
                logger.error(f"▸ Plugin yükleme hatası ({filename}): {str(e)}")
    return loaded

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    """Güncellenmiş help komutu"""
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(
            getattr(client, '_help_message', BASE_HELP),
            parse_mode='html'
        )

# BAŞLANGIÇ
async def main():
    await client.start()
    me = await client.get_me()
    
    # Plugin yükle
    loaded_plugins = await load_plugins()
    
    # Başlangıç mesajı
    start_msg = (
        f"🚀 <b>UserBot Aktif</b>\n"
        f"👤 <code>@{me.username}</code>\n"
        f"🛠️ <b>Platformlar:</b> TikTok, Reddit, Twitter, YouTube\n"
        f"🔌 <b>Pluginler:</b> <code>{loaded_plugins}</code>\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await client.send_message('me', start_msg, parse_mode='html')
    logger.info(f"▸ Bot başlatıldı ▸ @{me.username} ▸ {loaded_plugins} plugin")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
