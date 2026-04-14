# test.py

from ollama import chat

response = chat(
    model="gemma4:latest",
    messages=[{"role": "user", "content": "Say hello"}]
)

print(response.message.content)