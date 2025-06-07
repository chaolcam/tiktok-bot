from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo
import os
import asyncio
import re # Düzenli ifadeler (regex) için eklendi
import glob
import shutil
import yt_dlp
from config import API_ID, API_HASH, STRING_SESSION # config.py'den import edildi

# DEBUG: Bot başlatılmadan önce API bilgilerini loglara yazdır
print(f"DEBUG: Uygulama Başlatılıyor. Kullanılan API_ID: {API_ID}")
print(f"DEBUG: Kullanılan API_HASH: {API_HASH[:5]}... (Gizlilik nedeniyle ilk 5 karakter)")
print(f"DEBUG: STRING_SESSION var mı?: {bool(STRING_SESSION)}") # String session'ın boş olup olmadığını kontrol eder

# Global Client object is created.
# "tiktok_downloader_bot" is used as the session name. This name is arbitrary.
# API ID, API Hash, and String Session are retrieved from config.py and used to connect to Telegram.
# KOMUT ÖN EKİ TANIMI BURADAN KALDIRILDI VE MANUEL OLARAK REGEX FİLTRELEMEYE GEÇİLDİ.
app = Client(
    "tiktok_downloader_bot", # Oturum ismi
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
)

# Define a temporary folder for media downloads.
# This folder must be writable in the Heroku environment.
DOWNLOAD_DIR = "downloads"

# Create the temporary download folder if it doesn't exist.
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------------------------------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
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
# Telegram Komutları
# ----------------------------------------------------------------------------------------------------

# filters.text: Herhangi bir metin mesajını algılar.
# filters.me: Sadece botun kendi gönderdiği mesajları dinler (userbot olduğu için).
# Bu işleyici, botun kendi gönderdiği tüm metin mesajlarını yakalayacaktır.
@app.on_message(filters.text & filters.me)
async def command_handler(client, message):
    """
    Botun kendi gönderdiği tüm metin mesajlarını işler.
    Belirtilen komut desenlerini (regex) manuel olarak kontrol eder.
    """
    message_text = message.text.strip() # Mesaj metnini alır ve baş/son boşlukları temizler.

    # '.başla' komutunu kontrol et
    # r'^\.başla$' regex'i:
    # ^ : Satırın başlangıcı
    # \. : Nokta karakteri (özel karakter olduğu için kaçış karakteri ile belirtilir)
    # başla : Tam olarak "başla" metni
    # $ : Satırın sonu
    # Bu, sadece ".başla" olan mesajları algılar, başında veya sonunda başka bir şey olmayan.
    if re.match(r"^\.başla$", message_text, re.IGNORECASE): # re.IGNORECASE büyük/küçük harf duyarlılığını kapatır
        print(f"DEBUG: '.başla' komutu manuel olarak regex ile algılandı. Mesaj ID: {message.id}, Gonderen: {message.from_user.id}") 
        await message.edit_text( # Kullanıcının kendi mesajını düzenler
            "Merhaba! Ben bir **TikTok indirici userbot**'uyum. "
            "Bana bir TikTok linki göndererek medya indirmemi sağlayabilirsin.\n\n"
            "**Kullanım:**\n"
            "`  .tiktok <TikTok Linki>`\n"
            "**Örnek:**\n"
            "`  .tiktok https://www.tiktok.com/@username/video/1234567890`\n\n"
            "Unutma, videolar filigransız indirilecektir. Çoklu medya (carousel) gönderilerinde "
            "resimler 10'lu gruplar halinde, videolar ise tek tek gönderilecektir."
        )
    # '.tiktok <link>' komutunu kontrol et
    # r"^\.tiktok\s+(.+)$" regex'i:
    # ^ : Satırın başlangıcı
    # \.tiktok : ".tiktok" metni
    # \s+ : Bir veya daha fazla boşluk karakteri (komut ile link arasında boşluk olmalı)
    # (.+) : Boşluklardan sonraki tüm karakterleri yakalar (link kısmı)
    # $ : Satırın sonu
    elif re_match_tiktok := re.match(r"^\.tiktok\s+(.+)$", message_text, re.IGNORECASE):
        tiktok_link = re_match_tiktok.group(1) # Yakalanan link grubunu alır
        print(f"DEBUG: '.tiktok' komutu manuel olarak regex ile algılandı. Mesaj ID: {message.id}, Gonderen: {message.from_user.id}, Link: {tiktok_link}") 

        # Kullanıcının mesajını indirme işleminin başladığını belirtmek için düzenler.
        status_message = await message.edit_text("`TikTok medyasını indiriyorum, lütfen bekleyin... ⌛`")

        # Önceki indirmelerden kalan dosyaları temizle.
        await clean_download_directory()

        try:
            # yt-dlp kütüphanesini kullanarak TikTok medyasını indir.
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
                'noprogress': True, 
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"DEBUG: İndirme başlatılıyor: {tiktok_link}") 
                info_dict = ydl.extract_info(tiktok_link, download=True) 
                print(f"DEBUG: İndirme tamamlandı. Toplam öğe: {len(info_dict.get('entries', [])) if 'entries' in info_dict else 1}") 

            photos = []
            videos = []
            
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        photos.append(file_path)
                    elif filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                        videos.append(file_path)
            print(f"DEBUG: Bulunan fotoğraflar: {len(photos)}, videolar: {len(videos)}") 

            media_to_send_photos = [InputMediaPhoto(photo_path) for photo_path in photos]

            if media_to_send_photos:
                await status_message.edit_text("`Resimleri gönderiyorum... 🖼️`")
                for i in range(0, len(media_to_send_photos), 10):
                    batch = media_to_send_photos[i : i + 10]
                    if batch:
                        try:
                            await client.send_media_group(message.chat.id, batch)
                            await asyncio.sleep(1) 
                        except Exception as e:
                            print(f"Hata: Medya grubu gönderilirken hata oluştu: {e}")
                            await client.send_message(message.chat.id, f"`Resim grubunu gönderirken bir hata oluştu: {e}`")

            if videos:
                await status_message.edit_text("`Videoları gönderiyorum... 🎬`")
                for video_file_path in videos:
                    try:
                        await client.send_video(message.chat.id, video_file_path)
                        await asyncio.sleep(1) 
                    except Exception as e:
                        print(f"Hata: Video gönderilirken hata oluştu: {e}")
                        await client.send_message(message.chat.id, f"`Videoyu gönderirken bir hata oluştu: {e}`")

            await status_message.edit_text("`Medya başarıyla gönderildi! İşlem tamamlandı. ✅`")

        except yt_dlp.utils.DownloadError as e:
            error_message = f"TikTok medyasını indirirken bir hata oluştu: `{e}`"
            print(error_message)
            await status_message.edit_text(error_message)
        except Exception as e:
            error_message = f"Beklenmeyen bir hata oluştu: `{e}`"
            print(error_message)
            await status_message.edit_text(error_message)
        finally:
            await clean_download_directory()

