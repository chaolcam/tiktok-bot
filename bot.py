import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerUser, InputPeerChannel

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurations from environment variables
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Validate configuration
if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("Lütfen API_ID, API_HASH ve BOT_TOKEN ortam değişkenlerini ayarlayın!")
    exit(1)

# Bot mapping
BOT_MAPPING = {
    'tiktok': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
    'reddit': ['@reddit_download_bot'],
    'twitter': ['@twitterimage_bot', '@embedybot'],
    'youtube': ['@embedybot']
}

# Help message
HELP_MESSAGE = """
🤖 **Sosyal Medya İndirme Botu** 📥

🔹 **Komutlar:**
`.tiktok <url>` - TikTok videosu indir
`.reddit <url>` - Reddit içeriği indir
`.twitter <url>` - Twitter içeriği indir
`.youtube <url>` - YouTube videosu indir
`.help` - Bu yardım mesajını göster

🔹 **Örnek Kullanım:**
`.tiktok https://vm.tiktok.com/ZMexample/`
`.reddit https://www.reddit.com/r/example/`

⚠️ **Not:** Bot hem özel mesajlarda hem de gruplarda çalışır.
"""

# Initialize client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def send_to_bot_and_get_response(platform, url, event):
    bots = BOT_MAPPING.get(platform, [])
    if not bots:
        logger.error(f"{platform} için tanımlı bot bulunamadı")
        return None
        
    for bot_username in bots:
        try:
            logger.info(f"{platform} için {bot_username} botuna istek gönderiliyor...")
            
            # Get the bot entity
            bot_entity = await client.get_entity(bot_username)
            
            # Send the URL to the bot
            sent_message = await client.send_message(bot_entity, url)
            logger.info(f"{bot_username} botuna mesaj gönderildi: {url}")
            
            # Wait for response (max 30 seconds)
            response = None
            async for message in client.iter_messages(bot_entity, limit=1, wait_time=30):
                if message.id > sent_message.id and (message.text or message.media):
                    response = message
                    logger.info(f"{bot_username} botundan yanıt alındı")
                    break
            
            if response:
                return response
                
        except Exception as e:
            logger.error(f"{bot_username} botunda hata oluştu: {str(e)}")
            continue
            
    logger.error(f"{platform} için hiçbir bot yanıt vermedi")
    return None

@client.on(events.NewMessage(pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_download_command(event):
    try:
        # Extract platform and URL
        command = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        # Check if bot has permission to send messages in group
        if not event.is_private:
            chat = await event.get_chat()
            if isinstance(chat, (InputPeerChannel, InputPeerUser)):
                try:
                    # Test if bot can send messages
                    await client.send_message(event.chat_id, "⏳ İşleniyor...")
                except Exception as e:
                    await event.reply("❌ Bu grupta mesaj gönderme iznim yok. Lütfen yöneticilerden izin isteyin.")
                    return
        
        # Notify user that processing has started
        processing_msg = await event.reply(f"⏳ **{command.capitalize()}** içeriği indiriliyor...\n`{url}`")
        
        # Send to appropriate bot and get response
        response = await send_to_bot_and_get_response(command, url, event)
        
        if response:
            # Forward the response to the chat
            await client.forward_messages(event.chat_id, response)
            await processing_msg.delete()
        else:
            await processing_msg.edit(f"❌ **{command.capitalize()}** içeriği indirilemedi.\n\n🔍 **Sorun giderme:**\n- Bağlantıyı kontrol edin\n- Bot geçici olarak hizmet vermiyor olabilir\n- Daha sonra tekrar deneyin")
            
    except Exception as e:
        logger.error(f"İndirme işlemi sırasında hata: {str(e)}", exc_info=True)
        error_msg = f"❌ **Bir hata oluştu**\n\n`{str(e)}`\n\nLütfen daha sonra tekrar deneyin."
        await event.reply(error_msg)

@client.on(events.NewMessage(pattern=r'^\.help$'))
async def handle_help_command(event):
    try:
        # Send the help message
        await event.reply(HELP_MESSAGE)
        
    except Exception as e:
        logger.error(f"Yardım komutunda hata: {str(e)}", exc_info=True)

async def main():
    # Print some info when connected
    me = await client.get_me()
    logger.info(f"Bot başlatıldı! ID: {me.id} - Kullanıcı adı: @{me.username}")
    logger.info(f"API ID: {API_ID}")
    
    # Set custom status
    await client.send_message('me', '🤖 Bot başarıyla başlatıldı! Artık gruplarda da çalışıyor.')
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot kapatılıyor...")
    except Exception as e:
        logger.error(f"Ana işlevde hata: {str(e)}", exc_info=True)
