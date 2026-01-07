import instaloader
from instaloader import Post
import requests
# from pybalt import download
from asyncio import run

import yt_dlp
import os
import uuid

import subprocess

def compress_video(input_path):
    """
    Стискає відео, використовуючи ffmpeg.
    Повертає шлях до нового файлу або None, якщо не вийшло.
    """
    output_path = f"{os.path.splitext(input_path)[0]}_compressed.mp4"
    
    # CRF 28 - це баланс між якістю і розміром (чим більше число, тим гірша якість і менший розмір)
    # preset fast - щоб не чекати вічність
    command = [
        'ffmpeg', 
        '-i', input_path, 
        '-vcodec', 'libx264', 
        '-crf', '30', 
        '-preset', 'fast', 
        '-acodec', 'aac', # Перекодуємо аудіо в aac (стандарт для mp4)
        output_path
    ]
    
    try:
        # Запускаємо ffmpeg, приховуючи вивід, щоб не смітив у логи
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"Помилка стиснення: {e}")
        return None


def instagram_download(id):
    L = instaloader.Instaloader()
    post = Post.from_shortcode(L.context, id)
    url = post.video_url
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open('video.mp4', 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)


def download_video_local(url: str):
    """
    Скачує відео локально за допомогою yt-dlp.
    Повертає словник з шляхом до файлу та описом.
    """
    # Генеруємо унікальне ім'я файлу, щоб уникнути конфліктів при одночасному скачуванні
    filename = f"download_{uuid.uuid4().hex}"
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Найкраща якість
        'outtmpl': f'{filename}.%(ext)s',     # Шаблон імені файлу
        'quiet': True,                         # Менше сміття в логах
        'noplaylist': True,                    # Тільки одне відео, не плейлист
        'merge_output_format': 'mp4',          # Завжди намагатися робити mp4
        
        # Для TikTok/Insta іноді потрібні хедери, yt-dlp зазвичай справляється,
        # але іноді краще додати user-agent (опціонально)
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Отримуємо інфо (щоб знати автора і опис)
            info = ydl.extract_info(url, download=True) # download=True зразу качає
            
            # Отримуємо шлях до скачаного файлу
            # yt-dlp може змінити розширення, тому шукаємо файл
            downloaded_file = ydl.prepare_filename(info)
            
            # Якщо було merge (відео+аудіо), файл може мати .mp4, а prepare повертає .webm
            # Перевіряємо фактичний файл
            base, ext = os.path.splitext(downloaded_file)
            if not os.path.exists(downloaded_file) and os.path.exists(base + ".mp4"):
                downloaded_file = base + ".mp4"

            full_desc = info.get('description') or info.get('title') or "Без опису"
            author = info.get('uploader') or info.get('uploader_id') or 'Unknown'
            return {
                "type": "video",
                "file_path": downloaded_file,
                "caption": full_desc,
                "author": author,
                "error": None
            }

    except Exception as e:
        return {"error": str(e)}

def cleanup_file(path):
    """Видаляє файл після відправки"""
    if os.path.exists(path):
        os.remove(path)