from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
import os
import asyncio
import re
import glob
import shutil
import yt_dlp

# Global Client object is created.
# "tiktok_downloader_bot" is used as the session name. This name is arbitrary.
# API ID, API Hash, and String Session are retrieved from config.py and used to connect to Telegram.
app = Client(
    "tiktok_downloader_bot", # Session name
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

# Define a temporary folder for media downloads.
# This folder must be writable in the Heroku environment.
DOWNLOAD_DIR = "downloads"

# Create the temporary download folder if it doesn't exist.
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------------------------------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------------------------------

async def clean_download_directory():
    """
    Cleans the download directory. Deletes residual files from previous downloads.
    This is important for optimizing disk space usage on Heroku.
    """
    for file_path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path) # Delete the file
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path) # Delete the directory and its contents
        except Exception as e:
            print(f"Error: Could not delete temporary file/folder '{file_path}'. Reason: {e}")

# ----------------------------------------------------------------------------------------------------
# Telegram Commands
# ----------------------------------------------------------------------------------------------------

@app.on_message(filters.command("başla") & filters.me)
async def start_command(client, message):
    """
    Runs when the '.başla' command is detected. Informs the user about the bot's function.
    filters.me: Listens only to messages sent by the bot itself.
    """
    await message.edit_text(
        "Merhaba! Ben bir **TikTok indirici userbot**'uyum. "
        "Bana bir TikTok linki göndererek medya indirmemi sağlayabilirsin.\n\n"
        "**Kullanım:**\n"
        "`  .tiktok <TikTok Linki>`\n"
        "**Örnek:**\n"
        "`  .tiktok https://www.tiktok.com/@username/video/1234567890`\n\n"
        "Unutma, videolar filigransız indirilecektir. Çoklu medya (carousel) gönderilerinde "
        "resimler 10'lu gruplar halinde, videolar ise tek tek gönderilecektir."
    )

@app.on_message(filters.command("tiktok") & filters.me)
async def download_tiktok_media(client, message):
    """
    When the '.tiktok <link>' command is detected, it downloads TikTok media and sends it to Telegram.
    """
    # Check if a link is provided after the command.
    if len(message.text.split()) < 2:
        await message.edit_text("`Lütfen .tiktok komutundan sonra bir TikTok linki girin.`")
        return

    # Extract the TikTok link from the message.
    tiktok_link = message.text.split(" ", 1)[1] 

    # Send a message indicating the start of the download process.
    # This message will be updated with status changes.
    status_message = await message.edit_text("`TikTok medyasını indiriyorum, lütfen bekleyin... ⌛`")

    # Clean up residual files from previous downloads.
    await clean_download_directory()

    try:
        # Use the yt-dlp library to download TikTok media.
        # This handles watermark removal and multiple media (carousel) scenarios.
        
        # Define options for yt-dlp.
        # 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        #   - Prefers the best quality MP4 video and M4A audio formats.
        #   - If this combination is not available, it uses the best MP4 format.
        # 'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_%(playlist_index)s.%(ext)s')
        #   - Output file name template. '%(id)s' represents the video ID, '%(playlist_index)s' 
        #     represents the item order for carousel posts, and '%(ext)s' is the file extension.
        #     This ensures unique names for multiple media files.
        # 'noplaylist': False
        #   - Does not disable playlists (like carousel posts on TikTok).
        #     This allows downloading of posts containing multiple photos or videos.
        # 'ignoreerrors': True
        #   - Ensures the program continues even if a download error occurs for one item.
        # Other options (writedescription, writesubtitles, writethumbnail) are set to false
        #   - Prevents downloading unnecessary side files.
        # Watermark removal is generally the default behavior of yt-dlp for TikTok.
        # No specific postprocessor might be needed for it.
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', 
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s_%(playlist_index)s.%(ext)s'), 
            'writedescription': False, 
            'writesubtitles': False,   
            'writethumbnail': False,   
            'noplaylist': False,       
            'retries': 3,              
            'ignoreerrors': True,      
            'fragment_retries': 3,     
            'noprogress': True, # Do not print download progress to console (to avoid cluttering Heroku logs)
        }

        # Start the download process.
        # A yt_dlp.YoutubeDL() object is created, and its `extract_info` method is used
        # to fetch information and download the media.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_link, download=True) 

        # Categorize downloaded files (photos or videos).
        photos = []
        videos = []
        
        # Iterate through all files in the DOWNLOAD_DIR.
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                # Categorize as photo or video based on file extension.
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')): # GIF can also be added
                    photos.append(file_path)
                elif filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                    videos.append(file_path)

        # Create InputMediaPhoto objects for sending to Telegram.
        # Photos will be sent in batches of 10.
        media_to_send_photos = [InputMediaPhoto(photo_path) for photo_path in photos]

        # Send photos in batches of 10.
        if media_to_send_photos:
            await status_message.edit_text("`Resimleri gönderiyorum... 🖼️`")
            # Loop to send media groups.
            for i in range(0, len(media_to_send_photos), 10):
                batch = media_to_send_photos[i : i + 10]
                if batch:
                    try:
                        await client.send_media_group(message.chat.id, batch)
                        await asyncio.sleep(1) # Short delay to avoid hitting Telegram API limits
                    except Exception as e:
                        print(f"Error while sending media group: {e}")
                        await client.send_message(message.chat.id, f"`Resim grubunu gönderirken bir hata oluştu: {e}`")

        # Send videos one by one.
        # Since send_media_group often doesn't work well with videos, we send them separately.
        if videos:
            await status_message.edit_text("`Videoları gönderiyorum... 🎬`")
            # Loop to send each video individually.
            for video_file_path in videos:
                try:
                    await client.send_video(message.chat.id, video_file_path)
                    await asyncio.sleep(1) # Short delay to avoid hitting Telegram API limits
                except Exception as e:
                    print(f"Error while sending video: {e}")
                    await client.send_message(message.chat.id, f"`Videoyu gönderirken bir hata oluştu: {e}`")

        await status_message.edit_text("`Medya başarıyla gönderildi! İşlem tamamlandı. ✅`")

    except yt_dlp.utils.DownloadError as e:
        # Catch download errors specifically from yt-dlp.
        error_message = f"TikTok medyasını indirirken bir hata oluştu: `{e}`"
        print(error_message)
        await status_message.edit_text(error_message)
    except Exception as e:
        # Catch all other potential errors (file operations, Pyrogram errors, etc.).
        error_message = f"Beklenmeyen bir hata oluştu: `{e}`"
        print(error_message)
        await status_message.edit_text(error_message)
    finally:
        # Clean up downloaded files after every operation.
        # This is crucial for minimizing disk space usage on Heroku.
        await clean_download_directory()

# Start the bot. This command connects the bot to Telegram and starts listening for messages.
print("Bot başlatılıyor...")
app.run()
