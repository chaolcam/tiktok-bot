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

# Bot ayarları (TikTok + Twitter)
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
✨ <b>Social Media Downloader + Plugin Manager</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.help</code> - Bu mesajı göster

<b>🔌 Plugin Komutları:</b>
<code>.install</code> <i>(reply)</i> - Install .py plugin
<code>.uninstall</code> <i>plugin_name</i> - Remove plugin
<code>.plugins</code> - List installed plugins

📂 <b>Plugin Folder:</b> <code>{PLUGIN_DIR}</code>
⏳ <i>TikTok albums ~10s, Twitter ~20s</i>
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
client._help_message = BASE_HELP
client._plugin_commands = {}

# PLUGIN SİSTEMİ
async def load_plugin(plugin_path):
    """Load a single plugin"""
    try:
        plugin_name = os.path.basename(plugin_path)[:-3]
        loader = importlib.machinery.SourceFileLoader(plugin_name, plugin_path)
        module = loader.load_module()
        
        if hasattr(module, 'register_plugin'):
            # Get plugin info if exists
            plugin_info = getattr(module, 'PLUGIN_INFO', {
                "name": plugin_name,
                "commands": {}
            })
            
            module.register_plugin(client)
            
            # Register plugin commands
            if hasattr(module, 'PLUGIN_INFO'):
                for cmd, desc in plugin_info["commands"].items():
                    client._plugin_commands[cmd] = desc
            
            logger.info(f"✅ Plugin loaded: {plugin_name}")
            return True
        
        logger.error(f"❌ {plugin_name}: Missing register_plugin function")
        return False
    except Exception as e:
        logger.error(f"❌ Plugin error: {str(e)}")
        return False

async def load_plugins():
    """Load all plugins on startup"""
    loaded = 0
    for filename in os.listdir(PLUGIN_DIR):
        if filename.endswith('.py') and not filename.startswith('_'):
            if await load_plugin(os.path.join(PLUGIN_DIR, filename)):
                loaded += 1
    
    # Update help message with plugin commands
    if client._plugin_commands:
        plugin_help = "\n\n🔧 <b>Plugin Commands:</b>\n"
        for cmd, desc in client._plugin_commands.items():
            plugin_help += f"<code>{cmd}</code> - {desc}\n"
        client._help_message += plugin_help
    
    return loaded

