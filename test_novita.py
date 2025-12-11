# Quick test script for Novita AI
from openai import OpenAI

# Replace with your actual API key or set NOVITA_API_KEY env var
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("NOVITA_API_KEY", "your_novita_api_key_here")

client = OpenAI(
    base_url="https://api.novita.ai/v3/openai",
    api_key=api_key
)

print("Testing Novita AI with moonshotai/kimi-k2-thinking...")

try:
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-thinking",
        messages=[
            {"role": "user", "content": "Whatsup"}
        ],
        max_tokens=100
    )
    print("✓ Success!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"✗ Error: {e}")

