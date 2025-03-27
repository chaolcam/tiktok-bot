import os
import sys
import importlib.machinery
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

# Plugin klasörü
PLUGIN_DIR = "plugins"
os.makedirs(PLUGIN_DIR, exist_ok=True)

# Bot ayarları (SADECE TIKTOK VE TWITTER)
BOT_SETTINGS = {
    'tiktok': {
        'bots': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'wait': 15,
        'retry_wait': 8,
        'retry_text': "Yanlış TikTok Linki",
        'album_wait': 2
    },
    'twitter': {
        'bots': ['@twitterimage_bot', '@embedybot'],
        'wait': 20
    }
}

# Dinamik HELP mesajı
BASE_HELP = f"""
✨ <b>Social Media Downloader</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.help</code> - Bu mesajı göster

<b>🔌 Plugin Komutları:</b>
<code>.install</code> <i>(yanıt)</i> - .py plugin yükle
<code>.plugins</code> - Yüklü pluginleri listele

📂 <b>Plugin Klasörü:</b> <code>{PLUGIN_DIR}</code>
⏳ <i>TikTok albümler ~10s, Twitter ~20s</i>
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
client._help_message = BASE_HELP

# PLUGIN SİSTEMİ (TAM ÇALIŞIR)
async def load_plugin(plugin_path):
    try:
        plugin_name = os.path.basename(plugin_path)[:-3]
        loader = importlib.machinery.SourceFileLoader(plugin_name, plugin_path)
        module = loader.load_module()
        
        if hasattr(module, 'register_plugin'):
            module.register_plugin(client)
            logger.info(f"✅ Plugin yüklendi: {plugin_name}")
            return True
        logger.error(f"❌ {plugin_name}: register_plugin fonksiyonu yok")
        return False
    except Exception as e:
        logger.error(f"❌ Plugin hatası: {str(e)}")
        return False

async def load_plugins():
    loaded = 0
    for filename in os.listdir(PLUGIN_DIR):
        if filename.endswith('.py') and not filename.startswith('_'):
            if await load_plugin(os.path.join(PLUGIN_DIR, filename)):
                loaded += 1
    return loaded

# PLUGIN KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.install$'))
async def handle_install(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    reply = await event.get_reply_message()
    if not reply or not reply.document or not reply.file.name.endswith('.py'):
        await event.edit("❌ Lütfen bir .py dosyasına yanıt verin")
        return
    
    plugin_path = os.path.join(PLUGIN_DIR, reply.file.name)
    await reply.download_media(file=plugin_path)
    
    if await load_plugin(plugin_path):
        await event.edit(f"✅ **{reply.file.name}** yüklendi!")
    else:
        os.remove(plugin_path)
        await event.edit("❌ Plugin yüklenemedi")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.plugins$'))
async def handle_plugins(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugins = [f for f in os.listdir(PLUGIN_DIR) if f.endswith('.py')]
    msg = "📂 **Yüklü Pluginler:**\n\n" + "\n".join(f"▸ `{p}`" for p in plugins) if plugins else "❌ Hiç plugin yüklü değil"
    await event.edit(msg, parse_mode='html')

# SOSYAL MEDYA FONKSİYONLARI
async def get_unique_messages(bot_entity, first_msg_id, wait_time):
    messages = []
    end_time = datetime.now().timestamp() + wait_time
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=first_msg_id):
                if msg.id > first_msg_id and msg not in messages:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['tiktok', 'twitter']):
                        messages.append(msg)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Mesaj alma hatası: {str(e)}")
            break
    return messages

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    end_time = datetime.now().timestamp() + wait_time
    last_msg_id = after_msg_id
    
    while datetime.now().timestamp() < end_time:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=last_msg_id, limit=1):
                if msg.id > last_msg_id:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['http', 'tiktok', 'twitter']):
                        return msg
                    last_msg_id = msg.id
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Yanıt bekleme hatası: {str(e)}")
            await asyncio.sleep(1)
    return None

# TIKTOK & TWITTER KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|twitter)\s+(https?://\S+)$'))
async def handle_social_command(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    cmd = event.pattern_match.group(1)
    url = event.pattern_match.group(2)
    settings = BOT_SETTINGS.get(cmd, {})
    
    await event.delete()
    logger.info(f"▸ {cmd.upper()} isteği: {url}")
    
    status_msg = await event.respond(
        f"🔄 <b>{cmd.upper()}</b> işleniyor...\n⏳ Tahmini: <code>{settings.get('wait', 20)}s</code>",
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
                    result = await get_unique_messages(bot_entity, sent_msg.id, settings.get('wait'))
                else:
                    result = [first_response]
            else:  # Twitter
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
        f"📡 <b>Desteklenenler:</b> TikTok, Twitter\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await client.send_message('me', start_msg, parse_mode='html')
    logger.info(f"▸ Bot başlatıldı ▸ @{me.username}")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
