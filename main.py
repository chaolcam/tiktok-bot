def download_tiktok_media(url):
    api_url = f"https://ssstik.io/api?url={url}"
    response = requests.get(api_url)
    print(f"API Yanıtı: {response.json()}")  # API yanıtını konsola yazdır
    if response.status_code == 200:
        data = response.json()
        video_url = data.get('video', {}).get('url')
        image_urls = data.get('images', [])
        return video_url, image_urls
    return None, None
