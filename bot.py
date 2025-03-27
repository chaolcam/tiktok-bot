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

# Bot ayarları
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
✨ <b>Social Media Downloader + Plugin Yönetici</b> ✨

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

# PLUGIN SİSTEMİ
async def load_plugins():
    """Başlangıçta tüm pluginleri yükler"""
    loaded = 0
    for filename in os.listdir(PLUGIN_DIR):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                plugin_name = filename[:-3]
                plugin_path = os.path.join(PLUGIN_DIR, filename)
                
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
                
                if hasattr(module, 'register_plugin'):
                    module.register_plugin(client)
                    loaded += 1
                    logger.info(f"▸ Plugin yüklendi: {filename}")
            except Exception as e:
                logger.error(f"▸ Plugin hatası ({filename}): {str(e)}")
    return loaded

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.install$'))
async def handle_install(event):
    """Plugin yükler"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    reply = await event.get_reply_message()
    if not reply or not reply.document or not reply.file.name.endswith('.py'):
        await event.edit("❌ Lütfen bir .py dosyasına yanıt verin")
        return
    
    try:
        plugin_path = os.path.join(PLUGIN_DIR, reply.file.name)
        await reply.download_media(file=plugin_path)
        
        plugin_name = reply.file.name[:-3]
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'register_plugin'):
            module.register_plugin(client)
            await event.edit(f"✅ **{reply.file.name}** yüklendi!")
        else:
            os.remove(plugin_path)
            await event.edit("❌ Plugin geçersiz: register_plugin fonksiyonu yok")
    except Exception as e:
        await event.edit(f"❌ Yükleme hatası:\n`{str(e)}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.uninstall\s+(\w+)$'))
async def handle_uninstall(event):
    """Plugin kaldırır"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugin_name = event.pattern_match.group(1)
    plugin_path = os.path.join(PLUGIN_DIR, f"{plugin_name}.py")
    
    if os.path.exists(plugin_path):
        os.remove(plugin_path)
        await event.edit(f"✅ **{plugin_name}** kaldırıldı")
    else:
        await event.edit(f"❌ Plugin bulunamadı: `{plugin_name}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.plugins$'))
async def handle_plugins(event):
    """Yüklü pluginleri listeler"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugins = [f for f in os.listdir(PLUGIN_DIR) if f.endswith('.py')]
    msg = "📂 **Yüklü Pluginler:**\n\n" + "\n".join(f"▸ `{p}`" for p in plugins) if plugins else "❌ Hiç plugin yüklü değil"
    await event.edit(msg)

# SOSYAL MEDYA FONKSİYONLARI
async def get_unique_album_messages(bot_entity, first_msg_id, wait_time):
    """Albüm mesajlarını toplar"""
    messages = []
    end_time = datetime.now().timestamp() + wait_time
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=first_msg_id):
                if msg.id > first_msg_id and msg not in messages:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['tiktok', 'reddit', 'twitter', 'youtube']):
                        messages.append(msg)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Albüm tarama hatası: {str(e)}")
            break
    
    return messages

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Bot yanıtını bekler"""
    end_time = datetime.now().timestamp() + wait_time
    last_msg_id = after_msg_id
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
                if msg.id > last_msg_id:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['http', 'tiktok', 'reddit', 'twitter', 'youtube']):
                        return msg
                    last_msg_id = msg.id
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Yanıt bekleme hatası: {str(e)}")
            await asyncio.sleep(1)
    
    return None

# SOSYAL MEDYA KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_social_command(event):
    """Tüm sosyal medya komutları"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    cmd = event.pattern_match.group(1)
    url = event.pattern_match.group(2)
    settings = BOT_SETTINGS.get(cmd, {})
    
    await event.delete()
    logger.info(f"▸ {cmd.upper()} isteği: {url}")
    
    estimated_time = settings.get('wait', 20)
    status_msg = await event.respond(
        f"🔄 <b>{cmd.upper()}</b> işleniyor...\n⏳ Tahmini: <code>{estimated_time}s</code>",
        parse_mode='html'
    )
    
    start_time = datetime.now()
    result = None
    
    for bot_username in settings.get('bots', []):
        try:
            bot_entity = await client.get_entity(bot_username)
            sent_msg = await client.send_message(bot_entity, url)
            
            if cmd == 'tiktok':
                first_response = await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))
                if not first_response:
                    continue
                
                if settings.get('retry_text', '') in getattr(first_response, 'text', ''):
                    continue
                
                if hasattr(first_response, 'grouped_id') or 'album' in getattr(first_response, 'text', '').lower():
                    result = await get_unique_album_messages(bot_entity, sent_msg.id, settings.get('wait'))
                else:
                    result = [first_response]
            else:
                result = [await wait_for_response(bot_entity, sent_msg.id, settings.get('wait'))]
            
            if result:
                break
        except Exception as e:
            logger.error(f"▸ {cmd.upper()} hatası @{bot_username}: {str(e)}")
            continue
    
    elapsed = (datetime.now() - start_time).total_seconds()
    await status_msg.delete()
    
    if result:
        unique_results = []
        seen_ids = set()
        for item in result:
            if item and item.id not in seen_ids:
                unique_results.append(item)
                seen_ids.add(item.id)
        
        await event.respond(
            f"✅ <b>{cmd.upper()}</b> başarılı!\n📦 <code>{len(unique_results)}</code> içerik • ⏱️ <code>{elapsed:.1f}s</code>",
            parse_mode='html'
        )
        
        for item in unique_results:
            if item.media:
                await client.send_file(event.chat_id, item.media)
            elif item.text:
                await client.send_message(event.chat_id, item.text)
            await asyncio.sleep(0.5)
    else:
        await event.respond(
            f"❌ <b>{cmd.upper()}</b> başarısız\n⏱️ <code>{elapsed:.1f}s</code>",
            parse_mode='html'
        )

# DİĞER KOMUTLAR
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    """Yardım mesajını gösterir"""
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(client._help_message, parse_mode='html')

# BAŞLANGIÇ
async def main():
    await client.start()
    me = await client.get_me()
    loaded_plugins = await load_plugins()
    
    start_msg = (
        f"🚀 <b>UserBot Aktif</b>\n"
        f"👤 <code>@{me.username}</code>\n"
        f"🔌 <b>Pluginler:</b> <code>{loaded_plugins}</code>\n"
        f"🛠️ <b>Desteklenen Platformlar:</b> TikTok, Reddit, Twitter, YouTube\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await client.send_message('me', start_msg, parse_mode='html')
    logger.info(f"▸ Bot başlatıldı ▸ @{me.username}")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