# PLUGIN KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.install$'))
async def handle_install(event):
    """Install a plugin"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    reply = await event.get_reply_message()
    if not reply or not reply.document or not reply.file.name.endswith('.py'):
        await event.edit("❌ Please reply to a .py file")
        return
    
    plugin_path = os.path.join(PLUGIN_DIR, reply.file.name)
    await reply.download_media(file=plugin_path)
    
    if await load_plugin(plugin_path):
        installed_commands = [cmd for cmd in client._plugin_commands.keys() if cmd.startswith(f'.{os.path.basename(plugin_path)[:-3]}')]
        await event.edit(
            f"✅ **{reply.file.name}** installed!\n\n"
            f"🔧 Available commands: {', '.join(installed_commands)}"
        )
    else:
        os.remove(plugin_path)
        await event.edit("❌ Failed to load plugin (check logs)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.uninstall\s+(\w+)$'))
async def handle_uninstall(event):
    """Uninstall a plugin"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugin_name = event.pattern_match.group(1)
    plugin_path = os.path.join(PLUGIN_DIR, f"{plugin_name}.py")
    
    if os.path.exists(plugin_path):
        # Remove plugin commands from help
        for cmd in list(client._plugin_commands.keys()):
            if cmd.startswith(f".{plugin_name}"):
                del client._plugin_commands[cmd]
        
        os.remove(plugin_path)
        await event.edit(f"✅ **{plugin_name}** uninstalled!")
    else:
        await event.edit(f"❌ Plugin not found: `{plugin_name}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.plugins$'))
async def handle_plugins(event):
    """List installed plugins"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugins = []
    for filename in os.listdir(PLUGIN_DIR):
        if filename.endswith('.py'):
            plugin_name = filename[:-3]
            plugin_commands = [cmd for cmd in client._plugin_commands.keys() if cmd.startswith(f'.{plugin_name}')]
            plugins.append(f"▸ <code>{plugin_name}</code> (Commands: {', '.join(plugin_commands) or 'None'}")
    
    msg = "📂 <b>Installed Plugins:</b>\n\n" + "\n".join(plugins) if plugins else "❌ No plugins installed"
    await event.edit(msg, parse_mode='html')

# SOSYAL MEDYA FONKSİYONLARI
async def get_unique_messages(bot_entity, first_msg_id, wait_time):
    """Get unique messages from a bot"""
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
            logger.error(f"▸ Message fetch error: {str(e)}")
            break
    return messages

async def wait_for_response(bot_entity, after_msg_id, wait_time):
    """Wait for bot response"""
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
            logger.error(f"▸ Response wait error: {str(e)}")
            await asyncio.sleep(1)
    return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tiktok\s+(https?://\S+)$'))
async def handle_tiktok(event):
    """Download TikTok video"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    url = event.pattern_match.group(1)
    settings = BOT_SETTINGS['tiktok']
    
    await event.delete()
    logger.info(f"▸ TikTok request: {url}")
    
    status_msg = await event.respond(
        f"🔄 <b>TikTok</b> processing...\n⏳ Estimated: <code>{settings['wait']}s</code>",
        parse_mode='html'
    )
    
    start_time = datetime.now()
    result = None
    
    for bot_username in settings['bots']:
        try:
            bot_entity = await client.get_entity(bot_username)
            sent_msg = await client.send_message(bot_entity, url)
            
            first_response = await wait_for_response(bot_entity, sent_msg.id, settings['wait'])
            if not first_response:
                continue
                
            if settings['retry_text'] in getattr(first_response, 'text', ''):
                continue
                
            if hasattr(first_response, 'grouped_id') or 'album' in getattr(first_response, 'text', '').lower():
                result = await get_unique_messages(bot_entity, sent_msg.id, settings['wait'])
            else:
                result = [first_response]
            
            if result:
                break
        except Exception as e:
            logger.error(f"▸ TikTok error @{bot_username}: {str(e)}")
            continue
    
    await process_social_result(event, status_msg, start_time, result, "TikTok")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.twitter\s+(https?://\S+)$'))
async def handle_twitter(event):
    """Download Twitter content"""
    if event.sender_id != AUTHORIZED_USER:
        return
    
    url = event.pattern_match.group(1)
    settings = BOT_SETTINGS['twitter']
    
    await event.delete()
    logger.info(f"▸ Twitter request: {url}")
    
    status_msg = await event.respond(
        f"🔄 <b>Twitter</b> processing...\n⏳ Estimated: <code>{settings['wait']}s</code>",
        parse_mode='html'
    )
    
    start_time = datetime.now()
    result = None
    
    for bot_username in settings['bots']:
        try:
            bot_entity = await client.get_entity(bot_username)
            sent_msg = await client.send_message(bot_entity, url)
            result = [await wait_for_response(bot_entity, sent_msg.id, settings['wait'])]
            
            if result:
                break
        except Exception as e:
            logger.error(f"▸ Twitter error @{bot_username}: {str(e)}")
            continue
    
    await process_social_result(event, status_msg, start_time, result, "Twitter")

async def process_social_result(event, status_msg, start_time, result, service_name):
    """Process social media download results"""
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
            f"✅ <b>{service_name}</b> success!\n"
            f"📦 <code>{len(unique_results)}</code> items • ⏱️ <code>{elapsed:.1f}s</code>",
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
            f"❌ <b>{service_name}</b> failed\n"
            f"⏱️ <code>{elapsed:.1f}s</code>",
            parse_mode='html'
        )

# HELP KOMUTU
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help(event):
    """Show help message"""
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(client._help_message, parse_mode='html')

# BAŞLANGIÇ
async def main():
    await client.start()
    me = await client.get_me()
    loaded_plugins = await load_plugins()
    
    start_msg = (
        f"🚀 <b>UserBot Activated</b>\n"
        f"👤 <code>@{me.username}</code>\n"
        f"🔌 <b>Plugins:</b> <code>{loaded_plugins}</code>\n"
        f"📡 <b>Services:</b> TikTok, Twitter\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await client.send_message('me', start_msg, parse_mode='html')
    logger.info(f"▸ Bot started ▸ @{me.username}")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
