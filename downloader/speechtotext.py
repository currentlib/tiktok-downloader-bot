import configparser
from openai import OpenAI
import os

config = configparser.ConfigParser()
config.read('config.ini')

client = OpenAI(
    api_key=config['OpenAI']['SpeechKey']
)

def voice(filepath):
    """
    Відправляє аудіофайл в OpenAI Whisper і повертає текст.
    """

    with open(filepath, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
        )

    return transcription.text