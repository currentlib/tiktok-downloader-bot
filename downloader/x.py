import requests
from urllib.parse import urlparse

def get_x_post_content(url: str):
    """
    Отримує посилання на x.com або twitter.com
    Повертає словник:
    {
        "text": "Текст поста",
        "media": ["url_video.mp4", "url_photo.jpg"],
        "author": "Нікнейм",
        "error": None
    }
    """
    try:
        # 1. Парсимо URL, щоб отримати шлях
        parsed = urlparse(url)
        
        # Перевіряємо, чи це справді твіттер
        if "twitter.com" not in parsed.netloc and "x.com" not in parsed.netloc:
            return {"error": "Це не посилання на X/Twitter"}

        # 2. Формуємо запит до API vxTwitter
        # Логіка проста: міняємо x.com на api.vxtwitter.com
        # Це поверне нам чистий JSON замість HTML сайту
        api_url = f"https://api.vxtwitter.com{parsed.path}"

        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            return {"error": f"Не вдалося отримати дані. Код: {response.status_code}"}

        data = response.json()

        # 3. Витягуємо дані
        text = data.get("text", "")
        author = data.get("user_name", "Unknown")
        
        # Збираємо медіа (фото та відео)
        media_urls = []
        
        # vxTwitter зазвичай повертає список media_extended або media_urls
        if "media_extended" in data:
            for item in data["media_extended"]:
                if item.get("type") == "image":
                    media_urls.append(item.get("url"))
                elif item.get("type") == "video":
                    media_urls.append(item.get("url"))
        elif "media_urls" in data:
            media_urls = data["media_urls"]

        return {
            "text": text,
            "media": media_urls,
            "author": author,
            "error": None
        }

    except Exception as e:
        return {"error": f"Сталася помилка: {str(e)}"}

# --- Приклад використання ---

if __name__ == "__main__":
    # Тестове посилання (візьми будь-яке реальне посилання з X)
    test_link = "https://x.com/SpaceX/status/18342777777777" 
    # Примітка: підстав сюди існуюче посилання для тесту

    # Або ось реальний приклад (якщо пост ще існує на момент запуску)
    # Наприклад, твіт Ілона Маска або новина
    test_link = "https://x.com/censor_net/status/2008920955138023479?s=20" 

    result = get_x_post_content(test_link)

    if result.get("error"):
        print(f"Помилка: {result['error']}")
    else:
        print(f"👤 Автор: {result['author']}")
        print(f"📄 Текст: {result['text']}")
        print(f"🎞 Медіа ({len(result['media'])}):")
        for m in result['media']:
            print(f" - {m}")