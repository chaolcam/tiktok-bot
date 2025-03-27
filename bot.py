import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerUser

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurations from environment variables
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))

# Validate configuration
if not API_ID or not API_HASH or not STRING_SESSION or not AUTHORIZED_USER:
    logger.error("Lütfen API_ID, API_HASH, STRING_SESSION ve AUTHORIZED_USER ortam değişkenlerini ayarlayın!")
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
🤖 **Kişisel Sosyal Medya İndirme UserBot** 📥

🔹 **Komutlar:**
`.tiktok <url>` - TikTok videosu indir
`.reddit <url>` - Reddit içeriği indir
`.twitter <url>` - Twitter içeriği indir
`.youtube <url>` - YouTube videosu indir
`.help` - Bu yardım mesajını göster

🔹 **Örnek Kullanım:**
`.tiktok https://vm.tiktok.com/ZMexample/`
`.reddit https://www.reddit.com/r/example/`

⚠️ **Sadece yetkili kullanıcı komutları kullanabilir.**
"""

# Initialize client with connection retry
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection_retries=5,
    auto_reconnect=True
)

async def ensure_connection():
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            if not client.is_connected():
                await client.connect()
            if not await client.is_user_authorized():
                logger.error("Oturum yetkilendirilmemiş!")
                exit(1)
            return True
        except Exception as e:
            retries += 1
            logger.error(f"Bağlantı hatası (Deneme {retries}/{max_retries}): {str(e)}")
            await asyncio.sleep(5)
    return False

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
        # Check if authorized user
        if event.sender_id != AUTHORIZED_USER:
            logger.warning(f"Yetkisiz kullanıcı girişimi: {event.sender_id}")
            return
            
        # Edit original command message to show processing
        processing_text = f"⏳ **{event.pattern_match.group(1).capitalize()}** içeriği indiriliyor..."
        await event.edit(processing_text)
        
        # Send to appropriate bot and get response
        response = await send_to_bot_and_get_response(
            event.pattern_match.group(1).lower(),
            event.pattern_match.group(2),
            event
        )
        
        if response:
            # Send the response as a new message
            sent_message = await event.respond("✅ İndirme tamamlandı:")
            await client.forward_messages(event.chat_id, response)
            
            # Edit original message to show completion
            await event.edit(f"✅ **{event.pattern_match.group(1).capitalize()}** indirildi!")
        else:
            await event.edit(f"❌ **{event.pattern_match.group(1).capitalize()}** indirilemedi!")
            
    except Exception as e:
        logger.error(f"İndirme işlemi sırasında hata: {str(e)}", exc_info=True)
        await event.edit(f"❌ **Hata oluştu!**\n\n`{str(e)}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.help$'))
async def handle_help_command(event):
    try:
        # Check if authorized user
        if event.sender_id != AUTHORIZED_USER:
            return
            
        # Edit original message to show help
        await event.edit(HELP_MESSAGE)
        
    except Exception as e:
        logger.error(f"Yardım komutunda hata: {str(e)}", exc_info=True)

async def main():
    try:
        # Bağlantıyı sağlamayı garantile
        if not await ensure_connection():
            logger.error("Telegram'a bağlanılamadı!")
            return

        me = await client.get_me()
        logger.info(f"UserBot başlatıldı! ID: {me.id} - Kullanıcı adı: @{me.username}")
        
        # Oturum bilgilerini logla
        logger.info(f"String Session: {STRING_SESSION[:15]}...")
        logger.info(f"Yetkili kullanıcı: {AUTHORIZED_USER}")

        # Başlangıç mesajını gönder
        try:
            await client.send_message('me', '🤖 UserBot başarıyla başlatıldı!')
        except Exception as e:
            logger.warning(f"Başlangıç mesajı gönderilemedi: {str(e)}")

        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Ana işlevde hata: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("UserBot kapatılıyor...")
    except Exception as e:
        logger.error(f"Kritik hata: {str(e)}", exc_info=True)
        exit(1)