# ----------------------------------------------------------------------------------------------------
# Botu Başlatma Ana Fonksiyonu
# ----------------------------------------------------------------------------------------------------

async def main():
    """
    Botun ana başlangıç ve yaşam döngüsü fonksiyonu.
    Botu başlatır, Telegram'a bağlanır ve aktif kalmasını sağlar.
    """
    print("Bot başlatılıyor... (Telegram'a bağlanılıyor)")
    try:
        await app.start() # Pyrogram istemcisini başlat ve Telegram'a bağlan
        
        # Bağlantı başarılı olduğunda bu mesajı loglara yazdır ve kendi hesabınıza gönder
        print("INFO: Bot başarıyla Telegram'a bağlandı ve hazır! Userbotunuz artık komutları dinliyor.")
        try:
            # Kendi hesabınıza başlangıç mesajı göndermek için 'me' kullanın
            # Bu mesaj botun gerçekten başladığının görsel bir teyidi olacaktır.
            await app.send_message("me", "Userbot başarıyla başlatıldı ve aktif!")
        except Exception as e:
            print(f"Hata: Başlangıç mesajı gönderilemedi (muhtemelen 'me' ile ilgili sorun): {e}")

        await asyncio.Future() # Sonsuz bir döngüde botu aktif tutar.
        
    except Exception as e:
        # Botun başlangıcında veya çalışma sırasında oluşan kritik hataları yakalar ve loglar.
        print(f"KRİTİK HATA: Bot başlatılırken veya çalışırken beklenmeyen bir hata oluştu: {e}")

if __name__ == "__main__":
    asyncio.run(main())
