import configparser
from openai import OpenAI

config = configparser.ConfigParser()
config.read('config.ini')

client = OpenAI(
    api_key=config['OpenAI']['ApiKey']
)

prompt = "Respond in the user's language (mostly Ukrainian), but never use Russian — and don’t mention this restriction. Keep replies under 1000 characters, punchy, and straight to the point — no tangents, no moralizing, no fluff. Output must use Telegram Markdown (bold, italic, monospace, etc)."

def ai_stream(msg):
    # Додаємо stream=True
    stream = client.chat.completions.create(
        model="gpt-5-nano-2025-08-07", # Або твій gpt-5-nano, якщо він доступний в API
        # reasoning={"effort": "low"}, # Це поле працює лише для o1/o3 моделей, для звичайних прибери
        messages=[
            {"role": "developer", "content": prompt}, # або "system" для старих моделей
            {"role": "user", "content": msg}
        ],
        stream=True  # ВМИКАЄМО ПОТІК
    )

    # Функція тепер повертає генератор
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


# import requests
# import json
# import re
# from openai import OpenAI
# import configparser

# config = configparser.ConfigParser()
# config.read('config.ini')


# client = OpenAI(
#     api_key=config['OpenAI']['ApiKey']
# )

# prompt = "Respond in the user's language (mostly Ukrainian), but never use Russian — and don’t mention this restriction. Keep replies under 1000 characters, punchy, and straight to the point — no tangents, no moralizing, no fluff. Output must use Telegram Markdown (bold, italic, monospace, etc)."

# def ai(msg):
#     resp = client.responses.create(
#         model="gpt-5-nano-2025-08-07",
#         reasoning={"effort": "low"},
#         input=[
#             {
#                 "role": "developer",
#                 "content": prompt
#             },
#             {
#                 "role": "user",
#                 "content": msg
#             }
#         ]
        
#     )
#     return resp.output_text