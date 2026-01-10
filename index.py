import os
import telebot
from telebot.types import InputMediaPhoto, InputMediaVideo
from downloader import downloader
from downloader import speechtotext
from downloader import ai
from quote import generate_telegram_message
from downloader import x
import configparser
import time
from downloader import stats
from telebot import apihelper

config = configparser.ConfigParser()
config.read('config.ini')

apihelper.ENABLE_MIDDLEWARE = True

BOT_TOKEN = config['Telegram']['Token']
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

stats.register_stats_handlers(bot)

def is_twitter_link(msg):
    if not msg.text: return False
    return "x.com/" in msg.text or "twitter.com/" in msg.text

def is_media_link(message):
    if not message.text: return False
    text = message.text.lower() 
    return "tiktok.com/" in text or "instagram.com/" in text or "x.com/" in text or "twitter.com/" in text or "youtube.com/shorts" in text


def download_avatar(bot, user_id, save_path):
    try:
        user_profile_photos = bot.get_user_profile_photos(user_id) 
        if user_profile_photos.total_count > 0:
            file_id = user_profile_photos.photos[0][-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error downloading avatar: {e}")
        return False


@bot.message_handler(func=is_twitter_link)
def handle_twitter(message):
    words = message.text.split()
    url = next((w for w in words if "x.com/" in w or "twitter.com/" in w), None)

    if not url: return

    status_msg = bot.reply_to(message, "🔄 Завантажую твіт...")

    data = x.get_x_post_content(url)

    if data.get("error"):
        bot.edit_message_text(f"Помилка: {data['error']}", chat_id=message.chat.id, message_id=status_msg.message_id)
        return
    caption = data.get('caption', '')
    if len(caption) > 800:
        caption = caption[:800] + "..."
    caption = f"👤 <b>{data['author']}</b>:\n\n{caption}"
    bot.delete_message(message.chat.id, status_msg.message_id)
    try:
        media_files = data['media']
        
        if len(media_files) == 0:
            # Тільки текст
            bot.reply_to(message, caption, parse_mode="HTML")
            
        elif len(media_files) == 1:
            # Одне фото або відео
            link = media_files[0]
            if ".mp4" in link:
                bot.send_video(message.chat.id, link, caption=caption, parse_mode="HTML", reply_to_message_id=message.message_id, timeout=120, supports_streaming=True)
            else:
                bot.send_photo(message.chat.id, link, caption=caption, parse_mode="HTML", reply_to_message_id=message.message_id, timeout=120)
        
        else:
            # Група медіа (альбом)
            media_group = []
            for i, link in enumerate(media_files):
                # Підпис додаємо тільки до першого елемента групи
                cap = caption if i == 0 else ""
                
                if ".mp4" in link:
                    media_group.append(InputMediaVideo(link, caption=cap, parse_mode="HTML"))
                else:
                    media_group.append(InputMediaPhoto(link, caption=cap, parse_mode="HTML"))
            
            bot.send_media_group(message.chat.id, media_group, reply_to_message_id=message.message_id, timeout=120)

    except Exception as e:
        bot.send_message(message.chat.id, f"Не вдалося відправити медіа: {e}")


@bot.message_handler(func=is_media_link)
def handle_media(message):
    status_msg = None
    max_retries = config.getint('Downloader', 'max_retries', fallback=3)
    try:
        words = message.text.split()
        target_domains = ["tiktok.com", "instagram.com", "youtube.com"]
        url = next((w for w in words if any(d in w for d in target_domains)), None)

        if not url: return
        is_instagram = "instagram.com" in url
    except Exception:
        return

    for attempt in range(max_retries):
        folder_to_cleanup = None
        file_to_cleanup = None
        final_path = None
        was_compressed = False

        try:
            if status_msg is None:
                status_msg = bot.reply_to(message, "🔄 Завантажую ...")
                print(f"Start: {message.text}")
            else:
                try:
                    bot.edit_message_text(f"🔄 Спроба {attempt + 1} з {max_retries}...", chat_id=message.chat.id, message_id=status_msg.message_id)
                except Exception: pass

            if is_instagram:
                data = downloader.download_instagram_post(url)
                folder_to_cleanup = data.get('folder_to_delete')
            else:
                data = downloader.download_video_local(url)
                if data.get('type') == 'video':
                    file_to_cleanup = data.get('file_path')

            if data.get("error"):
                print(f"Помилка завантаження: {data['error']}")
                raise Exception(data['error'])

            user = message.from_user
            display_name = f"@{user.username}" if user.username else user.first_name

            if data['type'] == "video":
                file_path = data['file_path']
                final_path = file_path # За замовчуванням відправляємо оригінал

                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > 49: # Лишаємо 1 МБ запасу
                    def progress_updater(progress_text):
                        try:
                            bot.edit_message_text(
                                f"🐘 Стискаю відео...\n{progress_text}", 
                                chat_id=message.chat.id, 
                                message_id=status_msg.message_id
                            )
                        except Exception:
                            pass # Ігноруємо помилки (якщо текст не змінився)
                    time.sleep(1) # Невелика пауза, щоб користувач встиг побачити повідомлення
                    bot.edit_message_text(f"🐘 Відео велике ({int(file_size_mb)} MB). Стискаю...", chat_id=message.chat.id, message_id=status_msg.message_id)
                
                    compressed_path = downloader.compress_video(
                        file_path, 
                        total_duration=data.get('duration', 0), 
                        progress_callback=progress_updater
                    )
                
                    if compressed_path:
                        final_path = compressed_path
                        was_compressed = True
                    
                    # Перевіряємо розмір після стиснення
                        new_size = os.path.getsize(final_path) / (1024 * 1024)
                        if new_size > 49:
                            raise Exception("Файл завеликий навіть після стиснення (>50MB).")
                    else:
                        raise Exception("Не вдалося стиснути відео.")
                
                bot.edit_message_text("⬆️ Відправляю...", chat_id=message.chat.id, message_id=status_msg.message_id)


                file_path = data['file_path']
                caption = data.get('caption', '')
                if len(caption) > 800:
                    caption = caption[:800] + "..."
                caption = f"<b>{display_name}</b> -- <a href='{url}'>🔗</a>\n<blockquote expandable>📝 {caption}\n</blockquote>"
            
                with open(final_path, 'rb') as video_file:
                    bot.send_video(
                        message.chat.id, 
                        video_file, 
                        caption=caption,
                        timeout=120,
                        parse_mode="HTML",
                        supports_streaming=True
                    )

            elif data['type'] == "photo":
                bot.edit_message_text("📸 Відправляю фото...", chat_id=message.chat.id, message_id=status_msg.message_id)
                images = data['media_group']
                caption = data.get('caption', '')
                if len(caption) > 800:
                    caption = caption[:800] + "..."
                caption = f"<b>{display_name}</b> -- <a href='{url}'>🔗</a>\n<blockquote expandable>📝 {caption}\n</blockquote>"
            
                # Розбиваємо на групи по 10
                chunk_size = 10
                for i in range(0, len(images), chunk_size):
                    chunk = images[i:i + chunk_size]
                    media_group = []
                    opened_files = []
                    try:
                        for index, img_path in enumerate(chunk):
                            cap = caption if i == 0 and index == 0 else ""
                            file_handler = open(img_path, 'rb')
                            opened_files.append(file_handler) # Запам'ятовуємо, щоб потім закрити
                            media_group.append(InputMediaPhoto(file_handler, caption=cap, parse_mode="HTML"))
                        
                        bot.send_media_group(message.chat.id, media_group, reply_to_message_id=message.message_id)
                        bot.delete_message(message.chat.id, message.message_id)
                    finally:
                        for f in opened_files:
                            f.close()

            # Видаляємо статус
            if status_msg: bot.delete_message(message.chat.id, status_msg.message_id)
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
            
            # Чистка
            if is_instagram and folder_to_cleanup: downloader.cleanup_insta_folder(folder_to_cleanup)
            if file_to_cleanup and os.path.exists(file_to_cleanup): os.remove(file_to_cleanup)
            if was_compressed and final_path and os.path.exists(final_path): os.remove(final_path)
        
            return # ВИХІД З ФУНКЦІЇ ПРИ УСПІХУ

        except Exception as e:
            print(f"Спроба {attempt + 1} провалилась: {e}")
            # Обов'язкова чистка при помилці
            # 1. Обов'язкова чистка "сміття" від невдалої спроби
            if is_instagram and folder_to_cleanup: downloader.cleanup_insta_folder(folder_to_cleanup)
            elif file_to_cleanup and os.path.exists(file_to_cleanup): os.remove(file_to_cleanup)
            if was_compressed and final_path and os.path.exists(final_path): os.remove(final_path)

            # 2. Перевірка чи це остання спроба
            if attempt == max_retries - 1:
                # Все пропало
                err_text = f"❌ Не вдалося після {max_retries} спроб.\nПомилка: {e}"
                if status_msg:
                    bot.edit_message_text(err_text, chat_id=message.chat.id, message_id=status_msg.message_id)
                else:
                    bot.send_message(message.chat.id, err_text, reply_to_message_id=message.message_id)
            else:
                # Чекаємо перед наступною спробою
                time.sleep(3) 
                continue # Йдемо на наступну ітерацію циклу

@bot.message_handler(content_types=['voice'])
def process_audio(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = f"voice_{message.from_user.id}.ogg"
        with open(filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        status_msg = bot.reply_to(message, "🎧 Слухаю та розшифровую...")

        full_text = speechtotext.voice(filename)

        if not full_text:
            bot.edit_message_text("Не вдалося розчути.", chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        words = full_text.split()
        current_text = ""
        last_update_time = time.time()
        chunk_size = 3
        
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i+chunk_size]
            current_text += " " + " ".join(chunk)
            
            if time.time() - last_update_time > 0.8:
                try:
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=status_msg.message_id,
                        text=f"🗣 {current_text} ▌"
                    )
                    last_update_time = time.time()
                except Exception:
                    pass
            time.sleep(0.1)

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"🗣 {full_text}"
        )
    except Exception as e:
        print(e)
        if status_msg:
            bot.edit_message_text("Помилка обробки аудіо.", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            bot.send_message(chat_id=message.chat.id, reply_to_message_id=message.message_id, text="Щось пішло не так. Спробуй ще раз, може спрацює.")


@bot.message_handler(func=lambda message: "@grok" in message.text)
def handle_grok(message):
    try:
        user_input = str(message.text).replace("@grok", "").strip()
        if message.reply_to_message:
            user_input += f": {message.reply_to_message.text}"

        if not user_input:
            bot.reply_to(message, "Напиши щось після @grok")
            return

        sent_message = bot.send_message(
            chat_id=message.chat.id, 
            reply_to_message_id=message.message_id, 
            text="⏳ Думаю ..."
        )
        time.sleep(1.5)  # Невелика пауза, щоб користувач встиг побачити повідомлення
        full_response = ""
        last_update_time = time.time()
        update_interval = 1.5  # Оновлюємо повідомлення не частіше ніж раз на 1.5 секунди

        for chunk in ai.ai_stream(user_input):
            full_response += chunk

            if time.time() - last_update_time > update_interval:
                try:
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=sent_message.message_id,
                        text=full_response + " ▌",
                        parse_mode="Markdown" 
                    )
                    last_update_time = time.time()
                except Exception:
                    pass
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=sent_message.message_id,
            text=full_response,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(message.chat.id, f"Щось пішло не так: {e}")


@bot.message_handler(commands=['quote'])
def handle_quote_command(message):
    if message.reply_to_message:
        original_message = message.reply_to_message
        original_text = original_message.text
        original_user_id = original_message.from_user.id
        original_username = original_message.from_user.first_name
        download_avatar(bot, original_user_id, "profile_pic.jpg")
        generate_telegram_message(original_username, original_text, "profile_pic.jpg", "quote.png")
        with open("quote.png", 'rb') as sticker_file:
            bot.send_sticker(
                chat_id=message.chat.id, 
                sticker=sticker_file,
                reply_to_message_id=message.message_id
            )
        
    else:
        bot.reply_to(message, "Please use this command in reply to another message.")

bot.polling()

bot.infinity_polling()