import os
import telebot
from telebot.types import InputMediaPhoto, InputMediaVideo
import re
from downloader import downloader
from downloader import speechtotext
from downloader import ai
from quote import generate_telegram_message
import json
from asyncio import run
from downloader import x
import configparser
import time

config = configparser.ConfigParser()
config.read('config.ini')

BOT_TOKEN = config['Telegram']['Token']
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

def is_twitter_link(msg):
    if not msg.text: return False
    return "x.com/" in msg.text or "twitter.com/" in msg.text

def is_media_link(message):
    if not message.text: return False
    text = message.text.lower()
    return "tiktok.com/" in text or "instagram.com/reel" in text or "x.com/" in text or "twitter.com/" in text


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
    
    caption = f"👤 <b>{data['author']}</b>:\n\n{data['text']}"
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
                bot.send_video(message.chat.id, link, caption=caption, parse_mode="HTML", reply_to_message_id=message.message_id)
            else:
                bot.send_photo(message.chat.id, link, caption=caption, parse_mode="HTML", reply_to_message_id=message.message_id)
        
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
            
            bot.send_media_group(message.chat.id, media_group, reply_to_message_id=message.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"Не вдалося відправити медіа: {e}")


@bot.message_handler(func=is_media_link)
def handle_tiktok(message):
    try:
        words = message.text.split()
        target_domains = ["tiktok.com", "instagram.com", "x.com", "twitter.com"]
        url = next((w for w in words if any(d in w for d in target_domains)), None)

        if not url: return

        status_msg = bot.reply_to(message, "🔄 Завантажую тікток/рілз...")
        print(message.text)
        data = downloader.download_video_local(url)
        
        
        if data.get("error"):
            bot.edit_message_text(f"Помилка: {data['error']}", chat_id=message.chat.id, message_id=status_msg.message_id)
            return

        try:
            file_path = data['file_path']
            caption = f"👤 <b>{data['author']}</b>\n📝 {data['caption']}"
            
            if len(caption) > 1024:
                caption = caption[:1000] + "..."
            with open(file_path, 'rb') as video_file:
                bot.send_video(
                    message.chat.id, 
                    video_file, 
                    caption=caption, 
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id
                )
                
        except Exception as e:
            bot.edit_message_text(f"Не вдалося відправити: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)
            
        finally:
            bot.delete_message(message.chat.id, status_msg.message_id)
            if data.get('file_path'):
                downloader.cleanup_file(data['file_path'])
    except Exception as e:
        print(e)
        if status_msg:
            bot.edit_message_text(f"Щось пішло не так. Спробуй ще раз, може спрацює.", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            bot.send_message(chat_id=message.chat.id, reply_to_message_id=message.message_id, text="Щось пішло не так. Спробуй ще раз, може спрацює.")


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

        full_response = ""
        last_update_time = time.time()
        update_interval = 1 

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