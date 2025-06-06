import os

# Telegram API ID'niz (my.telegram.org adresinden alınır)
# Ortam değişkeni olarak ayarlanmazsa varsayılan 0 değerini kullanır.
API_ID = int(os.environ.get("API_ID", 0))

# Telegram API Hash'iniz (my.telegram.org adresinden alınır)
# Ortam değişkeni olarak ayarlanmazsa varsayılan boş dizeyi kullanır.
API_HASH = os.environ.get("API_HASH", "")

# Pyrogram oturum dizeniz. Botunuzun Telegram'a bağlanması için gereklidir.
# Ortam değişkeni olarak ayarlanmazsa varsayılan boş dizeyi kullanır.
STRING_SESSION = os.environ.get("STRING_SESSION", "")
