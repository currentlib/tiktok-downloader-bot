import os
import telebot
from urllib.parse import urlparse
from tiktok_module import downloader
from datetime import datetime

BOT_TOKEN = "1010362276:AAHKtRyn5B9RY71Kvrd4HEVfoiI92Y8Xp7I"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: "https://vm.tiktok.com" in message.text)
def echo_all(message):
    try:
        urls = [urlparse(url).geturl() for url in message.text.split() if urlparse(url).scheme]
        dl = downloader.tiktok_downloader()
        now = datetime.now()
        videoName = "video" + now.strftime("%m%d%Y%H%M%S") + ".mp4"
        print(videoName)
        dl.musicaldown(url=urls[0], output_name=str(videoName))
        bot.send_video(chat_id=message.chat.id, reply_to_message_id=message.message_id, video=open(videoName, 'rb'), supports_streaming=True)
        if os.path.exists(videoName):
            os.remove(videoName)
        else:
            print("The file does not exist") 
    except Exception as e:
        print(e)
        bot.send_message(chat_id=message.chat.id, reply_to_message_id=message.message_id, text="Щось пішло не так. Спробуй ще раз, може спрацює.")

bot.infinity_polling()