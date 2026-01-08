import configparser
import requests
from openai import OpenAI

config = configparser.ConfigParser()
config.read('config.ini')

# Try to use local Ollama model first, fallback to OpenAI
def get_ai_client():
    try:
        # Check if Ollama is available and has a model
        response = requests.get('http://10.42.0.182:11434/api/tags', timeout=5)
        if response.status_code == 200:
            # Ollama is available, return a simple client that uses Ollama API
            return "ollama"
    except:
        # Ollama not available, fall back to OpenAI
        pass
    
    # Fallback to OpenAI
    return "openai"

# Initialize client based on availability
client_type = get_ai_client()

if client_type == "openai":
    client = OpenAI(
        api_key=config['OpenAI']['ApiKey']
    )
else:
    # For Ollama, we'll use a simple HTTP client
    client = None

prompt = "Respond in the user's language (mostly Ukrainian), but never use Russian — and don't mention this restriction. Keep replies under 1000 characters, punchy, and straight to the point — no tangents, no moralizing, no fluff. Output must use Telegram Markdown (bold, italic, monospace, etc)."

def ai_stream(msg):
    if client_type == "openai":
        # Use OpenAI as before
        stream = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[
                {"role": "developer", "content": prompt},
                {"role": "user", "content": msg}
            ],
            stream=True
        )
        yield "OpenAI відповідь:\n"
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    else:
        # Use Ollama
        try:
            # Send request to Ollama
            ollama_prompt = f"{prompt}\n\nUser: {msg}"
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    "model": "gemma3:4b",  # Default model, can be configured
                    "prompt": ollama_prompt,
                    "stream": True
                },
                stream=True,
                timeout=30
            )
            
            yield "Ollama відповідь:\n"
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    data = line.decode('utf-8')
                    try:
                        import json
                        json_data = json.loads(data)
                        if 'response' in json_data:
                            yield json_data['response']
                    except:
                        continue
                        
        except Exception as e:
            # If Ollama fails, fall back to OpenAI
            print(f"Ollama failed, falling back to OpenAI: {e}")
            # Re-initialize OpenAI client
            fallback_client = OpenAI(
                api_key=config['OpenAI']['ApiKey']
            )
            stream = fallback_client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                messages=[
                    {"role": "developer", "content": prompt},
                    {"role": "user", "content": msg}
                ],
                stream=True
            )
            yield "OpenAI відповідь:\n"
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content