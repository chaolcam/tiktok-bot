import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerUser

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurations from environment variables (set these in Heroku config vars)
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
SESSION_NAME = os.environ.get('SESSION_NAME', 'userbot_session')

# Validate configuration
if not API_ID or not API_HASH:
    logger.error("Lütfen API_ID ve API_HASH ortam değişkenlerini ayarlayın!")
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
📚 **Kullanılabilir Komutlar**

`.tiktok <url>` - TikTok videosu indir
`.reddit <url>` - Reddit içeriği indir
`.twitter <url>` - Twitter içeriği indir
`.youtube <url>` - YouTube videosu indir
`.help` - Bu yardım mesajını göster

🔗 **Örnek Kullanım**
`.tiktok https://vm.tiktok.com/ZMexample/`
`.reddit https://www.reddit.com/r/example/`
"""

# Initialize client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

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

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(tiktok|reddit|twitter|youtube)\s+(https?://\S+)$'))
async def handle_download_command(event):
    try:
        # Extract platform and URL
        command = event.pattern_match.group(1).lower()
        url = event.pattern_match.group(2)
        
        # Delete the command message
        await event.delete()
        
        # Notify user that processing has started
        processing_msg = await event.respond(f"⏳ **{command.capitalize()}** içeriği indiriliyor...\n`{url}`")
        
        # Send to appropriate bot and get response
        response = await send_to_bot_and_get_response(command, url, event)
        
        if response:
            # Forward the response to the user
            await client.forward_messages(event.chat_id, response)
            await processing_msg.delete()
        else:
            await processing_msg.edit(f"❌ **{command.capitalize()}** içeriği indirilemedi.\n\n🔍 **Sorun giderme:**\n- Bağlantıyı kontrol edin\n- Bot geçici olarak hizmet vermiyor olabilir\n- Daha sonra tekrar deneyin")
            
    except Exception as e:
        logger.error(f"İndirme işlemi sırasında hata: {str(e)}", exc_info=True)
        error_msg = f"❌ **Bir hata oluştu**\n\n`{str(e)}`\n\nLütfen daha sonra tekrar deneyin."
        await event.respond(error_msg)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help_command(event):
    try:
        # Delete the help command
        await event.delete()
        
        # Send the help message
        await event.respond(HELP_MESSAGE)
        
    except Exception as e:
        logger.error(f"Yardım komutunda hata: {str(e)}", exc_info=True)

async def main():
    # Print some info when connected
    logger.info("UserBot başlatıldı!")
    logger.info(f"API ID: {API_ID}")
    logger.info(f"Session: {SESSION_NAME}")
    
    # Start the client
    await client.start()
    logger.info("Oturum başarıyla başlatıldı!")
    
    # Set custom status
    await client.send_message('me', '🤖 UserBot başarıyla başlatıldı!')
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("UserBot kapatılıyor...")
    except Exception as e:
        logger.error(f"Ana işlevde hata: {str(e)}", exc_info=True)
