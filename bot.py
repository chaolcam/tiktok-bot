import os
import sys
import importlib.machinery
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='▸ %(asctime)s ▸ %(levelname)s ▸ %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Ayarlar
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
STRING_SESSION = os.environ.get('STRING_SESSION', '')
AUTHORIZED_USER = int(os.environ.get('AUTHORIZED_USER', 0))

# Plugin klasörü
PLUGIN_DIR = "plugins"
os.makedirs(PLUGIN_DIR, exist_ok=True)

# Plugin veritabanı (restart'ta silinmemesi için)
PLUGIN_DB = os.path.join(PLUGIN_DIR, "plugins.db")

# Bot ayarları
BOT_SETTINGS = {
    'tiktok': {
        'botlar': ['@downloader_tiktok_bot', '@best_tiktok_downloader_bot'],
        'bekleme': 15,
        'yeniden_dene': 8,
        'hata_metni': "Yanlış TikTok Linki",
        'album_bekleme': 2
    },
    'twitter': {
        'botlar': ['@twitterimage_bot', '@embedybot'],
        'bekleme': 20
    }
}

# Yardım mesajı
YARDIM_MESAJI = f"""
✨ <b>Sosyal Medya İndirici + Plugin Yönetici</b> ✨

<code>.tiktok</code> <i>url</i> - TikTok video/albüm indir
<code>.twitter</code> <i>url</i> - Twitter içeriği indir
<code>.yardım</code> - Bu mesajı göster

<b>🔌 Plugin Komutları:</b>
<code>.yükle</code> <i>(yanıt)</i> - .py plugin yükle
<code>.kaldır</code> <i>plugin_adi</i> - Plugin kaldır
<code>.pluginler</code> - Yüklü pluginleri listele

📂 <b>Plugin Klasörü:</b> <code>{PLUGIN_DIR}</code>
⏳ <i>TikTok albümler ~10s, Twitter ~20s</i>
"""

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
client.yardim_mesaji = YARDIM_MESAJI
client.plugin_komutlari = {}

# PLUGİN SİSTEMİ
async def plugin_yukle(plugin_yolu):
    try:
        plugin_adi = os.path.basename(plugin_yolu)[:-3]
        
        # Modül yükleme
        loader = importlib.machinery.SourceFileLoader(plugin_adi, plugin_yolu)
        module = loader.load_module()
        
        if hasattr(module, 'plugin_kaydet'):
            # Plugin bilgilerini al
            plugin_bilgisi = getattr(module, 'PLUGIN_BILGISI', {
                "isim": plugin_adi,
                "komutlar": {}
            })
            
            # Komutları kaydet
            module.plugin_kaydet(client)
            
            # Komut bilgilerini güncelle
            if hasattr(module, 'PLUGIN_BILGISI'):
                for komut, aciklama in plugin_bilgisi["komutlar"].items():
                    client.plugin_komutlari[komut] = aciklama
            
            logger.info(f"✅ Plugin yüklendi: {plugin_adi} | Komutlar: {list(plugin_bilgisi['komutlar'].keys())}")
            return True
        
        logger.error(f"❌ {plugin_adi}: plugin_kaydet fonksiyonu eksik")
        return False
    except Exception as e:
        logger.error(f"❌ Plugin hatası ({plugin_adi}): {str(e)}")
        return False

async def pluginleri_yukle():
    """Başlangıçta tüm pluginleri yükler"""
    if os.path.exists(PLUGIN_DB):
        with open(PLUGIN_DB, 'r') as f:
            yuklenecekler = [line.strip() for line in f.readlines()]
    else:
        yuklenecekler = [f for f in os.listdir(PLUGIN_DIR) if f.endswith('.py')]
    
    yuklenen = 0
    for dosya in yuklenecekler:
        if dosya.endswith('.py'):
            if await plugin_yukle(os.path.join(PLUGIN_DIR, dosya)):
                yuklenen += 1
    
    # Yardım mesajını güncelle
    if client.plugin_komutlari:
        plugin_yardim = "\n\n🔧 <b>Plugin Komutları:</b>\n"
        for komut, aciklama in client.plugin_komutlari.items():
            plugin_yardim += f"<code>{komut}</code> - {aciklama}\n"
        client.yardim_mesaji += plugin_yardim
    
    return yuklenen

