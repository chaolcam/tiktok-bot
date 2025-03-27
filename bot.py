from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os

# Config değişkenlerini al
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")  # String session kullanıyoruz

bot_mapping = {
    'tiktok': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
    'reddit': ['@reddit_download_bot'],
    'twitter': ['@twitterimage_bot', '@embedybot'],
    'youtube': ['@embedybot']
}

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(pattern=r'^\.start$', incoming=True, outgoing=False))
async def start_handler(event):
    help_text = """
    🤖 **UserBot Komut Listesi:**
    
    📌 `.tiktok <link>` - TikTok videosu indirir.
    📌 `.reddit <link>` - Reddit gönderisini indirir.
    📌 `.twitter <link>` - Twitter videosu indirir.
    📌 `.youtube <link>` - YouTube videosu indirir.
    
    🚀 Komutu kullanarak ilgili içeriği indirebilirsiniz.
    """
    await event.reply(help_text)

@client.on(events.NewMessage(pattern=r'^\.(tiktok|reddit|twitter|youtube) (.+)', incoming=True, outgoing=False))
async def handler(event):
    platform, link = event.pattern_match.groups()
    bot_list = bot_mapping.get(platform, [])
    
    await event.reply(f"⏳ **{platform.capitalize()} içeriği indiriliyor...**")
    
    for bot in bot_list:
        try:
            msg = await client.send_message(bot, link)
            response = await client.get_response(bot)
            await event.reply(response.message)
            return
        except:
            continue
    
    await event.reply(f"⚠️ **{platform.capitalize()} için uygun bir bot bulunamadı veya yanıt alınamadı.**")

print("🚀 Bot çalışıyor... Telegram'dan .start yazarak komutları görebilirsiniz.")
client.connect()
client.run_until_disconnected()