# PLUGİN KOMUTLARI
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.yükle$'))
async def plugin_yukle_komut(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    yanit = await event.get_reply_message()
    if not yanit or not yanit.document or not yanit.file.name.endswith('.py'):
        await event.edit("❌ Lütfen bir .py dosyasını yanıtlayın")
        return
    
    plugin_yolu = os.path.join(PLUGIN_DIR, yanit.file.name)
    await yanit.download_media(file=plugin_yolu)
    
    if await plugin_yukle(plugin_yolu):
        with open(PLUGIN_DB, 'a') as f:
            f.write(f"{yanit.file.name}\n")
        
        komutlar = [k for k in client.plugin_komutlari.keys() if k.startswith(f'.{yanit.file.name[:-3]}')]
        await event.edit(
            f"✅ **{yanit.file.name}** yüklendi!\n\n"
            f"🔧 Komutlar: {', '.join(komutlar)}"
        )
    else:
        os.remove(plugin_yolu)
        await event.edit("❌ Plugin yüklenemedi (logları kontrol edin)")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.kaldır\s+(\w+)$'))
async def plugin_kaldir_komut(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugin_adi = event.pattern_match.group(1)
    plugin_yolu = os.path.join(PLUGIN_DIR, f"{plugin_adi}.py")
    
    if os.path.exists(plugin_yolu):
        # Veritabanından sil
        if os.path.exists(PLUGIN_DB):
            with open(PLUGIN_DB, 'r') as f:
                satirlar = f.readlines()
            with open(PLUGIN_DB, 'w') as f:
                for satir in satirlar:
                    if satir.strip() != f"{plugin_adi}.py":
                        f.write(satir)
        
        # Komutları temizle
        for komut in list(client.plugin_komutlari.keys()):
            if komut.startswith(f".{plugin_adi}"):
                del client.plugin_komutlari[komut]
        
        os.remove(plugin_yolu)
        await event.edit(f"✅ **{plugin_adi}** kaldırıldı!")
    else:
        await event.edit(f"❌ Plugin bulunamadı: `{plugin_adi}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.pluginler$'))
async def pluginleri_listele(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    plugin_listesi = []
    for dosya in os.listdir(PLUGIN_DIR):
        if dosya.endswith('.py'):
            plugin_adi = dosya[:-3]
            komutlar = [
                f"<code>{k}</code>" 
                for k, v in client.plugin_komutlari.items() 
                if k.startswith(f'.{plugin_adi}')
            ]
            
            if komutlar:
                plugin_listesi.append(f"▸ <b>{plugin_adi}</b> ({', '.join(komutlar)})")
            else:
                plugin_listesi.append(f"▸ <b>{plugin_adi}</b> (Komutlar yüklenemedi)")
    
    if plugin_listesi:
        await event.edit(
            "📂 <b>Yüklü Pluginler:</b>\n\n" + "\n".join(plugin_listesi),
            parse_mode='html'
        )
    else:
        await event.edit("❌ Hiç plugin yüklü değil")

# SOSYAL MEDYA FONKSİYONLARI
async def mesajlari_al(bot_entity, ilk_msg_id, bekleme_suresi):
    mesajlar = []
    bitis_zamani = datetime.now().timestamp() + bekleme_suresi
    
    while datetime.now().timestamp() < bitis_zamani:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=ilk_msg_id):
                if msg.id > ilk_msg_id and msg not in mesajlar:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['tiktok', 'twitter']):
                        mesajlar.append(msg)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Mesaj alma hatası: {str(e)}")
            break
    return mesajlar

async def yanit_bekle(bot_entity, msg_id, bekleme_suresi):
    bitis_zamani = datetime.now().timestamp() + bekleme_suresi
    son_msg_id = msg_id
    
    while datetime.now().timestamp() < bitis_zamani:
        try:
            async for msg in client.iter_messages(bot_entity, min_id=son_msg_id, limit=1):
                if msg.id > son_msg_id:
                    if msg.media or any(x in getattr(msg, 'text', '').lower() for x in ['http', 'tiktok', 'twitter']):
                        return msg
                    son_msg_id = msg.id
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"▸ Yanıt bekleme hatası: {str(e)}")
            await asyncio.sleep(1)
    return None

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.tiktok\s+(https?://\S+)$'))
async def tiktok_indir(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    url = event.pattern_match.group(1)
    ayarlar = BOT_SETTINGS['tiktok']
    
    await event.delete()
    logger.info(f"▸ TikTok isteği: {url}")
    
    durum_msg = await event.respond(
        f"🔄 <b>TikTok</b> işleniyor...\n⏳ Tahmini: <code>{ayarlar['bekleme']}s</code>",
        parse_mode='html'
    )
    
    baslangic = datetime.now()
    sonuc = None
    
    for bot_adi in ayarlar['botlar']:
        try:
            bot = await client.get_entity(bot_adi)
            gonderilen_msg = await client.send_message(bot, url)
            
            ilk_yanit = await yanit_bekle(bot, gonderilen_msg.id, ayarlar['bekleme'])
            if not ilk_yanit:
                continue
                
            if ayarlar['hata_metni'] in getattr(ilk_yanit, 'text', ''):
                continue
                
            if hasattr(ilk_yanit, 'grouped_id') or 'album' in getattr(ilk_yanit, 'text', '').lower():
                sonuc = await mesajlari_al(bot, gonderilen_msg.id, ayarlar['bekleme'])
            else:
                sonuc = [ilk_yanit]
            
            if sonuc:
                break
        except Exception as e:
            logger.error(f"▸ TikTok hatası @{bot_adi}: {str(e)}")
            continue
    
    await sonuclari_islet(event, durum_msg, baslangic, sonuc, "TikTok")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.twitter\s+(https?://\S+)$'))
async def twitter_indir(event):
    if event.sender_id != AUTHORIZED_USER:
        return
    
    url = event.pattern_match.group(1)
    ayarlar = BOT_SETTINGS['twitter']
    
    await event.delete()
    logger.info(f"▸ Twitter isteği: {url}")
    
    durum_msg = await event.respond(
        f"🔄 <b>Twitter</b> işleniyor...\n⏳ Tahmini: <code>{ayarlar['bekleme']}s</code>",
        parse_mode='html'
    )
    
    baslangic = datetime.now()
    sonuc = None
    
    for bot_adi in ayarlar['botlar']:
        try:
            bot = await client.get_entity(bot_adi)
            gonderilen_msg = await client.send_message(bot, url)
            sonuc = [await yanit_bekle(bot, gonderilen_msg.id, ayarlar['bekleme'])]
            
            if sonuc:
                break
        except Exception as e:
            logger.error(f"▸ Twitter hatası @{bot_adi}: {str(e)}")
            continue
    
    await sonuclari_islet(event, durum_msg, baslangic, sonuc, "Twitter")

async def sonuclari_islet(event, durum_msg, baslangic, sonuc, servis_adi):
    gecen_sure = (datetime.now() - baslangic).total_seconds()
    await durum_msg.delete()
    
    if sonuc and any(sonuc):
        benzersiz_sonuclar = []
        gorulenler = set()
        for item in sonuc:
            if item and item.id not in gorulenler:
                benzersiz_sonuclar.append(item)
                gorulenler.add(item.id)
        
        await event.respond(
            f"✅ <b>{servis_adi}</b> başarılı!\n"
            f"📦 <code>{len(benzersiz_sonuclar)}</code> içerik • ⏱️ <code>{gecen_sure:.1f}s</code>",
            parse_mode='html'
        )
        
        for item in benzersiz_sonuclar:
            if item.media:
                await client.send_file(event.chat_id, item.media)
            elif item.text:
                await client.send_message(event.chat_id, item.text)
            await asyncio.sleep(0.5)
    else:
        await event.respond(
            f"❌ <b>{servis_adi}</b> başarısız\n"
            f"⏱️ <code>{gecen_sure:.1f}s</code>",
            parse_mode='html'
        )

# YARDIM KOMUTU
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.yardım$'))
async def yardim_goster(event):
    if event.sender_id == AUTHORIZED_USER:
        await event.delete()
        await event.respond(client.yardim_mesaji, parse_mode='html')

# BAŞLANGIÇ
async def baslat():
    await client.start()
    ben = await client.get_me()
    yuklenen_pluginler = await pluginleri_yukle()
    
    baslangic_mesaji = (
        f"🚀 <b>UserBot Aktif</b>\n"
        f"👤 <code>@{ben.username}</code>\n"
        f"🔌 <b>Pluginler:</b> <code>{yuklenen_pluginler}</code>\n"
        f"📡 <b>Desteklenenler:</b> TikTok, Twitter\n"
        f"🕒 <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await client.send_message('me', baslangic_mesaji, parse_mode='html')
    logger.info(f"▸ Bot başlatıldı ▸ @{ben.username}")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(baslat())
